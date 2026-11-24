"""Comparador de condiciones del préstamo y registro de la elección humana."""
from html import escape

import streamlit as st

from conversacion.gestor import decir, generar_informe
from experiencia.comparador import (
    cancelar_seleccion,
    editar,
    guardar_seleccion,
    obtener,
    proponer_seleccion,
    regenerar,
)
from servicios.alternativas import Alternativa, NOMBRES, PESOS, efectos_principales, interpretar_saldo
from triple_t_pro_layout import dinero, icon, section_title, status_banner_html
from visualizaciones import estado_saldo


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


def titulo_alternativa(c, alternativa, *, corto=False):
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
    titulo = f"{alternativa.codigo} · {enfoque}"
    return titulo if corto else f"Alternativa {titulo}"


def analizar_alternativa(c, codigo):
    if c.alternativa_propuesta != codigo:
        cancelar_seleccion(c)
    c.alternativa_en_contexto = codigo
    c.vista = "ALTERNATIVAS"
    st.session_state.pestana_analisis = "Alternativas"
    st.session_state.pop("matriz_crediticia_visible", None)


def lecturas(cifras, umbral):
    saldo = cifras.get("saldo_post_cuota")
    estado_saldo_texto, color_saldo = estado_saldo(saldo)
    if saldo is None:
        estado_saldo_texto = "Faltan datos para estimar el saldo."
    elif saldo < 0:
        estado_saldo_texto = "Déficit mensual"
    elif saldo > 0:
        estado_saldo_texto = "Queda margen mensual"

    dti = cifras.get("dti_total")
    if dti is None:
        dti_valor, dti_color = "Pendiente", "gray"
        dti_estado = "Faltan datos para medir el endeudamiento."
        if cifras.get("ingresos_admisibles") == 0:
            dti_valor = "No calculable"
            dti_estado = "El ingreso admisible es S/ 0."
    elif dti <= umbral:
        dti_valor, dti_color = porcentaje(dti), "green"
        dti_estado = f"Dentro del umbral de {umbral:.2%}."
    else:
        dti_valor, dti_color = porcentaje(dti), "red"
        dti_estado = f"Supera el umbral de {umbral:.2%}."

    return (
        ("Saldo después del pago", dinero(saldo), estado_saldo_texto, color_saldo),
        ("Endeudamiento total (DTI)", dti_valor, dti_estado, dti_color),
    )


def lecturas_financieras(cifras, umbral):
    elementos = [
        f'<div class="tt-alt-reading tt-alt-reading--{color}"><dt>{escape(rotulo)}</dt>'
        f'<dd><strong>{escape(valor)}</strong><small>{escape(estado)}</small></dd></div>'
        for rotulo, valor, estado, color in lecturas(cifras, umbral)
    ]
    st.markdown('<dl class="tt-alt-readings">' + "".join(elementos) + "</dl>", unsafe_allow_html=True)


def _pago_mensual(cifras):
    return cifras.get("pago_mensual_total", cifras.get("cuota_base"))


def _metrica_html(rotulo, valor, icono, *, estado="", color="blue", puntaje=None):
    progreso = ""
    if puntaje is not None:
        progreso = f'<progress value="{puntaje:.2f}" max="100" aria-label="Puntuación académica sobre 100"></progress>'
    detalle = f'<small>{escape(estado)}</small>' if estado else ""
    return (
        f'<div class="tt-alt-metric tt-alt-metric--{color}">'
        f'<dt>{icon(icono)}<span>{escape(rotulo)}</span></dt>'
        f'<dd><strong>{escape(valor)}</strong>{detalle}{progreso}</dd></div>'
    )


def _etiqueta_alternativa(codigo, saldo, destacados, criterio):
    if codigo in destacados:
        return ("Menor déficit", "focus") if criterio == "deficit" else ("Priorizar revisión", "focus")
    if saldo is None:
        return "Datos pendientes", "gray"
    if saldo < 0:
        return "Déficit", "red"
    if saldo == 0:
        return "Sin margen", "gray"
    return "Con margen", "green"


def tarjeta(c, evaluacion, base, umbral, destacados, criterio):
    alternativa = evaluacion.alternativa
    escenario = evaluacion.escenarios[1]
    cifras = escenario.resultado.cifras
    beneficio, desventaja = efectos_principales(evaluacion, base)
    etiqueta, tono = _etiqueta_alternativa(alternativa.codigo, cifras.get("saldo_post_cuota"), destacados, criterio)
    with st.container(border=True, gap="xsmall", key=f"tt_alt_card_comparador_{alternativa.codigo}"):
        titulo = titulo_alternativa(c, alternativa, corto=True)
        icono_estado = {"focus": "star", "red": "alert", "green": "check"}.get(tono, "info")
        st.markdown(
            f'<div class="tt-alt-card-header"><h3>{escape(titulo)}</h3>'
            f'<span class="tt-alt-chip tt-alt-chip--{tono}">{icon(icono_estado)}{escape(etiqueta)}</span></div>'
            f'<div class="tt-alt-terms">{escape(condiciones(alternativa))}</div>',
            unsafe_allow_html=True,
        )
        (_, saldo, saldo_estado, saldo_color), (_, dti, dti_estado, dti_color) = lecturas(cifras, umbral)
        puntaje = evaluacion.puntaje_global
        etiqueta_pago = "Cuota con cargos" if cifras.get("cargos_mensuales") else "Cuota mensual"
        celdas = [
            _metrica_html(etiqueta_pago, dinero(_pago_mensual(cifras)), "layers"),
            _metrica_html("Saldo disponible", saldo, "wallet", estado=saldo_estado, color=saldo_color),
            _metrica_html("Endeudamiento (DTI)", dti, "chart", estado=dti_estado, color=dti_color),
            _metrica_html("Puntuación académica", "Pendiente" if puntaje is None else puntuacion(puntaje),
                          "scale", estado="Preliminar" if puntaje is not None and evaluacion.preliminar else "", puntaje=puntaje),
        ]
        st.markdown('<dl class="tt-alt-grid">' + "".join(celdas) + "</dl>", unsafe_allow_html=True)
        caida = f"{escenario.caida.normalize():f}%"
        resistencia = ("Evaluación de escenarios incompleta" if evaluacion.resisten is None else
                       f"{evaluacion.resisten} de {len(evaluacion.escenarios)} escenarios cumplen saldo y DTI")
        st.caption(f"Caída esperada {caida} · {resistencia}.")
        st.markdown(f'<div class="tt-alt-insight">{icon("chart" if tono == "focus" else "file")} '
                    f'<span>{escape(beneficio)} {escape(desventaja)}</span></div>', unsafe_allow_html=True)
        st.button(f"Analizar alternativa {alternativa.codigo}",
                  key=f"comparador_analizar_{alternativa.codigo}", width="stretch", icon=":material/chevron_right:",
                  type="primary" if tono == "focus" else "secondary",
                  on_click=analizar_alternativa, args=(c, alternativa.codigo))


def detalle_resultado(c, evaluacion, base, umbral):
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
            tarjeta_escenario(escenario, umbral)
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


def saldos_esperados(comparativa):
    return {e.alternativa.codigo: e.escenarios[1].resultado.cifras.get("saldo_post_cuota")
            for e in comparativa.alternativas}


def opciones_destacadas(comparativa, saldos):
    if saldos and all(saldo is not None and saldo < 0 for saldo in saldos.values()):
        mayor_saldo = max(saldos.values())
        return tuple(codigo for codigo, saldo in saldos.items() if saldo == mayor_saldo), "deficit"
    if comparativa.recomendadas:
        return comparativa.recomendadas, "revision"
    return (), None


def banner_comparativo(comparativa, saldos, criterio):
    if criterio == "deficit":
        return status_banner_html("Ninguna alternativa tiene saldo suficiente",
                                  "En el escenario esperado, todas presentan déficit mensual. Revisa los ingresos, los gastos o las condiciones antes de decidir.",
                                  tono="red")
    if any(saldo is None for saldo in saldos.values()) or any(e.puntaje_global is None for e in comparativa.alternativas):
        return status_banner_html("Comparación pendiente",
                                  "Completa los datos indicados en cada alternativa para comparar saldo, endeudamiento y puntuación.")
    if criterio == "revision":
        return status_banner_html("Hay alternativas para priorizar en la revisión",
                                  "Las opciones destacadas cumplen el límite de endeudamiento y dejan un saldo no negativo en los tres escenarios.",
                                  tono="green")
    if all(saldo <= 0 for saldo in saldos.values()):
        return status_banner_html("Ninguna alternativa deja margen mensual",
                                  "En el escenario esperado el saldo queda en cero o en déficit. Puedes simular una cuota más baja.",
                                  tono="red")
    return status_banner_html("Revisa los escenarios y las alertas",
                              "No hay una alternativa recomendada con los criterios académicos actuales.")


def _abrir_tablero(c, vista, pestana):
    c.vista = vista
    st.session_state.pestana_analisis = pestana


def _exportar_informe(c):
    try:
        generar_informe(c)
    except ValueError as error:
        decir(c, str(error))
    _abrir_tablero(c, "PDF", "Informe e IA")


def encabezado_comparativo(c, cantidad):
    with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center",
                      gap="xsmall", key="tt_alt_toolbar"):
        st.markdown(f'<div class="tt-alt-title"><h2>Comparación de Alternativas</h2>'
                    f'<p>Evaluación de {cantidad} opciones para la solicitud de crédito</p></div>',
                    unsafe_allow_html=True)
        with st.container(horizontal=True, gap="xsmall", width="content", key="tt_alt_toolbar_actions"):
            st.button("Exportar informe (PDF)", icon=":material/download:", key="comparador_exportar_pdf",
                      on_click=_exportar_informe, args=(c,))
            st.button("Simular condiciones", icon=":material/calculate:", key="comparador_simular",
                      on_click=_abrir_tablero, args=(c, "SIMULAR", "Simular"))
            with st.popover("Ayuda", icon=":material/info:"):
                st.write("La cuota y el saldo corresponden al escenario esperado de cada alternativa. Un saldo negativo indica que faltaría dinero para cubrir todos los pagos.")
                st.write("El DTI mide la proporción del ingreso admisible comprometida en cuotas. La puntuación promedia los tres escenarios con los criterios académicos.")
                st.write("Abre una alternativa para ver las diferencias con la solicitud original y la evidencia pendiente.")


def tabla_comparativa_html(comparativa, destacados):
    codigos = tuple(e.alternativa.codigo for e in comparativa.alternativas)
    cabecera = '<tr><th scope="col">Indicador</th>' + "".join(
        f'<th scope="col" class="{"tt-alt-table-highlight" if codigo in destacados else ""}">{escape(codigo)}</th>'
        for codigo in codigos
    ) + '</tr>'
    datos = [e.escenarios[1].resultado.cifras for e in comparativa.alternativas]
    estados = [lecturas(cifra, comparativa.umbral_dti) for cifra in datos]
    filas = (
        ("Monto", [(dinero(e.alternativa.monto), "") for e in comparativa.alternativas]),
        ("Plazo", [(f"{e.alternativa.meses} meses" if e.alternativa.meses is not None else "Pendiente", "")
                    for e in comparativa.alternativas]),
        ("Pago mensual", [(dinero(_pago_mensual(cifra)), "") for cifra in datos]),
        ("Endeudamiento (DTI)", [(dti[1], dti[3]) for _, dti in estados]),
        ("Saldo disponible", [(saldo[1], saldo[3]) for saldo, _ in estados]),
        ("Puntuación (0–100)", [("Pendiente" if e.puntaje_global is None else f"{e.puntaje_global:.2f}", "")
                               for e in comparativa.alternativas]),
    )
    cuerpo = []
    for rotulo, celdas in filas:
        fila = [f'<tr><th scope="row">{escape(rotulo)}</th>']
        for codigo, (texto, color) in zip(codigos, celdas):
            destaque = " tt-alt-table-highlight" if codigo in destacados else ""
            fila.append(f'<td class="tt-alt-table-value--{color}{destaque}">{escape(texto)}</td>')
        cuerpo.append("".join(fila) + '</tr>')
    return ('<div class="tt-alt-table-scroll" role="region" aria-label="Comparación de alternativas en el escenario esperado" tabindex="0">'
            '<table class="tt-alt-table"><thead>' + cabecera + '</thead><tbody>' + "".join(cuerpo) + '</tbody></table></div>')


def texto_conclusion(comparativa, saldos, destacados, criterio):
    if criterio != "deficit":
        return comparativa.recomendacion
    saldo = f"S/ {abs(saldos[destacados[0]]):,.2f}"
    if len(destacados) == 1:
        return (f"La alternativa {destacados[0]} presenta el menor déficit en el escenario esperado. Aun con esta opción, faltarían {saldo} al mes "
                "para cubrir los gastos y las cuotas.")
    codigos = ", ".join(destacados[:-1]) + " y " + destacados[-1]
    return f"Las alternativas {codigos} comparten el menor déficit del escenario esperado. Con cualquiera faltarían {saldo} al mes."


def mostrar_tablero(c, comparativa):
    saldos = saldos_esperados(comparativa)
    destacados, criterio = opciones_destacadas(comparativa, saldos)
    with st.container(key="tt_alt_board", gap="small"):
        encabezado_comparativo(c, len(comparativa.alternativas))
        st.markdown(banner_comparativo(comparativa, saldos, criterio), unsafe_allow_html=True)
        with st.container(key="tt_alt_choices"):
            for columna, evaluacion in zip(st.columns(len(comparativa.alternativas), gap="small"), comparativa.alternativas):
                with columna:
                    tarjeta(c, evaluacion, comparativa.base, comparativa.umbral_dti, destacados, criterio)
        with st.container(key="tt_alt_bottom"):
            tabla, conclusion = st.columns([1.25, 1], gap="small")
            with tabla, st.container(border=True, gap="xsmall", key="tt_alt_table_box"):
                section_title("Resumen comparativo · escenario esperado", "scale")
                st.markdown(tabla_comparativa_html(comparativa, destacados), unsafe_allow_html=True)
            with conclusion:
                with st.container(border=True, gap="xsmall", key="tt_alt_conclusion"):
                    section_title("Conclusión del análisis", "chart")
                    st.write(texto_conclusion(comparativa, saldos, destacados, criterio))
                with st.container(border=True, gap="xsmall", key="tt_alt_next"):
                    section_title("Próximas acciones", "file")
                    if criterio == "deficit":
                        st.markdown("- Valida los ingresos, gastos y cuotas existentes.\n- Prueba un ajuste del monto o el plazo en **Simular condiciones**.")
                    else:
                        st.markdown("- Revisa el detalle y las alertas de las alternativas.\n- Si eliges una, registra el motivo antes de preparar el informe.")
        with st.container(horizontal=True, gap="small", key="tt_alt_actions"):
            st.button("Ver matriz general de nueve escenarios", icon=":material/table_chart:", on_click=abrir_matriz, args=(c,))
            if st.button("Restablecer alternativas y caídas iniciales", key="regenerar_alternativas"):
                try:
                    regenerar(c)
                    st.rerun()
                except ValueError as error:
                    st.warning(str(error))


def tarjeta_escenario(escenario, umbral):
    cifras = escenario.resultado.cifras
    nombre = escenario.nombre.lower()
    with st.container(border=True, gap="small", key=f"tt_escenario_{nombre}"):
        st.markdown(f"**{escenario.nombre}** · caída de {escenario.caida:g}%")
        st.caption(f"Ingreso {dinero(cifras.get('ingresos_admisibles'))}")
        lecturas_financieras(cifras, umbral)
        st.caption(puntuacion(escenario.puntaje))


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
            detalle_resultado(c, evaluacion, comparativa.base, comparativa.umbral_dti)
            eleccion(c, evaluacion)
            formulario_edicion(c, evaluacion.alternativa)
        return
    if st.session_state.get("matriz_crediticia_visible") == c.revision:
        mostrar_matriz(comparativa)
        return
    mostrar_tablero(c, comparativa)
