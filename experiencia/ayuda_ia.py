"""Interpretación semántica optativa y despacho controlado al motor local."""
import json
import re
from decimal import Decimal
from dominio.modelos import VERSION_REGLAS
from conversacion.intenciones import interpretar, normalizar
from ia.privacidad import consulta_remota_admisible, contexto_minimo, mensaje_admisible
from ia.proveedor import Gemini, ErrorProveedor, diagnostico_sdk, registrar_diagnostico
from ia.politicas import ERRORES
from experiencia.flujo import faltan, siguiente
from experiencia.preguntas import ETIQUETAS, PREGUNTAS, TITULOS, legible
from ia.contrato_semantico import ACCIONES, validar_respuesta
from servicios.alternativas import interpretar_saldo
from servicios.costos import CATEGORIAS, diagnostico_tcea

ALERTAS = {
    "RN-01": "Solo se evalúa crédito personal en soles.",
    "VAL-01": "Falta información para completar el análisis.",
    "VAL-02": "Hay entradas que necesitan aclaración.",
    "VAL-03": "Ingreso cero: no puede determinarse el DTI.",
    "VAL-05/07": "Hay meses duplicados; requieren revisión y descarte justificado.",
    "RN-02": "El cálculo muestra un déficit después del pago.",
    "RN-03": "El DTI supera el umbral académico configurado; requiere revisión humana.",
    "RN-04": "Historial insuficiente no equivale a mora; requiere respaldo y revisión.",
    "RN-05": "Se requieren entre tres y seis meses únicos de boletas confirmadas para sustentar el promedio.",
    "RN-07": "Hay una diferencia entre ingreso declarado y documental; revisa su aclaración y la fuente elegida.",
    "RN-08": "Aclara si todas las cuotas ya están descontadas para evitar doble conteo.",
    "RN-09": "El patrimonio es declarado; no es ingreso líquido ni garantía constituida.",
    "RN-10": "La continuidad de ingresos requiere revisión conforme a reglas académicas.",
    "RN-11": "El historial declarado requiere atención; no es una verificación externa.",
}


def estado_asistente(estado, config, *, permitido=False):
    if not permitido:
        return "Asistente local"
    if estado.circuito_abierto or (estado.habilitado and (not config.disponible or diagnostico_sdk())):
        return "Conexión no disponible · asistente local"
    if estado.habilitado and estado.consentimiento and estado.llamadas < 20:
        return "Gemini disponible"
    return "Asistente local"


def _texto_tcea(exp, resultado=None):
    tcea = resultado.tcea if resultado else None
    if tcea is not None:
        return f"La TCEA calculada para los flujos confirmados es {tcea:.2%}."
    causas = diagnostico_tcea(exp, resultado)
    if not causas:
        return "Confirma el expediente y calcula el flujo para obtener la TCEA."
    return ("La TCEA está pendiente. " + " ".join(causas)
            + " Abre «Completar costos y fechas» para revisar el flujo.")


def disponible(c):
    from conversacion.gestor import actual
    _, r = actual(c)
    return bool(c.flujo and c.flujo.revision_confirmada == c.revision and not c.pendiente and r and "cuota_base" in r.cifras)


def hechos(c):
    from conversacion.gestor import actual
    exp, r = actual(c)
    if not disponible(c):
        return {}
    facts = {"contexto": "Escenario separado" if c.escenario else "Expediente base", "reglas": VERSION_REGLAS,
        "producto": "Crédito personal en PEN", "decision": "El análisis es para revisión humana; no aprueba ni rechaza créditos.",
        "documentos": "Confirmar transcripción no verifica autenticidad ni titularidad; patrimonio no es ingreso ni garantía."}
    for k, label in (("monto", "Monto declarado"), ("meses", "Plazo en meses"), ("tea", "TEA declarada (%)")):
        valor = getattr(exp, k)
        if isinstance(valor, (int, Decimal)) and not isinstance(valor, bool):
            facts[k] = f"{label}: {valor}"
    for k, label in (("cuota_base", "Cuota base (S/)"), ("pago_mensual_total", "Pago mensual con cargos (S/)"),
        ("saldo_post_cuota", "Disponible después del pago (S/)"), ("capacidad_neta", "Capacidad de pago antes de la nueva cuota (S/)"),
        ("intereses", "Intereses totales (S/)"), ("total_pagos", "Total de pagos (S/)"), ("dti_total", "DTI")):
        valor = r.cifras.get(k)
        facts[k] = f"{label}: pendiente" if valor is None else f"{label}: " + (f"{valor:.2%}" if k == "dti_total" else f"{valor:,.2f}")
    facts["umbral"] = f"Umbral DTI académico configurable: {c.config.umbral_dti:.2%}; no es política bancaria."
    facts["formula_dti"] = "DTI = servicio mensual total de deuda / ingreso admisible. Las cuotas ya descontadas se consideran para evitar doble conteo."
    facts["lectura_saldo"] = interpretar_saldo(r)
    dti = r.cifras.get("dti_total")
    if dti is not None:
        umbral = c.config.umbral_dti
        evaluacion = "supera" if dti > umbral else "está en" if dti == umbral else "está por debajo de"
        facts["lectura_dti"] = (f"Con la nueva cuota, todas las deudas comprometerían el {dti:.2%} del ingreso admisible. "
                                 f"El valor {evaluacion} el umbral académico de {umbral:.2%}.")
    elif r.cifras.get("ingresos_admisibles") == 0:
        facts["lectura_dti"] = "El ingreso admisible es cero, por lo que no se puede expresar la deuda como porcentaje del ingreso. Confirma el ingreso del escenario."
    else:
        facts["lectura_dti"] = "Para medir qué parte del ingreso se destina a cuotas, confirma el ingreso admisible y aclara las cuotas existentes."
    # Los diagnósticos ordinarios incluyen nombres de categorías fijas. Evita
    # enviar un nombre de cargo libre heredado de otra fuente.
    facts["tcea"] = (_texto_tcea(exp, r) if all((cargo.concepto, cargo.momento) in CATEGORIAS for cargo in exp.cargos)
                     else "Revisa los cargos y vencimientos en «Completar costos y fechas».")
    facts["pendientes"] = "Campos pendientes: " + (", ".join(faltan(c)) or "ninguno básico; revisar evidencia y alertas")
    facts["evidencia"] = f"Boletas con transcripción confirmada: {sum(e.estado == 'CONFIRMADO' for e in exp.evidencias)}. Respaldos generales presentados: {sum(e.estado != 'DESCARTADO' for e in exp.respaldos)}."
    for a in r.reglas:
        if a["regla"] in ALERTAS:
            facts["alerta_" + a["regla"]] = ALERTAS[a["regla"]]
    return facts


def explicar_local(facts, texto=""):
    t = normalizar(texto)
    if re.search(r"(?:que es|que significa|para que sirve)\b.*\bboleta\b", t):
        return "Una boleta de pago documenta los ingresos y descuentos de un período. En Triple-T sirve como respaldo cuando se revisa y confirma su transcripción."
    if re.search(r"(?:que es|que significa|para que sirve)\b.*\b(?:tea|tasa efectiva anual)\b", t):
        return "La TEA expresa en términos anuales el interés efectivo del préstamo y permite calcular la tasa de cada período."
    if not facts:
        if "capacidad" in t:
            return "La capacidad disponible indica cuánto ingreso queda después de gastos y otras cuotas. Completa y confirma esos datos para calcularla."
        if "tcea" in t:
            return "La TCEA expresa el costo anual del crédito considerando los flujos de pagos y cargos. Confirma costos, fechas y desembolso para calcularla."
        return "Los resultados todavía no están disponibles. Completa y confirma los datos para obtener el cálculo."
    claves = ["pago_mensual_total", "lectura_saldo"]
    if re.search(r"dti|endeud|compromet|porcentaje.*(?:sueldo|ingreso)|(?:sueldo|ingreso).*deudas", t):
        claves = ["lectura_dti"]
    elif re.search(r"alcanz|capacidad|saldo|plata libre|cuanto (?:queda|le queda)", t):
        claves = ["lectura_saldo"]
    if "tcea" in t:
        claves = ["tcea"]
    if re.search(r"document|boleta|propiedad", t):
        claves = ["documentos", "evidencia"]
    return "\n\n".join(facts[k] for k in claves if k in facts)


def _consulta_local(c, texto, estado=None):
    from conversacion.gestor import actual
    from experiencia.comparador import resumen_seguro

    t = normalizar(texto)
    exp, resultado = actual(c)
    if re.search(r"\btcea\b", t):
        return _texto_tcea(exp, resultado if disponible(c) else None)
    if re.search(r"\b(?:alcanz\w*|capacidad|saldo)\b|plata libre|cuanto (?:queda|le queda)", t):
        if not disponible(c) or resultado.cifras.get("saldo_post_cuota") is None:
            campos = [ETIQUETAS[k].lower() for k in faltan(c)
                      if k in {"ingreso", "gastos", "otras_cuotas", "descuento_planilla", "monto", "meses", "tea"}]
            motivo = "Completa y confirma " + ", ".join(campos) + ". " if campos else "Confirma la fuente del ingreso y los datos del expediente. "
            return motivo + "Con estos datos, Triple-T podrá determinar cuánto queda después de los gastos y las cuotas."
    scope = re.search(r"\b(?:opcion\w*|alternativa\w*|convien\w*|compar\w*|pesimista|optimista)\b|ganando menos|mas meses|mas cara|con cual", t)
    if scope:
        hechos_alternativas = resumen_seguro(c)
        if not hechos_alternativas:
            return "Completa y confirma el expediente para comparar las alternativas y sus escenarios de ingresos."
        if "primera" in t and "segunda" in t:
            return "\n\n".join(hechos_alternativas[f"{codigo}_consecuencias"] for codigo in ("A", "B"))
        if "ganando menos" in t or "pesimista" in t:
            return "Compara el saldo estimado bajo la caída de ingresos de cada escenario pesimista.\n\n" + "\n\n".join(
                hechos_alternativas[f"{codigo}_pesimista"] for codigo in ("A", "B", "C"))
        referencia = re.search(r"\b(?:alternativa|opcion)\s+([abc])\b", t)
        anterior = (estado.contexto_semantico.get("referencia", {}).get("objetivo")
                    if estado and estado.revision_contexto == c.revision else None)
        codigo = referencia[1].upper() if referencia else c.alternativa_en_contexto or anterior
        if codigo in ("A", "B", "C") and not re.search(r"convien|cual de", t):
            return hechos_alternativas[f"{codigo}_consecuencias"]
        if "mas meses" in t:
            return hechos_alternativas["B_consecuencias"] + " Verifica el plazo vigente de B o prueba un plazo distinto en Simular."
        if "mas cara" in t:
            return "¿A cuál alternativa te refieres? Abre A, B o C para ver cómo cambian la cuota, los intereses y el costo total."
        if "plata libre" in t or "saldo" in t:
            return "Compara cuánto queda después de pagar los gastos y las cuotas en el escenario esperado.\n\n" + "\n\n".join(
                hechos_alternativas[f"{codigo}_esperado"] for codigo in ("A", "B", "C"))
        return hechos_alternativas["recomendacion_alternativas"]
    if re.search(r"\b(?:cuota|letra|saldo|dti|capacidad|deudas|alcanz\w*)\b|plata libre", t):
        return explicar_local(hechos(c), texto)
    if re.fullmatch(r"explicame (?:eso|lo anterior)(?: de manera sencilla)?[.?! ]*", t.strip("¿¡ ")):
        if estado and estado.revision_contexto == c.revision:
            referencia = estado.contexto_semantico.get("referencia", {}).get("objetivo")
            if referencia in ("A", "B", "C"):
                actuales = resumen_seguro(c)
                if actuales:
                    return actuales[f"{referencia}_consecuencias"]
            ids = estado.contexto_semantico.get("hechos", ())
            tema = "dti" if any("dti" in id_hecho for id_hecho in ids) else "capacidad"
            return explicar_local(hechos(c), tema)
        return "¿Quieres revisar la cuota mensual, el saldo disponible o el costo de una alternativa?"
    return None


def _contexto(c, estado):
    from experiencia.comparador import contexto_seguro, resumen_seguro

    actuales = hechos(c)
    hechos_casos = dict(actuales)
    hechos_casos.update(resumen_seguro(c))
    if c.escenario is not None and disponible(c) and c.resultado is not None:
        for campo in ("cuota_base", "pago_mensual_total", "saldo_post_cuota", "dti_total", "intereses", "total_pagos"):
            valor = c.resultado.cifras.get(campo)
            if valor is not None:
                etiqueta = campo.replace("_", " ")
                hechos_casos[f"base_{campo}"] = f"Caso base · {etiqueta}: " + (f"{valor:.2%}" if campo == "dti_total" else f"S/ {valor:,.2f}")
    faltantes = [ETIQUETAS[k] for k in faltan(c)]
    hechos_casos["pendientes"] = "Datos básicos pendientes: " + (", ".join(faltantes) or "ninguno declarado; revisa la evidencia y las alertas.")
    hechos_casos["resultados_disponibles"] = (
        "Cálculo disponible para la revisión vigente." if actuales else
        "Todavía no hay un cálculo confirmado. Completa los datos de la solicitud y confirma el análisis."
    )
    hechos_casos["concepto_cuota"] = "La cuota base es el pago periódico de capital e interés. El pago mensual puede incluir cargos adicionales."
    hechos_casos["concepto_dti"] = "El DTI relaciona la suma de las cuotas mensuales, incluida la nueva, con el ingreso admisible."
    hechos_casos["concepto_tcea"] = "La TCEA expresa el costo efectivo anual de los flujos confirmados, incluidos cargos aplicables."
    hechos_casos["concepto_tea"] = "La TEA expresa el interés efectivo anual. El plazo y la tasa periódica se usan para calcular la cuota."
    hechos_casos["concepto_capacidad"] = "La capacidad financiera depende de los gastos y cuotas existentes. El saldo posterior también descuenta el nuevo pago."
    hechos_casos["concepto_boleta"] = "La boleta de pago documenta ingresos y descuentos de un período. Para incorporarla se confirma la transcripción."
    hechos_casos["concepto_plazo"] = "El plazo distribuye el capital y el interés entre pagos. Cuota, intereses y costo total deben compararse juntos."
    minimo = json.loads(contexto_minimo(c))
    minimo["etapa"] = c.flujo.etapa if c.flujo.etapa in TITULOS else "INICIO"
    minimo["campo_preguntado"] = c.campo_preguntado if c.campo_preguntado in PREGUNTAS else None
    minimo["alternativas"] = contexto_seguro(c)
    minimo["referencia_anterior"] = estado.contexto_semantico if estado.revision_contexto == c.revision else {}
    minimo["hechos"] = hechos_casos
    return minimo


def _accion(c, solicitud):
    from conversacion.gestor import crear_escenario, generar_informe, validar_cambios
    from experiencia.comparador import accion_semantica, evaluacion_para
    from experiencia.flujo import diferir, iniciar

    intencion = solicitud.intencion
    objetivo = solicitud.referencia["objetivo"]
    entidades = solicitud.entidades
    if intencion == "INICIAR":
        iniciar(c)
        return ""
    if intencion == "DIFERIR":
        diferir(c, "PENDIENTE")
        return ""
    if intencion == "CONFIRMAR_REVISION":
        return "Revisa los datos y pulsa «Confirmar y calcular» cuando estén listos." if c.flujo.etapa == "REVISION_DATOS" else siguiente(c)
    if intencion == "REINICIAR":
        c.pendiente = dict(accion="REINICIAR", revision=c.revision)
        return "Confirma o cancela el reinicio del caso de esta sesión."
    if intencion in ("REGISTRAR_DATO", "CORREGIR"):
        if not entidades:
            return "¿Qué dato deseas registrar y cuál es su valor?"
        if objetivo not in ("", "BASE"):
            return "¿Quieres cambiar el expediente base o simular condiciones para esa alternativa?"
        cambios = validar_cambios(c, entidades)
        efectivos = {k: v for k, v in cambios.items() if getattr(c.expediente, k) != v}
        if not efectivos:
            return "Esos valores ya están registrados en el expediente."
        resumen = ", ".join(f"{ETIQUETAS[k]}: {legible(v)}" for k, v in efectivos.items())
        c.pendiente = dict(accion="CAMBIOS", cambios=efectivos, fuente="DECLARADO_EN_CHAT",
                           revision=c.revision)
        c.estado = "ACLARACION_PENDIENTE"
        return f"Datos propuestos para el expediente: {resumen}. Confirma o cancela el cambio."
    if intencion == "SIMULAR":
        if c.flujo.revision_confirmada != c.revision:
            return "Primero confirma el caso base para calcular el escenario. " + siguiente(c)
        if not entidades:
            if objetivo in ("A", "B", "C"):
                return accion_semantica(c, "EXPLICAR_CONSECUENCIAS", solicitud.referencia, {})
            c.vista = "SIMULAR"
            return "En Simular puedes ajustar el monto, el plazo, la TEA y la caída de ingresos."
        parametros = dict(entidades)
        referente = "BASE" if objetivo != "SIMULACION" else None
        if objetivo in ("A", "B", "C"):
            alternativa = evaluacion_para(c, objetivo).alternativa
            if None in (alternativa.monto, alternativa.meses, alternativa.tea):
                return "Completa los términos de esta alternativa antes de simular sus resultados."
            parametros = dict(monto=alternativa.monto, meses=alternativa.meses, tea=alternativa.tea) | parametros
        crear_escenario(c, parametros, referente)
        return ""
    if intencion in ("GENERAR_ALTERNATIVAS", "COMPARAR", "EXPLICAR_CONSECUENCIAS", "SELECCIONAR_ALTERNATIVA", "REGISTRAR_JUSTIFICACION"):
        return accion_semantica(c, intencion, solicitud.referencia, entidades)
    if intencion == "DOCUMENTOS":
        c.vista = "EVIDENCIAS"
        return "Abrí el panel de evidencias. Puedes adjuntar respaldos sintéticos y revisar la transcripción antes de confirmarla."
    if intencion == "GRAFICO":
        if not disponible(c):
            return "Los gráficos estarán disponibles al obtener un cálculo confirmado."
        c.vista = "GRAFICO"
        return "La pestaña Gráficos muestra la evolución de las cuotas y los indicadores disponibles."
    if intencion == "PDF":
        if not disponible(c):
            return "Confirma los datos y el cálculo antes de preparar el informe."
        generar_informe(c)
        return ""
    if intencion == "FUERA_DE_ALCANCE":
        return "El asistente de Triple-T se centra en el análisis crediticio. Puedes consultar los datos del caso, comparar alternativas o revisar conceptos financieros."
    return ""


def _interaccion_local(c, texto):
    """Los saludos, agradecimientos y controles directos no usan la red."""
    from conversacion.gestor import decir
    from experiencia.flujo import iniciar

    t = re.sub(r"[¿?¡!.,;:]", " ", normalizar(texto))
    t = " ".join(t.split())
    if t in {"hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "hola que tal",
             "hola buenos dias", "hola buenas tardes", "hola buenas noches"}:
        contestacion = "Hola. Puedo ayudarte a evaluar el préstamo y comparar opciones. " + siguiente(c)
    elif t in {"gracias", "muchas gracias", "ok gracias", "listo gracias", "mil gracias"}:
        contestacion = "Con gusto. Puedes seguir con el expediente o preguntarme por el resultado."
    elif t in {"ayuda", "ayudame", "necesito ayuda", "me ayudas", "por favor ayudame"}:
        contestacion = ("Puedo ayudarte a completar el expediente, leer la cuota y comparar alternativas. "
                         + siguiente(c))
    elif t in {"empecemos", "comencemos", "arranquemos", "vamos a empezar", "iniciar evaluacion"}:
        decir(c, texto, "user")
        if c.pendiente:
            decir(c, "Confirma o cancela el cambio pendiente para continuar.")
        else:
            iniciar(c)
        return True
    else:
        return False
    decir(c, texto, "user")
    decir(c, contestacion)
    return True


def _modo_local(c, texto, estado):
    from conversacion.gestor import decir, recibir
    from experiencia.comparador import accion_semantica

    t = normalizar(texto).strip(" ¿?!.")
    eleccion = re.fullmatch(r"(?:elijo|selecciona|seleccionar|me quedo con)\s+(?:la alternativa\s+)?([abc])", t)
    if not c.pendiente and (eleccion or re.search(r"\balternativas? (?:de credito|creditici[ao]s?)\b", t)):
        decir(c, texto, "user")
        try:
            referencia = {"objetivo": eleccion[1].upper() if eleccion else "", "escenario": ""}
            intencion = "SELECCIONAR_ALTERNATIVA" if eleccion else "GENERAR_ALTERNATIVAS"
            mensaje = accion_semantica(c, intencion, referencia, {})
        except ValueError as error:
            mensaje = str(error)
        if mensaje:
            decir(c, mensaje)
        return
    if not c.pendiente and re.search(r"(?:que es|que significa|para que sirve)\b.*\bboleta\b", t):
        decir(c, texto, "user")
        decir(c, explicar_local(hechos(c), texto))
        return
    i = interpretar(texto, c.campo_preguntado)
    if not (c.pendiente or i.entities or i.requires_clarification or i.bloqueado) and i.intent not in {
        "PDF", "EVIDENCIAS", "REINICIAR", "DECISION", "GRAFICO", "AMORTIZACION",
    }:
        respuesta = _consulta_local(c, texto, estado)
        if respuesta:
            decir(c, texto, "user")
            decir(c, respuesta)
            return
    recibir(c, texto)


def _fallback_seguro(c, texto, estado, motivo):
    from conversacion.gestor import decir

    # Una llamada fallida no delega la misma orden a un parser que pueda escribir.
    i = interpretar(texto, c.campo_preguntado)
    if i.entities or i.intent in {"CORREGIR", "REGISTRAR", "REINICIAR", "PDF"}:
        detalle = "El expediente conserva sus datos. Puedes usar los controles de captura o el simulador."
    else:
        detalle = _consulta_local(c, texto, estado) or explicar_local(hechos(c), texto)
    decir(c, motivo + "\n\n" + detalle)


def responder(c, texto, estado, config, *, permitido=False, proveedor=None):
    from conversacion.gestor import decir

    estado.ultima_ruta = "LOCAL"
    if not mensaje_admisible(texto):
        decir(c, "No incorporé la pregunta por posible información personal o documental. Usa únicamente datos sintéticos y envía documentos desde su panel.")
        return
    if _interaccion_local(c, texto):
        return
    disponible_ia = (c.flujo and permitido and estado.habilitado and estado.consentimiento
                     and config.disponible and not estado.circuito_abierto and estado.llamadas < 20)
    control = normalizar(texto).strip(" ¿?¡!.\n") in {
        "confirmar datos", "confirmar y calcular", "calcular", "reiniciar",
        "iniciar evaluacion", "simular un prestamo", "agregar despues", "no lo se",
    }
    if c.pendiente or not disponible_ia or control:
        _modo_local(c, texto, estado)
        return
    if not consulta_remota_admisible(texto):
        decir(c, "Esa consulta quedó en el modo local por privacidad y seguridad. Formula la pregunta sin copiar datos, documentos ni instrucciones externas.")
        return

    decir(c, texto, "user")
    etapa = "contexto"
    try:
        contexto = _contexto(c, estado)
        estado.llamadas += 1
        etapa = "red"
        salida = (proveedor or Gemini(config)).interpretar(texto, contexto)
        etapa = "validacion"
        solicitudes = validar_respuesta(salida, texto, contexto["hechos"], c.campo_preguntado)
    except Exception as error:
        seguro = error if isinstance(error, ErrorProveedor) else ErrorProveedor(
            "CONTEXTO" if etapa == "contexto" else "RESPUESTA", etapa=etapa,
        )
        registrar_diagnostico(seguro)
        estado.errores += 1
        estado.circuito_abierto = True
        estado.habilitado = False
        estado.ultimo_error = seguro.codigo
        _fallback_seguro(c, texto, estado, ERRORES[seguro.codigo])
        return

    estado.respuestas_validas += 1
    estado.ultima_ruta = "GEMINI_VALIDADO"
    estado.ultimo_error = ""
    aclaracion = next((s for s in solicitudes if s.incertidumbres or s.intencion == "ACLARAR"), None)
    if aclaracion is not None:
        decir(c, aclaracion.respuesta)
        return

    # Solo guardar referencias cerradas. Nunca almacenar texto del modelo como contexto.
    relevante = next((s for s in reversed(solicitudes) if s.referencia["objetivo"]), solicitudes[-1])
    estado.contexto_semantico = dict(intencion=relevante.intencion, referencia=relevante.referencia, hechos=list(relevante.hechos))
    estado.revision_contexto = c.revision

    for solicitud in solicitudes:
        try:
            mensaje = _accion(c, solicitud)
        except (ValueError, ArithmeticError):
            decir(c, "No pude aplicar esa propuesta. Revisa los importes, las unidades, los datos pendientes y la alternativa referida.")
            continue
        consecuencias_ya_citadas = solicitud.intencion == "EXPLICAR_CONSECUENCIAS" and any(
            id_hecho.endswith("_consecuencias") for id_hecho in solicitud.hechos
        )
        if mensaje and not consecuencias_ya_citadas:
            decir(c, mensaje)
        if solicitud.respuesta and solicitud.intencion not in ACCIONES | {"FUERA_DE_ALCANCE"}:
            decir(c, solicitud.respuesta)
