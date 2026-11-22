"""Presentación aislada de supuestos: nunca modifica el expediente ni llama IA."""
from datetime import date
import streamlit as st
from servicios.riesgo import EscenarioHipotetico, NOMBRES, advertencias
from servicios.proveedores_riesgo import ScoreDemostracion
from triple_t_pro_layout import MetricCard, cards_html, section_title, score_html


def porcentaje(valor):
    return "No disponible" if valor is None else f"{valor:.2f}%"


def importe(valor):
    return "No disponible" if valor is None else f"S/ {valor:,.2f}"


def estado_riesgo(c):
    estado = st.session_state.get("riesgo_demo")
    if estado is None or estado["revision"] != c.revision:
        estado = dict(revision=c.revision, escenarios={n: EscenarioHipotetico(n) for n in NOMBRES}, score=None)
        st.session_state.riesgo_demo = estado
    return estado


def mostrar_riesgo(c, vm, detalle=False):
    estado = estado_riesgo(c)
    section_title("Evaluación del riesgo crediticio", "scale")
    st.caption("No hay PD validada ni score externo verificado. Los supuestos no representan probabilidades reales de clientes ni deciden un crédito.")
    if not detalle:
        e = estado["escenarios"]["Esperado"]
        capacidad = next(m for m in vm.metrics if m.label == "Capacidad de pago mensual")
        st.markdown(cards_html([
            MetricCard("Score crediticio verificado", "No disponible", "Sin consulta autorizada verificable"),
            MetricCard("No incumplimiento hipotético · Esperado", porcentaje(e.no_incumplimiento), f"Fuente: {e.fuente}. Horizonte: {str(e.horizonte_meses) + ' meses' if e.horizonte_meses else 'pendiente'}. HIPOTÉTICA"),
            capacidad,
        ]), unsafe_allow_html=True)
        st.caption("Escenarios editables, score simulado y enlace Sentinel en Indicadores. Al cambiar el expediente se limpian estos supuestos.")
        return
    st.markdown(score_html(vm.sentinel_url), unsafe_allow_html=True)
    score = estado["score"]
    if score:
        st.info(f"Score de demostración: {score.valor}/{score.escala_maxima} · SIMULADO · {score.fecha.isoformat()} · Fuente: {score.fuente}. No es un score crediticio verificado.")
    with st.expander("Registrar score de demostración"):
        st.caption("Fuente fija: registro manual simulado. Escala ilustrativa de cero al máximo elegido; no se atribuye a Sentinel ni se convierte en PD.")
        with st.form(f"score_demo_{c.revision}"):
            valor = st.number_input("Score simulado", min_value=0, max_value=100000, value=None, key=f"score_valor_{c.revision}")
            escala = st.number_input("Máximo de escala ilustrativa", min_value=1, max_value=100000, value=None, key=f"score_escala_{c.revision}")
            fecha = st.date_input("Fecha del registro simulado", value=date.today(), max_value=date.today())
            simulado = st.checkbox("Confirmo que es un dato simulado, sin consulta ni datos reales")
            guardar = st.form_submit_button("Guardar score simulado")
        if guardar:
            try:
                estado["score"] = ScoreDemostracion(valor, escala, fecha, simulado)
                st.rerun()
            except ValueError as error:
                st.warning(str(error))
        if score and st.button("Eliminar score simulado"):
            estado["score"] = None
            st.rerun()
    st.subheader("Escenarios probabilísticos hipotéticos")
    st.caption("PD = probabilidad supuesta de incumplimiento en el horizonte indicado. No incumplimiento = 100% − PD. Pérdida ilustrativa = exposición × PD/100 × LGD/100. LGD es la fracción porcentual que se supone perder si ocurre el incumplimiento. No se anualizan las PD ni se descuentan pérdidas.")
    for nombre in NOMBRES:
        e = estado["escenarios"][nombre]
        with st.expander(f"Editar escenario {nombre.lower()}"):
            with st.form(f"riesgo_{nombre}_{c.revision}"):
                pd = st.number_input("PD supuesta (%)", min_value=0., max_value=100., value=None if e.pd is None else float(e.pd), key=f"pd_{nombre}_{c.revision}")
                horizonte = st.number_input("Horizonte de evaluación (meses)", min_value=1, max_value=1200, value=e.horizonte_meses, key=f"horizonte_{nombre}_{c.revision}")
                lgd = st.number_input("LGD supuesta (%)", min_value=0., max_value=100., value=None if e.lgd is None else float(e.lgd), key=f"lgd_{nombre}_{c.revision}")
                exposicion = st.number_input("Exposición supuesta del escenario (S/)", min_value=0., max_value=1e10, value=None if e.exposicion is None else float(e.exposicion), key=f"exposicion_{nombre}_{c.revision}")
                st.caption("Fuente: supuesto manual del analista para demostración. La exposición no se copia del expediente.")
                guardar = st.form_submit_button("Guardar escenario " + nombre.lower())
            if guardar:
                try:
                    estado["escenarios"][nombre] = EscenarioHipotetico(nombre, pd, horizonte, lgd, exposicion)
                    st.rerun()
                except ValueError as error:
                    st.warning(str(error))
    escenarios = list(estado["escenarios"].values())
    for mensaje in advertencias(escenarios):
        st.warning(mensaje)
    for e in escenarios:
        st.markdown(cards_html([
            MetricCard(e.nombre + " · PD hipotética", porcentaje(e.pd)),
            MetricCard("No incumplimiento hipotético", porcentaje(e.no_incumplimiento)),
            MetricCard("Pérdida esperada ilustrativa", importe(e.perdida_esperada)),
        ]), unsafe_allow_html=True)
        st.caption(f"{e.naturaleza} · Fuente: {e.fuente} · Horizonte: {str(e.horizonte_meses) + ' meses' if e.horizonte_meses else 'pendiente'} · LGD: {porcentaje(e.lgd)} · Exposición: {importe(e.exposicion)}")
    graficables = [e for e in escenarios if e.pd is not None]
    if graficables:
        import pandas as pd
        tabla = pd.DataFrame([{"Escenario e horizonte": f"{e.nombre} · {e.horizonte_meses} meses", "Incumplimiento hipotético (%)": float(e.pd), "No incumplimiento hipotético (%)": float(e.no_incumplimiento)} for e in graficables]).set_index("Escenario e horizonte")
        st.bar_chart(tabla, stack=False)
        st.caption("Comparación de supuestos, no predicciones. Los escenarios sin PD se omiten del gráfico, no se representan como cero.")
    else:
        st.info("Probabilidades no disponibles. Registra una PD supuesta y su horizonte para visualizar la comparación.")
