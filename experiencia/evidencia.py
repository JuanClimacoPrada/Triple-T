"""Respaldo general/patrimonial separado de boletas y de cálculos de ingreso."""
from dataclasses import replace
from datetime import date
from hashlib import sha256
from dominio.modelos import Respaldo
from servicios.documentos import leer_archivo, texto_seguro, ErrorDocumento
from servicios.finanzas import numero


def adjuntar_respaldo(c, nombre, datos, sintetico, tipo):
    from conversacion.gestor import invalidar, decir
    huella = sha256(datos).hexdigest()
    if any(d.get("huella") == huella for d in c.documentos):
        raise ErrorDocumento("Este archivo ya está presentado. Revísalo o descártalo antes de cargarlo de nuevo.")
    doc = leer_archivo(nombre, datos, sintetico, len(c.documentos) + 1, tipo)
    doc["huella"] = huella
    c.documentos.append(doc)
    if tipo == "BOLETA":
        c.expediente = replace(c.expediente, evidencias=c.expediente.evidencias + tuple(doc["evidencias"]),
                              resolucion_ingreso=None, justificacion_ingreso="")
    else:
        c.expediente = replace(c.expediente, respaldos=c.expediente.respaldos + (Respaldo(doc["id"], tipo),))
    invalidar(c)
    c.vista = "PATRIMONIO" if tipo == "PATRIMONIO" else "EVIDENCIAS"
    decir(c, "Documento presentado. Confirma la transcripción o completa la revisión manual; autenticidad y titularidad no se verifican.")


def actualizar_respaldo(c, indice, *, tipo_bien, documento_presentado, valor, fuente_valor, relacion, fecha, observacion, descartar=False):
    from conversacion.gestor import invalidar
    texto_seguro(observacion)
    opciones = {"tipo_bien": ("SIN_DECLARAR", "INMUEBLE", "VEHICULO", "OTRO"),
        "documento_presentado": ("OTRO", "TITULO", "CONSTANCIA", "PARTIDA", "RECIBO", "ESTADO_CUENTA"),
        "fuente_valor": ("SIN_DECLARAR", "DECLARADO", "TASACION_PRESENTADA"),
        "relacion": ("SIN_DECLARAR", "PROPIETARIO_DECLARADO", "COPROPIETARIO_DECLARADO", "OTRO")}
    valores = dict(tipo_bien=tipo_bien, documento_presentado=documento_presentado, fuente_valor=fuente_valor, relacion=relacion)
    if any(valores[k] not in v for k, v in opciones.items()):
        raise ValueError("Seleccione metadatos admitidos.")
    if descartar and not observacion.strip():
        raise ValueError("Indique por qué descarta el respaldo.")
    if not descartar and not isinstance(fecha, date):
        raise ValueError("Indique la fecha observada; si no se conoce, conserve pendiente.")
    if valor is not None and fuente_valor == "SIN_DECLARAR":
        raise ValueError("Indique de dónde procede el valor presentado.")
    respaldos = list(c.expediente.respaldos)
    actual = respaldos[indice]
    if actual.tipo == "PATRIMONIO" and not descartar and (tipo_bien == "SIN_DECLARAR" or relacion == "SIN_DECLARAR"):
        raise ValueError("Indique tipo de bien y relación declarada; no se verificará externamente.")
    respaldos[indice] = replace(actual, **valores, valor=numero(valor, "Valor declarado") if valor is not None else None,
        fecha=fecha, observacion=observacion, estado="DESCARTADO" if descartar else "TRANSCRIPCION_CONFIRMADA")
    c.expediente = replace(c.expediente, respaldos=tuple(respaldos))
    invalidar(c)


def pendientes_documentales(c):
    pendientes = []
    if not any(e.estado == "CONFIRMADO" for e in c.expediente.evidencias):
        pendientes.append("Respaldo de ingresos pendiente; otros documentos no sustituyen boletas admisibles ni acreditan ingreso estable")
    if any(e.estado == "PENDIENTE" for e in c.expediente.evidencias):
        pendientes.append("Hay transcripciones de boletas sin confirmar")
    if any(e.estado == "PRESENTADO_PENDIENTE_REVISION" for e in c.expediente.respaldos):
        pendientes.append("Hay respaldos generales o patrimoniales pendientes de revisión")
    if c.flujo and c.flujo.propiedad == "SI":
        pendientes.append("Patrimonio declarado: autenticidad, titularidad y eventual garantía sin verificación externa")
    return pendientes
