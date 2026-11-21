"""Parser puro y determinista. Nunca calcula cuota, DTI, PD ni decisiones."""
import re
import unicodedata
from decimal import Decimal as D
from conversacion.modelos import Interpretacion
from servicios.documentos import contiene_identificadores
from servicios.finanzas import numero, entero

NUM = r"[-+]?(?:\d[\d.,]*|nan|infinity|infinito|inf)"
MONEDA = r"(?:s/\s*)?"


def normalizar(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def valor_numerico(token, campo):
    token = token.rstrip(".,")
    if "." in token and "," in token:
        raise ValueError(f"{campo}: separadores mixtos; escriba el importe sin miles y con hasta dos decimales.")
    if re.fullmatch(r"[-+]?\d{1,3}(?:\.\d{3})+", token):
        raise ValueError(f"{campo}: «{token}» es ambiguo. Confirme el valor sin separador de miles, por ejemplo 3500 o 3.50.")
    if "," in token:
        if re.fullmatch(r"[-+]?\d{1,3}(?:,\d{3})+", token):
            token = token.replace(",", "")
        elif re.fullmatch(r"[-+]?\d+,\d{1,2}", token):
            token = token.replace(",", ".")
        else:
            raise ValueError(f"{campo}: número ambiguo; use cifras sin separadores de miles.")
    return numero(token, campo, 0, D("10000000"))


def interpretar(texto: str, campo_pendiente=None) -> Interpretacion:
    if not texto.strip():
        return Interpretacion("VACIO", warnings=("Escriba una consulta o un dato ficticio.",))
    if len(texto) > 2000:
        return Interpretacion("DESCONOCIDO", warnings=("Use un mensaje de hasta 2000 caracteres.",), bloqueado=True)
    if contiene_identificadores(texto):
        return Interpretacion("PRIVACIDAD", warnings=("Posibles identificadores detectados: mensaje no incorporado. Solo datos ficticios/anónimos; la detección no garantiza anonimización.",), bloqueado=True)
    t = normalizar(texto)
    entidades, problemas = {}, []
    def asignar(campo, valor):
        if campo in entidades and entidades[campo] != valor:
            problemas.append(f"Dos valores contradictorios para {campo}; indique cuál corresponde.")
        else:
            entidades[campo] = valor
    def buscar(campo, patron, unidad=False):
        for m in re.finditer(patron, t):
            try:
                valor = valor_numerico(m[1], campo)
                if unidad and m[2].startswith("ano"):
                    valor *= 12  # Conversión de unidad, no regla crediticia.
                if campo in ("meses", "estabilidad_meses", "dias_mora"):
                    valor = entero(valor, campo, 1 if campo == "meses" else 0, 360 if campo == "meses" else 10000)
                if campo == "monto" and valor <= 0:
                    raise ValueError("monto: debe ser positivo.")
                if campo == "caida" and valor > 100:
                    raise ValueError("caída de ingresos: debe estar entre 0 y 100%.")
                asignar(campo, valor)
            except ValueError as error:
                problemas.append(str(error))
    separador = r"\s*(?:(?:es|de|son|a|en|por|del)\s+)?(?:[:=]\s*)?"
    buscar("ingreso", rf"\b(?:gana|ingresos?(?:\s+(?:netos?|mensuales?|declarados?))*){separador}{MONEDA}({NUM})(?![\d.,]|\s*%)")
    buscar("gastos", rf"\b(?:gastos?(?:\s+mensuales?)?|gasta){separador}{MONEDA}({NUM})")
    buscar("otras_cuotas", rf"\b(?:otras?\s+(?:cuotas|deudas)(?:\s+mensuales)?|deudas?\s+mensuales|cuotas?\s+existentes|cuotas){separador}{MONEDA}({NUM})")
    buscar("monto", rf"\b(?:quiero|solicita|solicito|pido|pedir|monto(?:\s+solicitado)?|prestamo(?:\s+personal)?|credito\s+personal){separador}{MONEDA}({NUM})")
    buscar("meses", rf"\b(?:a|en|plazo(?:\s+(?:fuera|sea|de|a))?)\s*({NUM})\s*(meses?|anos?)\b", True)
    buscar("estabilidad_meses", rf"\b(?:estabilidad|continuidad|antiguedad)(?:\s+(?:de|es|:))?\s*({NUM})\s*(meses?|anos?)\b", True)
    buscar("tea", rf"\b(?:tea|tasa\s+efectiva\s+anual){separador}({NUM})\s*%?")
    buscar("caida", rf"\b(?:cae|caen|baja|bajan|caida|reduccion)(?:\s+(?:el|los|de|del))?(?:\s+ingresos?)?\s*({NUM})\s*%")
    buscar("dias_mora", rf"\b(?:mora|atraso)(?:\s+(?:de|es))?\s*({NUM})\s*dias?\b")
    if campo_pendiente in ("meses", "estabilidad_meses"):
        buscar(campo_pendiente, rf"^\s*({NUM})\s*(meses?|anos?)\s*[?.!]?\s*$", True)
    if re.search(r"\b(?:sin historial|no (?:tiene|tengo|hay) historial|historial insuficiente)\b", t):
        asignar("historial", "INSUFICIENTE")
        asignar("dias_mora", None)
    if re.search(r"\b(?:sin mora|no (?:tiene|tengo|hay) (?:mora|atrasos)|al dia)\b", t):
        asignar("historial", "SIN_MORA_DECLARADA")
        asignar("dias_mora", 0)
    if re.search(r"\b(?:historial desconocido|no conozco (?:el )?historial)\b", t):
        asignar("historial", "DESCONOCIDO")
        asignar("dias_mora", None)
    if entidades.get("dias_mora") is not None and entidades["dias_mora"] > 0:
        asignar("historial", "MORA_DECLARADA")
    elif re.search(r"\b(?:tiene mora|tengo mora|con mora|mora declarada)\b", t):
        asignar("historial", "MORA_DECLARADA")
        asignar("dias_mora", None)
    if re.search(r"\b(?:no estan descontadas|no descontadas|planilla no descontada|no se descuentan)\b", t):
        asignar("descuento_planilla", "NO_DESCONTADAS")
    elif re.search(r"\b(?:ya estan descontadas|todas estan descontadas|planilla descontada|ya descontadas)\b", t):
        asignar("descuento_planilla", "YA_DESCONTADAS")
    if re.search(r"\b(?:vehicular|hipotecario|empresarial)\b", t):
        asignar("tipo_credito", re.search(r"\b(vehicular|hipotecario|empresarial)\b", t)[1])
    elif re.search(r"\bpersonal\b", t):
        asignar("tipo_credito", "personal")
    if re.search(r"\b(?:usd|dolares|euros)\b", t):
        asignar("moneda", "NO_PEN")
    elif re.search(r"\b(?:pen|soles)\b|s/", t):
        asignar("moneda", "PEN")
    # Ni una tasa nominal anual ni una tasa mensual se convierten silenciosamente.
    if re.search(r"\btasa\b.*?" + NUM, t) and "tea" not in entidades:
        problemas.append("Indique explícitamente TEA (tasa efectiva anual); no puedo inferir periodicidad ni convertir una tasa nominal/mensual.")
    if "%" in t and "tea" not in entidades and "caida" not in entidades:
        problemas.append("¿El porcentaje corresponde a TEA o a caída de ingresos? Indíquelo explícitamente.")
    if "tea" in entidades and re.search(r"\b(?:mensual|nominal)\b", t[t.find("tea"):]):
        problemas.append("La tasa tiene periodicidad contradictoria; confirme TEA efectiva anual.")
    if campo_pendiente and re.fullmatch(rf"\s*{MONEDA}({NUM})\s*(?:soles)?[?.!]?\s*", t):
        if campo_pendiente == "tea":
            problemas.append("Confirme la tasa escribiendo TEA y el porcentaje.")
        elif campo_pendiente in ("monto", "ingreso", "gastos", "otras_cuotas", "meses", "estabilidad_meses"):
            try:
                token = re.search(NUM, t)[0]
                v = valor_numerico(token, campo_pendiente)
                if campo_pendiente in ("meses", "estabilidad_meses"):
                    v = entero(v, campo_pendiente, 1 if campo_pendiente == "meses" else 0, 360 if campo_pendiente == "meses" else 10000)
                asignar(campo_pendiente, v)
            except ValueError as error:
                problemas.append(str(error))
    hipotetico = bool(re.search(r"\b(?:simula|simular|simulacion|y si|que pasa si|que ocurre si|y a|y por)\b", t))
    if re.search(r"\by por\s+(?:s/\s*)?" + NUM, t):
        buscar("monto", rf"\by por\s*{MONEDA}({NUM})")
    acciones = []
    if re.search(r"\b(?:grafico|evolucion|baja el saldo)\b", t):
        acciones.append("GRAFICO")
    if re.search(r"\b(?:pdf|reporte|informe)\b", t):
        acciones.append("PDF")
    if re.search(r"\b(?:reinicia|reiniciar|empieza otra|nuevo caso|otra evaluacion)\b", t):
        intent = "REINICIAR"
    elif re.search(r"\b(?:aprueba|aprobar|aprobarlo|rechaza|rechazar|rechazarlo|aprobacion)\b", t):
        intent = "DECISION"
    elif re.search(r"\b(?:compara|comparar)\b.*(?:alternativas|tecnolog|\ba\b.*\bb\b.*\bc\b)", t):
        intent = "ESTRATEGIA"
    elif re.search(r"\b(?:boletas?|subir|adjuntar|documentos?)\b", t):
        intent = "EVIDENCIAS"
    elif re.search(r"\b(?:que (?:datos )?faltan?|que falta)\b", t):
        intent = "FALTANTES"
    elif re.search(r"\b(?:que datos tienes|resumen|expediente actual|volver a (?:la )?base)\b", t):
        intent = "RESUMEN"
    elif re.search(r"\b(?:explica|explicar|por que)\b.*\b(?:alerta|dti|regla)\b", t):
        intent = "EXPLICAR"
    elif re.search(r"\b(?:ayuda|ejemplos|que puedes hacer)\b", t):
        intent = "AYUDA"
    elif hipotetico or "caida" in entidades:
        intent = "SIMULAR"
    elif re.search(r"\b(?:corrige|cambia|cambiar|corregir|reemplaza|actualiza)\b", t):
        intent = "CORREGIR"
    elif acciones:
        intent = acciones[0]
    elif re.search(r"\b(?:amortizacion|cronograma)\b", t):
        intent = "AMORTIZACION"
    elif re.search(r"\b(?:cuota|cuanto pagara|cuanto pagaria|cuanto pagare)\b", t) and not entidades:
        intent = "CUOTA"
    elif re.search(r"\b(?:analiza|analizar|evalua|evaluar)\b", t):
        intent = "ANALIZAR" if not entidades else "REGISTRAR"
    elif entidades and set(entidades) - {"moneda"}:
        intent = "REGISTRAR"
    else:
        intent = "DESCONOCIDO"
    if problemas:
        return Interpretacion(intent, {}, texto, True, tuple(dict.fromkeys(problemas)), tuple(acciones))
    return Interpretacion(intent, entidades, texto, acciones=tuple(acciones))
