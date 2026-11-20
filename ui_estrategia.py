import streamlit as st
import csv
import io
from motor import comparar_alternativas

def mostrar_estrategia():

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

