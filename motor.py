"""Motor explicable para una DEMOSTRACION ACADEMICA de riesgo crediticio.
No es un scoring real ni otorga/aprueba créditos.
"""
from dataclasses import dataclass
from math import isfinite, log1p, expm1


def validar_numero(nombre, valor, minimo=0, entero=False):
    """Rechaza ausencias, booleanos, NaN e infinitos antes de calcular."""
    if (isinstance(valor, bool) or not isinstance(valor, (int, float))
            or not isfinite(valor) or valor < minimo
            or (entero and int(valor) != valor)):
        raise ValueError(f"{nombre}: se requiere un número {'entero ' if entero else ''}finito >= {minimo}.")


@dataclass(frozen=True)
class Solicitud:
    ingreso: float
    gastos: float
    otras_cuotas: float
    monto: float
    meses: int
    tea: float
    estabilidad_meses: int
    dias_mora: int


def cuota_francesa(monto: float, meses: int, tea: float) -> float:
    validar_numero("Monto", monto)
    validar_numero("Plazo", meses, 1, entero=True)
    validar_numero("TEA", tea)
    if monto <= 0 or meses <= 0 or tea < 0:
        raise ValueError("Monto y plazo deben ser positivos; la TEA no puede ser negativa.")
    log_mensual = log1p(tea / 100) / 12
    tasa_mensual = expm1(log_mensual)
    if tasa_mensual == 0:
        return monto / meses
    cuota = monto * (tasa_mensual / -expm1(-meses * log_mensual))
    if not isfinite(cuota):
        raise ValueError("El cálculo excede el rango numérico admitido.")
    return cuota


def evaluar(s: Solicitud) -> dict:
    for nombre in ("ingreso", "gastos", "otras_cuotas"):
        validar_numero(nombre, getattr(s, nombre))
    for nombre in ("estabilidad_meses", "dias_mora"):
        validar_numero(nombre, getattr(s, nombre), entero=True)
    if min(s.ingreso, s.gastos, s.otras_cuotas, s.estabilidad_meses, s.dias_mora) < 0:
        raise ValueError("No se permiten valores negativos.")
    cuota = cuota_francesa(s.monto, s.meses, s.tea)
    dinero_disponible = s.ingreso - s.gastos - s.otras_cuotas
    saldo_final = dinero_disponible - cuota
    ratio_cuota = cuota / s.ingreso if s.ingreso > 0 else None
    ratio_total = (cuota + s.otras_cuotas) / s.ingreso if s.ingreso > 0 else None
    alertas = []
    if s.ingreso == 0:
        alertas.append("No hay ingresos declarados para respaldar el pago.")
    if s.dias_mora > 30:
        alertas.append("Morosidad superior a 30 días: requiere verificación documental.")
    if saldo_final < 0:
        alertas.append("El flujo mensual disponible no alcanza para pagar la cuota.")
    if ratio_cuota is not None and ratio_cuota > 0.30:
        alertas.append("La cuota supera el 30% del ingreso (umbral didáctico del equipo).")
    if s.estabilidad_meses < 6:
        alertas.append("Antigüedad de ingresos menor a 6 meses.")

    if s.ingreso == 0 or s.dias_mora > 30 or saldo_final < 0:
        clasificacion = "Alerta crítica: revisión humana prioritaria"
    elif alertas:
        clasificacion = "Revisión adicional necesaria"
    else:
        clasificacion = "Condiciones preliminares favorables"

    return {
        "cuota": cuota,
        "disponible_antes": dinero_disponible,
        "disponible_despues": saldo_final,
        "ratio_cuota": ratio_cuota,
        "ratio_total": ratio_total,
        "clasificacion": clasificacion,
        "alertas": alertas,
        "estabilidad_favorable": s.estabilidad_meses >= 12,
        "total_pagado": cuota * s.meses,
        "intereses_estimados": cuota * s.meses - s.monto,
    }


def perdida_esperada_ilustrativa(monto: float, pd_porcentaje: float, lgd_porcentaje: float) -> float:
    """EL=EAD×PD×LGD con PD y LGD hipotéticos ingresados por el usuario."""
    for nombre, valor in (("Monto", monto), ("PD", pd_porcentaje), ("LGD", lgd_porcentaje)):
        validar_numero(nombre, valor)
    if monto < 0 or not 0 <= pd_porcentaje <= 100 or not 0 <= lgd_porcentaje <= 100:
        raise ValueError("Valores inválidos para la simulación.")
    return monto * (pd_porcentaje / 100) * (lgd_porcentaje / 100)


ALTERNATIVAS = (
    {"codigo": "A", "nombre": "Reglas y revisión humana", "inversion": 50000, "opex": 1500,
     "reducciones": {"Pesimista": 0.10, "Esperado": 0.20, "Optimista": 0.30}},
    {"codigo": "B", "nombre": "Scoring predictivo (hipotético)", "inversion": 120000, "opex": 3500,
     "reducciones": {"Pesimista": 0.25, "Esperado": 0.45, "Optimista": 0.60}},
    {"codigo": "C", "nombre": "Chatbot + scoring (hipotético)", "inversion": 250000, "opex": 5500,
     "reducciones": {"Pesimista": 0.30, "Esperado": 0.55, "Optimista": 0.70}},
)


def comparar_alternativas(solicitudes_mensuales: int, minutos_base: float,
                          costo_hora: float, presupuesto: float, horizonte_meses: int = 12) -> list[dict]:
    validar_numero("Solicitudes", solicitudes_mensuales, 1, entero=True)
    validar_numero("Horizonte", horizonte_meses, 1, entero=True)
    for nombre, valor in (("Minutos", minutos_base), ("Costo", costo_hora), ("Presupuesto", presupuesto)):
        validar_numero(nombre, valor)
    if solicitudes_mensuales <= 0 or minutos_base <= 0 or costo_hora < 0 or presupuesto < 0 or horizonte_meses <= 0:
        raise ValueError("Los parámetros del escenario deben ser válidos.")
    filas = []
    for alt in ALTERNATIVAS:
        for escenario, reduccion in alt["reducciones"].items():
            horas_ahorradas = solicitudes_mensuales * minutos_base * reduccion / 60
            ahorro_mensual_teorico = horas_ahorradas * costo_hora
            beneficio_neto = (ahorro_mensual_teorico - alt["opex"]) * horizonte_meses - alt["inversion"]
            filas.append({
                "alternativa": alt["codigo"],
                "nombre": alt["nombre"],
                "escenario": escenario,
                "reduccion": reduccion,
                "tiempo_resultante": minutos_base * (1 - reduccion),
                "horas_ahorradas_mes": horas_ahorradas,
                "ahorro_mensual_teorico": ahorro_mensual_teorico,
                "inversion": alt["inversion"],
                "opex": alt["opex"],
                "beneficio_neto": beneficio_neto,
                "dentro_de_presupuesto": alt["inversion"] <= presupuesto,
            })
    return filas
