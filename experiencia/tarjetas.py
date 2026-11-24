"""ViewModels de presentación; no modifica fórmulas ni interpreta documentos."""
from dataclasses import dataclass
from decimal import Decimal

from experiencia.evidencia import pendientes_documentales
from experiencia.flujo import faltan
from experiencia.preguntas import ETIQUETAS, RAZONES


@dataclass(frozen=True)
class Aviso:
    titulo: str
    descripcion: str
    ruta: str | None = None
    tono: str = "azul"


def estado_flujo_mensual(resultado):
    """Describe el saldo posterior al pago cuando el motor pudo calcularlo."""
    saldo = resultado.cifras.get("saldo_post_cuota")
    if saldo is None:
        return None
    if saldo == 0:
        return Aviso("Sin margen mensual", "Los ingresos cubren los gastos y las cuotas, con un saldo de S/ 0.00.")
    importe = "menos de S/ 0.01" if abs(saldo) < Decimal("0.01") else f"S/ {abs(saldo):,.2f}"
    if saldo < 0:
        return Aviso("Déficit mensual", f"Faltarían {importe} al mes para cubrir todos los gastos y las cuotas.",
                     "ALTERNATIVAS", "rojo")
    return Aviso("Saldo mensual positivo", f"Quedarían {importe} al mes después de cubrir los gastos y las cuotas.",
                 tono="verde")


def avisos_evaluacion(c, resultado):
    """Motivos concretos y rutas de resolución para los resultados del motor."""
    avisos = []
    campos = faltan(c)
    if campos:
        motivos = " ".join(f"{ETIQUETAS[campo]}. {RAZONES[campo]}" for campo in campos)
        avisos.append(Aviso("Datos por completar", motivos, "CONTINUAR"))
    for a in resultado.reglas:
        regla, mensaje = a["regla"], a["mensaje"]
        if regla == "RN-13" or (regla == "VAL-01" and campos) or (regla == "RN-08" and "descuento_planilla" in campos):
            continue
        if regla == "RN-07" and a["nivel"] == "discrepancia":
            avisos.append(Aviso("Ingresos por conciliar", mensaje + " Confirma qué fuente de ingresos corresponde usar.",
                                "ACLARAR_INGRESO", "rojo"))
        elif regla == "VAL-05/07":
            avisos.append(Aviso("Boletas de un mismo mes", mensaje, "BOLETAS"))
        elif regla == "RN-05":
            avisos.append(Aviso("Respaldo de ingresos", mensaje, "BOLETAS"))
        elif regla == "RN-04":
            avisos.append(Aviso("Historial insuficiente", mensaje, "BOLETAS"))
        elif regla == "RN-03":
            dti = resultado.cifras.get("dti_total")
            detalle = (f"Las cuotas representan el {dti:.2%} del ingreso admisible. "
                       f"El umbral académico es {c.config.umbral_dti:.2%}.") if dti is not None else mensaje
            avisos.append(Aviso("Cuotas sobre el umbral académico", detalle, "ALTERNATIVAS", "rojo"))
        elif regla == "RN-02":
            avisos.append(estado_flujo_mensual(resultado) or Aviso("Déficit mensual", mensaje, "ALTERNATIVAS", "rojo"))
        elif regla == "VAL-03":
            avisos.append(Aviso("Ingreso admisible de S/ 0", "El cálculo de endeudamiento requiere un ingreso mayor que cero.",
                                "EXPEDIENTE", "rojo"))
        elif regla == "RN-10":
            avisos.append(Aviso("Continuidad de ingresos", mensaje + " Verifica los meses declarados de empleo o actividad.",
                                "EXPEDIENTE", "rojo" if a["nivel"] == "relevante" else "azul"))
        elif regla == "RN-11":
            mora = a["nivel"] == "relevante"
            avisos.append(Aviso("Mora declarada" if mora else "Historial de pagos", mensaje, "EXPEDIENTE",
                                "rojo" if mora else "azul"))
        else:
            avisos.append(Aviso("Dato por revisar", mensaje, "EXPEDIENTE" if a["nivel"] == "pendiente" else None,
                                "rojo" if a["nivel"] == "relevante" else "azul"))
    documentales = pendientes_documentales(c)
    for aviso in documentales:
        if aviso.startswith("Respaldo de ingresos") and any(a.titulo == "Respaldo de ingresos" for a in avisos):
            continue
        ruta = "PATRIMONIO" if aviso.startswith("Patrimonio declarado") else "OTRO_INGRESO" if "generales o patrimoniales" in aviso else "BOLETAS"
        avisos.append(Aviso("Documentación", aviso + ".", ruta))
    if resultado.cifras.get("continuidad"):
        avisos.append(Aviso("Continuidad de ingresos favorable",
                            "La antigüedad declarada alcanza los 12 meses de referencia académica. La capacidad de pago se evalúa con ingresos, gastos y cuotas.",
                            tono="verde"))
    prioridad = {"rojo": 0, "azul": 1, "verde": 2}
    return sorted(dict.fromkeys(avisos), key=lambda aviso: prioridad[aviso.tono])


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
