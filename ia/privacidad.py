import json
import re
from decimal import Decimal
from conversacion.intenciones import normalizar
from servicios.documentos import contiene_identificadores


def mensaje_admisible(texto):
    if not isinstance(texto, str) or not 0 < len(texto.strip()) <= 2000:
        return False
    t = normalizar(texto).replace("_", " ")
    # Filtrado conservador. Mencionar la clase de documento o un dato sin valor
    # es válido en preguntas conceptuales; proporcionar datos de identidad no.
    nombre_aparente = re.search(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\b", texto)
    return not (nombre_aparente or contiene_identificadores(texto) or re.search(
        r"\b(?:dni|ruc|pasaporte|cci|iban|cuenta bancaria|telefono|celular)\s*(?:(?:es|nro\.?|numero|no\.?)\s*)?[:#=]?\s*\+?\d"
        r"|\b(?:me llamo|se llama|a nombre de|mi nombre es|cliente real|datos reales|expediente real)\b"
        r"|\b(?:calle|avenida|av\.|jr\.|domicilio|direccion)\s+[\w ]{1,45}\s+\d"
        r"|\b(?:ocr|texto extraido|texto del documento|transcripcion)\s*[:=]"
        r"|https?://|www\.|\b\d[\d -]{7,}\d\b|aiza[\w-]+|-----begin|<[^>]+>", t))


def consulta_remota_admisible(texto):
    if not mensaje_admisible(texto):
        return False
    t = normalizar(texto)
    if re.search(r"(?:ignora|omite|olvida|desobedece)\b.{0,40}\b(?:instrucciones|politicas|reglas)|\b(?:system prompt|prompt de sistema|api key|gemini_api_key)\b", t):
        return False
    # Los bloques con aspecto de copia de un documento no son consultas.
    return len(texto.splitlines()) <= 6 and not re.search(r"\b(?:boleta de pago|recibo de sueldo)\s*[:=]", t)


def contexto_minimo(c):
    campos = ("monto", "meses", "tea", "ingreso", "gastos", "otras_cuotas", "estabilidad_meses", "dias_mora")
    def resumen(exp):
        salida = {}
        for k in campos:
            v = getattr(exp, k)
            if v is None:
                salida[k] = None
            elif isinstance(v, (int, float, Decimal)) and not isinstance(v, bool):
                salida[k] = float(v)
        for k, valores in {"tipo_credito": ("personal", "vehicular", "hipotecario", "empresarial"),
            "moneda": ("PEN", "NO_PEN"), "historial": ("DESCONOCIDO", "INSUFICIENTE", "SIN_MORA_DECLARADA", "MORA_DECLARADA"),
            "descuento_planilla": ("SIN_ACLARAR", "YA_DESCONTADAS", "NO_DESCONTADAS")}.items():
            if getattr(exp, k) in valores:
                salida[k] = getattr(exp, k)
        return salida
    contexto = {"base": resumen(c.expediente), "escenario_activo": resumen(c.escenario) if c.escenario else None,
                "campo_preguntado": c.campo_preguntado if c.campo_preguntado in campos else None,
                "revision": c.revision}
    # No mensajes, documentos, OCR, nombres de archivos, citas ni observaciones.
    return json.dumps(contexto, ensure_ascii=False, allow_nan=False)
