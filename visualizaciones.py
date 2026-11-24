"""Presentación basada exclusivamente en resultados del motor."""
from decimal import Decimal

import pandas as pd


COLORES_SALDO = {"green": "#19784a", "red": "#b52f36", "gray": "#677689"}


def filas_visibles(tabla):
    return [{k: round(float(v), 2) if isinstance(v, Decimal) else v for k, v in f.items()} for f in tabla]


def estado_saldo(valor):
    if valor is None:
        return "Pendiente", "gray"
    if valor < 0:
        return "Déficit", "red"
    if valor > 0:
        return "Disponible", "green"
    return "Sin margen", "gray"


def _mostrar_saldos(st, titulo, saldos, eje):
    filas = []
    for etiqueta, saldo in saldos:
        if saldo is not None:
            estado, color = estado_saldo(saldo)
            filas.append({eje: etiqueta, "Saldo (S/)": float(saldo), "Estado": estado, "Color": COLORES_SALDO[color]})
    if not filas:
        return
    st.subheader(titulo)
    st.bar_chart(pd.DataFrame(filas), x=eje, y="Saldo (S/)", color="Color", horizontal=True, sort=False,
                 height=max(160, len(filas) * 36), alt=titulo)
    st.caption("Verde: queda saldo. Rojo: hay déficit. Gris: queda S/ 0.")


def mostrar_graficos(st, resultado, base=None, comparativa=None):
    """Gráficos del resultado vigente, la simulación y las alternativas comparables."""
    if resultado is None:
        return

    if resultado.tabla:
        datos = pd.DataFrame(filas_visibles(resultado.tabla)).rename(columns={
            "periodo": "Mes", "saldo_final": "Saldo pendiente", "amortizacion": "Capital", "interes": "Interés",
        })
        st.subheader("Evolución de la deuda")
        st.line_chart(datos, x="Mes", y="Saldo pendiente", y_label="S/", color="#1459ba", height=210,
                      alt="Saldo de deuda pendiente al terminar cada mes")
        st.subheader("Capital e intereses por cuota")
        st.bar_chart(datos, x="Mes", y=["Capital", "Interés"], y_label="S/",
                     color=["#1459ba", "#67a8e9"], stack=True, height=220,
                     alt="Capital amortizado e interés pagado en cada cuota")

    _mostrar_saldos(st, "Margen mensual antes y después de la nueva cuota", (
        ("Antes de pagarla", resultado.cifras.get("saldo_pre_cuota")),
        ("Después de pagarla", resultado.cifras.get("saldo_post_cuota")),
    ), "Momento")

    if base is not None:
        filas = []
        for campo, etiqueta in (("ingresos_admisibles", "Ingreso admisible"), ("pago_mensual_total", "Pago mensual"),
                                ("saldo_post_cuota", "Saldo mensual"), ("intereses", "Intereses totales")):
            previo, simulado = base.cifras.get(campo), resultado.cifras.get(campo)
            if previo is not None and simulado is not None:
                filas.append({"Indicador": etiqueta, "Base": float(previo), "Simulación": float(simulado)})
        if filas:
            st.subheader("Caso base frente a la simulación")
            st.bar_chart(pd.DataFrame(filas), x="Indicador", y=["Base", "Simulación"], y_label="S/",
                         color=["#1957aa", "#5babe5"], horizontal=True, sort=False, stack=False, height=245,
                         alt="Comparación de ingreso, pago, saldo e intereses entre caso base y simulación")

    if comparativa is not None:
        saldos = [
            (f"{e.alternativa.codigo} · {s.nombre}", s.resultado.cifras.get("saldo_post_cuota"))
            for e in comparativa.alternativas for s in e.escenarios
        ]
        _mostrar_saldos(st, "Saldo mensual por alternativa y escenario", saldos, "Alternativa · escenario")
