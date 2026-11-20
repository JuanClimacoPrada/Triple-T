"""Chatbot académico BCP RiskPredict (sin relación institucional con el banco)."""
import csv
import io
import re
import streamlit as st

from motor import (Solicitud, evaluar, perdida_esperada_ilustrativa, comparar_alternativas,
                   solicitud_desde_datos, tabla_amortizacion)
from reglas_credito import PERFILES

st.set_page_config(page_title="RiskPredict | Caso BCP", page_icon="📊", layout="wide")
st.markdown("""
<style>
.block-container{padding-top:1.6rem}
h1,h2,h3{color:#0B3558}
div[data-testid="stMetric"]{border:1px solid #D7E2ED;padding:12px;border-radius:10px}
</style>""", unsafe_allow_html=True)

st.title("RiskPredict | Evaluación y escenarios")
st.caption("Prototipo académico basado en la brecha B01 del PETI BCP. No es una herramienta oficial, no usa datos reales ni decide solicitudes de crédito.")

PREGUNTAS = [
    ("ingreso", "¿Cuál es el **ingreso mensual** del solicitante en soles? Ejemplo: `3500`", float, 0, 10000000),
    ("gastos", "¿Cuánto gasta mensualmente, sin contar las cuotas de otras deudas?", float, 0, 10000000),
    ("otras_cuotas", "¿Cuánto paga al mes por **otras deudas**?", float, 0, 10000000),
    ("monto", "¿Cuánto dinero solicita (S/)?", float, 0.01, 10000000),
    ("meses", "¿En cuántos **meses** pagará el préstamo?", int, 1, 360),
    ("tea", "¿Cuál es la **tasa efectiva anual (TEA)** supuesta en %? Ejemplo: `25`", float, 0, 200),
    ("estabilidad_meses", "¿Cuántos meses de continuidad de ingresos tiene?", int, 0, 600),
    ("dias_mora", "¿Cuántos días de atraso o mora vigente registra en este caso ficticio?", int, 0, 10000),
]

CASOS = {
    "Optimista": dict(ingreso=45000, gastos=10000, otras_cuotas=0, monto=2000, meses=1, tea=18, estabilidad_meses=84, dias_mora=0),
    "Esperado": dict(ingreso=3500, gastos=1400, otras_cuotas=300, monto=10000, meses=12, tea=25, estabilidad_meses=24, dias_mora=0),
    "Pesimista": dict(ingreso=0, gastos=0, otras_cuotas=0, monto=20000, meses=24, tea=25, estabilidad_meses=0, dias_mora=60),
}


def reiniciar():
    for nombre, *_ in PREGUNTAS:
        st.session_state.pop("sim_" + nombre, None)
    st.session_state.datos = {}
    st.session_state.indice = 0
    st.session_state.historial = [{"role": "assistant", "content": "¡Bienvenido! Soy RiskPredict, un asistente **académico** de evaluación crediticia. Solo utilizaremos datos ficticios. " + PREGUNTAS[0][1]}]


def importar_caso(nombre):
    st.session_state.datos = CASOS[nombre].copy()
    for campo, valor in CASOS[nombre].items():
        st.session_state["sim_" + campo] = valor
    st.session_state.indice = len(PREGUNTAS)
    st.session_state.historial = [
        {"role": "assistant", "content": "He cargado el caso de demostración: **" + nombre + "**. Los datos son ficticios y la clasificación procede de reglas, no de un modelo ML."},
    ]


def leer_numero(texto, tipo, minimo, maximo):
    limpio = re.sub(r"[sS]/\s*|\s|%", "", texto.strip()).replace(",", ".")
    n = float(limpio)
    if not minimo <= n <= maximo or (tipo is int and not n.is_integer()):
        raise ValueError
    return tipo(n)


if "indice" not in st.session_state:
    reiniciar()

with st.sidebar:
    tipo_credito = st.selectbox("Tipo de crédito", list(PERFILES), format_func=lambda x: PERFILES[x].nombre)
    st.caption(PERFILES[tipo_credito].pendientes + " Políticas pendientes; se usan reglas académicas comunes.")
    if tipo_credito == "empresarial":
        st.info("Ingreso = flujo neto mensual antes de deuda. Gastos = 0 si ya fueron descontados del flujo. No usar ventas brutas como flujo neto.")
    else:
        st.caption("Ingreso neto mensual después de descuentos de nómina, antes de gastos del hogar y deudas. No descontar una obligación dos veces.")
    st.subheader("Casos de prueba")
    st.caption("Datos completamente ficticios del ejercicio universitario.")
    for c in CASOS:
        st.button("Cargar caso " + c.lower(), key="caso_" + c, on_click=importar_caso, args=(c,), use_container_width=True)
    st.button("Iniciar evaluación nueva", on_click=reiniciar, use_container_width=True)
    st.divider()
    st.info("No ingreses DNI, nombres, datos bancarios ni historiales reales. El modelo no genera aprobaciones automáticas ni PD real.")

p1, p2, p3, p4 = st.tabs(["Chatbot de evaluación", "Alternativas estratégicas", "Metodología", "Simulador y amortización"])

with p1:
    st.subheader("Conversación guiada")
    for mensaje in st.session_state.historial:
        with st.chat_message(mensaje["role"]):
            st.markdown(mensaje["content"])

    if st.session_state.indice < len(PREGUNTAS):
        st.warning(f"Información incompleta: faltan {len(PREGUNTAS) - st.session_state.indice} parámetros. Todavía no se puede emitir un informe.")
        texto = st.chat_input("Introduce el valor solicitado (solo números)")
        if texto is not None:
            nombre, pregunta, tipo, minimo, maximo = PREGUNTAS[st.session_state.indice]
            try:
                valor = leer_numero(texto, tipo, minimo, maximo)
                st.session_state.datos[nombre] = valor
                st.session_state.historial.append({"role": "user", "content": texto})
                st.session_state.indice += 1
                if st.session_state.indice < len(PREGUNTAS):
                    siguiente = PREGUNTAS[st.session_state.indice][1]
                    st.session_state.historial.append({"role": "assistant", "content": siguiente})
                else:
                    st.session_state.historial.append({"role": "assistant", "content": "Ya tengo los ocho parámetros. A continuación muestro los cálculos reproducibles y las alertas del caso."})
                st.rerun()
            except (ValueError, OverflowError):
                st.error(f"Valor no válido. Introduce un número entre {minimo} y {maximo}.")

    if st.session_state.indice == len(PREGUNTAS):
        s = solicitud_desde_datos({**st.session_state.datos, "tipo_credito": tipo_credito})
        r = evaluar(s)
        st.divider()
        st.subheader("Informe preliminar")
        st.info("**" + r["clasificacion"] + "**. Este resultado es una alerta orientativa para revisión humana; no es una aprobación ni un rechazo.")
        st.caption(r["recomendacion"] + ". " + r["pendientes_producto"])
        c1, c2, c3 = st.columns(3)
        c1.metric("Cuota mensual", f"S/ {r['cuota']:,.2f}")
        c2.metric("Saldo tras todas las obligaciones", f"S/ {r['disponible_despues']:,.2f}")
        c3.metric("Cuota / ingreso", "N/D" if r["ratio_cuota"] is None else f"{r['ratio_cuota']*100:.1f}%")
        c4, c5 = st.columns(2)
        c4.metric("Deudas totales / ingreso", "N/D" if r["ratio_total"] is None else f"{r['ratio_total']*100:.1f}%")
        c5.metric("Intereses totales estimados", f"S/ {r['intereses_estimados']:,.2f}")
        if r["alertas"]:
            st.warning("**Alertas:**\n\n" + "\n\n".join("- " + x for x in r["alertas"]))
        else:
            st.success("No se activaron las alertas académicas definidas en este prototipo.")
        st.caption("Cuota por sistema francés con TEA convertida a tasa efectiva mensual. No incluye seguros, comisiones ni condiciones particulares. 30% y días de mora son umbrales del ejercicio, no políticas oficiales del BCP.")
        with st.expander("Simular pérdida esperada con PD y LGD HIPOTÉTICAS"):
            colpd, collgd = st.columns(2)
            pd = colpd.number_input("PD supuesta (%)", min_value=0.0, max_value=100.0, value=None, step=0.5,
                                    help="No se predice con datos; es un supuesto escrito por el usuario.")
            lgd = collgd.number_input("LGD supuesta (%)", min_value=0.0, max_value=100.0, value=None, step=5.0)
            if pd is not None and lgd is not None:
                el = perdida_esperada_ilustrativa(s.monto, pd, lgd)
                st.metric("Pérdida esperada ilustrativa (EAD × PD × LGD)", f"S/ {el:,.2f}")
            else:
                st.info("Introduce ambos supuestos para calcular. El sistema no asigna probabilidades de incumplimiento.")
            st.caption("EAD se aproxima por el monto del préstamo. Este cálculo no es una previsión bancaria validada.")

with p2:
    st.subheader("Tres alternativas × tres escenarios")
    st.write("Comparación **estratégica** de tecnologías, distinta de la evaluación individual del solicitante. Cifras académicas editables; las alternativas B y C no tienen un modelo ML entrenado en esta versión.")
    with st.form("escenarios_form"):
        c1, c2, c3, c4 = st.columns(4)
        n = c1.number_input("Solicitudes al mes", min_value=1, value=1000, step=100)
        m = c2.number_input("Minutos actuales/solicitud", min_value=1.0, value=30.0, step=5.0)
        c = c3.number_input("Costo por hora (S/)", min_value=0.0, value=30.0, step=5.0)
        b = c4.number_input("Presupuesto de inversión (S/)", min_value=0.0, value=250000.0, step=10000.0)
        horizonte = st.number_input("Horizonte de comparación (meses)", min_value=1, max_value=60, value=12)
        st.form_submit_button("Recalcular escenarios", use_container_width=True)
    filas = comparar_alternativas(n, m, c, b, horizonte)
    display = []
    for x in filas:
        display.append({
            "Alternativa": x["alternativa"], "Escenario": x["escenario"],
            "Reducción supuesta": f"{x['reduccion']*100:.0f}%",
            "Min/solicitud": round(x["tiempo_resultante"], 2),
            "Horas liberadas/mes": round(x["horas_ahorradas_mes"], 1),
            "Beneficio neto (S/)": round(x["beneficio_neto"], 2),
            "Dentro del presupuesto": "Sí" if x["dentro_de_presupuesto"] else "No",
        })
    st.dataframe(display, use_container_width=True, hide_index=True)
    st.caption("Beneficio neto = (horas liberadas × costo/hora − mantenimiento mensual) × horizonte − inversión inicial. Solo monetiza ahorro teórico de tiempo: horas liberadas no equivalen necesariamente a reducción real de gasto.")
    viables = [x for x in filas if x["escenario"] == "Esperado" and x["dentro_de_presupuesto"]]
    if viables:
        mejor = max(viables, key=lambda x: x["beneficio_neto"])
        st.info(f"**En el escenario esperado**, la alternativa {mejor['alternativa']} presenta el mayor beneficio neto **modelado** dentro del presupuesto: S/ {mejor['beneficio_neto']:,.2f}. " +
                ("El resultado es negativo: ninguna alternativa puede justificarse solo con el ahorro de tiempo bajo estos supuestos." if max(x["beneficio_neto"] for x in viables) < 0 else "Debe contrastarse con métricas de precisión del riesgo, cumplimiento y efectos operativos reales."))
    else:
        st.warning("Ninguna inversión inicial cabe en el presupuesto ingresado.")
    salida = io.StringIO()
    writer = csv.DictWriter(salida, fieldnames=display[0].keys())
    writer.writeheader()
    writer.writerows(display)
    st.download_button("Descargar los 9 escenarios (CSV)", salida.getvalue().encode("utf-8-sig"), file_name="escenarios_bcp_riskpredict.csv", mime="text/csv")

with p3:
    st.subheader("Cómo interpretarlo y sustentarlo")
    st.markdown("""
    **Paso 1 – Problema:** fortalecer la identificación y evaluación del riesgo crediticio.

    **Paso 2 – Variables:** ingreso, gastos, otras cuotas, monto, plazo, tasa, estabilidad de ingresos y mora. Los resultados incluyen cuota, saldo, indicadores de endeudamiento y alertas.

    **Paso 3 – Alternativas:** A = reglas y revisión; B = scoring predictivo hipotético; C = chatbot + scoring hipotético. Se evalúan escenarios pesimista, esperado y optimista **en cada alternativa**.

    **Paso 4 – Motor:** reglas condicionales, sistema francés, costos y simulación de tiempos. No hay probabilidades calculadas por ML porque no existe un conjunto de entrenamiento ni calibración.

    **Paso 5 – Construcción:** aplicación Streamlit ejecutable localmente o desde un enlace compartido.

    **Paso 6 – Demostración:** cargar un caso optimista, uno esperado, uno pesimista y luego mostrar las nueve combinaciones estratégicas.

    **Advertencia:** es un ejercicio académico sin relación institucional con el BCP. No se deben introducir datos personales ni usar este prototipo para decidir créditos reales.
    """)

with p4:
    st.subheader("Simular monto, plazo y TEA")
    st.caption("Solo datos ficticios. Cuotas mensuales vencidas, TEA fija y sistema francés, sin gracia ni pagos extraordinarios.")
    st.info("No incluye seguros, comisiones, impuestos, gastos notariales/registrales, tasación ni mora. No calcula TCEA ni constituye una oferta bancaria.")
    base = st.session_state.datos
    with st.form("simulacion"):
        campos = {}
        for nombre, pregunta, tipo, minimo, maximo in PREGUNTAS:
            campos[nombre] = st.number_input(
                pregunta.replace("**", ""), min_value=tipo(minimo), max_value=tipo(maximo),
                value=tipo(base[nombre]) if nombre in base else None,
                step=1 if tipo is int else 0.01, key="sim_" + nombre)
        st.form_submit_button("Calcular simulación")
    try:
        simulada = solicitud_desde_datos({**campos, "tipo_credito": tipo_credito})
        resultado = evaluar(simulada)
        tabla = tabla_amortizacion(simulada.monto, simulada.meses, simulada.tea)
    except ValueError as error:
        st.warning(str(error))
    else:
        st.info(resultado["recomendacion"] + ". No implica aprobación ni rechazo.")
        st.caption(resultado["pendientes_producto"])
        a, b, c = st.columns(3)
        a.metric("Cuota teórica", f"S/ {resultado['cuota']:,.2f}")
        b.metric("Capacidad por flujo", f"S/ {resultado['capacidad_pago']:,.2f}")
        c.metric("Capacidad con reglas académicas", f"S/ {resultado['capacidad_segun_reglas']:,.2f}")
        a, b, c = st.columns(3)
        a.metric("Saldo disponible tras cuota teórica", f"S/ {resultado['disponible_despues']:,.2f}")
        ratio = resultado['ratio_total']
        b.metric("Servicio total de deuda / ingreso", "N/D" if ratio is None else f"{ratio:.1%}")
        c.metric("Cobertura de nueva cuota por flujo", f"{resultado['cobertura_cuota']:.2f} veces")
        perfil = PERFILES[tipo_credito]
        st.caption(f"Capacidad por flujo = máximo de cero e ingreso − gastos − otras cuotas. Capacidad con reglas considera flujo y {perfil.limite_cuota_ingreso:.0%} del ingreso, además del límite total si está configurado. Endeudamiento mide cuotas mensuales, no saldo de deuda.")
        for alerta in resultado["alertas"]:
            st.warning(alerta)
        st.dataframe(tabla, hide_index=True, use_container_width=True)
        st.caption("Importes redondeados a céntimos (mitades hacia arriba); la última cuota se ajusta para cancelar el saldo. Puede diferir de la cuota teórica. Meses iguales: TEM = (1 + TEA/100)^(1/12) − 1.")
        total = sum(fila["cuota"] for fila in tabla)
        interes = sum(fila["interes"] for fila in tabla)
        st.write(f"Total del cronograma: S/ {total:,.2f} · Intereses: S/ {interes:,.2f} · Última cuota: S/ {tabla[-1]['cuota']:,.2f}")
        archivo = io.StringIO()
        escritor = csv.DictWriter(archivo, fieldnames=tabla[0].keys())
        escritor.writeheader()
        escritor.writerows(tabla)
        st.download_button("Descargar amortización (CSV)", archivo.getvalue().encode("utf-8-sig"), "amortizacion.csv", "text/csv")
