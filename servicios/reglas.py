from datetime import date
from decimal import Decimal as D
from dominio.modelos import Configuracion, Expediente, Resultado
from servicios.finanzas import cronograma, numero, entero, tcea_fechada


def analizar(exp: Expediente, config=Configuracion(), ingreso_escenario=None):
    r = Resultado()
    def alerta(regla, campo, mensaje, nivel="revision"):
        r.reglas.append(dict(regla=regla, campo=campo, mensaje=mensaje, nivel=nivel))

    if exp.tipo_credito != "personal" or exp.moneda != "PEN":
        alerta("RN-01", "tipo_credito/moneda", "Próximamente; no evaluable aún. Solo personal en PEN.", "pendiente")
        return r
    requeridos = ("monto", "meses", "tea", "ingreso", "gastos", "otras_cuotas", "estabilidad_meses")
    faltantes = [k for k in requeridos if getattr(exp, k) is None]
    if faltantes:
        alerta("VAL-01", ", ".join(faltantes), "Información incompleta: " + ", ".join(faltantes), "pendiente")
        return r
    try:
        umbral = numero(config.umbral_dti, "Umbral DTI", 0, 1)
        tolerancia = numero(config.discrepancia, "Discrepancia", 0, 1)
        tope = numero(config.tea_maxima, "Tope TEA", 0, 10000)
        ingreso = numero(exp.ingreso, "Ingreso")
        gastos = numero(exp.gastos, "Gastos")
        deudas = numero(exp.otras_cuotas, "Otras cuotas")
        entero(exp.estabilidad_meses, "Estabilidad")
        numero(exp.tea, "TEA", 0, tope)
        if exp.dias_mora is not None:
            entero(exp.dias_mora, "Días de mora")
        if not isinstance(exp.fecha, date):
            raise ValueError("Fecha de evaluación requerida.")
        if exp.historial not in ("DESCONOCIDO", "INSUFICIENTE", "SIN_MORA_DECLARADA", "MORA_DECLARADA"):
            raise ValueError("Estado de historial inválido.")
        if exp.historial == "SIN_MORA_DECLARADA" and exp.dias_mora != 0:
            raise ValueError("Sin mora declarada requiere cero días explícitos.")
        if exp.historial == "MORA_DECLARADA" and (exp.dias_mora is None or exp.dias_mora <= 0):
            raise ValueError("Mora declarada requiere días positivos.")
        if exp.historial in ("DESCONOCIDO", "INSUFICIENTE") and exp.dias_mora is not None:
            raise ValueError("Historial desconocido o insuficiente: no inferir días de mora.")
        mensual, inicial = D(0), D(0)
        for cargo in exp.cargos:
            valor = numero(cargo.importe, "Cargo")
            if not cargo.concepto.strip() or cargo.momento not in ("MENSUAL", "INICIAL") or cargo.pagador not in ("SOLICITANTE", "TERCERO"):
                raise ValueError("Indicar concepto, momento y pagador de cada cargo.")
            if cargo.pagador == "SOLICITANTE":
                if cargo.momento == "MENSUAL":
                    mensual += valor
                else:
                    inicial += valor
        cuota, tabla = cronograma(exp.monto, exp.meses, exp.tea, mensual)
        if exp.patrimonio_valor is not None:
            numero(exp.patrimonio_valor, "Patrimonio")
    except (ValueError, ArithmeticError) as error:
        alerta("VAL-02", "entradas", str(error), "pendiente")
        return r

    # Ningún candidato pendiente entra a un promedio confirmado.
    grupos = {}
    for e in exp.evidencias:
        if e.estado != "CONFIRMADO" or e.tipo_documento != "BOLETA":
            continue
        try:
            neto = numero(e.valor_extraido, "Neto admisible")
            numero(e.extraordinarios_excluidos, "Extraordinarios excluidos")
            if not isinstance(e.fecha_documento, date) or e.fecha_documento > exp.fecha:
                raise ValueError("Mes de boleta ausente o posterior a evaluación.")
            if e.fuente != "CONFIRMADO_ANALISTA":
                raise ValueError("Boleta sin confirmación del analista.")
            mes = e.fecha_documento.strftime("%Y-%m")
            grupos.setdefault(mes, []).append((neto, e))
        except ValueError as error:
            alerta("RN-05", "evidencias", str(error), "pendiente")
    for mes, items in sorted(grupos.items()):
        if len(items) > 1:
            alerta("VAL-05/07", mes, "Mes duplicado: descartar duplicados con justificación y confirmar una sola evidencia.", "discrepancia")
        else:
            neto, e = items[0]
            r.meses_ingreso.append(dict(mes=mes, neto=neto, documento_id=e.documento_id,
                                       origen=e.nombre_archivo_sanitizado, fuente=e.fuente,
                                       extraordinarios_excluidos=e.extraordinarios_excluidos))
    cuenta = len(r.meses_ingreso)
    promedio = None
    if 3 <= cuenta <= 6 and not any(x["nivel"] in ("pendiente", "discrepancia") for x in r.reglas):
        promedio = sum((f["neto"] for f in r.meses_ingreso), D(0)) / cuenta
        r.cifras["promedio_documental"] = promedio
        r.cifras["rango_ingresos"] = f"{min(f['neto'] for f in r.meses_ingreso)} - {max(f['neto'] for f in r.meses_ingreso)}"
        diferencia = abs(ingreso - promedio) / max(ingreso, promedio) if max(ingreso, promedio) else D(0)
        r.cifras["discrepancia_relativa"] = diferencia
        if diferencia > tolerancia:
            if exp.resolucion_ingreso in ("DECLARADO", "DOCUMENTAL") and exp.justificacion_ingreso.strip():
                alerta("RN-07", "ingreso", f"Discrepancia aclarada por analista ({exp.resolucion_ingreso}): {exp.justificacion_ingreso}")
                ingreso = ingreso if exp.resolucion_ingreso == "DECLARADO" else promedio
            else:
                alerta("RN-07", "ingreso", f"Diferencia {diferencia:.2%} > {tolerancia:.2%}. Aclaración obligatoria.", "discrepancia")
        else:
            ingreso = promedio
    else:
        alerta("RN-05", "evidencias", f"Evidencia insuficiente: {cuenta} meses únicos confirmados; se requieren entre 3 y 6.",
               "pendiente" if exp.evidencias or exp.historial == "INSUFICIENTE" else "revision")
    if exp.historial == "DESCONOCIDO":
        alerta("RN-11", "historial", "Historial desconocido: aclaración pendiente, sin inferir mora.", "pendiente")
    elif exp.historial == "INSUFICIENTE":
        alerta("RN-04", "historial", "Historial insuficiente: se requiere evidencia complementaria y revisión humana; no equivale a mora.")
    elif exp.historial == "MORA_DECLARADA":
        alerta("RN-11", "dias_mora", f"Mora declarada: {exp.dias_mora} días; " + ("alerta crítica para revisión." if exp.dias_mora > 30 else "advertencia para revisión."), "relevante")
    if exp.estabilidad_meses < 6:
        alerta("RN-10", "estabilidad_meses", "Continuidad menor a 6 meses: alerta didáctica.", "relevante")
    elif exp.estabilidad_meses < 12:
        alerta("RN-10", "estabilidad_meses", "Continuidad de 6 a 11 meses: revisión adicional.")
    else:
        r.cifras["continuidad"] = "Favorable como señal auxiliar, no acredita capacidad."
    if exp.patrimonio or exp.patrimonio_valor is not None:
        alerta("RN-09", "patrimonio", "Patrimonio declarado, no verificado. No es garantía constituida ni ingreso líquido.")
    if exp.descuento_planilla not in ("NO_DESCONTADAS", "YA_DESCONTADAS"):
        alerta("RN-08", "descuento_planilla", "Confirmar si TODAS las otras cuotas ya están descontadas del neto. Si la situación es mixta, normalizar importes antes de continuar.", "pendiente")
    # Bloquear capacidad si hay evidencia contradictoria o doble conteo sin resolver.
    bloqueada = any(x["nivel"] in ("discrepancia", "pendiente") for x in r.reglas if x["regla"] not in ("RN-11",))
    r.tabla = tabla
    r.cifras.update(cuota_base=cuota, gastos=gastos, otras_cuotas=deudas, cargos_mensuales=mensual, cargos_iniciales=inicial,
                    pago_mensual_total=cuota + mensual, intereses=sum(f["interes"] for f in tabla),
                    total_pagos=sum(f["pago_total"] for f in tabla) + inicial)
    if not bloqueada:
        # Si todas las deudas ya se descontaron, reconstruir ingreso predeuda.
        ingreso_admisible = ingreso + deudas if exp.descuento_planilla == "YA_DESCONTADAS" else ingreso
        if ingreso_escenario is not None:
            ingreso_admisible = numero(ingreso_escenario, "Ingreso del escenario")
        saldo_pre = ingreso_admisible - gastos - deudas
        pago = cuota + mensual
        saldo_post = saldo_pre - pago
        dti = (deudas + pago) / ingreso_admisible if ingreso_admisible else None
        r.cifras.update(ingresos_admisibles=ingreso_admisible, saldo_pre_cuota=saldo_pre,
                        saldo_post_cuota=saldo_post, dti_total=dti,
                        capacidad_neta=max(D(0), saldo_pre),
                        capacidad_umbral=max(D(0), min(saldo_pre, ingreso_admisible * umbral - deudas)))
        if ingreso_admisible == 0:
            alerta("VAL-03", "ingreso", "Ingreso cero: DTI N/D; revisión por capacidad.", "relevante")
        if saldo_post < 0:
            alerta("RN-02", "saldo_post_cuota", f"Déficit mensual S/ {saldo_post:.2f}.", "relevante")
        if dti is not None and dti > umbral:
            alerta("RN-03", "dti_total", f"DTI total {dti:.2%} > umbral didáctico {umbral:.2%}.", "relevante")
    if exp.cargos_completos:
        try:
            r.tcea = tcea_fechada(exp.monto - inicial, [f["pago_total"] for f in tabla], exp.fechas_pago, exp.fecha_desembolso)
        except (ValueError, ArithmeticError) as error:
            alerta("RN-13", "TCEA", str(error))
    else:
        alerta("RN-13", "TCEA", "TCEA no calculable con los datos disponibles: confirmar todos los cargos, fechas y desembolso neto.")
    niveles = {x["nivel"] for x in r.reglas}
    r.estado = ("DISCREPANCIA PENDIENTE" if "discrepancia" in niveles else
                "DATOS INSUFICIENTES" if "pendiente" in niveles else
                "ALERTAS RELEVANTES" if "relevante" in niveles else
                "REVISIÓN ADICIONAL" if "revision" in niveles else
                "CONDICIONES PRELIMINARES FAVORABLES")
    return r
