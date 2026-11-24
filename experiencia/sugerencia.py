"""Explica la comparación vigente con una sugerencia local y directa."""

from servicios.alternativas import Comparativa, efectos_principales


def _motivo_para_esperar(evaluacion, umbral):
    for escenario in reversed(evaluacion.escenarios):
        cifras = escenario.resultado.cifras
        saldo = cifras.get("saldo_post_cuota")
        dti = cifras.get("dti_total")
        if saldo is not None and saldo < 0:
            detalle = f"faltarían S/ {abs(saldo):,.2f} al mes"
        elif dti is not None and dti > umbral:
            detalle = f"las cuotas llegarían al {dti:.1%} del ingreso ({umbral:.1%} de umbral académico)"
        else:
            continue
        caida = f"{escenario.caida.normalize():f}"
        return f"Con la caída de ingresos del {caida}% del escenario {escenario.nombre.lower()}, {detalle}."

    reglas = {alerta["regla"] for escenario in evaluacion.escenarios
              for alerta in escenario.resultado.reglas if alerta["nivel"] == "relevante"}
    if "RN-11" in reglas:
        return "Primero revisaría el atraso declarado en las deudas."
    if "RN-10" in reglas:
        return "Primero revisaría la continuidad de los ingresos."
    return "Primero aclararía las alertas y los indicadores pendientes."


def _opciones(codigos):
    return ", ".join(codigos[:-1]) + " y " + codigos[-1]


def sugerencia_comparativa(comparativa: Comparativa) -> str:
    ingreso = comparativa.base.cifras.get("ingresos_admisibles")
    if ingreso is None:
        return ("Causa, todavía no se puede comparar bien. Revisa los datos pendientes del caso, "
                "sobre todo el ingreso, los gastos, las deudas y el sustento que falta confirmar.")
    if ingreso == 0:
        return ("Causa, con el ingreso admisible en cero, yo esperaría. Revisa si el ingreso "
                "está bien registrado y si hay respaldo para actualizarlo.")

    evaluaciones = comparativa.alternativas
    saldos = [e.escenarios[1].resultado.cifras.get("saldo_post_cuota") for e in evaluaciones]
    if any(saldo is None for saldo in saldos):
        return "Causa, completaría las condiciones y los indicadores pendientes antes de decidir qué opción mirar primero."
    if all(saldo <= 0 for saldo in saldos):
        return ("Causa, yo esperaría. Ninguna opción deja margen después de gastos y cuotas "
                "en el escenario esperado. Probaría una cuota más baja ajustando el monto o el plazo.")

    codigos = comparativa.recomendadas
    if len(codigos) > 1:
        return (f"Causa, las opciones {_opciones(codigos)} empatan y resisten los tres escenarios. "
                "Para escoger entre ellas, miraría cuánto te financia cada una y cuánto terminarías pagando.")
    if codigos:
        elegida = next(e for e in evaluaciones if e.alternativa.codigo == codigos[0])
        beneficio, costo = efectos_principales(elegida, comparativa.base)
        if elegida.preliminar:
            decision = f"con los datos que tenemos, yo miraría primero la opción {codigos[0]}."
        else:
            decision = f"yo tomaría la opción {codigos[0]} para este caso."
        return f"Causa, {decision} Resiste los tres escenarios. {beneficio} {costo}"

    candidatas = [e for e, saldo in zip(evaluaciones, saldos)
                 if saldo > 0 and e.escenarios[1].puntaje is not None]
    if not candidatas:
        return ("Causa, hay datos o alertas por resolver antes de escoger una opción. "
                "Revisa el detalle del ingreso y del endeudamiento en el comparador.")

    # Los puntajes se presentan a dos decimales. Una diferencia invisible en la
    # tabla no sirve para sugerir una de dos alternativas al analista.
    mejor = max(e.escenarios[1].puntaje for e in candidatas)
    primeras = [e for e in candidatas if f"{e.escenarios[1].puntaje:.2f}" == f"{mejor:.2f}"]
    if len(primeras) > 1:
        opciones = _opciones(tuple(e.alternativa.codigo for e in primeras))
        return (f"Causa, miraría primero {opciones}. Quedan parejas en el escenario esperado "
                "y dejan algo de margen mensual, pero revisaría las alertas y el escenario difícil antes de elegir.")

    elegida = primeras[0]
    beneficio, costo = efectos_principales(elegida, comparativa.base)
    motivo = _motivo_para_esperar(elegida, comparativa.umbral_dti)
    return (f"Causa, miraría primero la opción {elegida.alternativa.codigo}. Entre las que dejan margen, "
            f"tiene el mayor puntaje en el escenario esperado. {beneficio} {costo} "
            f"Yo esperaría antes de elegir. {motivo}")
