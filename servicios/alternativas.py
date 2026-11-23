"""Comparación académica para un mismo expediente de crédito personal."""
from dataclasses import dataclass, replace
from decimal import Decimal as D
from types import MappingProxyType

from dominio.modelos import Configuracion, Expediente, Resultado
from servicios.finanzas import CENTIMO, dinero, entero, numero
from servicios.reglas import analizar
from servicios.simulacion import evaluar_escenario


CODIGOS = ("A", "B", "C")
NOMBRES = ("Optimista", "Esperado", "Pesimista")
CAIDAS_INICIALES = (D(0), D(10), D(30))
PESOS = MappingProxyType({"DTI": D(".30"), "Capacidad": D(".25"), "Resistencia": D(".20"),
                          "Intereses": D(".15"), "Cobertura": D(".10")})
VERSION_PONDERACION = "1.0.0-academico"


@dataclass(frozen=True)
class Alternativa:
    codigo: str
    monto: D | None
    meses: int | None
    tea: D | None
    caidas: tuple[D, D, D] = CAIDAS_INICIALES


@dataclass(frozen=True)
class EscalaPuntuacion:
    dti_minimo: D = D(".60")
    saldo_objetivo: D = D(".30")
    intereses_minimo: D = D(".50")


@dataclass(frozen=True)
class EscenarioEvaluado:
    nombre: str
    caida: D
    resultado: Resultado
    componentes: dict[str, D | None]
    puntaje: D | None
    resiste: bool | None


@dataclass(frozen=True)
class EvaluacionAlternativa:
    alternativa: Alternativa
    escenarios: tuple[EscenarioEvaluado, ...]
    puntaje_global: D | None
    resisten: int | None
    preliminar: bool
    consecuencias: tuple[str, ...]
    favorable: EscenarioEvaluado | None
    desfavorable: EscenarioEvaluado | None
    motivo_pendiente: str | None
    cobertura: D | None

    @property
    def seleccionable(self):
        return all("cuota_base" in e.resultado.cifras for e in self.escenarios)


@dataclass(frozen=True)
class Comparativa:
    base: Resultado
    alternativas: tuple[EvaluacionAlternativa, ...]
    escala: EscalaPuntuacion
    umbral_dti: D
    recomendacion: str
    recomendadas: tuple[str, ...]


def generar_alternativas(expediente: Expediente):
    """Deja un campo pendiente si el límite del motor impide diferenciar B o C."""
    monto, meses, tea = expediente.monto, expediente.meses, expediente.tea
    plazo_largo = min(2 * meses, 360) if meses is not None and meses < 360 else None
    monto_reducido = dinero(D(str(monto)) * D(".80")) if monto is not None else None
    if monto_reducido is not None and not CENTIMO <= monto_reducido < monto:
        monto_reducido = None
    return (Alternativa("A", monto, meses, tea), Alternativa("B", monto, plazo_largo, tea),
            Alternativa("C", monto_reducido, meses, tea))


def _validar_alternativa(a, config):
    monto = numero(a.monto, "Monto", CENTIMO) if a.monto is not None else None
    if monto is not None and dinero(monto) != monto:
        raise ValueError("El monto admite hasta dos decimales.")
    meses = entero(a.meses, "Plazo", 1, 360) if a.meses is not None else None
    tea = numero(a.tea, "TEA", 0, config.tea_maxima) if a.tea is not None else None
    if len(a.caidas) != 3:
        raise ValueError("Indique las tres caídas de ingreso de la alternativa.")
    caidas = tuple(numero(v, "Caída del ingreso (%)", 0, 100) for v in a.caidas)
    if tuple(sorted(caidas)) != caidas:
        raise ValueError("Ordene las caídas de menor a mayor: optimista, esperado y pesimista.")
    return Alternativa(a.codigo, monto, meses, tea, caidas)


def _escala_validada(escala, umbral):
    # El DTI puede superar el 100%. Un máximo mayor a 1 permite configurar un
    # umbral de evaluación de 100% sin dejar el denominador en cero.
    minimo_dti = numero(escala.dti_minimo, "DTI de puntuación mínima", 0, 10)
    objetivo_saldo = numero(escala.saldo_objetivo, "Saldo objetivo", D(".0001"), 1)
    minimo_interes = numero(escala.intereses_minimo, "Ratio de intereses de puntuación mínima", D(".0001"), 10)
    if minimo_dti <= umbral:
        raise ValueError("El DTI de puntuación mínima debe superar el umbral académico.")
    return EscalaPuntuacion(minimo_dti, objetivo_saldo, minimo_interes)


def _escala_100(ratio):
    return 100 * min(D(1), max(D(0), ratio))


def _resiste(resultado, umbral):
    dti = resultado.cifras.get("dti_total")
    saldo = resultado.cifras.get("saldo_post_cuota")
    if saldo is not None and saldo < 0 or dti is not None and dti > umbral:
        return False
    if dti is None or saldo is None:
        return None
    return True


def _calificar(a, resultado, base, escala, umbral, resisten, cobertura):
    cifras = resultado.cifras
    ingreso_base = base.cifras.get("ingresos_admisibles")
    dti, saldo, interes = (cifras.get(k) for k in ("dti_total", "saldo_post_cuota", "intereses"))
    componentes = {
        "DTI": None if dti is None else _escala_100((escala.dti_minimo - dti) / (escala.dti_minimo - umbral)),
        "Capacidad": None if not ingreso_base or saldo is None else _escala_100(saldo / (escala.saldo_objetivo * ingreso_base)),
        "Resistencia": None if resisten is None else D(100) * resisten / 3,
        "Intereses": None if interes is None or a.monto is None else _escala_100(1 - interes / (a.monto * escala.intereses_minimo)),
        "Cobertura": None if cobertura is None else _escala_100(cobertura),
    }
    bloqueado = resultado.estado in ("DATOS INSUFICIENTES", "DISCREPANCIA PENDIENTE")
    if bloqueado or any(v is None for v in componentes.values()):
        return componentes, None
    return componentes, sum(componentes[k] * peso for k, peso in PESOS.items())


def _texto_diferencia(nombre, antes, despues, formato):
    if antes is None or despues is None:
        return f"{nombre}: comparación pendiente."
    diferencia = despues - antes
    if diferencia == 0:
        return f"{nombre}: se mantiene en {formato(despues)}."
    verbo = "sube" if diferencia > 0 else "baja"
    return f"{nombre}: {verbo} de {formato(antes)} a {formato(despues)} ({formato(abs(diferencia))})."


def _moneda(x):
    return f"S/ {x:,.2f}"


def _porcentaje(x):
    return f"{x:.2%}"


def _consecuencias(exp, a, base, escenarios, cobertura, puntaje):
    primero = escenarios[0]
    cifras = primero.resultado.cifras
    if not cifras.get("cuota_base"):
        return ("Completa o revisa las condiciones y los datos del caso para comparar las consecuencias.",)
    cambios = [
        _texto_diferencia("Monto financiado", D(str(exp.monto)), a.monto, _moneda),
        _texto_diferencia("Plazo", exp.meses, a.meses, lambda x: f"{x} meses"),
        _texto_diferencia("TEA supuesta", D(str(exp.tea)), a.tea, lambda x: f"{x:.2f}%"),
    ]
    for campo, nombre in (("cuota_base", "Cuota base"), ("pago_mensual_total", "Pago mensual con cargos"),
                          ("intereses", "Intereses"), ("total_pagos", "Total pagado con cargos declarados")):
        cambios.append(_texto_diferencia(nombre, base.cifras.get(campo), cifras.get(campo), _moneda))
    if cobertura is not None:
        cobertura_texto = f"El monto cubre {_porcentaje(cobertura)} de lo solicitado."
        if cobertura < 1:
            cobertura_texto += f" Quedarían {_moneda(D(str(exp.monto)) - a.monto)} por financiar."
        cambios.append(cobertura_texto)
    for escenario in escenarios:
        r = escenario.resultado.cifras
        etiqueta = f"{escenario.nombre} ({escenario.caida:.2f}% de caída sobre el ingreso admisible base)"
        dti = _texto_diferencia("DTI", base.cifras.get("dti_total"), r.get("dti_total"), _porcentaje)
        saldo = _texto_diferencia("Saldo mensual", base.cifras.get("saldo_post_cuota"), r.get("saldo_post_cuota"), _moneda)
        if escenario.resiste is True:
            conclusion = " Mantiene saldo no negativo y DTI dentro del umbral."
        elif escenario.resiste is False:
            conclusion = " Cuenta con déficit, supera el DTI académico o presenta ambas condiciones."
        else:
            conclusion = " La resistencia queda pendiente."
        cambios.append(f"{etiqueta}. {dti} {saldo}{conclusion}")
    if puntaje is not None:
        aportes = _aportes(escenarios)
        mayor = max(aportes, key=aportes.get)
        menor = min(aportes, key=lambda k: aportes[k] / PESOS[k])
        cambios.append(f"{mayor} aporta {aportes[mayor]:.2f} puntos al promedio. {menor} obtiene el menor puntaje medio antes de ponderar ({aportes[menor] / PESOS[menor]:.2f}/100).")
    return tuple(cambios)


def _aportes(escenarios):
    return {k: sum(e.componentes[k] for e in escenarios) / 3 * peso for k, peso in PESOS.items()}


def _pendiente(mensaje, base=None):
    reglas = list(base.reglas) if base else []
    reglas.append(dict(regla="ALT", campo="alternativa", mensaje=mensaje, nivel="pendiente"))
    return Resultado(reglas=reglas)


def _evaluar(exp, a, base, escala, umbral, config):
    resultados = []
    motivo = None
    if None in (a.monto, a.meses, a.tea):
        motivo = "Indique monto, plazo y TEA para definir una alternativa con condiciones distintas."
    elif "cuota_base" not in base.cifras:
        motivo = "Complete y revise los datos esenciales del expediente base."
    for caida in a.caidas:
        if motivo:
            resultado = _pendiente(motivo, base)
        else:
            try:
                _, resultado = evaluar_escenario(exp, a.monto, a.meses, a.tea, caida, config, base,
                                                 conservar_calendario=True)
            except (ValueError, ArithmeticError) as error:
                resultado = _pendiente(str(error), base)
        resultados.append(resultado)
    resistencia = tuple(_resiste(r, umbral) for r in resultados)
    resisten = None if None in resistencia else sum(resistencia)
    cobertura = None
    if a.monto is not None and base.cifras.get("cuota_base") is not None:
        cobertura = a.monto / D(str(exp.monto))
    escenarios = []
    for nombre, caida, resultado, resiste in zip(NOMBRES, a.caidas, resultados, resistencia):
        componentes, puntaje = _calificar(a, resultado, base, escala, umbral, resisten, cobertura)
        escenarios.append(EscenarioEvaluado(nombre, caida, resultado, componentes, puntaje, resiste))
    total = None
    if all(e.puntaje is not None for e in escenarios):
        total = sum(e.puntaje for e in escenarios) / 3
    if total is None and motivo is None:
        motivo = "Falta capacidad o DTI en al menos un escenario, o hay datos pendientes. Revise ingresos, evidencias y alertas."
    preliminar = ("promedio_documental" not in base.cifras or exp.historial == "DESCONOCIDO"
                  or any(e.estado == "PENDIENTE" for e in exp.evidencias)
                  or any(x.estado == "PRESENTADO_PENDIENTE_REVISION" for x in exp.respaldos))
    con_saldo = [e for e in escenarios if e.resultado.cifras.get("saldo_post_cuota") is not None]
    favorable = desfavorable = None
    if len(con_saldo) == 3:
        favorable = max(con_saldo, key=lambda e: (e.resultado.cifras["saldo_post_cuota"], -e.caida))
        desfavorable = min(reversed(con_saldo), key=lambda e: (e.resultado.cifras["saldo_post_cuota"], -e.caida))
    consecuencias = _consecuencias(exp, a, base, escenarios, cobertura, total)
    return EvaluacionAlternativa(a, tuple(escenarios), total, resisten, preliminar, consecuencias,
                                 favorable, desfavorable, motivo, cobertura)


def _recomendar(evaluaciones):
    def problematica(e):
        return any(s.resiste is False or any(a["nivel"] == "relevante" for a in s.resultado.reglas)
                   for s in e.escenarios)

    if all(problematica(e) for e in evaluaciones):
        return (), "Ninguna alternativa ofrece condiciones robustas bajo los supuestos. Todas exceden algún criterio de DTI o saldo en al menos un escenario, o mantienen alertas relevantes. Revise las alertas y considere ajustar las condiciones."
    if any(e.puntaje_global is None for e in evaluaciones):
        return (), "Recomendación pendiente. Complete los datos y obtenga una puntuación comparable para las tres alternativas."
    robustas = [e for e in evaluaciones if not problematica(e)]
    mayor = max(e.puntaje_global for e in robustas)
    recomendadas = [e for e in robustas if e.puntaje_global == mayor]
    codigos = tuple(e.alternativa.codigo for e in recomendadas)
    nombres = ", ".join(codigos)
    etiqueta = "Comparación preliminar" if any(e.preliminar for e in evaluaciones) else "Comparación académica"
    mensaje = (f"{etiqueta}. Priorizar para revisión {nombres} entre las alternativas que resisten los tres escenarios sin alertas relevantes. "
               f"Mayor puntuación de ese grupo: {mayor:.2f}/100.")
    if len(codigos) > 1:
        mensaje += " Hay empate en el índice. Compare los costos y la cobertura antes de elegir."
    return codigos, mensaje


def _comparar_componentes(evaluaciones):
    aportes = {e.alternativa.codigo: _aportes(e.escenarios) for e in evaluaciones if e.puntaje_global is not None}
    comparadas = []
    for e in evaluaciones:
        codigo = e.alternativa.codigo
        otras = []
        if codigo in aportes:
            for criterio in PESOS:
                mejor = max(aportes, key=lambda opcion: aportes[opcion][criterio])
                diferencia = aportes[mejor][criterio] - aportes[codigo][criterio]
                if diferencia > 0:
                    otras.append(f"En {criterio}, {mejor} aporta {diferencia:.2f} puntos ponderados más que {codigo}.")
        comparadas.append(replace(e, consecuencias=e.consecuencias + tuple(otras)))
    return tuple(comparadas)


def comparar(expediente, alternativas, config=Configuracion(), escala=EscalaPuntuacion()):
    """Evalúa las nueve combinaciones desde el mismo caso sin cambiarlo."""
    umbral = numero(config.umbral_dti, "Umbral DTI", 0, 1)
    escala = _escala_validada(escala, umbral)
    alternativas = tuple(alternativas)
    if tuple(a.codigo for a in alternativas) != CODIGOS:
        raise ValueError("La comparación necesita las alternativas A, B y C en ese orden.")
    alternativas = tuple(_validar_alternativa(a, config) for a in alternativas)
    completas = [(a.monto, a.meses, a.tea) for a in alternativas if None not in (a.monto, a.meses, a.tea)]
    if len(set(completas)) != len(completas):
        raise ValueError("Hay alternativas con el mismo monto, plazo y TEA. Ajuste sus condiciones para diferenciarlas.")
    base = analizar(expediente, config)
    evaluaciones = _comparar_componentes(tuple(_evaluar(expediente, a, base, escala, umbral, config) for a in alternativas))
    recomendadas, recomendacion = _recomendar(evaluaciones)
    return Comparativa(base, evaluaciones, escala, umbral, recomendacion, recomendadas)
