"""Ciclo de vida del comparador individual, la elección y sus datos remotos."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import re
from zoneinfo import ZoneInfo

from conversacion.gestor import decir
from dominio.modelos import VERSION_REGLAS
from servicios.alternativas import (CODIGOS, EscalaPuntuacion, PESOS, VERSION_PONDERACION, comparar,
                                    efectos_principales, generar_alternativas, interpretar_saldo)
from servicios.documentos import texto_seguro

@dataclass(frozen=True)
class SeleccionAlternativa:
    codigo: str
    fecha: datetime
    revision: int
    evaluacion: object
    justificacion: str


def invalidar_comparativa(c, *, reiniciar_opciones=False):
    c.clave_comparativa = None
    c.comparativa_crediticia = None
    c.alternativa_propuesta = None
    c.seleccion_alternativa = None
    c.alternativa_en_contexto = None
    c.informe = None
    c.informe_revision = None
    if reiniciar_opciones:
        c.opciones_crediticias = ()


def _entrada(c):
    if not c.flujo or c.flujo.revision_confirmada != c.revision or c.resultado is None or c.pendiente:
        raise ValueError("Confirma primero los datos vigentes del expediente para comparar las alternativas.")
    opciones = c.opciones_crediticias or generar_alternativas(c.expediente)
    escala = escala_para(c)
    clave = (c.revision, c.expediente, c.config, opciones, escala,
             tuple(PESOS.items()), VERSION_REGLAS, VERSION_PONDERACION)
    return opciones, escala, clave


def obtener(c):
    opciones, escala, clave = _entrada(c)
    if c.clave_comparativa != clave:
        comparativa = comparar(c.expediente, opciones, c.config, escala)
        invalidar_comparativa(c)
        c.opciones_crediticias = opciones
        c.clave_comparativa = clave
        c.comparativa_crediticia = comparativa
    return c.comparativa_crediticia


def editar(c, alternativa):
    obtener(c)
    if alternativa.codigo not in CODIGOS:
        raise ValueError("Selecciona una alternativa A, B o C.")
    opciones = tuple(alternativa if a.codigo == alternativa.codigo else a for a in c.opciones_crediticias)
    if opciones == c.opciones_crediticias:
        return
    # Validar la matriz completa antes de sustituir la edición anterior.
    nueva = comparar(c.expediente, opciones, c.config, escala_para(c))
    invalidar_comparativa(c)
    c.opciones_crediticias = opciones
    _, _, c.clave_comparativa = _entrada(c)
    c.comparativa_crediticia = nueva
    c.alternativa_en_contexto = alternativa.codigo
    c.vista = "ALTERNATIVAS"


def escala_para(c):
    escala = EscalaPuntuacion()
    if c.config.umbral_dti >= escala.dti_minimo:
        # Conserva un tramo descendente de 30 puntos porcentuales, incluso si
        # el umbral de la demo supera el máximo didáctico inicial de 60%.
        return EscalaPuntuacion(dti_minimo=c.config.umbral_dti + Decimal("0.30"))
    return escala


def regenerar(c):
    obtener(c)
    invalidar_comparativa(c, reiniciar_opciones=True)
    c.vista = "ALTERNATIVAS"
    return obtener(c)


def evaluacion_para(c, codigo):
    comparativa = obtener(c)
    if codigo not in CODIGOS:
        raise ValueError("Indica si te refieres a la alternativa A, B o C.")
    return next(e for e in comparativa.alternativas if e.alternativa.codigo == codigo)


def proponer_seleccion(c, codigo):
    evaluacion = evaluacion_para(c, codigo)
    if not evaluacion.seleccionable:
        raise ValueError("Completa las condiciones de la alternativa para calcular sus cuotas antes de seleccionarla.")
    c.alternativa_propuesta = c.alternativa_en_contexto = codigo
    c.vista = "ALTERNATIVAS"


def cancelar_seleccion(c):
    c.alternativa_propuesta = None


def guardar_seleccion(c, codigo, justificacion):
    evaluacion = evaluacion_para(c, codigo)
    if c.alternativa_propuesta != codigo:
        raise ValueError("Selecciona la alternativa vigente antes de confirmar.")
    justificacion = justificacion.strip()
    palabras = {p for p in re.findall(r"[^\W\d_]+", justificacion.casefold()) if len(p) >= 3 and len(set(p)) > 1}
    if not 1 <= len(justificacion) <= 300 or len(palabras) < 3:
        raise ValueError("Explica el motivo de tu elección en una frase de hasta 300 caracteres. Incluye al menos tres palabras distintas sobre las condiciones o los resultados.")
    texto_seguro(justificacion)
    c.seleccion_alternativa = SeleccionAlternativa(
        codigo, datetime.now(ZoneInfo("America/Lima")), c.revision, evaluacion, justificacion,
    )
    c.alternativa_propuesta = None
    c.informe = c.informe_revision = None
    a = evaluacion.alternativa
    decir(c, f"Alternativa {codigo} seleccionada. Monto S/ {a.monto:,.2f}, plazo de {a.meses} meses y TEA supuesta de {a.tea}%.")


def contexto_seguro(c):
    try:
        _, _, clave = _entrada(c)
    except ValueError:
        return {}
    vigente = c.clave_comparativa == clave
    return {
        "disponibles": list(CODIGOS),
        "seleccion": c.seleccion_alternativa.codigo if vigente and c.seleccion_alternativa else None,
        "propuesta": c.alternativa_propuesta if vigente else None,
        "en_contexto": c.alternativa_en_contexto if vigente else None,
    }


def resumen_seguro(c):
    """Solo hechos con etiquetas fijas. No enviar alertas ni notas libres."""
    try:
        opciones, escala, clave = _entrada(c)
        comparativa = c.comparativa_crediticia if c.clave_comparativa == clave else comparar(c.expediente, opciones, c.config, escala)
    except ValueError:
        return {}
    hechos = {"recomendacion_alternativas": comparativa.recomendacion}
    for e in comparativa.alternativas:
        a = e.alternativa
        puntaje = "pendiente" if e.puntaje_global is None else f"{e.puntaje_global:.2f}/100"
        hechos[f"{a.codigo}_condiciones"] = f"Alternativa {a.codigo}: monto S/ {a.monto}, plazo {a.meses} meses, TEA supuesta {a.tea}%, puntuación académica {puntaje}."
        hechos[f"{a.codigo}_consecuencias"] = describir_alternativa(comparativa, e)
        for s in e.escenarios:
            nombre = s.nombre.lower()
            cifras = s.resultado.cifras
            metricas = []
            for k, etiqueta in (("cuota_base", "cuota base"), ("pago_mensual_total", "pago mensual"),
                                ("dti_total", "DTI"), ("saldo_post_cuota", "saldo"),
                                ("intereses", "intereses"), ("total_pagos", "total pagado")):
                v = cifras.get(k)
                if v is not None:
                    valor = f"{v:.2%}" if k == "dti_total" else f"S/ {v:,.2f}"
                    metricas.append(f"{etiqueta} {valor}")
            hechos[f"{a.codigo}_{nombre}"] = f"{a.codigo} {nombre}, caída supuesta {s.caida}%: " + (", ".join(metricas) or "resultados pendientes")
            hechos[f"{a.codigo}_{nombre}_lectura"] = f"Alternativa {a.codigo}, escenario {nombre}: {interpretar_saldo(s.resultado)}"
    return hechos


def describir_alternativa(comparativa, evaluacion):
    beneficio, desventaja = efectos_principales(evaluacion, comparativa.base)
    saldo = interpretar_saldo(evaluacion.escenarios[1].resultado)
    return (f"Alternativa {evaluacion.alternativa.codigo}. {beneficio} {desventaja} "
            f"En el escenario esperado, {saldo[0].lower() + saldo[1:]}")


def accion_semantica(c, intent, referencia, entities):
    comparativa = obtener(c)
    codigo = (referencia or {}).get("objetivo")
    if intent in ("SELECCIONAR_ALTERNATIVA", "REGISTRAR_JUSTIFICACION"):
        if intent == "REGISTRAR_JUSTIFICACION" and codigo not in CODIGOS:
            codigo = c.alternativa_propuesta
        proponer_seleccion(c, codigo)
        a = evaluacion_para(c, codigo).alternativa
        return f"Alternativa {codigo}: S/ {a.monto:,.2f} a {a.meses} meses con TEA supuesta de {a.tea}%. Escribe la justificación en el comparador y confirma allí."
    c.vista = "ALTERNATIVAS"
    if codigo in CODIGOS:
        c.alternativa_en_contexto = codigo
    if intent == "EXPLICAR_CONSECUENCIAS":
        e = evaluacion_para(c, codigo)
        return describir_alternativa(comparativa, e)
    return comparativa.recomendacion
