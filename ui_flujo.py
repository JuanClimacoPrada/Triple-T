"""Interfaz del Sprint 5; el estado y las transiciones viven en experiencia/."""
from dataclasses import replace
from decimal import Decimal as D
import os
import streamlit as st
from dominio.modelos import Configuracion, VERSION_REGLAS
from conversacion.gestor import decir, recibir, confirmar_accion, invalidar, crear_escenario, actual, generar_informe, aclarar_ingreso
from experiencia.flujo import siguiente, iniciar, diferir, confirmar_revision, faltan
from experiencia.preguntas import TITULOS, ETIQUETAS, legible
from experiencia.ambientes import entorno, ia_permitida, AVISO_DEMO
from experiencia.evidencia import pendientes_documentales
from experiencia.tarjetas import comparacion, avisos_evaluacion
from experiencia.ayuda_ia import responder, estado_asistente
from ia.politicas import EstadoIA, ERRORES
from ia.proveedor import configuracion, diagnostico_sdk
from ui_documentos import mostrar_documentos
from ui_resultados import mostrar_resultado
from ui_estrategia import mostrar_estrategia
from casos import CASOS
from ui_riesgo import mostrar_riesgo
from ui_alternativas import mostrar_alternativas, mostrar_resumen_alternativas, mostrar_seleccion, mostrar_puntuaciones
from ui_chat import editor_costos, editor_anotaciones
from servicios.costos import diagnostico_tcea
from servicios.alternativas import interpretar_saldo
from triple_t_pro_layout import (construir_vm, sentinel_config, load_styles, hero_html,
    message_html, steps_html, section_title, render_dashboard_area, sentinel_link_html)

TAB_POR_VISTA = {"ALTERNATIVAS": "Alternativas", "SIMULAR": "Simular", "DETALLE": "Detalle",
                 "GRAFICO": "Gráficos", "PDF": "Informe", "COSTOS": "Detalle"}


def abrir_pestana(c):
    if c.vista in TAB_POR_VISTA:
        st.session_state.pestana_analisis = TAB_POR_VISTA[c.vista]


def cambiar_pestana(c):
    if c.vista in TAB_POR_VISTA and TAB_POR_VISTA[c.vista] != st.session_state.pestana_analisis:
        c.vista = "RESUMEN"


def enviar(texto, *, desde_chat=False):
    c = st.session_state.conversacion
    vista_anterior = c.vista
    if desde_chat:
        responder(c, texto, st.session_state.ia, configuracion(st.secrets), permitido=ia_permitida(st.secrets))
    else:
        recibir(c, texto)
    if c.vista != vista_anterior:
        abrir_pestana(c)


def accion(nombre):
    c = st.session_state.conversacion
    f = c.flujo
    if nombre == "INICIAR":
        iniciar(c)
    elif nombre == "SIMULACION":
        iniciar(c, True)
    elif nombre == "CONTINUAR":
        st.session_state.navegacion = "ANALISIS"
        f.iniciado = True
        f.revision_confirmada = f.ia_revision = None
        f.diferidos.clear()
        f.objetivo = "EVALUACION"
        c.vista = "RESUMEN"
        decir(c, siguiente(c))
    elif nombre == "CALCULAR":
        confirmar_revision(c)
    elif nombre in ("NO_SE", "DESPUES", "SOLICITAR"):
        diferir(c, "SOLICITAR" if nombre == "SOLICITAR" else "PENDIENTE")
    elif nombre in ("BOLETAS", "OTRO_INGRESO", "PATRIMONIO"):
        st.session_state.navegacion = "ANALISIS"
        c.vista = {"BOLETAS": "EVIDENCIAS", "OTRO_INGRESO": "OTRO_INGRESO", "PATRIMONIO": "PATRIMONIO"}[nombre]
        f.ia_revision = None
    elif nombre == "FIN_DOCUMENTOS":
        if c.vista == "PATRIMONIO":
            f.patrimonio_documentos = "REVISADO"
        else:
            f.ingresos_documentos = "REVISADO"
        c.vista = "RESUMEN"
        decir(c, siguiente(c))
    elif nombre in ("PROPIEDAD_SI", "PROPIEDAD_NO", "PROPIEDAD_DESCONOCIDO"):
        f.propiedad = nombre.removeprefix("PROPIEDAD_")
        if f.propiedad == "SI":
            c.expediente = replace(c.expediente, patrimonio="Bien declarado; sin verificación externa")
            invalidar(c)
            c.vista = "PATRIMONIO"
        else:
            decir(c, siguiente(c))
    elif nombre in ("ALTERNATIVAS", "COSTOS", "DETALLE"):
        st.session_state.navegacion = "ANALISIS"
        c.vista = nombre
        abrir_pestana(c)
    elif nombre == "EXPEDIENTE":
        navegar("EXPEDIENTE")
    elif nombre == "INDICADORES":
        st.session_state.pestana_analisis = "Indicadores"
    elif nombre == "ACLARAR_INGRESO":
        st.session_state.navegacion = "ANALISIS"
        st.session_state.mostrar_aclaracion = True
    elif nombre == "PDF":
        try:
            generar_informe(c)
        except ValueError as error:
            decir(c, str(error))


def boton(etiqueta, nombre, **kwargs):
    st.button(etiqueta, on_click=accion, args=(nombre,), **kwargs)


def resumen(c, incluir_pendientes=True):
    filas = []
    fuentes = dict(c.expediente.origen_campos)
    for campo, etiqueta in ETIQUETAS.items():
        valor = getattr(c.expediente, campo)
        pendiente = valor is None or valor in ("DESCONOCIDO", "SIN_ACLARAR")
        if pendiente and not incluir_pendientes:
            continue
        fuente = "Pendiente" if pendiente else "Declarado" if campo in fuentes else "Condición de demostración"
        filas.append({"Dato": etiqueta, "Valor": legible(valor), "Fuente": fuente})
    return filas


def navegar(pagina):
    st.session_state.navegacion = pagina


def barra_lateral(c):
    with st.sidebar:
        st.markdown('<div class="tt-side-brand">Triple<span>-T</span></div>', unsafe_allow_html=True)
        destinos = [("Análisis crediticio", "ANALISIS", "analytics"), ("Expediente", "EXPEDIENTE", "folder_open"),
                    ("Historial de cambios", "HISTORIAL", "history"), ("Configuración", "CONFIGURACION", "settings")]
        if os.environ.get("TRIPLE_T_HERRAMIENTAS_DEV", "").lower() == "true":
            destinos.append(("Desarrollo", "DESARROLLO", "science"))
        for etiqueta, pagina, icono in destinos:
            st.button(etiqueta, key="nav_" + pagina, icon=f":material/{icono}:", width="stretch",
                      type="primary" if st.session_state.get("navegacion", "ANALISIS") == pagina else "secondary",
                      on_click=navegar, args=(pagina,))
        st.markdown('<div class="tt-side-label">Mi evaluación</div>', unsafe_allow_html=True)
        st.caption(TITULOS[c.flujo.etapa])
        st.button("Nueva evaluación", icon=":material/add:", on_click=enviar, args=("reiniciar",))


def configuracion_academica(c):
    section_title("Criterios académicos", "scale")
    with st.form("configuracion_guiada"):
        umbral = st.number_input("Umbral DTI de demostración (%)", 0., 100., float(c.config.umbral_dti * 100))
        dif = st.number_input("Tolerancia de discrepancia documental (%)", 0., 100., float(c.config.discrepancia * 100))
        tope = st.number_input("Tope técnico TEA (%)", 0., 10000., float(c.config.tea_maxima))
        if st.form_submit_button("Guardar criterios"):
            nueva = Configuracion(D(str(umbral))/100, D(str(dif))/100, D(str(tope)))
            if nueva != c.config:
                c.config = nueva
                invalidar(c)
                st.rerun()
            st.caption("Los criterios ya están guardados.")


def herramientas_dev(c, vm, pedir_caso):
    section_title("Herramientas de desarrollo")
    st.caption("Material sintético para verificar el prototipo.")
    casos, riesgo, estrategia = st.tabs(["Casos sintéticos", "Probabilidad ilustrativa", "Comparación tecnológica"])
    with casos, st.container(horizontal=True):
        for nombre in CASOS:
            st.button("Cargar caso " + nombre.lower(), key="caso_" + nombre, on_click=pedir_caso, args=(nombre,))
    with riesgo:
        mostrar_riesgo(c, vm, detalle=True)
    with estrategia:
        mostrar_estrategia()


def opciones(c):
    # Flujo horizontal nativo: las sugerencias saltan de línea en pantallas estrechas.
    with st.container(horizontal=True, gap="xsmall", key="tt_suggestions"):
        opciones_contextuales(c)


def opciones_contextuales(c):
    f = c.flujo
    if c.pendiente:
        return
    if not f.iniciado:
        boton("Iniciar evaluación", "INICIAR", type="primary")
        boton("Simular un préstamo", "SIMULACION")
        if c.expediente.monto is not None:
            boton("Continuar expediente", "CONTINUAR")
        return
    campo = c.campo_preguntado
    if campo:
        if campo == "descuento_planilla":
            st.button("Sí, todas descontadas", on_click=enviar, args=("ya están descontadas",))
            st.button("No están descontadas", on_click=enviar, args=("no están descontadas",))
        if campo == "historial":
            st.button("Sin mora declarada", on_click=enviar, args=("sin mora",))
            st.button("Sin historial suficiente", on_click=enviar, args=("sin historial",))
        boton("No sé", "NO_SE")
        boton("Agregar después", "DESPUES")
        st.button("¿Por qué necesitas ese dato?", on_click=enviar, args=("¿Por qué necesitas ese dato?",))
    elif f.etapa == "EVIDENCIA_INGRESOS" and c.vista not in ("EVIDENCIAS", "OTRO_INGRESO"):
        boton("Subir boletas", "BOLETAS", type="primary")
        boton("Otro respaldo", "OTRO_INGRESO")
        boton("No dispongo por ahora", "DESPUES")
        boton("Solicitar al cliente", "SOLICITAR")
    elif f.etapa == "EVIDENCIA_PATRIMONIO" and c.vista != "PATRIMONIO":
        if f.propiedad is None:
            boton("Sí, hay un bien", "PROPIEDAD_SI")
            boton("No declara bienes", "PROPIEDAD_NO")
            boton("Desconocido", "PROPIEDAD_DESCONOCIDO")
        else:
            boton("Presentar documento del bien", "PATRIMONIO")
            boton("Agregar después", "DESPUES")


def revisar(c):
    st.subheader("Revisa antes de calcular")
    st.dataframe(resumen(c), hide_index=True, use_container_width=True)
    for mensaje in pendientes_documentales(c):
        st.caption(mensaje)
    boton("Confirmar y calcular", "CALCULAR", type="primary")
    boton("Editar datos pendientes", "CONTINUAR")
    st.caption("Para corregir un valor puedes escribir «ingreso 3500» o abrir la edición manual. Los valores existentes requieren confirmación.")
    if st.button("Dejar revisión pendiente"):
        decir(c, "La revisión queda pendiente. Puedes regresar cuando tengas la información; no se confirma automáticamente.")
        st.rerun()


def simulador(c):
    exp, _ = actual(c)
    with st.form("simulador_guiado"):
        monto = st.number_input("Monto del escenario (S/)", min_value=.01, value=float(exp.monto))
        meses = st.number_input("Plazo del escenario (meses)", min_value=1, max_value=360, value=exp.meses)
        tea = st.number_input("TEA del escenario (%)", min_value=0., max_value=float(c.config.tea_maxima), value=float(exp.tea))
        caida = st.number_input("Caída de ingresos supuesta (%)", min_value=0., max_value=100., value=float(c.parametros_escenario.get("caida", 0)))
        if st.form_submit_button("Calcular escenario sin cambiar la base"):
            try:
                crear_escenario(c, {"monto": D(str(monto)), "meses": meses, "tea": D(str(tea)), "caida": D(str(caida))})
                st.rerun()
            except ValueError as error:
                st.warning(str(error))


def cambiar_consentimiento():
    ia = st.session_state.ia
    permitido = ia_permitida(st.secrets)
    ia.consentimiento = bool(st.session_state.consentimiento_gemini and permitido)
    ia.habilitado = ia.consentimiento


def panel_ia():
    ia = st.session_state.ia
    cfg = configuracion(st.secrets)
    permitido = ia_permitida(st.secrets)
    section_title("Asistente conversacional", "bot")
    st.caption("Con tu consentimiento, Google recibe consultas ficticias filtradas y los indicadores necesarios. El nivel gratuito puede usar el contenido para mejorar sus productos. Los documentos, transcripciones y notas se procesan dentro de Triple-T.")
    st.checkbox("Consiento el envío de consultas de demostración", key="consentimiento_gemini",
                value=ia.consentimiento, disabled=not permitido, on_change=cambiar_consentimiento)
    st.caption(estado_asistente(ia, cfg, permitido=permitido))
    if permitido and cfg.pendientes:
        st.caption("Configuración del servidor pendiente: " + ", ".join(cfg.pendientes))
    elif permitido and (problema_sdk := diagnostico_sdk()) and problema_sdk != ia.ultimo_error:
        st.info(ERRORES[problema_sdk])
    if ia.ultimo_error:
        st.info(ERRORES.get(ia.ultimo_error, ERRORES["CONEXION"]))
    if ia.circuito_abierto and ia.consentimiento and permitido and cfg.disponible and ia.llamadas < 20:
        if st.button("Volver a habilitar la conexión"):
            ia.circuito_abierto = False
            ia.habilitado = True
            ia.ultimo_error = ""
            st.rerun()
    st.caption(f"Consultas externas en esta sesión: {ia.llamadas}/20.")


ACCIONES_AVISO = {
    "CONTINUAR": "Completar datos del análisis", "ACLARAR_INGRESO": "Aclarar fuente de ingresos",
    "BOLETAS": "Revisar boletas", "ALTERNATIVAS": "Comparar alternativas", "EXPEDIENTE": "Revisar expediente",
    "OTRO_INGRESO": "Revisar otros respaldos", "PATRIMONIO": "Revisar patrimonio",
}


def mostrar_avisos(c, r, *, resumen=False):
    avisos = avisos_evaluacion(c, r)
    if not avisos:
        return
    section_title("Qué conviene revisar" if resumen else "Alertas financieras y documentales", "file")
    mostrados = avisos[:2] if resumen else avisos
    acciones = set()
    for indice, (titulo, descripcion, ruta) in enumerate(mostrados):
        with st.container(border=True):
            st.markdown(f"**{titulo}**")
            st.text(descripcion)
            if ruta and ruta not in acciones:
                boton(ACCIONES_AVISO[ruta], ruta, key=f"aviso_{resumen}_{indice}")
                acciones.add(ruta)
    if resumen and len(avisos) > len(mostrados):
        boton("Ver todas las alertas", "INDICADORES")


def mostrar_tcea(exp, resultado):
    pendientes = diagnostico_tcea(exp, resultado)
    if resultado.tcea is not None and not pendientes:
        return
    with st.container(border=True, key="tt_tcea_notice"):
        st.markdown("**TCEA pendiente**")
        for pendiente in pendientes:
            st.text(pendiente)
        boton("Completar costos y fechas", "COSTOS", key="costos_tcea")


def resultados(c, seccion):
    exp, r = actual(c)
    if r is None:
        return
    if seccion == "Resumen":
        st.write(interpretar_saldo(r))
        mostrar_avisos(c, r, resumen=True)
        mostrar_resumen_alternativas(c)
        mostrar_seleccion(c)
    elif seccion == "Indicadores":
        st.write(interpretar_saldo(r))
        mostrar_tcea(exp, r)
        mostrar_avisos(c, r)
        mostrar_puntuaciones(c)
    elif seccion == "Detalle":
        if c.vista == "COSTOS":
            boton("Volver al detalle del caso", "DETALLE")
            editor_costos(c)
        else:
            section_title("Cronograma y supuestos")
            boton("Completar costos y fechas", "COSTOS", key="costos_detalle")
            mostrar_resultado(r, base=c.resultado if c.escenario else None, mostrar_alertas=False)
            st.caption(f"Reglas {VERSION_REGLAS} · Fecha {exp.fecha} · Sistema francés con TEA fija. Las cifras se redondean para su presentación.")
            with st.expander("Supuestos del cálculo"):
                for supuesto in r.supuestos:
                    st.caption(supuesto)
    elif seccion == "Simular":
        if "cuota_base" in r.cifras:
            simulador(c)
            if c.escenario:
                st.dataframe(comparacion(c.resultado, c.resultado_escenario), hide_index=True, width="stretch")
        else:
            st.info("Completa monto, plazo y TEA antes de crear escenarios financieros.")
            boton("Completar condiciones", "CONTINUAR", key="completar_simular")
    elif seccion == "Informe":
        mostrar_seleccion(c, "informe")
        boton("Preparar informe PDF", "PDF", type="primary")
        if c.informe is not None and c.informe_revision == c.revision and not c.pendiente:
            st.download_button("Descargar informe vigente", c.informe, "triple-t-informe.pdf", "application/pdf")


def mostrar(editor, reiniciar_ui, pedir_caso):
    try:
        entorno(st.secrets)
    except ValueError as error:
        st.error(str(error))
        st.stop()
    if "conversacion" not in st.session_state or st.session_state.conversacion.flujo is None:
        # Migración sin borrar expediente existente al actualizar la aplicación.
        if "conversacion" not in st.session_state:
            reiniciar_ui()
        else:
            from experiencia.flujo import Flujo
            st.session_state.conversacion.flujo = Flujo(iniciado=True)
    if "ia" not in st.session_state:
        st.session_state.ia = EstadoIA()
    c = st.session_state.conversacion
    if not ia_permitida(st.secrets):
        st.session_state.ia.habilitado = st.session_state.ia.consentimiento = False
    siguiente(c)
    load_styles()
    vm = construir_vm(c, sentinel_config(st.secrets))
    st.markdown(hero_html(vm), unsafe_allow_html=True)
    st.caption(AVISO_DEMO)
    if c.pendiente:
        st.session_state.navegacion = "ANALISIS"
    barra_lateral(c)
    pagina = st.session_state.get("navegacion", "ANALISIS")
    if pagina == "EXPEDIENTE":
        with st.container(border=True, key="tt_dossier"):
            section_title("Expediente y evidencias")
            st.dataframe(resumen(c), hide_index=True, width="stretch")
            with st.container(horizontal=True):
                boton("Revisar boletas", "BOLETAS", key="boletas_expediente")
                boton("Otro respaldo", "OTRO_INGRESO", key="otros_expediente")
                if c.flujo.propiedad == "SI":
                    boton("Patrimonio", "PATRIMONIO", key="patrimonio_expediente")
                boton("Completar costos y fechas", "COSTOS", key="costos_expediente")
            editor(c)
            editor_anotaciones(c)
        return
    if pagina == "HISTORIAL":
        section_title("Historial de cambios de la sesión")
        if c.flujo.cambios:
            st.dataframe(c.flujo.cambios, hide_index=True, width="stretch")
        else:
            st.caption("Todavía no hay cambios registrados.")
        return
    if pagina == "CONFIGURACION":
        with st.container(border=True, key="tt_settings"):
            panel_ia()
            st.divider()
            configuracion_academica(c)
        return
    if pagina == "DESARROLLO" and os.environ.get("TRIPLE_T_HERRAMIENTAS_DEV", "").lower() == "true":
        herramientas_dev(c, vm, pedir_caso)
        return
    with st.container(key="tt_workspace"):
        chat, dashboard = st.columns([1, 1.65], gap="medium")
        with chat:
            with st.container(key="tt_chat_panel", border=True):
                section_title("Evaluación guiada", "bot")
                st.caption(estado_asistente(st.session_state.ia, configuracion(st.secrets), permitido=ia_permitida(st.secrets)))
                with st.expander(f"Etapas · {TITULOS[c.flujo.etapa]}", expanded=False):
                    st.markdown(steps_html(vm), unsafe_allow_html=True)
                    st.caption("El panel financiero muestra la revisión vigente; los mensajes anteriores conservan el contexto de su momento.")
                with st.container(height=300, border=False, key="tt_conversation", autoscroll=True):
                    for mensaje in c.mensajes:
                        st.markdown(message_html(mensaje.rol, mensaje.texto), unsafe_allow_html=True)
                texto = st.chat_input("Escribe tu consulta…", key="chat_principal")
                if texto:
                    with st.spinner("Revisando tu consulta…"):
                        enviar(texto, desde_chat=True)
                    st.rerun()
                if c.pendiente:
                    st.info("Confirma la modificación o cancélala para conservar los datos.")
                    if st.button("Confirmar acción"):
                        pendiente = c.pendiente.copy()
                        if pendiente["accion"] == "CASO":
                            reiniciar_ui(pendiente["caso"])
                        elif confirmar_accion(c, True):
                            reiniciar_ui()
                        st.rerun()
                    if st.button("Cancelar acción"):
                        confirmar_accion(c, False)
                        st.rerun()
                if c.vista in ("EVIDENCIAS", "OTRO_INGRESO", "PATRIMONIO"):
                    mostrar_documentos(c, "BOLETA" if c.vista == "EVIDENCIAS" else c.vista)
                    boton("Continuar, conservando pendientes", "FIN_DOCUMENTOS", type="primary")
                else:
                    opciones(c)
                    if c.flujo.etapa == "REVISION_DATOS" and not c.pendiente:
                        revisar(c)
                if st.session_state.get("mostrar_aclaracion") and c.resultado and c.resultado.estado == "DISCREPANCIA PENDIENTE":
                    with st.form("aclaracion_ingresos"):
                        st.caption("Hay diferencias entre ingreso declarado y documental. Elige la fuente y justifica la decisión.")
                        fuente = st.selectbox("Fuente elegida", ["PENDIENTE", "DECLARADO", "DOCUMENTAL"], format_func=lambda x: {"PENDIENTE":"Seleccionar", "DECLARADO":"Ingreso declarado", "DOCUMENTAL":"Promedio de boletas"}[x])
                        nota = st.text_input("Justificación sin datos personales", max_chars=300)
                        if st.form_submit_button("Registrar aclaración"):
                            try:
                                aclarar_ingreso(c, fuente, nota)
                                st.session_state.mostrar_aclaracion = False
                                st.rerun()
                            except ValueError as error:
                                st.warning(str(error))
        with dashboard:
            with st.container(key="tt_dashboard_panel", border=True):
                section_title("Análisis del crédito")
                nombres = ["Resumen", "Alternativas", "Indicadores", "Gráficos", "Detalle", "Simular", "Informe"]
                pestanas = st.tabs(nombres, key="pestana_analisis", on_change=cambiar_pestana, args=(c,))
                confirmado = c.flujo.etapa == "RESULTADOS" and not c.pendiente
                for nombre, pestana in zip(nombres, pestanas):
                    with pestana, st.container(key="panel_" + nombre):
                        if nombre in ("Resumen", "Indicadores", "Gráficos"):
                            render_dashboard_area(vm, nombre)
                        if nombre == "Indicadores" and vm.sentinel_url:
                            st.markdown(sentinel_link_html(vm.sentinel_url), unsafe_allow_html=True)
                        if nombre == "Detalle" and c.vista == "COSTOS" and not confirmado:
                            boton("Volver al detalle del caso", "DETALLE")
                            editor_costos(c)
                        elif confirmado:
                            if nombre == "Alternativas":
                                mostrar_alternativas(c)
                            else:
                                resultados(c, nombre)
                        elif nombre in ("Alternativas", "Detalle", "Simular", "Informe"):
                            st.info("Completa y confirma los datos desde la evaluación guiada para habilitar esta sección.")
                        elif nombre in ("Resumen", "Indicadores") and c.flujo.iniciado:
                            if nombre == "Indicadores":
                                mostrar_tcea(c.expediente, vm.resultado)
                            mostrar_avisos(c, vm.resultado, resumen=nombre == "Resumen")
    if c.vista == "ESTRATEGIA" and os.environ.get("TRIPLE_T_HERRAMIENTAS_DEV", "").lower() == "true":
        mostrar_estrategia()
