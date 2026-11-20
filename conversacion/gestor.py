"""Orquestación pura respecto a Streamlit. Solo los servicios calculan finanzas."""
from dataclasses import replace
from decimal import Decimal as D
from conversacion.modelos import Conversacion, Mensaje
from conversacion.intenciones import interpretar
from conversacion.respuestas import AYUDA, ETIQUETAS, faltantes, pregunta, respuesta_calculo
from dominio.modelos import Resultado
from servicios.finanzas import cronograma, numero, entero
from servicios.reglas import analizar
from servicios.simulacion import simular
from servicios.documentos import leer_archivo, confirmar, descartar, texto_seguro
from servicios.reporte import generar_pdf


def decir(c, texto, rol="assistant"):
    c.mensajes.append(Mensaje(rol, texto, c.revision))


def nuevo():
    c = Conversacion()
    decir(c, "Bienvenido a **Triple-T — Asistente de análisis crediticio**. Uso académico; solo datos ficticios/anónimos. Las decisiones corresponden al analista. " + AYUDA)
    return c


def invalidar(c):
    c.revision += 1
    c.resultado = None
    c.escenario = None
    c.resultado_escenario = None
    c.parametros_escenario = {}
    c.informe = None
    c.informe_revision = None
    c.pendiente = None


def validar_cambios(c, cambios):
    permitidos = {"monto", "meses", "tea", "ingreso", "gastos", "otras_cuotas", "estabilidad_meses", "historial", "dias_mora", "descuento_planilla", "tipo_credito", "moneda"}
    if set(cambios) - permitidos:
        raise ValueError("Campo no soportado; utilice los controles contextuales.")
    salida = dict(cambios)
    for k, v in cambios.items():
        if k in ("monto", "tea", "ingreso", "gastos", "otras_cuotas"):
            salida[k] = numero(v, k, D('.01') if k == "monto" else 0, c.config.tea_maxima if k == "tea" else 10000000)
        elif k in ("meses", "estabilidad_meses", "dias_mora") and v is not None:
            salida[k] = entero(v, k, 1 if k == "meses" else 0, 360 if k == "meses" else 10000)
    enums = {"historial": ("DESCONOCIDO", "INSUFICIENTE", "SIN_MORA_DECLARADA", "MORA_DECLARADA"),
             "descuento_planilla": ("SIN_ACLARAR", "YA_DESCONTADAS", "NO_DESCONTADAS"),
             "tipo_credito": ("personal", "vehicular", "hipotecario", "empresarial"), "moneda": ("PEN", "NO_PEN")}
    for k, valores in enums.items():
        if k in salida and salida[k] not in valores:
            raise ValueError(f"{k}: valor no soportado.")
    return salida


def aplicar(c, cambios, fuente="DECLARADO_EN_CHAT"):
    cambios = validar_cambios(c, cambios)
    fuentes = dict(c.expediente.origen_campos)
    fuentes.update({k: fuente for k in cambios})
    if "ingreso" in cambios:
        cambios.update(resolucion_ingreso=None, justificacion_ingreso="")
    if any(k in cambios for k in ("monto", "meses", "tea")):
        # Cambiar contrato invalida confirmación de fechas/costos, no inventa flujos.
        cambios.update(cargos_completos=False, fechas_pago=())
    c.expediente = replace(c.expediente, **cambios, origen_campos=tuple(fuentes.items()))
    invalidar(c)


def resultado_para(c, exp):
    r = analizar(exp, c.config)
    if exp.tipo_credito != "personal" or exp.moneda != "PEN":
        return r
    if not r.tabla and all(getattr(exp, k) is not None for k in ("monto", "meses", "tea")):
        # Consulta parcial de cuota admitida por SRS; no sintetiza capacidad.
        cuota, filas = cronograma(exp.monto, exp.meses, exp.tea)
        r.tabla = filas
        r.cifras.update(cuota_base=cuota, cargos_mensuales=D(0))
        r.supuestos.append("Cuota teórica sin cargos, sin evaluación de capacidad por información pendiente.")
    return r


def actualizar_estado(c):
    if c.pendiente:
        c.estado = "ACLARACION_PENDIENTE"
    elif any(e.estado == "PENDIENTE" for e in c.expediente.evidencias):
        c.estado = "CONFIRMACION_PENDIENTE"
    elif c.resultado and c.resultado.estado == "DISCREPANCIA PENDIENTE":
        c.estado = "ACLARACION_PENDIENTE"
    elif c.expediente.historial == "INSUFICIENTE" and (not c.resultado or "promedio_documental" not in c.resultado.cifras):
        c.estado = "EVIDENCIA_PENDIENTE"
    elif c.resultado and c.resultado.estado != "DATOS INSUFICIENTES":
        c.estado = "ANALIZABLE"
    else:
        c.estado = "CAPTURA"


def evaluar_actual(c, vista="RESUMEN", responder=True):
    c.resultado = resultado_para(c, c.expediente)
    actualizar_estado(c)
    c.vista = vista
    if responder:
        decir(c, respuesta_calculo(c.expediente, c.resultado))
        c.campo_preguntado, siguiente = pregunta(c.expediente)
        decir(c, siguiente)


def proponer(c, cambios, fuente="DECLARADO_EN_CHAT"):
    cambios = validar_cambios(c, cambios)
    sensibles = {k: v for k, v in cambios.items() if getattr(c.expediente, k) is not None and getattr(c.expediente, k) != v
                 and k not in ("tipo_credito", "moneda") and getattr(c.expediente, k) not in ("DESCONOCIDO", "SIN_ACLARAR")}
    if sensibles:
        c.pendiente = dict(accion="CAMBIOS", cambios=cambios, fuente=fuente, revision=c.revision)
        c.estado = "ACLARACION_PENDIENTE"
        decir(c, "Confirma los cambios del expediente: " + "; ".join(f"{k}: {getattr(c.expediente, k)} → {v}" for k, v in sensibles.items()) + ". Se invalidarán escenarios e informes anteriores.")
    else:
        aplicar(c, cambios, fuente)
        decir(c, "Registrado como " + fuente + ": " + "; ".join(f"{k}={v}" for k, v in cambios.items()))
        evaluar_actual(c)


def confirmar_accion(c, aceptar):
    p = c.pendiente
    if not p or p["revision"] != c.revision:
        decir(c, "No hay una acción vigente para confirmar.")
        return False
    c.pendiente = None
    if not aceptar:
        decir(c, "Acción cancelada; expediente conservado.")
        actualizar_estado(c)
        return False
    if p["accion"] == "REINICIAR":
        return True  # La UI sustituye todo el estado y las claves de widgets.
    aplicar(c, p["cambios"], p["fuente"])
    evaluar_actual(c)
    return False


def crear_escenario(c, cambios):
    if c.pendiente:
        raise ValueError("Confirme o cancele primero el cambio de expediente pendiente.")
    if set(cambios) - {"monto", "meses", "tea", "caida", "moneda"}:
        raise ValueError("Simulación soporta monto, plazo, TEA y caída de ingresos; especifique esos campos.")
    if c.expediente.tipo_credito != "personal" or c.expediente.moneda != "PEN":
        raise ValueError("Producto no evaluable todavía; solo personal PEN.")
    parametros = dict(c.parametros_escenario)  # Seguimientos continúan el escenario activo, etiquetado.
    parametros.update({k: v for k, v in cambios.items() if k != "moneda"})
    monto, meses, tea = (parametros.get(k, getattr(c.expediente, k)) for k in ("monto", "meses", "tea"))
    if any(v is None for v in (monto, meses, tea)):
        raise ValueError("Para simular cuota necesito monto, plazo y TEA explícitos.")
    validar_cambios(c, dict(monto=monto, meses=meses, tea=tea))
    c.resultado = resultado_para(c, c.expediente)
    try:
        exp, r = simular(c.expediente, monto, meses, tea, parametros.get("caida", D(0)), c.config)
    except ValueError:
        if parametros.get("caida", D(0)):
            raise ValueError("No se puede simular capacidad con caída de ingreso hasta resolver los datos/discrepancias del expediente.") from None
        exp = replace(c.expediente, monto=monto, meses=meses, tea=tea, cargos_completos=False, fechas_pago=())
        r = resultado_para(c, exp)
        r.supuestos.append("Escenario parcial: cambios de préstamo; no valida capacidad ni resuelve discrepancias.")
    c.revision += 1
    c.escenario, c.resultado_escenario = exp, r
    c.parametros_escenario = parametros
    c.informe = None
    c.informe_revision = None
    c.estado, c.vista = "SIMULACION", "GRAFICO"
    decir(c, "Escenario activo: " + "; ".join(f"{k}={v}" for k, v in parametros.items()) + ". El expediente, fuentes y evidencias base se conservan. Los parámetros no indicados mantienen el escenario activo o, si no existe, la base.")
    decir(c, respuesta_calculo(exp, r, True))


def actual(c):
    return (c.escenario, c.resultado_escenario) if c.escenario is not None else (c.expediente, c.resultado)


def recibir(c, texto):
    i = interpretar(texto, c.campo_preguntado)
    if i.bloqueado:
        decir(c, " ".join(i.warnings))
        return
    if i.intent == "VACIO":
        return
    decir(c, texto, "user")
    if i.requires_clarification:
        c.estado = "ACLARACION_PENDIENTE"
        decir(c, "No guardé datos de este mensaje. " + " ".join(i.warnings))
        return
    try:
        if i.intent == "REINICIAR":
            c.pendiente = dict(accion="REINICIAR", revision=c.revision)
            decir(c, "Confirma reiniciar: se limpiarán conversación, expediente, archivos, simulaciones e informes de esta sesión. No se garantiza borrado físico inmediato del proveedor.")
        elif i.intent == "AYUDA":
            decir(c, AYUDA)
        elif i.intent == "DESCONOCIDO":
            decir(c, "No he podido interpretar la solicitud. " + AYUDA)
        elif i.intent == "ESTRATEGIA":
            c.vista = "ESTRATEGIA"
            decir(c, "Comparación estratégica de tres alternativas × tres escenarios, separada de la evaluación individual. Abajo se muestran los nueve escenarios del módulo existente.")
        elif i.intent == "SIMULAR":
            crear_escenario(c, i.entities)
        elif i.intent == "FALTANTES":
            campos = faltantes(c.expediente)
            decir(c, "Faltan: " + "; ".join(ETIQUETAS[k] for k in campos) if campos else "No faltan campos básicos. Revisa las alertas y la evidencia pendiente.")
            evaluar_actual(c, responder=False)
            if c.expediente.historial == "INSUFICIENTE":
                decir(c, "Historial insuficiente no equivale a mora. Se requieren 3–6 meses distintos de netos confirmados para respaldar el ingreso.")
            c.campo_preguntado, _ = pregunta(c.expediente)
        elif i.entities:
            proponer(c, i.entities)
        elif i.intent == "EVIDENCIAS":
            c.vista = "EVIDENCIAS"
            decir(c, "Adjunta únicamente boletas sintéticas/anónimas abajo. Se presentarán candidatos y origen; no entrarán al promedio hasta confirmación visual explícita. Para historial insuficiente, 3–6 meses distintos.")
        elif i.intent == "RESUMEN":
            c.escenario = c.resultado_escenario = None
            c.parametros_escenario = {}
            c.informe = None
            evaluar_actual(c)
        elif i.intent in ("CUOTA", "ANALIZAR", "EXPLICAR", "DECISION", "AMORTIZACION", "GRAFICO", "PDF"):
            if i.intent == "DECISION":
                decir(c, "No puedo decidir la concesión del crédito. Estas son las alertas y limitaciones para revisión humana; no hay PD estimada ni verificación externa.")
            if c.escenario is None:
                evaluar_actual(c, i.intent)
            else:
                c.vista = i.intent
                decir(c, respuesta_calculo(*actual(c), escenario=True))
        if i.intent == "EVIDENCIAS":
            c.vista = "EVIDENCIAS"
        if "GRAFICO" in i.acciones:
            c.vista = "GRAFICO"
        if "PDF" in i.acciones or i.intent == "PDF":
            generar_informe(c)
    except (ValueError, ArithmeticError) as error:
        decir(c, "No se aplicó la solicitud: " + str(error))


def generar_informe(c):
    if c.pendiente:
        raise ValueError("Resuelva o cancele el cambio pendiente antes de generar el PDF.")
    if c.resultado is None:
        evaluar_actual(c, responder=False)
    exp, r = actual(c)
    if exp.tipo_credito != "personal" or exp.moneda != "PEN":
        raise ValueError("Producto no evaluable; no se genera un informe financiero.")
    comparaciones = [("Base", c.resultado)] + ([("Escenario activo", c.resultado_escenario)] if c.escenario else [])
    try:
        pdf = generar_pdf(exp, r, comparaciones, c.config)
    except Exception:
        raise ValueError("PDF no disponible; el informe en pantalla sigue accesible.") from None
    c.informe, c.informe_revision, c.estado = pdf, c.revision, "REPORTE"
    decir(c, "PDF del " + ("escenario activo" if c.escenario else "expediente base") + f" disponible abajo. Estado financiero: {r.estado}. Incluye fuentes, supuestos, fecha y limitaciones; los pendientes permanecen señalados.")


def adjuntar(c, nombre, datos, sintetico):
    doc = leer_archivo(nombre, datos, sintetico, len(c.documentos) + 1)
    c.documentos.append(doc)
    c.expediente = replace(c.expediente, evidencias=c.expediente.evidencias + tuple(doc["evidencias"]), resolucion_ingreso=None, justificacion_ingreso="")
    invalidar(c)
    c.vista = "EVIDENCIAS"
    evaluar_actual(c, "EVIDENCIAS", responder=False)
    decir(c, f"Archivo {doc['nombre']}: {len(doc['evidencias'])} candidatos DOCUMENTAL_PENDIENTE. Revisa página/frase, confirma o descarta abajo. " + " ".join(doc["avisos"]))


def cambiar_evidencia(c, indice, valor=None, fecha=None, nota="", extra=0, descartar_dato=False):
    evidencias = list(c.expediente.evidencias)
    evidencias[indice] = descartar(evidencias[indice], nota) if descartar_dato else confirmar(evidencias[indice], valor, fecha, nota, extra)
    c.expediente = replace(c.expediente, evidencias=tuple(evidencias), resolucion_ingreso=None, justificacion_ingreso="")
    invalidar(c)
    evaluar_actual(c, "EVIDENCIAS")


def aclarar_ingreso(c, fuente, justificacion):
    texto_seguro(justificacion)
    if fuente not in ("DECLARADO", "DOCUMENTAL") or not justificacion.strip():
        raise ValueError("Seleccione fuente y escriba una justificación no sensible.")
    c.expediente = replace(c.expediente, resolucion_ingreso=fuente, justificacion_ingreso=justificacion)
    invalidar(c)
    evaluar_actual(c)
