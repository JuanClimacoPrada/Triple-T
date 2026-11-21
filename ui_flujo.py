"""Interfaz del Sprint 5; el estado y las transiciones viven en experiencia/."""
from dataclasses import replace
from decimal import Decimal as D
import streamlit as st
from dominio.modelos import Configuracion, VERSION_REGLAS
from conversacion.gestor import decir, recibir, confirmar_accion, invalidar, crear_escenario, actual, generar_informe, aclarar_ingreso
from experiencia.flujo import siguiente, iniciar, diferir, confirmar_revision, faltan
from experiencia.preguntas import TITULOS, ETIQUETAS, legible
from experiencia.ambientes import entorno, ia_permitida, AVISO_DEMO
from experiencia.evidencia import pendientes_documentales
from experiencia.tarjetas import comparacion
from experiencia.ayuda_ia import disponible, responder, hechos, explicar_local, ALERTAS
from ia.politicas import EstadoIA, ERRORES
from ia.proveedor import configuracion
from ui_documentos import mostrar_documentos
from ui_resultados import mostrar_resultado
from ui_estrategia import mostrar_estrategia
from motor import perdida_esperada_ilustrativa
from casos import CASOS
from triple_t_pro_layout import (construir_vm, sentinel_config, load_styles, hero_html,
    message_html, steps_html, section_title, render_dashboard_area)


def enviar(texto):
    c = st.session_state.conversacion
    if c.flujo.ia_revision == c.revision:
        responder(c, texto, st.session_state.ia, configuracion(st.secrets), permitido=ia_permitida(st.secrets))
    else:
        recibir(c, texto)


def accion(nombre):
    c = st.session_state.conversacion
    f = c.flujo
    if nombre == "INICIAR":
        iniciar(c)
    elif nombre == "SIMULACION":
        iniciar(c, True)
    elif nombre == "CONTINUAR":
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
    elif nombre == "SIN_IA":
        f.ia_revision = None
        st.session_state.ia.consentimiento = False
        st.session_state["consentimiento_resultados"] = False
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
    c = st.session_state.conversacion
    if pagina == "SIMULADOR":
        if disponible(c):
            c.vista = "SIMULAR"
        else:
            iniciar(c, True)
    elif pagina == "ANALISIS":
        c.vista = "RESUMEN"
    elif pagina == "EXPEDIENTE":
        c.vista = "RESUMEN"


def barra_lateral(c, editor, pedir_caso):
    with st.sidebar:
        st.markdown('<div class="tt-side-brand">Triple<span>-T</span></div>', unsafe_allow_html=True)
        for label, page, icono in (("Análisis crediticio", "ANALISIS", "analytics"), ("Simulador", "SIMULADOR", "calculate"),
                                  ("Expediente", "EXPEDIENTE", "folder_open"), ("Historial", "HISTORIAL", "history"), ("Ayuda", "AYUDA", "help_outline")):
            st.button(label, key="nav_"+page, icon=f":material/{icono}:", use_container_width=True,
                      type="primary" if st.session_state.get("navegacion", "ANALISIS") == page else "secondary",
                      on_click=navegar, args=(page,))
        st.markdown('<div class="tt-side-label">Mi evaluación</div>', unsafe_allow_html=True)
        st.caption(TITULOS[c.flujo.etapa])
        boton("Continuar paso pendiente", "CONTINUAR", key="continuar_sidebar")
        st.button("Nueva evaluación", on_click=enviar, args=("reiniciar",))
        with st.expander("Resumen del expediente"):
            filas = resumen(c, False)
            if filas:
                st.dataframe(filas, hide_index=True, use_container_width=True)
            else:
                st.caption("Todavía no hay datos registrados.")
        with st.expander("Documentos y evidencia"):
            st.caption(f"{len(c.documentos)} archivos presentados · {sum(e.estado == 'CONFIRMADO' for e in c.expediente.evidencias)} boletas con transcripción confirmada")
            boton("Revisar boletas", "BOLETAS", key="boletas_sidebar")
            boton("Otro respaldo", "OTRO_INGRESO", key="otro_sidebar")
            if c.flujo.propiedad == "SI":
                boton("Patrimonio declarado", "PATRIMONIO", key="patrimonio_sidebar")
        with st.expander("Simulaciones"):
            if disponible(c):
                st.button("Comparar condiciones", on_click=enviar, args=("simular",))
            else:
                boton("Simular un préstamo", "SIMULACION", key="sim_sidebar")
        with st.expander("Historial de cambios de la sesión"):
            if c.flujo.cambios:
                st.dataframe(c.flujo.cambios, hide_index=True)
            else:
                st.caption("Sin cambios todavía. Las correcciones requieren confirmación y pueden cancelarse.")
        # Popover permite alojar los expanders del editor sin expanders anidados.
        with st.popover("Herramientas avanzadas"):
            editor(c)
            with st.form("configuracion_guiada"):
                umbral = st.number_input("Umbral DTI de demostración (%)", 0., 100., float(c.config.umbral_dti * 100))
                dif = st.number_input("Tolerancia de discrepancia documental (%)", 0., 100., float(c.config.discrepancia * 100))
                tope = st.number_input("Tope técnico TEA (%)", 0., 10000., float(c.config.tea_maxima))
                if st.form_submit_button("Aplicar parámetros"):
                    c.config = Configuracion(D(str(umbral))/100, D(str(dif))/100, D(str(tope)))
                    invalidar(c)
                    st.rerun()
            st.caption("Pérdida esperada ilustrativa; no estimación de riesgo")
            pd = st.number_input("PD supuesta (%)", 0., 100., value=None, key="pd")
            lgd = st.number_input("LGD supuesta (%)", 0., 100., value=None, key="lgd")
            if pd is not None and lgd is not None and c.expediente.monto is not None:
                st.write(f"Pérdida ilustrativa: S/ {perdida_esperada_ilustrativa(float(c.expediente.monto), pd, lgd):,.2f}")
            st.button("Comparación estratégica A/B/C", on_click=enviar, args=("compara A, B y C",))
            for nombre in CASOS:
                st.button("Cargar caso " + nombre.lower(), key="caso_" + nombre, on_click=pedir_caso, args=(nombre,))


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


def panel_ia(c):
    if not disponible(c):
        return
    ia = st.session_state.ia
    cfg = configuracion(st.secrets)
    permitido = ia_permitida(st.secrets)
    with st.expander("Preguntar a la IA sobre este análisis", expanded=c.flujo.ia_revision == c.revision):
        st.caption("Opcional. Se envían tu pregunta filtrada y hechos mínimos de esta demostración a Google. El nivel gratuito puede usar los datos para mejorar productos. No se envían documentos, OCR, nombres de archivo, notas ni historial. La IA no edita el expediente.")
        consentimiento = st.checkbox("Consiento esta consulta sobre resultados de demostración", key="consentimiento_resultados")
        if not permitido:
            st.info("La consulta remota está deshabilitada por el responsable. Puedes seguir sin IA.")
        elif cfg.pendientes:
            st.caption("Consulta local disponible. Configuración pendiente: " + ", ".join(cfg.pendientes))
        elif ia.ultimo_error:
            st.caption(ERRORES.get(ia.ultimo_error, ERRORES["CONEXION"]) + " Se utiliza una explicación local.")
        else:
            st.caption("Gemini ya respondió en esta sesión." if ia.respuestas_validas else "Configurado; aún sin respuesta remota en esta sesión.")
        if not consentimiento:
            ia.consentimiento = False
            c.flujo.ia_revision = None
        if st.button("Activar preguntas sobre este análisis", disabled=not consentimiento or not permitido or not cfg.disponible or ia.llamadas >= 20):
            ia.consentimiento = ia.habilitado = True
            ia.circuito_abierto = False
            ia.ultimo_error = ""
            c.flujo.ia_revision = c.revision
            st.rerun()
        boton("Seguir sin IA", "SIN_IA")
        st.caption(f"Consultas remotas: {ia.llamadas}/20. Sin reintentos automáticos.")


def resultados(c):
    exp, r = actual(c)
    if r is None:
        return
    pendientes = faltan(c)
    if pendientes:
        st.caption("Por completar: " + ", ".join(ETIQUETAS[k] for k in pendientes))
        boton("Continuar con los datos pendientes", "CONTINUAR", key="continuar_resultados")
    alertas = sorted(r.reglas, key=lambda a: {"discrepancia":0, "pendiente":1, "relevante":2}.get(a["nivel"], 3))
    if alertas:
        st.warning(ALERTAS.get(alertas[0]["regla"], "Revisa los datos y limitaciones antes de decidir."))
        with st.expander("Ver todas las alertas"):
            for a in alertas:
                st.write(ALERTAS.get(a["regla"], a["mensaje"]))
                if a["regla"] in ("RN-07", "VAL-05/07"):
                    st.caption(a["mensaje"])
    for mensaje in pendientes_documentales(c):
        st.caption(mensaje)
    with st.expander("Ver detalle y evidencias", expanded=c.vista == "DETALLE"):
        mostrar_resultado(r, base=c.resultado if c.escenario else None)
        st.caption("Solo boletas confirmadas con meses únicos alimentan el promedio. Otros respaldos no acreditan ingreso estable.")
        boton("Revisar documentos de ingresos", "BOLETAS", key="documentos_resultados")
    if "cuota_base" in r.cifras:
        with st.expander("Comparar escenario", expanded=c.vista == "SIMULAR"):
            simulador(c)
        if c.escenario:
            st.dataframe(comparacion(c.resultado, c.resultado_escenario), hide_index=True, use_container_width=True)
    with st.expander("Cómo se calculó"):
        st.write("Cuotas mensuales vencidas, sistema francés: TEM = (1 + TEA/100)^(1/12) − 1. A tasa cero, cuota = monto / meses. DTI = servicio mensual de deuda / ingreso admisible.")
        st.caption(f"Reglas: {VERSION_REGLAS} · Fecha: {exp.fecha} · Fuente de cifras: motor Python. Redondeo solo en presentación a dos decimales; saldo interno de alta precisión.")
        for supuesto in r.supuestos:
            st.caption(supuesto)
        st.dataframe(resumen(c), hide_index=True)
    boton("Preparar informe PDF", "PDF")
    if c.informe is not None and c.informe_revision == c.revision and not c.pendiente:
        st.download_button("Descargar informe vigente", c.informe, "triple-t-informe.pdf", "application/pdf")
    panel_ia(c)


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
    if c.flujo.revision_confirmada != c.revision:
        c.flujo.ia_revision = None
        st.session_state.ia.consentimiento = False
        st.session_state["consentimiento_resultados"] = False
    if not ia_permitida(st.secrets):
        c.flujo.ia_revision = None
        st.session_state.ia.consentimiento = False
    siguiente(c)
    load_styles()
    vm = construir_vm(c, sentinel_config(st.secrets))
    st.markdown(hero_html(vm), unsafe_allow_html=True)
    st.caption(AVISO_DEMO)
    barra_lateral(c, editor, pedir_caso)
    with st.container(key="tt_workspace"):
        chat, dashboard = st.columns([1, 1.2], gap="medium")
        with chat:
            with st.container(key="tt_chat_panel", border=True):
                section_title("Evaluación guiada", "bot")
                pagina = st.session_state.get("navegacion", "ANALISIS")
                if pagina == "EXPEDIENTE":
                    st.dataframe(resumen(c), hide_index=True, use_container_width=True)
                elif pagina == "HISTORIAL":
                    st.caption("Cambios de esta sesión; no constituye auditoría bancaria.")
                    if c.flujo.cambios:
                        st.dataframe(c.flujo.cambios, hide_index=True)
                    else:
                        st.caption("Todavía no hay cambios registrados.")
                elif pagina == "AYUDA":
                    st.info("Comienza con un monto, plazo y TEA. Puedes responder varios datos juntos, preguntar por qué se solicitan o agregarlos después. Los documentos se procesan en el servidor, nunca en Gemini. El score externo no está integrado.")
                with st.expander(f"Etapas · {TITULOS[c.flujo.etapa]}", expanded=False):
                    st.markdown(steps_html(vm), unsafe_allow_html=True)
                    st.caption("El panel financiero muestra la revisión vigente; los mensajes anteriores conservan el contexto de su momento.")
                with st.container(height=300, border=False, key="tt_conversation", autoscroll=True):
                    for mensaje in c.mensajes:
                        st.markdown(message_html(mensaje.rol, mensaje.texto), unsafe_allow_html=True)
                texto = st.chat_input("Escribe tu consulta…", key="chat_principal")
                if texto:
                    with st.spinner("Revisando tu consulta…"):
                        enviar(texto)
                    st.rerun()
                if c.flujo.ia_revision == c.revision:
                    st.caption("Asistencia sobre resultados · Ediciones y simulaciones siempre locales")
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
                if c.resultado and c.resultado.estado == "DISCREPANCIA PENDIENTE":
                    with st.form("aclaracion_ingresos"):
                        st.caption("Hay diferencias entre ingreso declarado y documental. Elige la fuente y justifica la decisión.")
                        fuente = st.selectbox("Fuente elegida", ["PENDIENTE", "DECLARADO", "DOCUMENTAL"], format_func=lambda x: {"PENDIENTE":"Seleccionar", "DECLARADO":"Ingreso declarado", "DOCUMENTAL":"Promedio de boletas"}[x])
                        nota = st.text_input("Justificación sin datos personales", max_chars=300)
                        if st.form_submit_button("Registrar aclaración"):
                            try:
                                aclarar_ingreso(c, fuente, nota)
                                st.rerun()
                            except ValueError as error:
                                st.warning(str(error))
        with dashboard:
            with st.container(key="tt_dashboard_panel", border=True):
                render_dashboard_area(vm)
                if c.flujo.etapa == "RESULTADOS" and not c.pendiente:
                    resultados(c)
                elif c.flujo.iniciado:
                    st.caption("El panel se actualiza con el motor. Los datos todavía requieren confirmación antes del informe y la asistencia IA.")
    if c.vista == "ESTRATEGIA":
        st.caption("Comparación tecnológica independiente de esta evaluación crediticia")
        mostrar_estrategia()
