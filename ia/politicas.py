"""Enrutamiento con opt-in, presupuesto por sesión y corte ante fallos."""
import re
from dataclasses import dataclass
from conversacion.intenciones import interpretar, normalizar
from conversacion.modelos import Interpretacion
from ia.privacidad import mensaje_admisible, contexto_minimo
from ia.esquemas import validar_json
from ia.proveedor import Gemini


@dataclass
class EstadoIA:
    habilitado: bool = False
    consentimiento: bool = False
    llamadas: int = 0
    errores: int = 0
    circuito_abierto: bool = False
    ultima_ruta: str = "LOCAL"


def resolver(c, texto, estado, config, proveedor=None):
    local = interpretar(texto, c.campo_preguntado)
    t = normalizar(texto)
    # Bloqueo anterior a cualquier conexión; nunca usar excepciones para mostrar texto sensible.
    if texto.strip() and not mensaje_admisible(texto):
        return Interpretacion("PRIVACIDAD", bloqueado=True, warnings=("Mensaje bloqueado por posible información personal/documental o tamaño. No se envió al proveedor. Solo datos sintéticos; detección no exhaustiva.",)), None, ""
    if re.search(r"\b(?:aprueb\w*|aprobar\w*|rechaz\w*)\b", t):
        return Interpretacion("DECISION", source_text=texto), None, ""
    if re.search(r"\b(?:politicas internas|estado de cuenta|probabilidad de incumplimiento|predice la pd)\b", t):
        return Interpretacion("DESCONOCIDO", source_text=texto, requires_clarification=True,
            warnings=("No hay conexión a fuentes bancarias verificadas ni PD predictiva. Solo puedo explicar reglas académicas y datos ficticios.",)), None, ""
    if re.search(r"(?:explica|por que).*?(?:rn-03|endeudamiento)", t):
        return Interpretacion("EXPLICAR", source_text=texto), None, ""
    if "documentacion" in t and re.search(r"solicitar|pedir|necesit", t):
        return Interpretacion("EVIDENCIAS", source_text=texto), None, ""
    if local.bloqueado or local.requires_clarification or local.intent == "VACIO":
        return local, None, ""
    if re.search(r"\b(?:tea|tasa efectiva anual)\b.*\b(?:mensual|nominal)\b", t):
        return Interpretacion("DESCONOCIDO", source_text=texto, requires_clarification=True,
            warnings=("Periodicidad contradictoria: confirme TEA efectiva anual.",)), None, ""
    # Dar prioridad a expresiones conocidas; palabras numéricas requieren interpretación adicional.
    palabras = bool(re.search(r"\b(?:uno|un ano|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|mil|veinticinco|quinientos)\b", t))
    ambiguo = local.intent == "DESCONOCIDO" or palabras or (local.intent == "SIMULAR" and not local.entities)
    estado.ultima_ruta = "LOCAL"
    if not ambiguo:
        return local, None, ""
    if not estado.habilitado or not estado.consentimiento or estado.circuito_abierto or not config.disponible:
        if palabras:
            return Interpretacion("DESCONOCIDO", source_text=texto, requires_clarification=True,
                warnings=("Modo local: reformule cantidades con cifras y unidades explícitas (por ejemplo, monto 10000 a 12 meses con TEA 25%). No se guardaron interpretaciones parciales.",)), None, ""
        return local, None, ""
    if estado.llamadas >= 20:
        estado.habilitado = False
        estado.circuito_abierto = True
        return Interpretacion("DESCONOCIDO", source_text=texto), None, "Límite de 20 llamadas de esta sesión alcanzado; continuamos en modo local."
    estado.llamadas += 1  # Incluye fallos; una única llamada por interacción.
    try:
        contexto = contexto_minimo(c)
        if len(contexto) > 4000:
            raise ValueError("Contexto fuera de límite.")
        respuesta = (proveedor or Gemini(config)).interpretar(texto, contexto)
        interpretacion, referente = validar_json(respuesta, texto, c)
        estado.ultima_ruta = "GEMINI_VALIDADO"
        return interpretacion, referente, "Interpretación IA validada localmente; los cálculos y las respuestas proceden del motor Python."
    except Exception:
        estado.errores += 1
        estado.habilitado = False
        estado.circuito_abierto = True
        # No incorporar salida ni texto de error del proveedor a logs, mensajes o PDF.
        return Interpretacion("DESCONOCIDO", source_text=texto, requires_clarification=True,
            warnings=("Reformule con cifras y campos explícitos para continuar localmente; no se modificaron los datos ni el informe.",)), None, "IA no disponible; continuamos en modo local. Reactive conscientemente tras revisar configuración/cuota."
