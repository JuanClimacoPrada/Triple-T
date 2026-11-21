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


RAZONES = {
    "monto": "El monto indica cuánto se financiará y permite calcular la cuota.",
    "meses": "El plazo determina cuántos pagos habrá y cómo se distribuyen capital e intereses.",
    "tea": "La TEA permite obtener la tasa mensual del cálculo. No puedo sustituirla por una tasa inventada.",
    "ingreso": "El ingreso estable permite comparar las cuotas con los recursos disponibles.",
    "gastos": "Los gastos habituales se restan para estimar cuánto quedaría después del pago.",
    "otras_cuotas": "Los préstamos actuales también consumen ingreso y forman parte del endeudamiento total.",
    "descuento_planilla": "Necesito evitar restar dos veces una cuota que ya fue descontada del ingreso neto.",
    "estabilidad_meses": "La continuidad aporta una señal académica para revisión; no acredita capacidad por sí sola.",
    "historial": "Permite señalar antecedentes declarados y necesidades de respaldo, sin consultar centrales de riesgo.",
    "dias_mora": "Los días declarados permiten señalar la alerta correspondiente sin inferir un atraso desconocido.",
}
