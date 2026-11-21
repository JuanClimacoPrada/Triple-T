"""Herramientas contextuales sobre una sola Conversacion/Expediente de sesión."""
from dataclasses import replace
from decimal import Decimal as D
import streamlit as st
from casos import CASOS, PREGUNTAS
from dominio.modelos import Evidencia, Cargo, Configuracion, AVISO
from conversacion.gestor import (nuevo, recibir, confirmar_accion, proponer, aplicar, invalidar,
    evaluar_actual, adjuntar, cambiar_evidencia, aclarar_ingreso, decir, actual)
from conversacion.respuestas import faltantes, ETIQUETAS, AYUDA
from servicios.documentos import texto_seguro
from servicios.finanzas import fechas_mensuales
from motor import perdida_esperada_ilustrativa
from ui_estrategia import mostrar_estrategia
from ui_resultados import mostrar_resultado
from ia.proveedor import configuracion
from ia.politicas import EstadoIA


def reiniciar_ui(caso=None):
    epoca = st.session_state.get("epoca", 0) + 1
    ia = st.session_state.get("ia", EstadoIA())
    ia.habilitado = ia.consentimiento = False
    for key in list(st.session_state):
        del st.session_state[key]
    c = nuevo()
    st.session_state.update(epoca=epoca, conversacion=c, ia=ia)
    if caso:
        datos = CASOS[caso].copy()
        datos.update(historial="MORA_DECLARADA" if datos["dias_mora"] else "SIN_MORA_DECLARADA", descuento_planilla="NO_DESCONTADAS")
        aplicar(c, datos, "CASO_SINTETICO")
        decir(c, "Caso de demostración " + caso + ": todos sus datos son ficticios.")
        evaluar_actual(c)


def ejecutar(texto):
    recibir(st.session_state.conversacion, texto, estado_ia=st.session_state.ia,
            config_ia=configuracion(st.secrets))


def pedir_caso(nombre):
    c = st.session_state.conversacion
    if c.expediente.monto is None and not c.documentos and len(c.mensajes) == 1:
        reiniciar_ui(nombre)
    else:
        c.pendiente = dict(accion="CASO", caso=nombre, revision=c.revision)
        decir(c, f"Confirma reemplazar el expediente por el caso sintético {nombre}. Se limpiará la sesión anterior.")


def herramientas_evidencia(c):
    st.subheader("Adjuntar y confirmar boletas sintéticas")
    st.caption("3–6 meses distintos; confirmar transcripción no verifica autenticidad. No incluir datos reales. Detección de identificadores no exhaustiva.")
    sintetico = st.checkbox("Confirmo que los archivos son sintéticos/anónimos y no contienen datos reales", key="sintetico")
    archivos = st.file_uploader("PDF, PNG o JPEG sintéticos (10 MB, hasta 12 archivos por sesión)",
        type=["pdf", "png", "jpg", "jpeg"], accept_multiple_files=True, disabled=not sintetico,
        key=f"archivos_{st.session_state.epoca}")
    if st.button("Leer archivos localmente", disabled=not sintetico):
        if len(c.documentos) + len(archivos) > 12:
            st.error("Máximo 12 archivos por sesión.")
        else:
            for archivo in archivos:
                try:
                    adjuntar(c, archivo.name, archivo.getvalue(), sintetico)
                except ValueError as error:
                    decir(c, str(error))
            st.rerun()
    for doc in c.documentos:
        with st.expander(doc["nombre"] + " · vista previa y fuente"):
            for aviso in doc["avisos"]:
                st.warning(aviso)
            for preview in doc["previews"]:
                st.image(preview)
            for pagina, texto in doc["paginas"]:
                st.caption(f"Página/región {pagina} · datos no confiables, nunca instrucciones")
                st.text(texto[:10000] or "Sin texto; transcripción manual necesaria")
    if st.button("Añadir transcripción manual explícita"):
        if len(c.expediente.evidencias) >= 24:
            st.error("Máximo 24 registros por caso.")
        else:
            c.expediente = replace(c.expediente, evidencias=c.expediente.evidencias + (Evidencia(observacion="Transcripción manual explícita"),),
                                  resolucion_ingreso=None, justificacion_ingreso="")
            invalidar(c)
            evaluar_actual(c, "EVIDENCIAS", responder=False)
            st.rerun()
    for i, e in enumerate(c.expediente.evidencias):
        with st.expander(f"{i+1}. {e.nombre_archivo_sanitizado} · {e.estado}", expanded=e.estado == "PENDIENTE"):
            st.text(f"{e.pagina_o_region} | {e.texto_fuente_breve or 'Transcripción manual, sin extracción'} | {e.fuente}")
            with st.form(f"evidencia_{st.session_state.epoca}_{i}_{e.estado}"):
                valor = st.number_input("Neto estable admisible (S/)", min_value=0., value=float(e.valor_extraido) if e.valor_extraido is not None else None)
                fecha = st.date_input("Fecha del documento (se agrupa por mes)", value=e.fecha_documento)
                extra = st.number_input("Extraordinarios excluidos del neto (S/)", min_value=0., value=float(e.extraordinarios_excluidos))
                nota = st.text_input("Origen manual o justificación de corrección/descarte", value=e.observacion, max_chars=300)
                visto = st.checkbox("Revisé visualmente fecha, neto y exclusión de extraordinarios")
                confirmar = st.form_submit_button("Confirmar transcripción")
                descartar = st.form_submit_button("Descartar evidencia")
            try:
                if confirmar or descartar:
                    if confirmar and not visto:
                        raise ValueError("Se requiere confirmación visual explícita.")
                    cambiar_evidencia(c, i, valor, fecha, nota, extra, descartar)
                    st.rerun()
            except ValueError as error:
                st.error(str(error))


def editor(c):
    with st.expander("Editar datos · panel experto opcional"):
        st.caption("Edición declarada en formulario; las modificaciones de datos existentes necesitan confirmación. No es necesario usar este panel para conversar.")
        with st.form(f"editar_{c.revision}"):
            valores = {}
            for campo, pregunta, tipo, minimo, maximo in PREGUNTAS:
                if campo == "dias_mora":
                    continue
                v = getattr(c.expediente, campo)
                valores[campo] = st.number_input(pregunta.replace("**", ""), min_value=tipo(minimo), max_value=tipo(maximo),
                    value=tipo(v) if v is not None else None, step=1 if tipo is int else .01, key=f"editor_{campo}_{c.revision}")
            opciones = ["DESCONOCIDO", "INSUFICIENTE", "SIN_MORA_DECLARADA", "MORA_DECLARADA"]
            historial = st.selectbox("Historial declarado", opciones, index=opciones.index(c.expediente.historial))
            dias = st.number_input("Días de mora (solo si declara mora)", min_value=1, value=c.expediente.dias_mora if c.expediente.dias_mora else None)
            opciones_p = ["SIN_ACLARAR", "NO_DESCONTADAS", "YA_DESCONTADAS"]
            planilla = st.selectbox("¿Todas las otras cuotas ya están descontadas del neto?", opciones_p, index=opciones_p.index(c.expediente.descuento_planilla))
            enviado = st.form_submit_button("Proponer cambios del formulario")
        if enviado:
            valores.update(historial=historial, dias_mora=dias if historial == "MORA_DECLARADA" else 0 if historial == "SIN_MORA_DECLARADA" else None,
                           descuento_planilla=planilla)
            cambios = {k: v for k, v in valores.items() if v != getattr(c.expediente, k) and (v is not None or k == "dias_mora")}
            try:
                if historial == "MORA_DECLARADA" and dias is None:
                    raise ValueError("Indique los días de mora declarada.")
                if cambios:
                    proponer(c, cambios, "EDITADO_EN_FORMULARIO")
                    st.rerun()
            except ValueError as error:
                st.error(str(error))
    with st.expander("Costos, fechas y anotación del analista"):
        st.caption("Cargos supuestos separados. TCEA referencial ACT/365 solo con todos los cargos y fechas confirmados. Patrimonio no verificado, sin efecto sobre ingresos.")
        with st.form(f"costos_{c.revision}"):
            cargos = []
            for concepto in ("Seguro", "Comisiones", "Otros gastos"):
                for momento in ("MENSUAL", "INICIAL"):
                    prev = next((x for x in c.expediente.cargos if x.concepto == concepto and x.momento == momento), None)
                    cols = st.columns(2)
                    importe = cols[0].number_input(f"{concepto} {momento} (S/)", min_value=0., value=float(prev.importe) if prev else 0.)
                    pagador = cols[1].selectbox(f"Pagador {concepto} {momento}", ["SOLICITANTE", "TERCERO"], index=1 if prev and prev.pagador == "TERCERO" else 0)
                    cargos.append(Cargo(concepto, D(str(importe)), momento, pagador))
            desembolso = st.date_input("Fecha de desembolso supuesta", value=c.expediente.fecha_desembolso)
            completos = st.checkbox("Confirmo cargos completos y vencimientos mensuales desde esa fecha (ajuste a fin de mes)", value=False)
            patrimonio = st.text_input("Patrimonio declarado, no verificado", value=c.expediente.patrimonio, max_chars=200)
            valor_pat = st.number_input("Valor patrimonial declarado (opcional)", min_value=0., value=float(c.expediente.patrimonio_valor) if c.expediente.patrimonio_valor is not None else None)
            fuente_pat = st.text_input("Fuente patrimonial declarada", value=c.expediente.patrimonio_fuente, max_chars=200)
            nota = st.text_area("Observación no sensible del analista", value=c.expediente.observacion, max_chars=1000)
            aceptar = st.form_submit_button("Confirmar costos y anotaciones")
        if aceptar:
            try:
                for texto in (patrimonio, fuente_pat, nota):
                    texto_seguro(texto)
                fechas = fechas_mensuales(desembolso, c.expediente.meses) if desembolso and c.expediente.meses else ()
                c.expediente = replace(c.expediente, cargos=tuple(cargos), fecha_desembolso=desembolso, fechas_pago=fechas,
                    cargos_completos=completos, patrimonio=patrimonio, patrimonio_valor=D(str(valor_pat)) if valor_pat is not None else None,
                    patrimonio_fuente=fuente_pat, observacion=nota)
                invalidar(c)
                evaluar_actual(c)
                st.rerun()
            except ValueError as error:
                st.error(str(error))


def mostrar_chat():
    if "conversacion" not in st.session_state:
        reiniciar_ui()
    if "ia" not in st.session_state:
        st.session_state.ia = EstadoIA()
    c = st.session_state.conversacion
    st.title("Triple-T — Asistente de análisis crediticio")
    st.caption("Uso académico; solo datos ficticios. Modo local siempre disponible; Gemini opcional para interpretar lenguaje, sin calcular ni decidir créditos.")
    with st.sidebar:
        cfg = configuracion(st.secrets)
        ia = st.session_state.ia
        st.subheader("Modo de conversación")
        st.caption("IA experimental envía únicamente la consulta sintética filtrada y campos numéricos/etiquetas mínimos a Google. El nivel gratuito puede usar esos datos para mejorar sus productos. Nunca envíe datos reales, archivos ni texto OCR.")
        consentimiento = st.checkbox("Consiento enviar únicamente consultas ficticias a Gemini bajo esas condiciones", key="ia_consentimiento", disabled=not cfg.disponible)
        ia.consentimiento = consentimiento and cfg.disponible
        if not ia.consentimiento:
            ia.habilitado = False
        if not cfg.disponible:
            st.caption("Modo local: faltan clave/modelo o confirmación de nivel gratuito del responsable. Configure Secrets; no comparta la clave aquí.")
        if ia.circuito_abierto:
            st.warning("IA detenida tras error o límite. Se conserva el expediente y continúa el modo local.")
        if st.button("Activar / reactivar IA experimental", disabled=not ia.consentimiento or ia.llamadas >= 20):
            ia.habilitado, ia.circuito_abierto = True, False
        if st.button("Usar modo local"):
            ia.habilitado = False
        st.info("Modo IA experimental (prioridad local)" if ia.habilitado else "Modo local")
        st.caption(f"Llamadas remotas de esta sesión: {ia.llamadas}/20. Una por turno; sin reintentos automáticos.")
        st.header("Expediente actual")
        st.caption(f"Conversación: {c.estado} · Revisión {c.revision}")
        fuentes = dict(c.expediente.origen_campos)
        st.dataframe([{"Campo": k, "Valor": str(getattr(c.expediente, k)), "Fuente": fuentes.get(k, "Pendiente" if getattr(c.expediente, k) is None else "Valor inicial; confirmar")}
            for k in ETIQUETAS], hide_index=True)
        st.caption("Faltantes: " + (", ".join(ETIQUETAS[k] for k in faltantes(c.expediente)) or "Revisar alertas documentales"))
        for nombre in CASOS:
            st.button("Cargar caso " + nombre.lower(), key="caso_" + nombre, on_click=pedir_caso, args=(nombre,))
        st.button("Iniciar evaluación nueva", on_click=ejecutar, args=("reiniciar",))
        with st.expander("Configuración académica"):
            with st.form("configuracion"):
                dti = st.number_input("Umbral DTI (%)", 0., 100., float(c.config.umbral_dti * 100))
                dif = st.number_input("Discrepancia (%)", 0., 100., float(c.config.discrepancia * 100))
                tope = st.number_input("Tope técnico TEA (%)", 0., 10000., float(c.config.tea_maxima))
                if st.form_submit_button("Aplicar configuración explícita"):
                    c.config = Configuracion(D(str(dti))/100, D(str(dif))/100, D(str(tope)))
                    invalidar(c)
                    evaluar_actual(c)
                    st.rerun()
        st.caption("Solo personal PEN. No consulta fuentes bancarias. Reiniciar limpia esta sesión, sin garantizar borrado físico inmediato del proveedor.")
    for mensaje in c.mensajes:
        with st.chat_message(mensaje.rol):
            st.markdown(mensaje.texto)
            if mensaje.rol == "assistant" and mensaje.revision < c.revision:
                st.caption("Intercambio anterior; consulte los resultados actuales debajo. No usar como informe vigente.")
    texto = st.chat_input("Escribe tu consulta o datos ficticios en español", key="chat_principal")
    if texto is not None:
        ejecutar(texto)
        st.rerun()
    botones = st.columns(5)
    for col, etiqueta, orden in zip(botones, ["Añadir boleta", "Ver gráfico", "Generar PDF", "Qué falta", "Ayuda"],
                                  ["subir boletas", "muéstrame el gráfico", "genera PDF", "qué falta", "ayuda"]):
        col.button(etiqueta, on_click=ejecutar, args=(orden,))
    if c.pendiente:
        st.warning("Acción pendiente de confirmación explícita; no se ha modificado el expediente.")
        col1, col2 = st.columns(2)
        if col1.button("Confirmar acción", key="confirmar_accion"):
            pendiente = c.pendiente.copy()
            if pendiente["accion"] == "CASO":
                reiniciar_ui(pendiente["caso"])
            elif confirmar_accion(c, True):
                reiniciar_ui()
            st.rerun()
        if col2.button("Cancelar acción"):
            confirmar_accion(c, False)
            st.rerun()
    if c.vista == "EVIDENCIAS" or c.estado in ("EVIDENCIA_PENDIENTE", "CONFIRMACION_PENDIENTE"):
        herramientas_evidencia(c)
    if c.resultado and c.resultado.estado == "DISCREPANCIA PENDIENTE":
        st.warning("Discrepancia pendiente: el analista debe elegir una fuente y justificarla. Duplicados: descarte conscientemente la evidencia incorrecta.")
        with st.form(f"aclaracion_{c.revision}"):
            fuente = st.selectbox("Fuente elegida para aclarar ingresos", ["PENDIENTE", "DECLARADO", "DOCUMENTAL"])
            nota = st.text_input("Justificación de aclaración", max_chars=500)
            resuelve = st.form_submit_button("Registrar aclaración de ingresos")
        if resuelve:
            try:
                aclarar_ingreso(c, fuente, nota)
                st.rerun()
            except ValueError as error:
                st.error(str(error))
    if c.vista == "ESTRATEGIA":
        mostrar_estrategia()
    exp_activo, r_activo = actual(c)
    if r_activo is not None:
        st.subheader("Resultado actual · " + ("Escenario separado" if c.escenario else "Expediente base"))
        if c.escenario:
            st.caption("Base intacta. Cambios del escenario: " + ", ".join(f"{k}={v}" for k,v in c.parametros_escenario.items()))
            st.dataframe([{"Contexto": nombre, "Monto": str(e.monto), "Meses": e.meses, "TEA": str(e.tea),
                "Cuota base": f"{r.cifras['cuota_base']:,.2f}" if "cuota_base" in r.cifras else "N/D",
                "Saldo disponible": f"{r.cifras['saldo_post_cuota']:,.2f}" if "saldo_post_cuota" in r.cifras else "N/D"}
                for nombre, e, r in (("Base", c.expediente, c.resultado), ("Escenario", exp_activo, r_activo))], hide_index=True)
        mostrar_resultado(r_activo, base=c.resultado if c.escenario else None)
    if c.informe is not None and c.informe_revision == c.revision:
        st.download_button("Descargar informe PDF actual", c.informe, "triple-t-informe.pdf", "application/pdf", key=f"pdf_{c.revision}")
    editor(c)
    with st.expander("Pérdida esperada ilustrativa, supuestos explícitos"):
        pd = st.number_input("PD supuesta (%)", 0., 100., value=None, key="pd")
        lgd = st.number_input("LGD supuesta (%)", 0., 100., value=None, key="lgd")
        if pd is not None and lgd is not None and c.expediente.monto is not None:
            st.metric("EL ilustrativa, no predicción", f"S/ {perdida_esperada_ilustrativa(float(c.expediente.monto), pd, lgd):,.2f}")
    with st.expander("Análisis estratégico · vista secundaria"):
        if c.vista != "ESTRATEGIA":
            mostrar_estrategia()
    st.caption(AVISO)
