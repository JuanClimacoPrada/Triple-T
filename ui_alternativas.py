"""Comparador de condiciones del préstamo y registro de la elección humana."""
import streamlit as st

from conversacion.gestor import decir
from experiencia.comparador import (
    cancelar_seleccion,
    editar,
    guardar_seleccion,
    obtener,
    proponer_seleccion,
    regenerar,
)
from servicios.alternativas import Alternativa, NOMBRES, PESOS
from triple_t_pro_layout import section_title


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


def tarjeta(c, evaluacion, base):
    alternativa = evaluacion.alternativa
    escenario = evaluacion.escenarios[1]
    cifras = escenario.resultado.cifras
    with st.container(border=True):
        st.markdown(f"**Alternativa {alternativa.codigo}**")
        st.caption(condiciones(alternativa))
        st.markdown(f"**{puntuacion(evaluacion.puntaje_global)}**")
        st.caption(f"Pago esperado {dinero(cifras.get('pago_mensual_total'))} · Cobertura {porcentaje(evaluacion.cobertura)}")
        pago_base = base.cifras.get("pago_mensual_total")
        pago = cifras.get("pago_mensual_total")
        if pago is not None and pago_base is not None and pago != pago_base:
            direccion = "menos" if pago < pago_base else "más"
            st.caption(f"{dinero(abs(pago - pago_base))} {direccion} al mes frente al caso base.")
        interes_base = base.cifras.get("intereses")
        interes = cifras.get("intereses")
        if interes is not None and interes_base is not None and interes != interes_base:
            direccion = "menos" if interes < interes_base else "más"
            st.caption(f"{dinero(abs(interes - interes_base))} {direccion} de intereses frente al caso base.")
        if evaluacion.preliminar and evaluacion.puntaje_global is not None:
            st.caption("Evaluación preliminar")
        if st.button("Ver consecuencias", key=f"ver_alternativa_{alternativa.codigo}", width="stretch"):
            c.alternativa_en_contexto = alternativa.codigo
            c.vista = "ALTERNATIVAS"
            resumen = [linea for linea in evaluacion.consecuencias if linea.startswith((
                "Pago mensual con cargos", "Intereses", "El monto cubre",
            ))]
            detalle = " ".join(resumen or evaluacion.consecuencias[:1])
            decir(c, f"Alternativa {alternativa.codigo}. {detalle} Puedes revisar los tres escenarios en el comparador.")
            st.rerun()
        if st.button(f"Seleccionar alternativa {alternativa.codigo}", key=f"elegir_alternativa_{alternativa.codigo}",
                     width="stretch", disabled=not evaluacion.seleccionable):
            try:
                proponer_seleccion(c, alternativa.codigo)
                st.rerun()
            except ValueError as error:
                st.warning(str(error))


def detalle_resultado(evaluacion):
    alternativa = evaluacion.alternativa
    if evaluacion.motivo_pendiente:
        st.warning(evaluacion.motivo_pendiente)
    for parrafo in evaluacion.consecuencias:
        st.write(parrafo)
    for etiqueta, escenario in (("Más favorable", evaluacion.favorable), ("Más desfavorable", evaluacion.desfavorable)):
        if escenario is None:
            continue
        cifras = escenario.resultado.cifras
        st.caption(f"{etiqueta} por saldo mensual · {escenario.nombre} · caída {escenario.caida:.2f}% · "
                   f"saldo {dinero(cifras.get('saldo_post_cuota'))} · DTI {porcentaje(cifras.get('dti_total'))}")
    st.dataframe([fila_escenario(alternativa, escenario) for escenario in evaluacion.escenarios],
                 hide_index=True, width="stretch", column_config={"Alternativa": None})
    with st.container(border=True):
        st.markdown("**Puntuación por criterio y alertas**")
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
        for escenario in evaluacion.escenarios:
            st.markdown(f"**{escenario.nombre} · caída {escenario.caida:.2f}%**")
            for aviso in escenario.resultado.reglas:
                st.text(aviso["mensaje"])
            if not escenario.resultado.reglas:
                st.caption("Sin alertas del motor.")
            for supuesto in escenario.resultado.supuestos:
                st.caption(supuesto)


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


def eleccion(c, evaluaciones):
    propuesta = c.alternativa_propuesta
    seleccion = c.seleccion_alternativa
    if seleccion is not None:
        st.success(f"Alternativa {seleccion.codigo} seleccionada")
        st.caption(f"{condiciones(seleccion.evaluacion.alternativa)} · {puntuacion(seleccion.evaluacion.puntaje_global)} · "
                   f"{seleccion.fecha:%d/%m/%Y %H:%M %Z}")
        st.text(f"Justificación: {seleccion.justificacion}")
    if propuesta is None:
        return
    evaluacion = evaluaciones[propuesta]
    alternativa = evaluacion.alternativa
    with st.container(border=True):
        st.markdown(f"**Confirmar alternativa {propuesta}**")
        st.caption(f"{condiciones(alternativa)} · {puntuacion(evaluacion.puntaje_global)}")
        st.dataframe([fila_escenario(alternativa, escenario) for escenario in evaluacion.escenarios],
                     hide_index=True, width="stretch",
                     column_config={"Alternativa": None, "Supuestos": None})
        with st.form(f"confirmar_alternativa_{c.revision}_{propuesta}", clear_on_submit=True):
            justificacion = st.text_area("Justificación breve, sin datos personales", max_chars=300)
            with st.container(horizontal=True):
                confirmar = st.form_submit_button("Confirmar selección", type="primary")
                cancelar = st.form_submit_button("Cancelar selección")
        if confirmar:
            try:
                guardar_seleccion(c, propuesta, justificacion)
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


def mostrar_alternativas(c):
    section_title("Comparación de alternativas del préstamo", "scale")
    try:
        comparativa = obtener(c)
    except ValueError as error:
        st.info(str(error))
        return
    st.caption("Tres condiciones de crédito para el mismo expediente y tres escenarios de ingreso por alternativa.")
    st.info(comparativa.recomendacion)
    evaluaciones = {e.alternativa.codigo: e for e in comparativa.alternativas}
    for columna, evaluacion in zip(st.columns(3, gap="small"), evaluaciones.values()):
        with columna:
            tarjeta(c, evaluacion, comparativa.base)
    eleccion(c, evaluaciones)

    codigo = c.alternativa_en_contexto
    for item, evaluacion in evaluaciones.items():
        with st.expander(f"Consecuencias y tres escenarios de {item}", expanded=codigo == item):
            detalle_resultado(evaluacion)

    with st.expander("Matriz de nueve resultados"):
        filas = [fila_escenario(e.alternativa, escenario) for e in evaluaciones.values() for escenario in e.escenarios]
        st.dataframe(filas, hide_index=True, width="stretch", height=360)
        st.caption("Desplázate dentro de la tabla para ver costos, alertas, supuestos y puntuación de cada escenario.")

    for evaluacion in evaluaciones.values():
        formulario_edicion(c, evaluacion.alternativa)
    metodologia(comparativa)
    if st.button("Restablecer alternativas y caídas iniciales", key="regenerar_alternativas"):
        try:
            regenerar(c)
            st.rerun()
        except ValueError as error:
            st.warning(str(error))
