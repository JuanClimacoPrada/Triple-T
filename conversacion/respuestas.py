from dominio.modelos import AVISO

ETIQUETAS = {"monto": "monto solicitado", "meses": "plazo en meses", "tea": "TEA (%)",
    "ingreso": "ingreso neto estable", "gastos": "gastos sin deuda", "otras_cuotas": "otras cuotas mensuales",
    "estabilidad_meses": "continuidad de ingresos en meses", "historial": "estado del historial crediticio",
    "descuento_planilla": "si TODAS las otras cuotas ya están descontadas del ingreso neto"}
AYUDA = "Soy un chatbot local de intenciones y reglas, sin IA generativa. Ejemplos: «Cliente gana 3500 soles, solicita 10000 soles a 12 meses con TEA 25%»; «gastos 1400 y otras cuotas 300»; «no están descontadas»; «¿cuál es la cuota?»; «¿y a 24 meses?»; «subir boletas»; «qué falta»; «genera PDF»; «compara A, B y C»."


def faltantes(exp):
    campos = [k for k in ("monto", "meses", "tea", "ingreso", "gastos", "otras_cuotas", "estabilidad_meses") if getattr(exp, k) is None]
    if exp.historial == "DESCONOCIDO":
        campos.append("historial")
    if exp.descuento_planilla == "SIN_ACLARAR":
        campos.append("descuento_planilla")
    return campos


def pregunta(exp):
    campos = faltantes(exp)
    if not campos:
        return None, "Puedes revisar las alertas, añadir boletas sintéticas o simular condiciones."
    campo = campos[0]
    return campo, f"Falta {ETIQUETAS[campo]}. ¿Puedes indicarlo explícitamente?"


def respuesta_calculo(exp, resultado, escenario=False):
    contexto = "Simulación separada" if escenario else "Expediente base"
    partes = [f"**{contexto} · {resultado.estado}**", f"Datos usados: monto S/ {exp.monto}, plazo {exp.meses} meses, TEA {exp.tea}%. Fuente de entradas: declaradas o confirmadas según el expediente."]
    if "cuota_base" in resultado.cifras:
        partes.append(f"Servicio financiero: cronograma francés con TEM=(1+TEA/100)^(1/12)−1. **Cuota base S/ {resultado.cifras['cuota_base']:,.2f}**; cargos mensuales indicados S/ {resultado.cifras.get('cargos_mensuales', 0):,.2f}.")
    if "dti_total" in resultado.cifras:
        dti = resultado.cifras["dti_total"]
        partes.append(f"DTI total: {'N/D' if dti is None else format(dti, '.2%')}; saldo después de cuota S/ {resultado.cifras['saldo_post_cuota']:,.2f}. Ingreso admisible usado S/ {resultado.cifras['ingresos_admisibles']:,.2f}.")
    else:
        partes.append("Cuota teórica parcial: **no se ha evaluado la capacidad de pago**. Resolver datos pendientes antes de concluir.")
    if "promedio_documental" in resultado.cifras:
        partes.append(f"Promedio documental confirmado: S/ {resultado.cifras['promedio_documental']:,.2f}; confirmar transcripción no verifica autenticidad.")
    partes.extend(f"{a['regla']} · {a['campo']}: {a['mensaje']}" for a in resultado.reglas)
    if not exp.cargos_completos:
        partes.append("Costos no confirmados como completos; cuota base no equivale a costo total. TCEA no calculable con los datos disponibles.")
    partes.append(AVISO)
    return "\n\n".join(partes)
