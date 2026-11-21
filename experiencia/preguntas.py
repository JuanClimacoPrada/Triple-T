PREGUNTAS = {
    "monto": "¿Qué monto de financiamiento solicita, en soles?",
    "meses": "¿En cuántos meses desea pagarlo?",
    "tea": "¿Cuál es la tasa efectiva anual? Escribe, por ejemplo, «TEA 25%». Si no la conoces, puedes dejarla pendiente y consultarla en la oferta de la entidad.",
    "ingreso": "¿Cuál es su ingreso neto mensual estable, en soles?",
    "gastos": "¿Cuánto destina al mes a gastos habituales, sin incluir cuotas de préstamos?",
    "otras_cuotas": "¿Cuánto paga al mes por otros préstamos? Indica 0 solo si confirmas que no tiene esas cuotas.",
    "descuento_planilla": "¿Todas esas cuotas ya están descontadas del ingreso neto que indicaste? Esto evita restar la misma deuda dos veces.",
    "estabilidad_meses": "¿Cuántos meses lleva en su empleo o actividad actual?",
    "historial": "¿Qué se conoce de su historial de pagos? No tener historial no significa tener mora.",
    "dias_mora": "¿Cuántos días de atraso declara? Escribe «mora de 10 días», por ejemplo.",
}
ETAPAS = ("INICIO", "CONDICIONES", "FINANZAS", "HISTORIAL", "EVIDENCIA_INGRESOS", "EVIDENCIA_PATRIMONIO", "REVISION_DATOS", "RESULTADOS")
TITULOS = dict(zip(ETAPAS, ("Inicio", "Condiciones del préstamo", "Ingresos y gastos", "Continuidad e historial", "Respaldo de ingresos", "Patrimonio opcional", "Revisión de datos", "Resultados")))
ETIQUETAS = {"monto": "Monto solicitado", "meses": "Plazo (meses)", "tea": "TEA (%)",
    "ingreso": "Ingreso neto mensual", "gastos": "Gastos habituales", "otras_cuotas": "Cuotas de otros préstamos",
    "descuento_planilla": "Cuotas descontadas del ingreso", "estabilidad_meses": "Continuidad (meses)",
    "historial": "Historial declarado", "dias_mora": "Días de atraso", "tipo_credito": "Producto", "moneda": "Moneda"}
VALORES = {"DESCONOCIDO": "Desconocido", "INSUFICIENTE": "Sin historial suficiente", "SIN_MORA_DECLARADA": "Sin mora declarada",
    "MORA_DECLARADA": "Mora declarada", "SIN_ACLARAR": "Pendiente de aclarar", "YA_DESCONTADAS": "Sí, todas descontadas",
    "NO_DESCONTADAS": "No descontadas", "personal": "Crédito personal"}


def legible(valor):
    return "Pendiente" if valor is None else VALORES.get(str(valor), str(valor))
