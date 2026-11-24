"""Herramientas contextuales sobre una sola Conversacion/Expediente de sesión."""
from dataclasses import replace
from datetime import date
from decimal import Decimal as D
import streamlit as st
from casos import CASOS, PREGUNTAS
from dominio.modelos import Cargo
from conversacion.gestor import nuevo, proponer, aplicar, invalidar, evaluar_actual, decir
from servicios.documentos import texto_seguro
from servicios.costos import CATEGORIAS, PAGADORES, diagnostico_tcea
from servicios.finanzas import fechas_mensuales
from ia.politicas import EstadoIA


def reiniciar_ui(caso=None):
    epoca = st.session_state.get("epoca", 0) + 1
    ia = st.session_state.get("ia", EstadoIA())
    ia.contexto_semantico = {}
    ia.revision_contexto = None
    for key in list(st.session_state):
        del st.session_state[key]
    c = nuevo(guiado=True)
    st.session_state.update(epoca=epoca, conversacion=c, ia=ia)
    if caso:
        datos = CASOS[caso].copy()
        datos.update(historial="MORA_DECLARADA" if datos["dias_mora"] else "SIN_MORA_DECLARADA", descuento_planilla="NO_DESCONTADAS")
        aplicar(c, datos, "CASO_SINTETICO")
        decir(c, "Caso de demostración " + caso + ": todos sus datos son ficticios.")
        c.flujo.iniciado = True


def pedir_caso(nombre):
    c = st.session_state.conversacion
    if c.expediente.monto is None and not c.documentos and len(c.mensajes) == 1:
        reiniciar_ui(nombre)
    else:
        c.pendiente = dict(accion="CASO", caso=nombre, revision=c.revision)
        decir(c, f"Confirma reemplazar el expediente por el caso sintético {nombre}. Se limpiará la sesión anterior.")


def editor(c):
    with st.expander("Editar información del expediente"):
        st.caption("Edición declarada en formulario; las modificaciones de datos existentes necesitan confirmación. No es necesario usar este panel para conversar.")
        with st.form(f"editar_{c.revision}"):
            valores = {}
            for campo, pregunta, tipo, minimo, maximo in PREGUNTAS:
                if campo == "dias_mora":
                    continue
                v = getattr(c.expediente, campo)
                valores[campo] = st.number_input(pregunta.replace("**", ""), min_value=tipo(minimo), max_value=tipo(maximo),
                    value=tipo(v) if v is not None else None, step=1 if tipo is int else .01, key=f"editor_{campo}_{c.revision}")
            opciones = ["DESCONOCIDO", "INSUFICIENTE", "SIN_MORA_DECLARADA", "MORA_DECLARADA"]
            historial = st.selectbox("Historial declarado", opciones, index=opciones.index(c.expediente.historial))
            dias = st.number_input("Días de mora (solo si declara mora)", min_value=1, value=c.expediente.dias_mora if c.expediente.dias_mora else None)
            opciones_p = ["SIN_ACLARAR", "NO_DESCONTADAS", "YA_DESCONTADAS"]
            planilla = st.selectbox("¿Todas las otras cuotas ya están descontadas del neto?", opciones_p, index=opciones_p.index(c.expediente.descuento_planilla))
            enviado = st.form_submit_button("Proponer cambios del formulario")
        if enviado:
            valores.update(historial=historial, dias_mora=dias if historial == "MORA_DECLARADA" else 0 if historial == "SIN_MORA_DECLARADA" else None,
                           descuento_planilla=planilla)
            cambios = {k: v for k, v in valores.items() if v != getattr(c.expediente, k) and (v is not None or k == "dias_mora")}
            try:
                if historial == "MORA_DECLARADA" and dias is None:
                    raise ValueError("Indique los días de mora declarada.")
                if cambios:
                    proponer(c, cambios, "EDITADO_EN_FORMULARIO")
                    st.rerun()
            except ValueError as error:
                st.error(str(error))


def _guardar_datos(c, exp, vista, *, conservar_confirmacion):
    if c.pendiente:
        raise ValueError("Confirma o cancela el cambio pendiente antes de guardar.")
    if c.expediente == exp:
        st.info("Los datos guardados ya coinciden con el formulario.")
        return
    confirmado = c.flujo.revision_confirmada == c.revision
    c.expediente = exp
    invalidar(c)
    evaluar_actual(c, vista=vista, responder=False)
    if conservar_confirmacion and confirmado:
        c.flujo.revision_confirmada = c.revision
    st.rerun()


def editor_costos(c):
    exp = c.expediente
    st.caption("Deja en blanco los importes desconocidos. Escribe S/ 0 solo cuando hayas confirmado que el cargo no aplica.")
    causas = diagnostico_tcea(exp, c.resultado)
    if causas:
        st.markdown("**Datos por completar**")
        for causa in causas:
            st.text(causa)
    with st.form(f"costos_{c.revision}"):
        cargos = [cargo for cargo in exp.cargos if (cargo.concepto, cargo.momento) not in CATEGORIAS]
        for concepto, momento in CATEGORIAS:
            prev = next((x for x in exp.cargos if x.concepto == concepto and x.momento == momento), None)
            importe_col, pagador_col = st.columns(2)
            etiqueta = f"{concepto} · {momento.lower()}"
            importe = importe_col.number_input(f"{etiqueta} (S/)", min_value=0., max_value=1e10,
                                               value=float(prev.importe) if prev and prev.importe is not None else None,
                                               step=.01, format="%.2f")
            pagador = pagador_col.selectbox(
                f"Pagador · {etiqueta}", PAGADORES,
                index=PAGADORES.index(prev.pagador) if prev and prev.pagador in PAGADORES else None,
                placeholder="Por identificar",
            )
            if importe is not None:
                # Los cargos cero no generan flujo y no requieren atribución a una persona.
                cargos.append(Cargo(concepto, D(str(importe)), momento, pagador or ("NO_APLICA" if importe == 0 else "PENDIENTE")))
        completos = st.checkbox("Confirmo que todos los costos aplicables están registrados", exp.cargos_completos)
        desembolso = st.date_input("Fecha de desembolso", value=exp.fecha_desembolso)
        fechas_texto = st.text_area(
            "Vencimientos específicos (opcional)",
            value="\n".join(str(f) for f in exp.fechas_pago),
            placeholder="Escribe una fecha AAAA-MM-DD por línea",
            help="Si queda vacío, se proponen fechas mensuales desde el desembolso, ajustadas al último día del mes cuando corresponda.",
            max_chars=4400,
        )
        confirmadas = st.checkbox("Confirmo las fechas de vencimiento", bool(exp.fechas_pago) and exp.origen_fechas_pago in (None, "CONFIRMADAS"))
        aceptar = st.form_submit_button("Guardar costos y fechas", type="primary")
    if not aceptar:
        return
    try:
        if fechas_texto.strip():
            fechas = tuple(date.fromisoformat(linea.strip()) for linea in fechas_texto.splitlines() if linea.strip())
        else:
            fechas = fechas_mensuales(desembolso, exp.meses) if desembolso and exp.meses else ()
    except ValueError:
        st.error("Revisa los vencimientos. Ingresa una fecha válida en formato AAAA-MM-DD por línea.")
        return
    presentes = {(cargo.concepto, cargo.momento) for cargo in cargos}
    completos = completos and all(categoria in presentes for categoria in CATEGORIAS)
    candidato = replace(
        exp, cargos=tuple(cargos), cargos_completos=completos, fecha_desembolso=desembolso,
        fechas_pago=fechas, origen_fechas_pago=("CONFIRMADAS" if confirmadas else "PROPUESTAS") if fechas else None,
    )
    try:
        _guardar_datos(c, candidato, "COSTOS", conservar_confirmacion=True)
    except ValueError as error:
        st.error(str(error))


def editor_anotaciones(c):
    with st.expander("Patrimonio y anotaciones"):
        st.caption("El patrimonio declarado permanece sin verificar y no se convierte en ingreso.")
        with st.form(f"anotaciones_{c.revision}"):
            patrimonio = st.text_input("Patrimonio declarado, no verificado", value=c.expediente.patrimonio, max_chars=200)
            valor_pat = st.number_input("Valor patrimonial declarado (opcional)", min_value=0., value=float(c.expediente.patrimonio_valor) if c.expediente.patrimonio_valor is not None else None)
            fuente_pat = st.text_input("Fuente patrimonial declarada", value=c.expediente.patrimonio_fuente, max_chars=200)
            nota = st.text_area("Observación no sensible del analista", value=c.expediente.observacion, max_chars=1000)
            aceptar = st.form_submit_button("Guardar anotaciones")
        if aceptar:
            try:
                for texto in (patrimonio, fuente_pat, nota):
                    texto_seguro(texto)
                candidato = replace(c.expediente, patrimonio=patrimonio,
                                    patrimonio_valor=D(str(valor_pat)) if valor_pat is not None else None,
                                    patrimonio_fuente=fuente_pat, observacion=nota)
                _guardar_datos(c, candidato, "RESUMEN", conservar_confirmacion=False)
            except ValueError as error:
                st.error(str(error))


def mostrar_chat():
    from ui_flujo import mostrar
    mostrar(editor, reiniciar_ui, pedir_caso)
