"""Esquema cerrado y validación local independiente de response_schema."""
import json
import re
from decimal import Decimal as D
from conversacion.intenciones import interpretar, normalizar, valor_numerico
from conversacion.modelos import Interpretacion
from servicios.finanzas import numero, entero

INTENCIONES = {"REGISTRAR": "REGISTRAR", "CONSULTAR_CUOTA": "CUOTA", "ANALIZAR": "ANALIZAR", "FALTANTES": "FALTANTES",
    "SIMULAR": "SIMULAR", "EXPLICAR": "EXPLICAR", "EVIDENCIAS": "EVIDENCIAS", "GRAFICO": "GRAFICO", "PDF": "PDF",
    "ESTRATEGIA": "ESTRATEGIA", "AYUDA": "AYUDA", "RESUMEN": "RESUMEN", "CORREGIR": "CORREGIR",
    "REINICIAR": "REINICIAR", "FUERA_DE_ALCANCE": "DESCONOCIDO", "ACLARAR": "DESCONOCIDO", "DECISION": "DECISION"}
NUMERICOS = ("monto", "meses", "tea", "ingreso", "gastos", "otras_cuotas", "estabilidad_meses", "caida", "dias_mora")
ENUMS = {"historial": ["DESCONOCIDO", "INSUFICIENTE", "SIN_MORA_DECLARADA", "MORA_DECLARADA"],
         "descuento_planilla": ["SIN_ACLARAR", "YA_DESCONTADAS", "NO_DESCONTADAS"],
         "moneda": ["PEN"], "tipo_credito": ["personal", "vehicular", "hipotecario", "empresarial"]}
CAMPOS = NUMERICOS + tuple(ENUMS)
ESQUEMA = {"type": "object", "additionalProperties": False, "required": ["intent", "entities", "supports", "referente", "requires_clarification", "clarification_field"],
 "properties": {
  "intent": {"type": "string", "enum": list(INTENCIONES)},
  "entities": {"type": "object", "additionalProperties": False, "properties": {
      **{k: {"type": ["number", "null"]} for k in NUMERICOS},
      **{k: {"type": ["string", "null"], "enum": v + [None]} for k, v in ENUMS.items()}}},
  "supports": {"type": "object", "additionalProperties": False, "properties": {k: {"type": "string", "maxLength": 180} for k in CAMPOS}},
  "referente": {"type": "string", "enum": ["BASE", "ESCENARIO_ACTIVO"]},
  "requires_clarification": {"type": "boolean"},
  "clarification_field": {"type": ["string", "null"], "enum": list(CAMPOS) + [None]}}}

UNIDADES = dict(zip("cero uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince dieciseis diecisiete dieciocho diecinueve veinte veintiuno veintidos veintitres veinticuatro veinticinco veintiseis veintisiete veintiocho veintinueve".split(), range(30)))
UNIDADES.update(un=1, una=1, treinta=30, cuarenta=40, cincuenta=50, sesenta=60, setenta=70, ochenta=80, noventa=90,
                cien=100, ciento=100, doscientos=200, trescientos=300, cuatrocientos=400, quinientos=500,
                seiscientos=600, setecientos=700, ochocientos=800, novecientos=900)


def cantidad_literal(fragmento):
    """Normaliza una cantidad lingüística; no calcula indicadores de crédito."""
    t = normalizar(fragmento)
    t = t.replace("por ciento", "")
    cifras = re.findall(r"[-+]?\d[\d.,]*", t)
    if len(cifras) == 1:
        return valor_numerico(cifras[0], "cantidad citada")
    if cifras:
        raise ValueError("Cita con varias cantidades.")
    palabras = re.findall(r"[a-z]+", t)
    tokens = [p for p in palabras if p in UNIDADES or p in ("mil", "millon", "millones")]
    if not tokens:
        raise ValueError("Cantidad sin soporte textual.")
    # La cita debe ser breve y contener una sola secuencia numérica.
    indices = [i for i, p in enumerate(palabras) if p in UNIDADES or p in ("mil", "millon", "millones")]
    if any(p not in UNIDADES and p not in ("mil", "millon", "millones", "y") for p in palabras[indices[0]:indices[-1]+1]):
        raise ValueError("Cita numérica ambigua.")
    total = grupo = 0
    for p in tokens:
        if p == "mil":
            total += (grupo or 1) * 1000
            grupo = 0
        elif p in ("millon", "millones"):
            total += (grupo or 1) * 1000000
            grupo = 0
        else:
            grupo += UNIDADES[p]
    return D(total + grupo)


def _pares(pares):
    d = {}
    for k, v in pares:
        if k in d:
            raise ValueError("Clave JSON duplicada.")
        d[k] = v
    return d


def validar_json(respuesta, texto, c):
    if not isinstance(respuesta, str) or len(respuesta) > 8192:
        raise ValueError("Salida fuera de límite.")
    obj = json.loads(respuesta, object_pairs_hook=_pares, parse_float=D,
                     parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Número no finito")))
    if not isinstance(obj, dict) or set(obj) != set(ESQUEMA["required"]):
        raise ValueError("Esquema no permitido.")
    if obj["intent"] not in INTENCIONES or obj["referente"] not in ("BASE", "ESCENARIO_ACTIVO") or type(obj["requires_clarification"]) is not bool:
        raise ValueError("Acción o tipo no permitido.")
    if obj["clarification_field"] not in CAMPOS + (None,):
        raise ValueError("Campo de aclaración no permitido.")
    ent, citas = obj["entities"], obj["supports"]
    if not isinstance(ent, dict) or not isinstance(citas, dict) or set(ent) - set(CAMPOS) or set(citas) - set(CAMPOS):
        raise ValueError("Entidades no permitidas.")
    if obj["requires_clarification"] or obj["intent"] == "ACLARAR":
        if any(v is not None for v in ent.values()):
            raise ValueError("Aclaración no puede incluir datos a guardar.")
        return Interpretacion("DESCONOCIDO", source_text=texto, requires_clarification=True,
            warnings=("Aclare explícitamente " + (obj["clarification_field"] or "la intención o los datos") + "; no se guardaron valores.",)), obj["referente"]
    salida = {}
    local = interpretar(texto, c.campo_preguntado)
    if local.requires_clarification or local.bloqueado:
        raise ValueError("No se permite resolver ambigüedad local mediante IA.")
    for k, v in ent.items():
        if v is None:
            continue
        cita = citas.get(k)
        if not isinstance(cita, str) or not 0 < len(cita) <= 180 or cita not in texto:
            raise ValueError("Entidad sin cita literal de la consulta.")
        if k in NUMERICOS:
            etiquetas = {"monto": r"monto|prestamo|financiamiento|solicita|solicito|pido|pedir|credito|por s/",
                "ingreso": r"ingreso|gana|sueldo", "gastos": r"gasto|gasta", "otras_cuotas": r"cuota|deuda",
                "tea": r"\btea\b|tasa efectiva anual", "estabilidad_meses": r"estabilidad|continuidad|antiguedad",
                "caida": r"cae|baja|menos|caida|disminu|reduc", "dias_mora": r"mora|atraso"}
            if k in etiquetas and not re.search(etiquetas[k], normalizar(cita)):
                raise ValueError("Cita sin relación explícita con el campo.")
            if isinstance(v, bool) or not isinstance(v, (int, D)):
                raise ValueError("Tipo numérico estricto requerido.")
            tope = c.config.tea_maxima if k == "tea" else 100 if k == "caida" else 10000000
            n = numero(v, k, D('.01') if k == "monto" else 0, tope)
            if k in ("meses", "estabilidad_meses", "dias_mora"):
                n = entero(n, k, 1 if k == "meses" else 0, 360 if k == "meses" else 10000)
            elif n.as_tuple().exponent < -2:
                raise ValueError("Máximo dos decimales en propuestas IA.")
            literal = cantidad_literal(cita)
            if k in ("meses", "estabilidad_meses") and re.search(r"\banos?\b", normalizar(cita)):
                literal *= 12
            if D(n) != literal:
                raise ValueError("Cantidad no coincide con la cita.")
            if k == "tea" and not re.search(r"\btea\b|tasa efectiva anual", normalizar(texto)):
                raise ValueError("Falta periodicidad TEA explícita.")
            if k == "meses" and not re.search(r"\b(?:meses?|anos?)\b", normalizar(cita)):
                raise ValueError("Falta unidad temporal.")
            if k == "meses" and not re.search(r"plazo|pagar|pagaria|cancelar|extiend|extender|financiamiento|prestamo|credito|solicita", normalizar(texto)) and c.expediente.monto is None:
                raise ValueError("No está claro si la duración es plazo o estabilidad.")
            salida[k] = n
        else:
            if not isinstance(v, str) or v not in ENUMS[k]:
                raise ValueError("Enumeración no permitida.")
            # Campos críticos categóricos necesitan soporte del parser local o etiqueta exacta.
            if local.entities.get(k) != v and not (k == "moneda" and re.search(r"soles|pen|s/", normalizar(cita))) and not (k == "tipo_credito" and v in normalizar(cita)):
                raise ValueError("Estado categórico requiere declaración local explícita.")
            salida[k] = v
    for k, v in local.entities.items():
        if k in salida and salida[k] != v:
            raise ValueError("Contradicción con extracción determinista.")
    if salida.get("historial") in ("INSUFICIENTE", "DESCONOCIDO"):
        if salida.get("dias_mora") is not None:
            raise ValueError("No inferir mora del historial.")
        salida["dias_mora"] = None
    if salida.get("historial") == "SIN_MORA_DECLARADA":
        if salida.get("dias_mora", 0) != 0:
            raise ValueError("Historial y mora contradictorios.")
        salida["dias_mora"] = 0
    intent = INTENCIONES[obj["intent"]]
    if len(re.findall(r"\bgana\b", normalizar(texto))) > 1 and "ingreso" in salida:
        raise ValueError("Más de una declaración de ingreso requiere aclaración.")
    if intent not in ("REGISTRAR", "CORREGIR", "SIMULAR", "CUOTA", "ANALIZAR", "EVIDENCIAS") and salida:
        raise ValueError("Acción no puede modificar campos.")
    if intent == "SIMULAR" and set(salida) - {"monto", "meses", "tea", "caida"}:
        raise ValueError("Campos de escenario no permitidos.")
    if obj["referente"] == "ESCENARIO_ACTIVO" and c.escenario is None:
        raise ValueError("No hay escenario activo.")
    if intent in ("REGISTRAR", "CORREGIR") and obj["referente"] != "BASE":
        raise ValueError("La edición del expediente debe referirse a la base.")
    # Si el mensaje es hipotético, nunca permitir registrar cambios base.
    if re.search(r"\b(?:y si|seria|extiendo|extender|simula|menos|mas tiempo)\b", normalizar(texto)) and intent in ("REGISTRAR", "CORREGIR"):
        raise ValueError("Una hipótesis no modifica la base.")
    return Interpretacion(intent, salida, texto), obj["referente"]
