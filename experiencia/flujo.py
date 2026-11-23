"""Transiciones guiadas: captura sin red, ausencia explícita y revisión versionada."""
from dataclasses import dataclass, field
import re
from conversacion.intenciones import interpretar, normalizar
from experiencia.preguntas import PREGUNTAS, ETIQUETAS, legible, RAZONES
from ia.privacidad import mensaje_admisible


@dataclass
class Flujo:
    iniciado: bool = False
    objetivo: str = "EVALUACION"
    etapa: str = "INICIO"
    diferidos: dict = field(default_factory=dict)
    ingresos_documentos: str = "POR_PREGUNTAR"
    propiedad: str | None = None
    patrimonio_documentos: str = "POR_PREGUNTAR"
    revision_confirmada: int | None = None
    ia_revision: int | None = None
    cambios: list = field(default_factory=list)
    revision_observada: int = 0


def faltan(c):
    exp = c.expediente
    campos = [k for k in ("monto", "meses", "tea", "ingreso", "gastos", "otras_cuotas", "descuento_planilla", "estabilidad_meses", "historial")
              if getattr(exp, k) is None or getattr(exp, k) in ("DESCONOCIDO", "SIN_ACLARAR")]
    if exp.historial == "MORA_DECLARADA" and exp.dias_mora is None:
        campos.append("dias_mora")
    return campos


def siguiente(c):
    f = c.flujo
    if not f.iniciado:
        f.etapa = "INICIO"
        c.campo_preguntado = None
        return "¿Iniciamos una evaluación o prefieres simular un préstamo?"
    if f.revision_confirmada == c.revision and c.resultado is not None:
        f.etapa = "RESULTADOS"
        c.campo_preguntado = None
        return "¿Quieres revisar el detalle, comparar un escenario o preparar el informe?"
    for campo in faltan(c):
        if campo in f.diferidos or (f.objetivo == "SIMULACION" and campo not in ("monto", "meses", "tea")):
            continue
        c.campo_preguntado = campo
        f.etapa = "CONDICIONES" if campo in ("monto", "meses", "tea") else "HISTORIAL" if campo in ("estabilidad_meses", "historial", "dias_mora") else "FINANZAS"
        return PREGUNTAS[campo]
    c.campo_preguntado = None
    if f.objetivo != "SIMULACION":
        if f.ingresos_documentos == "POR_PREGUNTAR":
            f.etapa = "EVIDENCIA_INGRESOS"
            return "¿Tienes documentos que respalden los ingresos? Puedes subir boletas, presentar otro respaldo o agregarlo después."
        if f.propiedad is None or (f.propiedad == "SI" and f.patrimonio_documentos == "POR_PREGUNTAR"):
            f.etapa = "EVIDENCIA_PATRIMONIO"
            return "¿Declara algún bien o propiedad? Es opcional: no sustituye ingresos ni constituye una garantía."
    f.etapa = "REVISION_DATOS"
    return "Revisa los datos y sus fuentes. ¿Los confirmas para calcular lo que permita la información disponible?"


def registrar_revision(c, descripcion):
    f = c.flujo
    if f and f.revision_observada != c.revision:
        f.cambios.append({"revision": c.revision, "descripcion": descripcion})
        f.revision_observada = c.revision
        f.revision_confirmada = f.ia_revision = None


def iniciar(c, simulacion=False):
    c.flujo.iniciado = True
    c.flujo.objetivo = "SIMULACION" if simulacion else "EVALUACION"
    from conversacion.gestor import decir
    decir(c, siguiente(c))


def diferir(c, motivo):
    from conversacion.gestor import decir
    campo = c.campo_preguntado
    if campo:
        c.flujo.diferidos[campo] = motivo
        decir(c, f"{ETIQUETAS[campo]} queda pendiente; no se asignó ningún valor.")
        if campo == "tea":
            decir(c, "La TEA se consulta en la oferta o contrato de la entidad. Sin ella no calcularé una cuota.")
    elif c.flujo.etapa == "EVIDENCIA_INGRESOS":
        c.flujo.ingresos_documentos = motivo
    elif c.flujo.etapa == "EVIDENCIA_PATRIMONIO":
        if c.flujo.propiedad is None:
            c.flujo.propiedad = "DESCONOCIDO"
        c.flujo.patrimonio_documentos = motivo
    decir(c, siguiente(c))


def confirmar_revision(c):
    from conversacion.gestor import evaluar_actual, decir
    if c.pendiente:
        decir(c, "Confirma o cancela primero la modificación pendiente.")
        return
    if c.flujo.etapa != "REVISION_DATOS":
        decir(c, siguiente(c))
        return
    evaluar_actual(c, responder=False)
    c.flujo.revision_confirmada = c.revision
    c.flujo.ia_revision = None
    c.flujo.etapa = "RESULTADOS"
    decir(c, "Preparé el resumen con los datos confirmados. Los importes pendientes y las limitaciones documentales siguen señalados. ¿Quieres revisar el detalle o comparar condiciones?")


def recibir_guiado(c, texto):
    from conversacion.gestor import decir, proponer, crear_escenario, generar_informe
    if not texto.strip():
        return
    if not mensaje_admisible(texto):
        decir(c, "No incorporé el mensaje por posible información personal o documental. Usa solo datos de demostración; adjunta los documentos en su panel.")
        return
    t = normalizar(texto).strip(" ¿?¡!.\n")
    decir(c, texto, "user")
    if c.pendiente:
        decir(c, "Confirma o cancela la modificación pendiente antes de continuar.")
        return
    if t in ("alternativas", "comparar alternativas del credito", "ver alternativas del credito"):
        from experiencia.comparador import accion_semantica
        try:
            decir(c, accion_semantica(c, "COMPARAR", {}, {}))
        except ValueError as error:
            decir(c, str(error))
        return
    if t in ("hola", "buenas", "buenos dias", "buenas tardes", "buenas noches"):
        decir(c, "Hola, soy Triple-T. Puedo guiarte en una evaluación crediticia. ¿Iniciamos una solicitud o prefieres simular condiciones?")
        return
    if re.search(r"por que (?:necesitas|solicitas|pides|preguntas)(?: ese dato| esto)?", t):
        decir(c, RAZONES.get(c.campo_preguntado, "Los respaldos ayudan a documentar el análisis; su transcripción requiere revisión y no verifica autenticidad.") + " Si no lo sabes, puedes agregarlo después. " + siguiente(c))
        return
    if re.search(r"(?:por que|porque).*descont|doble conteo", t):
        decir(c, "Si las cuotas ya se restaron del ingreso neto, el motor reconstruye el ingreso antes de deuda para no descontarlas dos veces. ¿Todas están descontadas o ninguna?")
        return
    if re.search(r"obligatorio.*(?:document|boleta)|(?:que es|que significa).*tea", t):
        decir(c, "Sin respaldo documental se conservan limitaciones y pendientes; el análisis no acredita ingresos. La TEA es la tasa efectiva anual de la oferta, no incluye por sí sola todos los costos. " + siguiente(c))
        return
    if re.search(r"\b(?:aprueb\w*|aprobar\w*|rechaz\w*)\b", t):
        decir(c, "La decisión corresponde al analista. Puedo mostrar indicadores y pendientes, pero no aprobar ni rechazar. " + siguiente(c))
        return
    if re.search(r"\b(?:iniciar evaluacion|quiero evaluar (?:un cliente|una solicitud(?: de credito)?)|empezar|iniciar solicitud)\b", t):
        iniciar(c)
        return
    if t == "simular un prestamo":
        iniciar(c, True)
        return
    if t in ("no se", "no lo se", "no tengo", "no dispongo", "no por ahora", "agregar despues", "agregar mas tarde", "pendiente", "solicitar al cliente") or "no conozco la tea" in t:
        diferir(c, "SOLICITAR" if "solicitar" in t else "PENDIENTE")
        return
    if c.campo_preguntado == "descuento_planilla" and t in ("si", "no"):
        proponer(c, {"descuento_planilla": "YA_DESCONTADAS" if t == "si" else "NO_DESCONTADAS"})
        return
    if c.flujo.etapa == "EVIDENCIA_PATRIMONIO" and c.flujo.propiedad is None and t in ("no", "desconocido"):
        c.flujo.propiedad = "NO" if t == "no" else "DESCONOCIDO"
        decir(c, siguiente(c))
        return
    if re.search(r"\bno (?:tengo|tiene|hay|declara)\b.*\b(?:propiedad|propiedades|inmueble|bienes)\b", t):
        if c.flujo.propiedad is None:
            c.flujo.propiedad = "NO"
            decir(c, siguiente(c))
        else:
            decir(c, "La declaración patrimonial previa se conserva. Revisa y descarta el respaldo con justificación si ya no corresponde.")
        return
    if re.search(r"\b(?:tengo|tiene|hay|declara)\b.*\b(?:propiedad|inmueble|bien)\b", t):
        if c.pendiente:
            decir(c, "Primero confirma o cancela el cambio pendiente.")
            return
        from dataclasses import replace
        from conversacion.gestor import invalidar
        c.flujo.iniciado = True
        c.flujo.propiedad = "SI"
        c.flujo.patrimonio_documentos = "POR_PREGUNTAR"
        c.expediente = replace(c.expediente, patrimonio="Bien declarado; sin verificación externa")
        invalidar(c)
        c.vista = "EVIDENCIAS" if "boleta" in t else "PATRIMONIO"
        decir(c, "Podemos registrar el respaldo en el servidor de la aplicación, sin enviarlo a Gemini. La propiedad quedará declarada y sin verificación externa; no aumenta la capacidad de pago.")
        return
    if t in ("continuar", "continuar expediente", "que falta"):
        c.flujo.iniciado = True
        decir(c, siguiente(c))
        return
    if t in ("confirmar datos", "confirmar y calcular", "calcular"):
        confirmar_revision(c)
        return
    i = interpretar(texto, c.campo_preguntado)
    if i.bloqueado or i.requires_clarification:
        decir(c, "No cambié datos. " + " ".join(i.warnings))
        return
    if i.intent == "REINICIAR":
        c.pendiente = dict(accion="REINICIAR", revision=c.revision)
        decir(c, "¿Confirmas iniciar otra evaluación? Se limpiará el caso de esta sesión.")
        return
    if c.pendiente:
        decir(c, "Confirma o cancela la modificación pendiente antes de continuar.")
        return
    try:
        if i.intent == "SIMULAR" and c.flujo.revision_confirmada != c.revision:
            decir(c, "Primero confirma el caso base; después podré crear un escenario separado. " + siguiente(c))
            return
        if i.intent == "SIMULAR" and c.flujo.revision_confirmada == c.revision:
            if not i.entities:
                c.vista = "SIMULAR"
                decir(c, "Elige las nuevas condiciones en el simulador; la base se conservará.")
            else:
                crear_escenario(c, i.entities)
                c.flujo.revision_confirmada = c.revision
                c.flujo.ia_revision = None
            return
        if i.entities:
            c.flujo.iniciado = True
            proponer(c, i.entities)
            return
        if i.intent == "EVIDENCIAS":
            c.vista = "EVIDENCIAS"
            decir(c, "Carga boletas de demostración aquí. Confirma período e importe antes de incorporarlos. El procesamiento ocurre en el servidor; nunca se envían a Gemini.")
        elif i.intent == "ESTRATEGIA":
            c.vista = "ESTRATEGIA"
        elif i.intent in ("GRAFICO", "AMORTIZACION", "PDF", "CUOTA", "EXPLICAR", "ANALIZAR", "RESUMEN"):
            if c.flujo.revision_confirmada != c.revision:
                decir(c, "Primero revisemos los datos disponibles. " + siguiente(c))
            elif i.intent == "PDF":
                generar_informe(c)
            elif i.intent == "RESUMEN":
                c.vista = "DETALLE"
            else:
                c.vista = "DETALLE"
                from experiencia.ayuda_ia import explicar_local, hechos
                decir(c, explicar_local(hechos(c), texto))
        else:
            decir(c, "Podemos avanzar paso a paso; indica cantidades en cifras. " + siguiente(c))
    except (ValueError, ArithmeticError):
        decir(c, "No pude aplicar ese cambio. Revisa los importes, unidades y datos pendientes; el cálculo necesita condiciones válidas.")
