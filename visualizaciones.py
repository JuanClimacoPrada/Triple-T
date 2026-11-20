"""Presentación basada exclusivamente en resultados del motor."""
from decimal import Decimal


def filas_visibles(tabla):
    return [{k: round(float(v), 2) if isinstance(v, Decimal) else v for k, v in f.items()} for f in tabla]


def mostrar_graficos(st, resultado, base=None):
    try:
        import pandas as pd
        if resultado.tabla:
            datos = pd.DataFrame(filas_visibles(resultado.tabla)).set_index("periodo")
            st.line_chart(datos[["saldo_final"]])
            st.bar_chart(datos[["amortizacion", "interes"]])
        if "ingresos_admisibles" in resultado.cifras:
            st.bar_chart(pd.DataFrame({"S/": {k: float(resultado.cifras[k]) for k in
                ("ingresos_admisibles", "gastos", "otras_cuotas", "capacidad_neta", "saldo_post_cuota")}}))
        if base and "saldo_post_cuota" in resultado.cifras:
            st.bar_chart(pd.DataFrame({nombre: {k: float(r.cifras[k]) for k in
                ("ingresos_admisibles", "pago_mensual_total", "saldo_post_cuota")}
                for nombre, r in (("Base", base), ("Simulación", resultado))}))
    except Exception:
        st.warning("Gráficos no disponibles. Los valores calculados siguen disponibles en las tablas.")
