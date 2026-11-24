"""Datos requeridos para calcular el costo efectivo anual de un flujo fechado."""
from datetime import date
from decimal import Decimal

from servicios.finanzas import entero, numero, problemas_flujo_fechado


CONCEPTOS = ("Seguro", "Comisiones", "Otros gastos")
MOMENTOS = ("MENSUAL", "INICIAL")
PAGADORES = ("SOLICITANTE", "TERCERO")
CATEGORIAS = tuple((concepto, momento) for concepto in CONCEPTOS for momento in MOMENTOS)


def diagnostico_tcea(exp, resultado=None):
    if resultado is not None:
        if resultado.tcea is not None:
            return ()
        if resultado.pendientes_tcea:
            return resultado.pendientes_tcea
    causas = []
    if exp.monto is None or exp.meses is None or exp.tea is None:
        faltantes = [nombre for nombre, valor in (("monto", exp.monto), ("plazo", exp.meses), ("TEA", exp.tea))
                     if valor is None]
        causas.append("Completa " + ", ".join(faltantes) + " para generar el flujo de pagos.")

    registrados = {(c.concepto, c.momento) for c in exp.cargos if c.importe is not None}
    if not exp.cargos_completos:
        for concepto, momento in CATEGORIAS:
            if (concepto, momento) not in registrados:
                causas.append(f"Registra {concepto.lower()} · {momento.lower()}, con S/ 0 si confirmas que no aplica.")
        causas.append("Confirma que se incluyeron todos los costos aplicables.")

    inicial = Decimal(0)
    for cargo in exp.cargos:
        campo = f"{cargo.concepto or 'cargo sin nombre'} · {cargo.momento.lower()}"
        if not cargo.concepto.strip() or cargo.momento not in MOMENTOS:
            causas.append("Identifica el concepto y si el cargo es inicial o mensual.")
        if cargo.pagador not in PAGADORES and not (cargo.pagador == "NO_APLICA" and cargo.importe == 0):
            causas.append(f"Indica quién paga {campo}.")
        try:
            importe = numero(cargo.importe, "Importe del cargo")
        except ValueError:
            causas.append(f"Completa un importe válido para {campo}, incluido S/ 0 cuando corresponda.")
        else:
            if cargo.momento == "INICIAL" and cargo.pagador == "SOLICITANTE":
                inicial += importe

    try:
        monto = numero(exp.monto, "Monto", Decimal(".01")) if exp.monto is not None else None
    except ValueError:
        causas.append("Corrige el monto del préstamo para calcular el desembolso neto.")
        monto = None
    try:
        plazo = entero(exp.meses, "Plazo", 1, 360) if exp.meses is not None else None
    except ValueError:
        causas.append("Corrige el plazo para determinar el número de vencimientos.")
        plazo = None
    if exp.origen_fechas_pago == "PROPUESTAS" and exp.fechas_pago:
        causas.append("Confirma las fechas de vencimiento propuestas.")

    pagos = [fila.get("pago_total") for fila in resultado.tabla] if resultado is not None and resultado.tabla else None
    causas.extend(problemas_flujo_fechado(None if monto is None else monto - inicial, pagos,
                                        exp.fechas_pago, exp.fecha_desembolso, plazo))
    if resultado is not None and not resultado.tabla and not causas:
        causas.append("Revisa las condiciones del préstamo para obtener un cronograma de pagos válido.")
    return tuple(dict.fromkeys(causas))
