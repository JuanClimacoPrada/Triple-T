"""ViewModels de presentación; no modifica fórmulas ni interpreta documentos."""
from experiencia.evidencia import pendientes_documentales
from experiencia.flujo import faltan
from experiencia.preguntas import ETIQUETAS, RAZONES


def avisos_evaluacion(c, resultado):
    """Motivos concretos y rutas de resolución para los resultados del motor."""
    avisos = []
    campos = faltan(c)
    if campos:
        motivos = " ".join(f"{ETIQUETAS[campo]}. {RAZONES[campo]}" for campo in campos)
        avisos.append(("Datos por completar", motivos, "CONTINUAR"))
    for a in resultado.reglas:
        regla, mensaje = a["regla"], a["mensaje"]
        if regla in ("RN-13", "VAL-01", "RN-08") and (regla == "RN-13" or campos):
            continue
        if regla == "RN-07" and a["nivel"] == "discrepancia":
            avisos.append(("Ingresos por conciliar", mensaje + " Revisa las boletas y confirma la fuente que corresponde usar.", "ACLARAR_INGRESO"))
        elif regla in ("VAL-05/07", "RN-05", "RN-04"):
            avisos.append(("Respaldo de ingresos", mensaje + " Revisa las transcripciones y conserva un registro por mes.", "BOLETAS"))
        elif regla == "RN-03":
            avisos.append(("Cuotas sobre el umbral académico", mensaje + " Compara otras condiciones de monto o plazo.", "ALTERNATIVAS"))
        elif regla == "RN-02":
            avisos.append(("Déficit mensual", mensaje + " Los ingresos calculados no cubren todos los gastos y cuotas en este escenario.", "ALTERNATIVAS"))
        elif regla == "VAL-03":
            avisos.append(("DTI sin base de cálculo", "El ingreso admisible es S/ 0. Confirma si ese ingreso es correcto para el escenario evaluado.", "EXPEDIENTE"))
        elif regla == "RN-10":
            avisos.append(("Continuidad de ingresos", mensaje + " Verifica los meses declarados de empleo o actividad.", "EXPEDIENTE"))
        elif regla == "RN-11":
            avisos.append(("Historial de pagos", mensaje + " Confirma el historial y los días de atraso declarados.", "EXPEDIENTE"))
        else:
            avisos.append(("Dato por revisar", mensaje, "EXPEDIENTE" if a["nivel"] == "pendiente" else None))
    documentales = pendientes_documentales(c)
    for aviso in documentales:
        if aviso.startswith("Respaldo de ingresos") and any(t == "Respaldo de ingresos" for t, _, _ in avisos):
            continue
        ruta = "PATRIMONIO" if aviso.startswith("Patrimonio declarado") else "OTRO_INGRESO" if "generales o patrimoniales" in aviso else "BOLETAS"
        avisos.append(("Documentación", aviso + ".", ruta))
    return avisos


def estado_revision(c, r):
    if c.pendiente or r.estado == "DISCREPANCIA PENDIENTE":
        return "Requiere aclaración"
    if r.estado == "DATOS INSUFICIENTES" or r.cifras.get("dti_total") is None or pendientes_documentales(c):
        return "Información pendiente"
    if r.reglas:
        return "Alertas identificadas"
    return "Listo para revisión"


def tarjetas(c, r):
    def dinero(v):
        return "Pendiente" if v is None else f"S/ {v:,.2f}"
    cuota = r.cifras.get("pago_mensual_total", r.cifras.get("cuota_base"))
    dti = r.cifras.get("dti_total")
    return [
        ("Cuota mensual estimada", dinero(cuota), "Pago con cargos declarados" if "pago_mensual_total" in r.cifras else "Cuota teórica sin cargos; capacidad no evaluada"),
        ("Compromiso de ingresos (DTI)", "Pendiente" if dti is None else f"{dti:.2%}", f"Umbral configurable: {c.config.umbral_dti:.0%}; no es política oficial"),
        ("Disponible después del pago", dinero(r.cifras.get("saldo_post_cuota")), "Luego de gastos y cuotas; pendiente si no hay capacidad calculable"),
        ("Estado de revisión", estado_revision(c, r), "Decisión humana; no implica aprobación"),
    ]


def comparacion(base, escenario):
    filas = []
    for campo, etiqueta in (("cuota_base", "Cuota base"), ("intereses", "Intereses totales"), ("saldo_post_cuota", "Disponible después del pago")):
        a, b = base.cifras.get(campo), escenario.cifras.get(campo)
        filas.append({"Indicador": etiqueta, "Base": "Pendiente" if a is None else f"S/ {a:,.2f}",
                      "Escenario": "Pendiente" if b is None else f"S/ {b:,.2f}",
                      "Diferencia": "Pendiente" if a is None or b is None else f"S/ {b-a:+,.2f}"})
    return filas
