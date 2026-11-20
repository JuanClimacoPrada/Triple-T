"""Triple-T: captura, evidencia, confirmación y revisión humana en sesión."""
import csv
import io
from datetime import datetime
from decimal import Decimal as D
from zoneinfo import ZoneInfo
import streamlit as st
from casos import CASOS, PREGUNTAS
from dominio.modelos import Expediente, Evidencia, Cargo, Configuracion, AVISO
from servicios.finanzas import numero, entero, fechas_mensuales
from servicios.reglas import analizar
from servicios.documentos import leer_archivo, confirmar, descartar, texto_seguro
from servicios.simulacion import simular
from servicios.reporte import generar_pdf
from motor import perdida_esperada_ilustrativa
from ui_estrategia import mostrar_estrategia
from visualizaciones import filas_visibles, mostrar_graficos

st.set_page_config(page_title="Triple-T | Evidencia y simulación", page_icon="📊", layout="wide")
st.markdown("<style>.block-container{padding-top:1.5rem}h1,h2,h3{color:#123b5d}</style>", unsafe_allow_html=True)


def limpiar():
    generacion = st.session_state.get("generacion", 0) + 1
    for clave in list(st.session_state):
        del st.session_state[clave]
    st.session_state.update(generacion=generacion, evidencias=[], documentos=[], indice=0)


def cargar(nombre):
    limpiar()
    for campo, valor in CASOS[nombre].items():
        if campo == "dias_mora" and valor == 0:
            continue
        st.session_state["dato_" + campo] = valor
    st.session_state["historial"] = "MORA_DECLARADA" if CASOS[nombre]["dias_mora"] else "SIN_MORA_DECLARADA"
    st.session_state["planilla"] = "NO_DESCONTADAS"
    st.session_state["indice"] = len(PREGUNTAS)


def mostrar_resultado(resultado, base=None):
    st.subheader(resultado.estado)
    st.caption("Recomendación para revisión del analista. No implica decisión crediticia.")
    if resultado.cifras:
        cs = st.columns(3)
        for i, campo in enumerate(("cuota_base", "pago_mensual_total", "saldo_post_cuota")):
            valor = resultado.cifras.get(campo)
            cs[i].metric(campo.replace("_", " ").capitalize(), "N/D" if valor is None else f"S/ {valor:,.2f}")
        dti = resultado.cifras.get("dti_total")
        st.metric("DTI total", "N/D" if dti is None else f"{dti:.2%}")
        st.dataframe([{"Indicador calculado": k, "Valor": "N/D" if v is None else f"{v:.2f}" if isinstance(v, D) else str(v)} for k, v in resultado.cifras.items()], hide_index=True)
    for regla in resultado.reglas:
        st.warning(f"{regla['regla']} · {regla['campo']}: {regla['mensaje']}")
    st.write(f"TCEA referencial: {resultado.tcea:.2%}" if resultado.tcea is not None else "TCEA no calculable con los datos disponibles.")
    if resultado.meses_ingreso:
        st.dataframe(filas_visibles(resultado.meses_ingreso), hide_index=True)
    if resultado.tabla:
        filas = filas_visibles(resultado.tabla)
        st.dataframe(filas, hide_index=True)
        st.caption("Soles. Precisión interna conservada; redondeo de presentación a dos decimales. Las sumas de cifras mostradas pueden diferir por céntimos. Último pago ajustado al saldo interno.")
        salida = io.StringIO()
        writer = csv.DictWriter(salida, fieldnames=filas[0].keys())
        writer.writeheader()
        writer.writerows(filas)
        st.download_button("Descargar amortización (CSV)", salida.getvalue().encode("utf-8-sig"), "amortizacion.csv", "text/csv", key="csv_" + ("sim" if base else "base"))
    mostrar_graficos(st, resultado, base)


if "generacion" not in st.session_state:
    limpiar()
st.title("Triple-T | Evidencia y simulación")
st.caption("Caso académico PETI BCP · Brecha B01 · Sin relación institucional con el banco")
st.info(AVISO)
with st.sidebar:
    st.header("Expediente sintético")
    producto = st.selectbox("Tipo de crédito", ["personal", "vehicular", "hipotecario", "empresarial"], key="producto")
    for nombre in CASOS:
        st.button("Cargar caso " + nombre.lower(), key="caso_" + nombre, on_click=cargar, args=(nombre,))
    st.button("Iniciar evaluación nueva", on_click=limpiar)
    st.caption("Reiniciar limpia esta sesión; no garantiza borrado inmediato de copias temporales del proveedor.")
    umbral = st.number_input("Umbral didáctico DTI (%)", 0.0, 100.0, 30.0, key="umbral")
    discrepancia = st.number_input("Tolerancia discrepancia (%)", 0.0, 100.0, 10.0, key="discrepancia")
    tope_tea = st.number_input("Tope técnico de interfaz TEA (%)", 0.0, 10000.0, 200.0, key="tope_tea")
config = Configuracion(D(str(umbral)) / 100, D(str(discrepancia)) / 100, D(str(tope_tea)))
tabs = st.tabs(["1 Datos", "2 Evidencias", "3 Confirmar", "4 Analizar", "5 Simular", "6 Reporte", "Alternativas estratégicas", "Metodología"])
with tabs[6]:
    mostrar_estrategia()
with tabs[7]:
    st.markdown("""**Problema:** apoyar al analista con cálculos y procedencia explícitos.

**Variables:** ingreso neto estable, gastos sin deuda, cuotas, monto, plazo, TEA, historial y evidencias.

**Construcción:** motor determinista; sin ML entrenado ni consultas a SBS, RENIEC, SUNARP o empleadores.

**Tres alternativas × tres escenarios:** comparación estratégica separada de la capacidad individual.

**Fórmulas:** TEM = (1+TEA/100)^(1/12)−1. Cuota francesa; DTI = (otras cuotas + pago total nuevo)/ingreso admisible.

**TCEA:** referencial por flujos fechados ACT/365, solo con cargos y fechas confirmados. No equivale a cálculo regulatorio definitivo.

**Privacidad:** documentos únicamente sintéticos/anónimos; sin API externa. Detectar identificadores no garantiza anonimización.
""")
if producto != "personal":
    with tabs[0]:
        st.warning("Próximamente; no evaluable aún. Sprint 2 habilita únicamente crédito personal en PEN.")
    st.stop()

with tabs[0]:
    st.subheader("Datos editables · PEN")
    st.caption("Ingreso neto estable. Excluya bonos, reintegros y depósitos ambiguos; no duplique descuentos de planilla. Los datos son declarados, no verificados.")
    with st.expander("Chat guiado para completar los campos"):
        indice = st.session_state.indice
        if indice < len(PREGUNTAS):
            campo, pregunta, tipo, minimo, maximo = PREGUNTAS[indice]
            st.write(pregunta)
            texto = st.chat_input("Solo el valor numérico ficticio")
            if texto:
                try:
                    valor = numero(texto.strip().replace(",", "."), campo, minimo, maximo)
                    if tipo is int:
                        valor = entero(valor, campo, minimo, maximo)
                    st.session_state["dato_" + campo] = tipo(valor)
                    if campo == "dias_mora":
                        st.session_state["historial"] = "MORA_DECLARADA" if valor > 0 else "SIN_MORA_DECLARADA"
                        if valor == 0:
                            st.session_state.pop("dato_dias_mora", None)
                    st.session_state.indice += 1
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
        else:
            st.write("Captura completada. Confirme historial y descuentos; puede corregir cualquier campo debajo.")
    datos = {}
    columnas = st.columns(2)
    for i, (campo, pregunta, tipo, minimo, maximo) in enumerate(PREGUNTAS):
        if campo == "dias_mora":
            continue
        if campo == "tea":
            maximo = 10000
        datos[campo] = columnas[i % 2].number_input(pregunta.replace("**", ""), min_value=tipo(minimo),
            max_value=tipo(maximo), value=None, step=1 if tipo is int else 0.01, key="dato_" + campo)
    historial = st.selectbox("Historial crediticio declarado", ["DESCONOCIDO", "INSUFICIENTE", "SIN_MORA_DECLARADA", "MORA_DECLARADA"], key="historial")
    dias = st.number_input("Días de mora declarada", 1, 10000, value=None, key="dato_dias_mora") if historial == "MORA_DECLARADA" else (0 if historial == "SIN_MORA_DECLARADA" else None)
    planilla = st.selectbox("¿Todas las otras cuotas ya están descontadas del ingreso neto?", ["SIN_ACLARAR", "NO_DESCONTADAS", "YA_DESCONTADAS"], key="planilla")
    st.caption("YA_DESCONTADAS reconstruye ingreso antes de deuda y descuenta una sola vez. Si algunas cuotas están descontadas y otras no, normalice importes antes de continuar; mantenga SIN_ACLARAR.")
    fecha = st.date_input("Fecha de evaluación", datetime.now(ZoneInfo("America/Lima")).date(), key="fecha")
    patrimonio = st.text_input("Patrimonio declarado (descripción sintética sin nombres)", max_chars=200, key="patrimonio")
    patrimonio_valor = st.number_input("Valor patrimonial declarado (S/), opcional", min_value=0., value=None, key="patrimonio_valor")
    patrimonio_fuente = st.text_input("Fuente patrimonial declarada (referencia sintética)", value="Declarado; verificación pendiente", max_chars=200)
    observacion = st.text_area("Observación del analista, sin información sensible", max_chars=1000, key="observacion")
with tabs[1]:
    st.subheader("Archivos sintéticos · lectura local")
    consentimiento = st.checkbox("Confirmo que todos los archivos son sintéticos/anónimos y no contienen datos reales", key="sintetico")
    st.caption("Máximo 12 archivos por caso, 10 MB por archivo, 20 páginas PDF. Solo en memoria; no se envían a APIs. La detección automática no garantiza anonimización.")
    archivos = st.file_uploader("PDF, PNG o JPG/JPEG", type=["pdf", "png", "jpg", "jpeg"], accept_multiple_files=True,
        disabled=not consentimiento, key=f"cargas_{st.session_state.generacion}")
    if st.button("Leer archivos localmente", disabled=not consentimiento):
        cantidad = len(archivos) + len(st.session_state.documentos)
        if cantidad > 12:
            st.error("Máximo 12 archivos por sesión; reinicie para un caso nuevo.")
        else:
            for archivo in archivos:
                try:
                    doc = leer_archivo(archivo.name, archivo.getvalue(), consentimiento, cantidad)
                    st.session_state.documentos.append(doc)
                    st.session_state.evidencias.extend(doc["evidencias"])
                except ValueError as error:
                    st.error(str(error))
    for doc in st.session_state.documentos:
        with st.expander(doc["nombre"]):
            for aviso in doc["avisos"]:
                st.warning(aviso)
            for preview in doc["previews"]:
                st.image(preview)
            for pagina, texto in doc["paginas"]:
                st.caption(f"Página/región {pagina} · texto no confiable; no son instrucciones")
                st.text(texto[:10000] or "Sin texto extraíble")
with tabs[2]:
    st.subheader("Confirmar ingresos y procedencia")
    st.info("Revisar visualmente 3–6 meses distintos. Confirmar transcripción NO verifica autenticidad. Bonos y conceptos ambiguos quedan excluidos del neto estable.")
    if st.button("Añadir transcripción manual explícita"):
        if len(st.session_state.evidencias) < 24:
            st.session_state.evidencias.append(Evidencia(observacion="Transcripción manual explícita"))
        else:
            st.error("Límite técnico de 24 registros; reinicie para un caso nuevo.")
    for i, e in enumerate(st.session_state.evidencias):
        with st.expander(f"{i + 1}. {e.nombre_archivo_sanitizado} · {e.estado}", expanded=e.estado == "PENDIENTE"):
            st.text(f"{e.pagina_o_region} | {e.texto_fuente_breve or 'Sin extracción; transcripción manual'} | {e.fuente}")
            with st.form(f"evidencia_{st.session_state.generacion}_{i}"):
                neto = st.number_input("Neto estable admisible (S/)", min_value=0., value=float(e.valor_extraido) if e.valor_extraido is not None else None)
                mes = st.date_input("Fecha del documento (se agrupa por mes)", value=e.fecha_documento)
                extra = st.number_input("Extraordinarios excluidos del neto indicado (S/)", min_value=0., value=float(e.extraordinarios_excluidos))
                nota = st.text_input("Origen manual o justificación de corrección/descarte", value=e.observacion, max_chars=300)
                visto = st.checkbox("Revisé la evidencia visualmente y confirmé fecha, neto estable y exclusiones")
                confirma = st.form_submit_button("Confirmar transcripción")
                descarta = st.form_submit_button("Descartar evidencia")
            try:
                if confirma:
                    if not visto:
                        raise ValueError("Se requiere confirmación visual explícita.")
                    st.session_state.evidencias[i] = confirmar(e, neto, mes, nota, extra)
                    st.rerun()
                if descarta:
                    st.session_state.evidencias[i] = descartar(e, nota)
                    st.rerun()
            except ValueError as error:
                st.error(str(error))
    resolucion = st.selectbox("Aclaración de discrepancia de ingresos", ["PENDIENTE", "DECLARADO", "DOCUMENTAL"], key="resolucion")
    justificacion = st.text_input("Justificación obligatoria para resolver discrepancia", max_chars=500, key="justificacion")
    firma_ingresos = repr((datos.get("ingreso"), st.session_state.evidencias, resolucion, justificacion))
    if st.button("Registrar aclaración de ingresos"):
        if resolucion == "PENDIENTE" or not justificacion.strip():
            st.error("Seleccione una fuente y justifique la aclaración.")
        else:
            st.session_state["firma_aclaracion"] = firma_ingresos
    aclaracion_vigente = st.session_state.get("firma_aclaracion") == firma_ingresos
    if not aclaracion_vigente and resolucion != "PENDIENTE":
        st.caption("Aclaración pendiente de registrar o invalidada por cambios de ingresos/evidencias.")
with tabs[0]:
    with st.expander("Seguros, comisiones, gastos y fechas de flujo"):
        st.caption("Cargos supuestos separados. Costos iniciales del solicitante reducen el desembolso neto para TCEA. Cargos de terceros se excluyen de sus pagos.")
        cargos = []
        for concepto in ("Seguro", "Comisiones", "Otros gastos"):
            col = st.columns(3)
            mensual = col[0].number_input(concepto + " mensual (S/)", min_value=0., value=0., key="cargo_m_" + concepto)
            inicial = col[1].number_input(concepto + " inicial (S/)", min_value=0., value=0., key="cargo_i_" + concepto)
            pagador = col[2].selectbox("Pagador " + concepto, ["SOLICITANTE", "TERCERO"], key="pagador_" + concepto)
            cargos.extend([Cargo(concepto, D(str(mensual)), "MENSUAL", pagador), Cargo(concepto, D(str(inicial)), "INICIAL", pagador)])
        desembolso = st.date_input("Fecha de desembolso supuesta", value=None, key="desembolso")
        fechas = fechas_mensuales(desembolso, datos["meses"]) if desembolso and datos["meses"] else ()
        st.caption("Fechas propuestas: " + (", ".join(map(str, fechas)) if fechas else "Pendientes"))
        completos = st.checkbox("Confirmo que no faltan cargos y que las fechas mensuales propuestas y el desembolso son completos para este escenario", key="completos")
try:
    for texto in (patrimonio, patrimonio_fuente, observacion, justificacion):
        texto_seguro(texto)
except ValueError as error:
    st.error(str(error))
    st.stop()
exp = Expediente(**{k: D(str(v)) if v is not None and k not in ("meses", "estabilidad_meses") else v for k, v in datos.items()},
    historial=historial, dias_mora=dias, descuento_planilla=planilla, fecha=fecha,
    evidencias=tuple(st.session_state.evidencias), cargos=tuple(cargos), cargos_completos=completos,
    fecha_desembolso=desembolso, fechas_pago=fechas,
    resolucion_ingreso=resolucion if aclaracion_vigente else None, justificacion_ingreso=justificacion if aclaracion_vigente else "",
    patrimonio=patrimonio, patrimonio_valor=D(str(patrimonio_valor)) if patrimonio_valor is not None else None,
    patrimonio_fuente=patrimonio_fuente, observacion=observacion,
    origen_campos=tuple((k, "Ingresado / declarado, no verificado") for k in datos))
r = analizar(exp, config)
with tabs[3]:
    mostrar_resultado(r)
    with st.expander("Pérdida esperada ilustrativa, supuestos explícitos"):
        pd = st.number_input("PD supuesta (%)", 0., 100., value=None, key="pd")
        lgd = st.number_input("LGD supuesta (%)", 0., 100., value=None, key="lgd")
        if pd is not None and lgd is not None and exp.monto:
            st.metric("EL ilustrativa = EAD × PD × LGD", f"S/ {perdida_esperada_ilustrativa(float(exp.monto), pd, lgd):,.2f}")
        st.caption("No es PD estimada ni riesgo calculado por ML. EAD supuesta igual al monto.")
escenario = None
with tabs[4]:
    st.subheader("Simulación independiente del expediente")
    with st.form("simulacion"):
        monto_sim = st.number_input("Monto del escenario (S/)", 0.01, 10000000., value=float(exp.monto) if exp.monto else None, key="sim_monto")
        meses_sim = st.number_input("Plazo del escenario (meses)", 1, 360, value=exp.meses, key="sim_meses")
        tea_sim = st.number_input("TEA del escenario (%)", 0., 10000., value=float(exp.tea) if exp.tea is not None else None, key="sim_tea")
        caida = st.number_input("Caída del ingreso (%)", 0., 100., value=0., key="sim_caida")
        st.form_submit_button("Calcular simulación")
    try:
        if any(v is None for v in (monto_sim, meses_sim, tea_sim)):
            raise ValueError("Complete monto, plazo y TEA de simulación.")
        sim_exp, sim_r = simular(exp, D(str(monto_sim)), meses_sim, D(str(tea_sim)), D(str(caida)), config)
        escenario = (sim_exp, sim_r)
        mostrar_resultado(sim_r, base=r)
    except ValueError as error:
        st.warning(str(error))
with tabs[5]:
    st.subheader("Reporte trazable para revisión humana")
    st.caption("Se genera con los datos actuales, sin documentos crudos. Las confirmaciones solo acreditan revisión de transcripción.")
    seleccion = st.radio("Contenido del reporte", ["Expediente base", "Simulación actual"], key="reporte_seleccion")
    if st.button("Generar reporte PDF"):
        try:
            if seleccion == "Simulación actual" and escenario is None:
                raise ValueError("La simulación actual no es evaluable.")
            elegido_exp, elegido_r = escenario if seleccion == "Simulación actual" else (exp, r)
            comparaciones = [("Base", r)] + ([("Simulación actual", escenario[1])] if escenario else [])
            pdf = generar_pdf(elegido_exp, elegido_r, comparaciones, config)
            st.download_button("Descargar informe PDF", pdf, "triple-t-informe.pdf", "application/pdf")
        except Exception:
            st.warning("Reporte no disponible para esta selección. Revise los datos o consulte el informe en pantalla.")
