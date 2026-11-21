"""Herramientas contextuales sobre una sola Conversacion/Expediente de sesión."""
from dataclasses import replace
from decimal import Decimal as D
import streamlit as st
from casos import CASOS, PREGUNTAS
from dominio.modelos import Cargo
from conversacion.gestor import nuevo, proponer, aplicar, invalidar, evaluar_actual, decir
from servicios.documentos import texto_seguro
from servicios.finanzas import fechas_mensuales
from ia.politicas import EstadoIA


def reiniciar_ui(caso=None):
    epoca = st.session_state.get("epoca", 0) + 1
    ia = st.session_state.get("ia", EstadoIA())
    ia.habilitado = ia.consentimiento = False
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
    with st.expander("Editar datos · panel experto opcional"):
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
    with st.expander("Costos, fechas y anotación del analista"):
        st.caption("Cargos supuestos separados. TCEA referencial ACT/365 solo con todos los cargos y fechas confirmados. Patrimonio no verificado, sin efecto sobre ingresos.")
        with st.form(f"costos_{c.revision}"):
            cargos = []
            for concepto in ("Seguro", "Comisiones", "Otros gastos"):
                for momento in ("MENSUAL", "INICIAL"):
                    prev = next((x for x in c.expediente.cargos if x.concepto == concepto and x.momento == momento), None)
                    cols = st.columns(2)
                    importe = cols[0].number_input(f"{concepto} {momento} (S/)", min_value=0., value=float(prev.importe) if prev else 0.)
                    pagador = cols[1].selectbox(f"Pagador {concepto} {momento}", ["SOLICITANTE", "TERCERO"], index=1 if prev and prev.pagador == "TERCERO" else 0)
                    cargos.append(Cargo(concepto, D(str(importe)), momento, pagador))
            desembolso = st.date_input("Fecha de desembolso supuesta", value=c.expediente.fecha_desembolso)
            completos = st.checkbox("Confirmo cargos completos y vencimientos mensuales desde esa fecha (ajuste a fin de mes)", value=False)
            patrimonio = st.text_input("Patrimonio declarado, no verificado", value=c.expediente.patrimonio, max_chars=200)
            valor_pat = st.number_input("Valor patrimonial declarado (opcional)", min_value=0., value=float(c.expediente.patrimonio_valor) if c.expediente.patrimonio_valor is not None else None)
            fuente_pat = st.text_input("Fuente patrimonial declarada", value=c.expediente.patrimonio_fuente, max_chars=200)
            nota = st.text_area("Observación no sensible del analista", value=c.expediente.observacion, max_chars=1000)
            aceptar = st.form_submit_button("Confirmar costos y anotaciones")
        if aceptar:
            try:
                for texto in (patrimonio, fuente_pat, nota):
                    texto_seguro(texto)
                fechas = fechas_mensuales(desembolso, c.expediente.meses) if desembolso and c.expediente.meses else ()
                c.expediente = replace(c.expediente, cargos=tuple(cargos), fecha_desembolso=desembolso, fechas_pago=fechas,
                    cargos_completos=completos, patrimonio=patrimonio, patrimonio_valor=D(str(valor_pat)) if valor_pat is not None else None,
                    patrimonio_fuente=fuente_pat, observacion=nota)
                invalidar(c)
                evaluar_actual(c)
                st.rerun()
            except ValueError as error:
                st.error(str(error))


def mostrar_chat():
    from ui_flujo import mostrar
    mostrar(editor, reiniciar_ui, pedir_caso)
