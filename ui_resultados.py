import csv
import io
from decimal import Decimal as D
import streamlit as st
from visualizaciones import filas_visibles, mostrar_graficos

def mostrar_resultado(resultado, base=None, *, mostrar_alertas=True):
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
    if mostrar_alertas:
        for regla in resultado.reglas:
            st.warning(regla["mensaje"])
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
