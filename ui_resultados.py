"""Cronograma y sustento de ingresos del expediente vigente."""
import csv
import io

import streamlit as st

from visualizaciones import filas_visibles


def mostrar_resultado(resultado, base=None):
    if resultado.tabla:
        filas = filas_visibles(resultado.tabla)
        columnas = {
            "periodo": "Mes",
            "pago_total": "Pago",
            "amortizacion": "Capital",
            "interes": "Interés",
        }
        if any(fila["cargos"] for fila in resultado.tabla):
            columnas["cargos"] = "Cargos"
        columnas["saldo_final"] = "Saldo pendiente"

        st.dataframe(
            [{titulo: fila[campo] for campo, titulo in columnas.items()} for fila in filas],
            hide_index=True,
            width="stretch",
            column_config={titulo: st.column_config.NumberColumn(format="%.2f")
                           for campo, titulo in columnas.items() if campo != "periodo"},
        )
        st.caption("Importes en soles. El redondeo a céntimos puede causar pequeñas diferencias al sumar las filas.")

        salida = io.StringIO()
        writer = csv.DictWriter(salida, fieldnames=filas[0].keys())
        writer.writeheader()
        writer.writerows(filas)
        st.download_button(
            "Descargar amortización (CSV)", salida.getvalue().encode("utf-8-sig"),
            "amortizacion.csv", "text/csv", key="csv_sim" if base is not None else "csv_base",
        )
    else:
        st.info("Completa las condiciones del préstamo para calcular el cronograma de pagos.")

    if resultado.meses_ingreso:
        with st.expander("Ingresos documentados por mes"):
            filas = filas_visibles(resultado.meses_ingreso)
            st.dataframe(
                [{"Mes": fila["mes"], "Ingreso neto (S/)": fila["neto"],
                  "Extraordinarios excluidos (S/)": fila["extraordinarios_excluidos"],
                  "Documento": fila["origen"]} for fila in filas],
                hide_index=True,
                width="stretch",
                column_config={campo: st.column_config.NumberColumn(format="%.2f")
                               for campo in ("Ingreso neto (S/)", "Extraordinarios excluidos (S/)")},
            )
