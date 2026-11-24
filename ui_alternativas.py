"""Comparador de condiciones del préstamo y registro de la elección humana."""
import streamlit as st

from experiencia.comparador import (
    cancelar_seleccion,
    editar,
    guardar_seleccion,
    obtener,
    proponer_seleccion,
    regenerar,
)
from servicios.alternativas import Alternativa, NOMBRES, PESOS, efectos_principales, interpretar_saldo
from triple_t_pro_layout import section_title
from visualizaciones import estado_saldo


def dinero(valor):
    return "Pendiente" if valor is None else f"S/ {valor:,.2f}"


def porcentaje(ratio):
    return "N/D" if ratio is None else f"{ratio:.2%}"


def puntuacion(valor):
    return "Puntuación pendiente" if valor is None else f"{valor:.2f} / 100"


def condiciones(alternativa):
    plazo = "Plazo pendiente" if alternativa.meses is None else f"{alternativa.meses} meses"
    tea = "TEA pendiente" if alternativa.tea is None else f"TEA {alternativa.tea:.2f}%"
    return f"{dinero(alternativa.monto)} · {plazo} · {tea}"


def fila_escenario(alternativa, escenario):
    resultado = escenario.resultado
    cifras = resultado.cifras
    resiste = {None: "N/D", True: "Sí", False: "No"}[escenario.resiste]
    return {
        "Alternativa": alternativa.codigo,
        "Escenario": escenario.nombre,
        "Caída de ingreso": f"{escenario.caida:.2f}%",
        "Ingreso del escenario": dinero(cifras.get("ingresos_admisibles")),
        "Cuota base": dinero(cifras.get("cuota_base")),
        "Pago mensual con cargos": dinero(cifras.get("pago_mensual_total")),
        "Cargos mensuales": dinero(cifras.get("cargos_mensuales")),
        "Cargos iniciales": dinero(cifras.get("cargos_iniciales")),
        "DTI": porcentaje(cifras.get("dti_total")),
        "Saldo después del pago": dinero(cifras.get("saldo_post_cuota")),
        "Capacidad de pago": dinero(cifras.get("capacidad_neta")),
        "Intereses": dinero(cifras.get("intereses")),
        "Pagos totales": dinero(cifras.get("total_pagos")),
        "TCEA referencial": "Pendiente" if resultado.tcea is None else porcentaje(resultado.tcea),
        "Resiste": resiste,
        "Puntuación": puntuacion(escenario.puntaje),
        "Alertas": " · ".join(aviso["mensaje"] for aviso in resultado.reglas) or "Sin alertas del motor",
        "Supuestos": " · ".join(resultado.supuestos),
    }


def titulo_alternativa(c, alternativa):
    exp = c.expediente
    if alternativa.codigo == "A" and (alternativa.monto, alternativa.meses, alternativa.tea) == (exp.monto, exp.meses, exp.tea):
        enfoque = "Mantener condiciones"
    elif (alternativa.codigo == "B" and alternativa.monto == exp.monto and alternativa.tea == exp.tea
          and alternativa.meses is not None and exp.meses is not None and alternativa.meses > exp.meses):
        enfoque = "Ampliar plazo"
    elif (alternativa.codigo == "C" and alternativa.meses == exp.meses and alternativa.tea == exp.tea
          and alternativa.monto is not None and exp.monto is not None and alternativa.monto < exp.monto):
        enfoque = "Reducir monto"
    else:
        enfoque = "Condiciones ajustadas" if None not in (alternativa.monto, alternativa.meses, alternativa.tea) else "Completar condiciones"
    return f"Alternativa {alternativa.codigo} · {enfoque}"


def analizar_alternativa(c, codigo):
    if c.alternativa_propuesta != codigo:
        cancelar_seleccion(c)
    c.alternativa_en_contexto = codigo
    c.vista = "ALTERNATIVAS"
    st.session_state.pestana_analisis = "Alternativas"
    st.session_state.pop("matriz_crediticia_visible", None)


def tarjeta(c, evaluacion, base):
    alternativa = evaluacion.alternativa
    cifras = evaluacion.escenarios[1].resultado.cifras
    beneficio, desventaja = efectos_principales(evaluacion, base)
    with st.container(border=True, gap="small", key=f"tt_alt_card_comparador_{alternativa.codigo}"):
        st.markdown(f"**{titulo_alternativa(c, alternativa)}**")
        st.caption(condiciones(alternativa))
        st.markdown(f"Cuota mensual **{dinero(cifras.get('cuota_base'))}**")
        pago = cifras.get("pago_mensual_total")
        if pago is not None and pago != cifras.get("cuota_base"):
            st.caption(f"Pago con cargos {dinero(pago)}")
        st.caption(f"Escenario esperado · DTI {porcentaje(cifras.get('dti_total'))} · Saldo {dinero(cifras.get('saldo_post_cuota'))}")
        st.markdown(f"Puntuación académica **{puntuacion(evaluacion.puntaje_global)}**")
        if evaluacion.preliminar and evaluacion.puntaje_global is not None:
            st.caption("Evaluación preliminar")
        st.caption(beneficio)
        st.caption(desventaja)
        st.button(f"Analizar alternativa {alternativa.codigo}",
                  key=f"comparador_analizar_{alternativa.codigo}", width="stretch",
                  on_click=analizar_alternativa, args=(c, alternativa.codigo))


def detalle_resultado(c, evaluacion, base):
    alternativa = evaluacion.alternativa
    st.markdown(f"### {titulo_alternativa(c, alternativa)}")
    st.caption(f"{condiciones(alternativa)} · Puntuación académica {puntuacion(evaluacion.puntaje_global)}")
    if evaluacion.motivo_pendiente:
        st.warning(evaluacion.motivo_pendiente)
    beneficio, desventaja = efectos_principales(evaluacion, base)
    st.markdown("**Consecuencias de aplicar la alternativa**")
    st.write(f"{beneficio} {desventaja}")
    esperado = evaluacion.escenarios[1].resultado
    saldo_esperado = interpretar_saldo(esperado)
    st.write(f"En el escenario esperado, {saldo_esperado[0].lower() + saldo_esperado[1:]}")
    for etiqueta, escenario in (("Más favorable", evaluacion.favorable), ("Más desfavorable", evaluacion.desfavorable)):
        if escenario is None:
            continue
        cifras = escenario.resultado.cifras
        st.caption(f"{etiqueta} por saldo mensual · {escenario.nombre} · caída {escenario.caida:.2f}% · "
                   f"saldo {dinero(cifras.get('saldo_post_cuota'))} · DTI {porcentaje(cifras.get('dti_total'))}")
    st.markdown("**Tres escenarios de ingreso**")
    for columna, escenario in zip(st.columns(3, gap="small"), evaluacion.escenarios):
        with columna:
            tarjeta_escenario(escenario)
    if evaluacion.desfavorable and evaluacion.desfavorable is not evaluacion.escenarios[1]:
        st.caption(interpretar_saldo(evaluacion.desfavorable.resultado))
    with st.expander("Comparación con la solicitud original y puntuación por criterio"):
        for parrafo in evaluacion.consecuencias:
            if not parrafo.startswith(tuple(NOMBRES)):
                st.text(parrafo)
        filas = []
        for escenario in evaluacion.escenarios:
            fila = {"Escenario": escenario.nombre}
            for criterio, peso in PESOS.items():
                componente = escenario.componentes.get(criterio)
                fila[f"{criterio} ({peso:.0%})"] = "N/D" if componente is None else f"{componente:.2f}"
            fila["Puntuación"] = puntuacion(escenario.puntaje)
            filas.append(fila)
        st.dataframe(filas, hide_index=True, width="stretch")
        st.caption(f"Promedio académico de escenarios, sin probabilidades asignadas · {puntuacion(evaluacion.puntaje_global)}")
    with st.expander("Alertas y supuestos de la alternativa"):
        avisos, supuestos = {}, {}
        for escenario in evaluacion.escenarios:
            for aviso in escenario.resultado.reglas:
                avisos.setdefault(aviso["mensaje"], []).append(escenario.nombre)
            for supuesto in escenario.resultado.supuestos:
                supuestos.setdefault(supuesto, []).append(escenario.nombre)
        for mensaje, etiquetas in avisos.items():
            st.text(f"{', '.join(etiquetas)} · {mensaje}")
        if not avisos:
            st.caption("Sin alertas del motor.")
        for mensaje, etiquetas in supuestos.items():
            st.caption(f"{', '.join(etiquetas)} · {mensaje}")


def formulario_edicion(c, alternativa):
    with st.expander(f"Editar alternativa {alternativa.codigo}"):
        # Cambiar condiciones regeneradas reinicia los widgets con los nuevos valores.
        version = hash((alternativa.monto, alternativa.meses, alternativa.tea, alternativa.caidas))
        clave = f"editar_alternativa_{c.revision}_{alternativa.codigo}_{version}"
        with st.form(clave):
            monto = st.number_input("Monto (S/)", min_value=0.01, max_value=1e10,
                                    value=None if alternativa.monto is None else float(alternativa.monto),
                                    format="%.2f", key=clave + "_monto")
            meses = st.number_input("Plazo (meses)", min_value=1, max_value=360, value=alternativa.meses)
            tea = st.number_input("TEA supuesta (%)", min_value=0.0, max_value=float(c.config.tea_maxima),
                                  value=None if alternativa.tea is None else float(alternativa.tea), format="%.4f")
            st.caption("Indica caídas respecto al ingreso admisible base. El orden debe ser optimista ≤ esperado ≤ pesimista.")
            caidas = tuple(st.number_input(f"{nombre} · caída (%)", min_value=0.0, max_value=100.0,
                                           value=float(caida), key=f"{clave}_{nombre}")
                           for nombre, caida in zip(NOMBRES, alternativa.caidas))
            aplicar = st.form_submit_button(f"Aplicar cambios a {alternativa.codigo}")
        if aplicar:
            try:
                if any(valor is None for valor in (monto, meses, tea, *caidas)):
                    raise ValueError("Completa monto, plazo, TEA y las tres caídas de ingresos.")
                editar(c, Alternativa(alternativa.codigo, monto, meses, tea, caidas))
                c.alternativa_en_contexto = alternativa.codigo
                st.rerun()
            except ValueError as error:
                st.warning(str(error))


def mostrar_seleccion(c, ambito="resumen"):
    if not c.flujo or c.flujo.revision_confirmada != c.revision or c.pendiente:
        return
    seleccion = c.seleccion_alternativa
    if seleccion is None or seleccion.revision != c.revision:
        return
    with st.container(border=True, key=f"tt_seleccion_alternativa_{ambito}"):
        st.markdown(f"**Alternativa {seleccion.codigo} seleccionada**")
        st.caption(f"{condiciones(seleccion.evaluacion.alternativa)} · {puntuacion(seleccion.evaluacion.puntaje_global)} · "
                   f"{seleccion.fecha:%d/%m/%Y %H:%M %Z}")
        st.text(f"Justificación: {seleccion.justificacion}")


def eleccion(c, evaluacion):
    alternativa = evaluacion.alternativa
    codigo = alternativa.codigo
    if c.seleccion_alternativa and c.seleccion_alternativa.codigo == codigo and c.alternativa_propuesta is None:
        mostrar_seleccion(c, "detalle")
        return
    if c.alternativa_propuesta != codigo:
        if st.button("Seleccionar esta alternativa", key=f"seleccionar_detalle_{codigo}",
                     type="primary", disabled=not evaluacion.seleccionable):
            try:
                proponer_seleccion(c, codigo)
                st.rerun()
            except ValueError as error:
                st.warning(str(error))
        if not evaluacion.seleccionable:
            st.caption("Completa las condiciones y calcula la cuota para registrar la elección.")
        return
    with st.container(border=True):
        st.markdown(f"**Confirmar alternativa {codigo}**")
        st.caption(f"{condiciones(alternativa)} · {puntuacion(evaluacion.puntaje_global)}")
        with st.form(f"confirmar_alternativa_{c.revision}_{codigo}"):
            justificacion = st.text_area("Justificación breve, sin datos personales", max_chars=300,
                                         placeholder="Explica qué indicador o condición motivó tu elección.")
            with st.container(horizontal=True):
                confirmar = st.form_submit_button("Confirmar selección", type="primary")
                cancelar = st.form_submit_button("Cancelar selección")
        if confirmar:
            try:
                guardar_seleccion(c, codigo, justificacion)
                st.rerun()
            except ValueError as error:
                st.warning(str(error))
        if cancelar:
            cancelar_seleccion(c)
            st.rerun()


def metodologia(comparativa):
    with st.expander("Supuestos, pesos y escalas"):
        st.write("Escenarios de estrés con caídas de ingreso iniciales de 0%, 10% y 30%. Se mantienen gastos y otras cuotas. "
                 "La TEA editada es un supuesto y el costo total corresponde a los cargos registrados.")
        st.write("Índice comparativo académico de 0 a 100. DTI y capacidad financiera miden aspectos relacionados del mismo flujo. "
                 "El promedio de escenarios asigna el mismo peso a los tres resultados, sin probabilidades de ocurrencia.")
        umbral = porcentaje(comparativa.umbral_dti)
        escala = comparativa.escala
        explicaciones = {
            "DTI": f"100 puntos hasta {umbral} de DTI; disminuye linealmente a cero en {porcentaje(escala.dti_minimo)}.",
            "Capacidad": f"El saldo mensual puntúa hasta su objetivo de {porcentaje(escala.saldo_objetivo)} del ingreso admisible base.",
            "Resistencia": f"Fracción de los tres escenarios con saldo no negativo y DTI de hasta {umbral}.",
            "Intereses": f"Intereses sobre el capital de la alternativa; la escala llega a cero puntos en {porcentaje(escala.intereses_minimo)}.",
            "Cobertura": "Monto de la alternativa sobre monto solicitado, hasta 100 puntos.",
        }
        st.dataframe([{"Criterio": criterio, "Peso": porcentaje(peso), "Escala": explicaciones[criterio]}
                      for criterio, peso in PESOS.items()], hide_index=True, width="stretch")


def tarjetas_alternativas(c, comparativa):
    st.info(comparativa.recomendacion)
    for columna, evaluacion in zip(st.columns(3, gap="small"), comparativa.alternativas):
        with columna:
            tarjeta(c, evaluacion, comparativa.base)


def tarjeta_escenario(escenario):
    cifras = escenario.resultado.cifras
    saldo = cifras.get("saldo_post_cuota")
    estado, color = estado_saldo(saldo)
    nombre = escenario.nombre.lower()
    with st.container(border=True, gap="small", key=f"tt_escenario_{nombre}"):
        st.markdown(f"**{escenario.nombre}** · caída de {escenario.caida:.0f}%")
        st.caption(f"Ingreso {dinero(cifras.get('ingresos_admisibles'))} · DTI {porcentaje(cifras.get('dti_total'))}")
        saldo_texto = "Saldo pendiente" if saldo is None else f"{estado}: {dinero(saldo)}"
        st.markdown(f":{color}[**{saldo_texto}**]")
        st.caption(puntuacion(escenario.puntaje))
        if saldo is not None and saldo < 0:
            st.caption("El ingreso no cubre todos los gastos y pagos.")


def volver_al_listado(c):
    cancelar_seleccion(c)
    c.alternativa_en_contexto = None
    st.session_state.pop("matriz_crediticia_visible", None)


def abrir_matriz(c):
    volver_al_listado(c)
    st.session_state.matriz_crediticia_visible = c.revision


def mostrar_matriz(comparativa):
    section_title("Matriz de nueve resultados", "chart")
    filas = [fila_escenario(e.alternativa, escenario) for e in comparativa.alternativas for escenario in e.escenarios]
    orden = ("Alternativa", "Escenario", "Saldo después del pago", "DTI", "Pago mensual con cargos", "Caída de ingreso", "Puntuación")
    columnas = (*orden, *(k for k in filas[0] if k not in orden))
    st.dataframe(filas, column_order=columnas, hide_index=True, width="stretch", height=360)
    st.caption("Desplázate dentro de la tabla para ver ingresos, cargos, alertas y demás indicadores.")
    metodologia(comparativa)


def mostrar_alternativas(c):
    try:
        comparativa = obtener(c)
    except ValueError as error:
        st.info(str(error))
        return
    evaluaciones = {e.alternativa.codigo: e for e in comparativa.alternativas}
    evaluacion = evaluaciones.get(c.alternativa_en_contexto)
    if evaluacion is not None or st.session_state.get("matriz_crediticia_visible") == c.revision:
        st.button("Volver a alternativas", icon=":material/arrow_back:", on_click=volver_al_listado, args=(c,))
    if evaluacion is not None:
        with st.container(key=f"tt_alternativa_detalle_{evaluacion.alternativa.codigo}"):
            detalle_resultado(c, evaluacion, comparativa.base)
            eleccion(c, evaluacion)
            formulario_edicion(c, evaluacion.alternativa)
        return
    if st.session_state.get("matriz_crediticia_visible") == c.revision:
        mostrar_matriz(comparativa)
        return
    section_title("Alternativas del préstamo", "scale")
    tarjetas_alternativas(c, comparativa)
    st.button("Ver matriz general de nueve escenarios", icon=":material/table_chart:", on_click=abrir_matriz, args=(c,))
    if st.button("Restablecer alternativas y caídas iniciales", key="regenerar_alternativas"):
        try:
            regenerar(c)
            st.rerun()
        except ValueError as error:
            st.warning(str(error))
