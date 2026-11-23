from dataclasses import replace
from decimal import Decimal as D
from servicios.finanzas import numero, entero, fechas_mensuales
from servicios.reglas import analizar
from dominio.modelos import Configuracion


def simular(expediente, monto, meses, tea, caida, config=Configuracion()):
    """Copia inmutable; ingreso documental resuelto se estresa sin reabrir discrepancia."""
    base = analizar(expediente, config)
    if base.estado in ("DATOS INSUFICIENTES", "DISCREPANCIA PENDIENTE") or "ingresos_admisibles" not in base.cifras:
        raise ValueError("Resolver datos pendientes del expediente antes de simular capacidad.")
    return evaluar_escenario(expediente, monto, meses, tea, caida, config, base)


def evaluar_escenario(expediente, monto, meses, tea, caida, config, base, *, conservar_calendario=False):
    """Reutiliza un resultado base para escenarios de una misma evaluación."""
    caida = numero(caida, "Caída de ingresos", 0, 100)
    meses = entero(meses, "Plazo", 1, 360)
    # La caída aplica al ingreso anterior a deuda; nunca a gastos/cuotas.
    ingreso_base = base.cifras.get("ingresos_admisibles")
    ingreso = None if ingreso_base is None else ingreso_base * (1 - caida / 100)
    cargos_completos = expediente.cargos_completos
    if conservar_calendario and meses == expediente.meses:
        fechas = expediente.fechas_pago
    elif expediente.fecha_desembolso and expediente.fechas_pago:
        fechas = fechas_mensuales(expediente.fecha_desembolso, meses)
        if conservar_calendario:
            cargos_completos = cargos_completos and base.tcea is not None
    else:
        fechas = ()
    copia = replace(expediente, monto=monto, meses=meses, tea=tea,
                    fechas_pago=fechas, cargos_completos=cargos_completos)
    resultado = analizar(copia, config, ingreso_escenario=ingreso)
    if ingreso_base is None:
        resultado.supuestos.append("Escenario de ingresos pendiente: falta ingreso admisible base.")
    else:
        resultado.supuestos.append(f"Escenario: caída {caida}% sobre ingreso admisible base {ingreso_base}; gastos y deudas constantes.")
    if conservar_calendario and meses != expediente.meses and fechas:
        resultado.supuestos.append("Vencimientos proyectados mensualmente desde la fecha de desembolso del caso base; cargos mantenidos como supuesto.")
    resultado.meses_ingreso = base.meses_ingreso.copy()
    return copia, resultado
