"""Motor explicable para una DEMOSTRACION ACADEMICA de riesgo crediticio.
No es un scoring real ni otorga/aprueba créditos.
"""
from dataclasses import dataclass
from math import isfinite, log1p, expm1
from decimal import Decimal, ROUND_HALF_UP, localcontext
from reglas_credito import PERFILES, ReglasCredito


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
    tipo_credito: str = "personal"


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


def tabla_amortizacion(monto: float, meses: int, tea: float) -> list[dict]:
    """Cuotas vencidas; redondeo HALF_UP y última cuota ajustada al saldo."""
    cuota_francesa(monto, meses, tea)
    if meses > 1200:
        raise ValueError("La tabla admite hasta 1200 meses (límite técnico, no política crediticia).")
    with localcontext() as ctx:
        ctx.prec = 40
        centimo = Decimal("0.01")
        saldo = Decimal(str(monto)).quantize(centimo, rounding=ROUND_HALF_UP)
        if saldo <= 0 or saldo != Decimal(str(monto)):
            raise ValueError("El monto debe ser positivo y expresarse con hasta dos decimales.")
        tasa = (1 + Decimal(str(tea)) / 100) ** (Decimal(1) / 12) - 1
        cuota = (saldo / int(meses) if tasa == 0 else
                 saldo * tasa / (1 - (1 + tasa) ** -int(meses)))
        cuota = cuota.quantize(centimo, rounding=ROUND_HALF_UP)
        filas = []
        for periodo in range(1, int(meses) + 1):
            interes = (saldo * tasa).quantize(centimo, rounding=ROUND_HALF_UP)
            capital = saldo if periodo == meses else min(saldo, max(Decimal(0), cuota - interes))
            saldo -= capital
            filas.append({"mes": periodo, "capital": float(capital),
                          "interes": float(interes), "cuota": float(capital + interes),
                          "saldo_pendiente": float(saldo)})
        return filas


def solicitud_desde_datos(datos: dict) -> Solicitud:
    requeridos = ("ingreso", "gastos", "otras_cuotas", "monto", "meses", "tea", "estabilidad_meses", "dias_mora")
    faltantes = [campo for campo in requeridos if datos.get(campo) is None or datos.get(campo) == ""]
    if faltantes:
        raise ValueError("Información incompleta: " + ", ".join(faltantes))
    s = Solicitud(**{campo: datos[campo] for campo in requeridos}, tipo_credito=datos.get("tipo_credito", "personal"))
    evaluar(s)
    return s


def evaluar(s: Solicitud, reglas: ReglasCredito | None = None) -> dict:
    if s.tipo_credito not in PERFILES:
        raise ValueError("Tipo de crédito desconocido.")
    reglas = reglas or PERFILES[s.tipo_credito]
    validar_numero("Límite cuota/ingreso", reglas.limite_cuota_ingreso)
    validar_numero("Mora", reglas.dias_mora_alerta, entero=True)
    validar_numero("Estabilidad", reglas.estabilidad_minima, entero=True)
    if reglas.limite_deuda_total is not None:
        validar_numero("Límite deuda total", reglas.limite_deuda_total)
    if reglas.limite_cuota_ingreso > 1 or (reglas.limite_deuda_total is not None and reglas.limite_deuda_total > 1):
        raise ValueError("Los límites de ratios deben estar entre 0 y 1.")
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
    if s.dias_mora > reglas.dias_mora_alerta:
        alertas.append(f"Morosidad superior a {reglas.dias_mora_alerta} días: requiere verificación documental.")
    if saldo_final < 0:
        alertas.append("El flujo mensual disponible no alcanza para pagar la cuota.")
    if ratio_cuota is not None and ratio_cuota > reglas.limite_cuota_ingreso:
        alertas.append(f"La cuota supera el {reglas.limite_cuota_ingreso:.0%} del ingreso (umbral didáctico del equipo).")
    if s.estabilidad_meses < reglas.estabilidad_minima:
        alertas.append(f"Antigüedad de ingresos menor a {reglas.estabilidad_minima} meses.")
    if s.gastos + s.otras_cuotas > s.ingreso:
        alertas.append("Gastos y deudas existentes superan el ingreso: verificar el flujo declarado.")
    if reglas.limite_deuda_total is not None and ratio_total is not None and ratio_total > reglas.limite_deuda_total:
        alertas.append("El servicio total de deuda supera el límite académico configurado.")

    if s.ingreso == 0 or s.dias_mora > reglas.dias_mora_alerta or saldo_final < 0:
        clasificacion = "Alerta crítica: revisión humana prioritaria"
    elif alertas:
        clasificacion = "Revisión adicional necesaria"
    else:
        clasificacion = "Condiciones preliminares favorables"

    return {
        "tipo_credito": s.tipo_credito,
        "pendientes_producto": reglas.pendientes,
        "recomendacion": "Revisión humana prioritaria" if "crítica" in clasificacion else "Revisar documentación y políticas del producto antes de decidir",
        "capacidad_pago": max(0, dinero_disponible),
        "capacidad_segun_reglas": max(0, min(dinero_disponible, s.ingreso * reglas.limite_cuota_ingreso,
            s.ingreso * reglas.limite_deuda_total - s.otras_cuotas if reglas.limite_deuda_total is not None else float("inf"))),
        "ratio_deuda_actual": s.otras_cuotas / s.ingreso if s.ingreso > 0 else None,
        "cobertura_cuota": dinero_disponible / cuota,
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
