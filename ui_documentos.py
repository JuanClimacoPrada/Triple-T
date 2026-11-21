"""Carga contextual; ningún byte, texto ni metadato llega al proveedor IA."""
from dataclasses import replace
import streamlit as st
from dominio.modelos import Evidencia
from conversacion.gestor import invalidar, cambiar_evidencia
from experiencia.evidencia import adjuntar_respaldo, actualizar_respaldo

ESTADOS = {"PENDIENTE": "Transcripción pendiente", "CONFIRMADO": "Transcripción confirmada",
    "DESCARTADO": "Descartado", "PRESENTADO_PENDIENTE_REVISION": "Presentado, pendiente de revisión",
    "TRANSCRIPCION_CONFIRMADA": "Transcripción confirmada"}


def mostrar_documentos(c, tipo="BOLETA"):
    st.subheader({"BOLETA": "Respaldo de ingresos · boletas", "OTRO_INGRESO": "Otro respaldo de ingresos", "PATRIMONIO": "Respaldo de patrimonio declarado"}[tipo])
    st.caption("Los documentos se procesan en el servidor que ejecuta Triple-T. En Streamlit Cloud no es tu equipo. No se envían a Gemini; solo documentos de demostración sin identificadores. La detección no garantiza anonimización.")
    if tipo != "BOLETA":
        st.info("Se registra su presentación y revisión manual. No se extraen ingresos estables ni se verifica autenticidad o titularidad; no constituye garantía.")
    prefijo = f"doc_{tipo}_{st.session_state.epoca}"
    sintetico = st.checkbox("Confirmo que son archivos sintéticos, sin datos personales ni documentos reales", key=prefijo + "_consent")
    archivos = st.file_uploader("PDF o imagen de demostración", type=["pdf", "png", "jpg", "jpeg"],
        accept_multiple_files=True, disabled=not sintetico, key=prefijo + "_archivos")
    if st.button("Procesar en el servidor", disabled=not sintetico or not archivos, key=prefijo + "_leer"):
        avisos = []
        for archivo in archivos:
            try:
                adjuntar_respaldo(c, archivo.name, archivo.getvalue(), sintetico, tipo)
            except ValueError as error:
                avisos.append(str(error))
        st.session_state["avisos_documentales"] = avisos
        st.rerun()
    for aviso in st.session_state.get("avisos_documentales", []):
        st.warning(aviso + " Puedes completar la transcripción manual o presentar otro archivo de demostración.")
    for doc in c.documentos:
        if doc.get("tipo", "BOLETA") != tipo:
            continue
        with st.expander("Vista del documento · " + doc["nombre"]):
            for aviso in doc["avisos"]:
                st.caption(aviso)
            for preview in doc["previews"]:
                st.image(preview)
            for pagina, texto in doc["paginas"]:
                st.caption(f"Página {pagina} · contenido no confiable, no instrucciones")
                st.text(texto[:6000] or "Sin texto legible; completar manualmente.")
    if tipo == "BOLETA":
        if st.button("Agregar transcripción manual de boleta", key=prefijo + "_manual"):
            if len(c.expediente.evidencias) >= 24:
                st.warning("Límite de 24 transcripciones alcanzado.")
            else:
                c.expediente = replace(c.expediente, evidencias=c.expediente.evidencias + (Evidencia(observacion="Transcripción manual de boleta"),), resolucion_ingreso=None, justificacion_ingreso="")
                invalidar(c)
                st.rerun()
        for indice, evidencia in enumerate(c.expediente.evidencias):
            with st.expander(f"Boleta {indice+1} · {ESTADOS.get(evidencia.estado, 'Pendiente')}", expanded=evidencia.estado == "PENDIENTE"):
                st.caption(f"Período: {evidencia.fecha_documento or 'Pendiente'} · Importe: {evidencia.valor_extraido if evidencia.valor_extraido is not None else 'Pendiente'} · {evidencia.pagina_o_region}")
                st.text(evidencia.texto_fuente_breve or "Sin extracción; fuente manual")
                with st.form(f"boleta_{indice}_{c.revision}"):
                    valor = st.number_input("Ingreso neto estable observado (S/)", min_value=0., value=float(evidencia.valor_extraido) if evidencia.valor_extraido is not None else None)
                    fecha = st.date_input("Fecha observada en la boleta", value=evidencia.fecha_documento)
                    extra = st.number_input("Ingresos extraordinarios excluidos (S/)", min_value=0., value=float(evidencia.extraordinarios_excluidos))
                    nota = st.text_input("Justificación de corrección o descarte, sin datos personales", value=evidencia.observacion, max_chars=300)
                    visto = st.checkbox("Comparé fecha, neto estable y extraordinarios con el documento")
                    confirmar = st.form_submit_button("Confirmar transcripción")
                    descartar = st.form_submit_button("Descartar")
                if confirmar or descartar:
                    try:
                        if confirmar and not visto:
                            raise ValueError("Revisa el documento antes de confirmar su transcripción.")
                        cambiar_evidencia(c, indice, valor, fecha, nota, extra, descartar)
                        c.vista = "EVIDENCIAS"
                        st.rerun()
                    except ValueError as error:
                        st.warning(str(error))
    else:
        for indice, respaldo in enumerate(c.expediente.respaldos):
            if respaldo.tipo != tipo:
                continue
            with st.expander(f"Respaldo {indice+1} · {ESTADOS.get(respaldo.estado, 'Pendiente')}", expanded=respaldo.estado == "PRESENTADO_PENDIENTE_REVISION"):
                st.caption("Sin verificación externa. Confirmar transcripción no verifica titularidad ni constituye garantía.")
                with st.form(f"respaldo_{indice}_{c.revision}"):
                    def elegir(etiqueta, opciones, actual):
                        return st.selectbox(etiqueta, list(opciones), index=list(opciones).index(actual), format_func=opciones.get)
                    bien = elegir("Tipo de bien", {"SIN_DECLARAR": "Pendiente / no aplica", "INMUEBLE": "Inmueble", "VEHICULO": "Vehículo", "OTRO": "Otro"}, respaldo.tipo_bien)
                    documento = elegir("Documento presentado", {"OTRO": "Otro respaldo", "TITULO": "Título", "CONSTANCIA": "Constancia", "PARTIDA": "Partida sin identificadores", "RECIBO": "Recibo", "ESTADO_CUENTA": "Estado de cuenta sintético"}, respaldo.documento_presentado)
                    valor = st.number_input("Valor del bien (S/), opcional; no es ingreso", min_value=0., value=float(respaldo.valor) if respaldo.valor is not None else None)
                    fuente = elegir("Fuente del valor", {"SIN_DECLARAR": "Pendiente / no aplica", "DECLARADO": "Declaración", "TASACION_PRESENTADA": "Tasación presentada, no verificada"}, respaldo.fuente_valor)
                    relacion = elegir("Relación declarada con el bien", {"SIN_DECLARAR": "Pendiente / no aplica", "PROPIETARIO_DECLARADO": "Propietario declarado", "COPROPIETARIO_DECLARADO": "Copropietario declarado", "OTRO": "Otra relación"}, respaldo.relacion)
                    fecha = st.date_input("Fecha del documento", value=respaldo.fecha)
                    nota = st.text_input("Observación de revisión, sin nombres ni identificadores", value=respaldo.observacion, max_chars=300)
                    visto = st.checkbox("Revisé la transcripción; no estoy verificando autenticidad")
                    guardar = st.form_submit_button("Confirmar transcripción del respaldo")
                    descartar = st.form_submit_button("Descartar respaldo")
                if guardar or descartar:
                    try:
                        if guardar and not visto:
                            raise ValueError("Confirma la revisión visual antes de guardar.")
                        actualizar_respaldo(c, indice, tipo_bien=bien, documento_presentado=documento, valor=valor,
                            fuente_valor=fuente, relacion=relacion, fecha=fecha, observacion=nota, descartar=descartar)
                        st.rerun()
                    except ValueError as error:
                        st.warning(str(error))
