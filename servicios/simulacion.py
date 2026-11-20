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
    caida = numero(caida, "Caída de ingresos", 0, 100)
    meses = entero(meses, "Plazo", 1, 360)
    # La caída aplica al ingreso anterior a deuda; nunca a gastos/cuotas.
    ingreso = base.cifras["ingresos_admisibles"] * (1 - caida / 100)
    copia = replace(expediente, monto=monto, meses=meses, tea=tea,
                    fechas_pago=fechas_mensuales(expediente.fecha_desembolso, meses) if expediente.fecha_desembolso and expediente.fechas_pago else ())
    resultado = analizar(copia, config, ingreso_escenario=ingreso)
    resultado.supuestos.append(f"Escenario: caída {caida}% sobre ingreso admisible base {base.cifras['ingresos_admisibles']}; expediente original intacto.")
    resultado.meses_ingreso = base.meses_ingreso.copy()
    return copia, resultado
