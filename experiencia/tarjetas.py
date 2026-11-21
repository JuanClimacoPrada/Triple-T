"""ViewModels de presentación; no modifica fórmulas ni interpreta documentos."""
from experiencia.evidencia import pendientes_documentales


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
