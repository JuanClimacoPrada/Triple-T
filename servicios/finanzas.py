"""Cálculos Sprint 2; el motor público del Sprint 1 conserva su contrato."""
from calendar import monthrange
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext

D = Decimal
CENTIMO = D("0.01")


def numero(valor, nombre, minimo=0, maximo=D("1e10")):
    try:
        if isinstance(valor, bool) or valor is None:
            raise ValueError
        n = D(str(valor))
        if not n.is_finite() or n < minimo or n > maximo:
            raise ValueError
        return n
    except (ValueError, InvalidOperation, TypeError):
        raise ValueError(f"{nombre}: número finito entre {minimo} y {maximo} requerido.") from None


def entero(valor, nombre, minimo=0, maximo=10000):
    n = numero(valor, nombre, minimo, maximo)
    if n != n.to_integral_value():
        raise ValueError(f"{nombre}: se requiere un entero.")
    return int(n)


def dinero(valor):
    return valor.quantize(CENTIMO, rounding=ROUND_HALF_UP)


def cronograma(monto, meses, tea, adicional=D(0)):
    monto = numero(monto, "Monto", CENTIMO)
    if dinero(monto) != monto:
        raise ValueError("Monto: máximo dos decimales.")
    meses = entero(meses, "Plazo", 1, 360)
    tea = numero(tea, "TEA", 0, 10000)
    adicional = numero(adicional, "Cargos mensuales")
    with localcontext() as ctx:
        ctx.prec = 40
        tasa = (1 + tea / 100) ** (D(1) / 12) - 1
        cuota = monto / meses if tasa == 0 else monto * tasa / (1 - (1 + tasa) ** -meses)
        saldo = monto
        filas = []
        for mes in range(1, meses + 1):
            inicial = saldo
            interes = saldo * tasa
            capital = saldo if mes == meses else min(saldo, cuota - interes)
            saldo -= capital
            filas.append(dict(periodo=mes, saldo_inicial=inicial, cuota_base=capital + interes,
                              interes=interes, amortizacion=capital, cargos=adicional,
                              pago_total=capital + interes + adicional, saldo_final=saldo))
        return cuota, filas


def fechas_mensuales(inicio: date, meses: int):
    fechas = []
    for n in range(1, meses + 1):
        indice = inicio.year * 12 + inicio.month - 1 + n
        ano, mes = divmod(indice, 12)
        mes += 1
        fechas.append(date(ano, mes, min(inicio.day, monthrange(ano, mes)[1])))
    return tuple(fechas)


def tcea_fechada(neto, pagos, fechas, desembolso):
    """IRR anual ACT/365; una entrada positiva seguida solo de salidas positivas."""
    neto = numero(neto, "Desembolso neto", CENTIMO)
    if not isinstance(desembolso, date) or len(pagos) != len(fechas) or not pagos:
        raise ValueError("TCEA pendiente: faltan fechas o flujos.")
    if any(not isinstance(f, date) for f in fechas) or any(b <= a for a, b in zip((desembolso,) + tuple(fechas), fechas)):
        raise ValueError("TCEA pendiente: fechas no crecientes.")
    import math
    valores = [float(numero(p, "Pago", CENTIMO)) for p in pagos]
    tiempos = [(f - desembolso).days / 365 for f in fechas]
    # Resolver log(1+r) evita desbordamiento con tasas altas y raíz negativa.
    def vpn(log_tasa):
        return sum(p * math.exp(max(-700, min(700, -log_tasa * t))) for p, t in zip(valores, tiempos)) - float(neto)
    bajo, alto = -10.0, 20.0
    if vpn(bajo) < 0 or vpn(alto) > 0:
        raise ValueError("TCEA no calculable: flujo fuera del rango numérico.")
    for _ in range(160):
        medio = (bajo + alto) / 2
        if vpn(medio) > 0:
            bajo = medio
        else:
            alto = medio
    return D(str(math.expm1((bajo + alto) / 2)))
