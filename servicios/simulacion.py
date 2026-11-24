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
    origen_fechas = expediente.origen_fechas_pago
    if conservar_calendario and meses == expediente.meses:
        fechas = expediente.fechas_pago
    elif expediente.fecha_desembolso and expediente.fechas_pago and (not conservar_calendario or base.tcea is not None):
        fechas = fechas_mensuales(expediente.fecha_desembolso, meses)
        origen_fechas = "PROYECTADAS" if expediente.origen_fechas_pago != "PROPUESTAS" else "PROPUESTAS"
    else:
        fechas = ()
        origen_fechas = None
    copia = replace(expediente, monto=monto, meses=meses, tea=tea,
                    fechas_pago=fechas, origen_fechas_pago=origen_fechas)
    resultado = analizar(copia, config, ingreso_escenario=ingreso)
    if ingreso_base is None:
        resultado.supuestos.append("Escenario de ingresos pendiente: falta ingreso admisible base.")
    else:
        resultado.supuestos.append(f"Escenario: caída {caida}% sobre ingreso admisible base {ingreso_base}; gastos y deudas constantes.")
    if origen_fechas == "PROYECTADAS":
        resultado.supuestos.append("Vencimientos proyectados mensualmente desde la fecha de desembolso del caso base; cargos mantenidos como supuesto.")
    resultado.meses_ingreso = base.meses_ingreso.copy()
    return copia, resultado
