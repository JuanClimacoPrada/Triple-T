"""PDF en memoria a partir de los mismos resultados presentados en pantalla."""
from dataclasses import asdict
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape
from dominio.modelos import AVISO


def formato(valor):
    if valor is None:
        return "N/D"
    if isinstance(valor, Decimal):
        return f"{valor:,.2f}"
    return str(valor)


def generar_pdf(expediente, resultado, escenarios=(), config=None, *, alternativas=None, seleccion=None, base=None):
    try:
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    except ImportError:
        raise ValueError("Exportador PDF no disponible; consulte el informe en pantalla.") from None
    buffer = BytesIO()
    estilos = getSampleStyleSheet()
    estilos["BodyText"].fontSize = 9
    estilos["BodyText"].leading = 12
    story = []
    def p(texto, estilo="BodyText"):
        return Paragraph(escape(str(texto)), estilos[estilo])
    def titulo(texto):
        story.extend([Spacer(1, 10), p(texto, "Heading2")])
    def tabla(filas, anchos):
        t = Table([[p(c) for c in fila] for fila in filas], colWidths=anchos, repeatRows=1, hAlign="LEFT")
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f0f7")),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                               ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey)]))
        story.append(t)
    story.extend([p("Triple-T | Informe académico", "Title"), p(AVISO),
                  p(f"Fecha: {expediente.fecha} | Reglas: {resultado.version}"),
                  p(resultado.estado, "Heading2")])
    titulo("Entradas y procedencia")
    fuentes = dict(expediente.origen_campos)
    filas = [["Campo", "Valor", "Fuente / estado"]]
    for campo, valor in asdict(expediente).items():
        if campo in ("evidencias", "respaldos", "origen_campos", "cargos", "fechas_pago"):
            continue
        filas.append([campo, formato(valor), fuentes.get(campo, "Ingresado / declarado; no verificado")])
    tabla(filas, [140, 190, 180])
    if config:
        story.append(p(f"Umbral DTI: {config.umbral_dti:.2%}; discrepancia: {config.discrepancia:.2%}; tope técnico TEA: {config.tea_maxima}%."))
    titulo("Cargos supuestos y fechas de flujo")
    tabla([["Concepto", "Importe", "Momento", "Pagador"]] +
          [[c.concepto, formato(c.importe), c.momento, c.pagador] for c in expediente.cargos], [180, 90, 100, 140])
    estado_calendario = {"PROPUESTAS": "propuestas, por confirmar", "CONFIRMADAS": "confirmadas en la sesión",
                         "PROYECTADAS": "proyectadas para la simulación"}.get(expediente.origen_fechas_pago, "registradas")
    fechas = ", ".join(map(str, expediente.fechas_pago))
    story.append(p(f"Fechas de pago ({estado_calendario}): {fechas}" if fechas else "Fechas de pago pendientes."))
    titulo("Evidencias: confirmación no equivale a autenticidad")
    for e in expediente.evidencias:
        story.append(p(f"{e.documento_id} | {e.nombre_archivo_sanitizado} | {e.pagina_o_region} | {e.fecha_documento}"))
        story.append(p(f"{e.campo}: {formato(e.valor_extraido)} | {e.fuente} / {e.estado} | Extraordinarios excluidos: {formato(e.extraordinarios_excluidos)}"))
        story.append(p(f"Observación: {e.observacion or 'Sin observación'}"))
    # No se exportan documentos crudos, previews ni texto extraído íntegro.
    titulo("Otros respaldos y patrimonio declarado")
    for e in expediente.respaldos:
        story.append(p(f"{e.tipo} | {e.documento_presentado} | {e.fecha} | {e.estado}"))
        story.append(p(f"Bien: {e.tipo_bien}; valor: {formato(e.valor)}; fuente: {e.fuente_valor}; relación: {e.relacion}. {e.verificacion}."))
    story.append(p("Los respaldos generales y patrimoniales no se convierten en ingreso ni garantía. Si no hay boletas confirmadas, la evidencia de ingreso permanece pendiente. Ninguna transcripción verifica autenticidad."))
    titulo("Indicadores calculados")
    tabla([["Indicador", "Valor calculado"]] + [[k, f"{v:.2%}" if k in ("dti_total", "discrepancia_relativa") and v is not None else formato(v)] for k, v in resultado.cifras.items()], [260, 250])
    story.append(p(f"TCEA referencial: {resultado.tcea:.2%}" if resultado.tcea is not None else "TCEA no calculable con los datos disponibles."))
    titulo("Reglas activadas y limitaciones")
    for regla in resultado.reglas:
        story.append(p(f"{regla['regla']} | {regla['campo']} | {regla['mensaje']}"))
    for supuesto in resultado.supuestos:
        story.append(p(supuesto))
    story.append(p("Fórmula: TEM=(1+TEA/100)^(1/12)-1; C=M*TEM/(1-(1+TEM)^(-n)); a tasa cero C=M/n. Redondeo solo de presentación; saldo interno de alta precisión."))
    titulo("Comparación de escenarios calculados")
    for nombre, escenario in escenarios:
        story.append(p(f"{nombre}: {escenario.estado}"))
        story.append(p("; ".join(f"{k}: " + (f"{v:.2%}" if k in ("dti_total", "discrepancia_relativa") and v is not None else formato(v)) for k, v in escenario.cifras.items())))
        for supuesto in escenario.supuestos:
            story.append(p(supuesto))
    if alternativas is not None:
        from servicios.alternativas import PESOS, VERSION_PONDERACION

        story.append(PageBreak())
        titulo("Alternativas crediticias del expediente base")
        if base is not None:
            story.append(p(f"Base: S/ {formato(base.monto)}, {formato(base.meses)} meses, TEA {formato(base.tea)}%. Ingreso admisible sin caída: S/ {formato(alternativas.base.cifras.get('ingresos_admisibles'))}."))
        story.append(p("Índice académico de alternativas de 0 a 100. Promedio simple de escenarios sin probabilidades asignadas. El DTI y el saldo miden aspectos relacionados."))
        story.append(p("Pesos: " + ", ".join(f"{k} {v:.0%}" for k, v in PESOS.items()) + "."))
        escala = alternativas.escala
        story.append(p(f"Ponderación {VERSION_PONDERACION}. DTI: 100 puntos hasta {alternativas.umbral_dti:.2%}, cero desde {escala.dti_minimo:.2%}. Saldo objetivo: {escala.saldo_objetivo:.2%} del ingreso admisible base. Intereses: cero puntos desde {escala.intereses_minimo:.2%} del monto financiado."))
        story.append(p("Resistencia: proporción de escenarios que cumplen DTI y saldo no negativo. Cobertura: monto financiado dividido por monto solicitado, con un máximo de 100 puntos."))
        story.append(p(alternativas.recomendacion))
        if seleccion is None:
            story.append(p("Alternativa seleccionada: pendiente."))
        else:
            story.append(p(f"Alternativa {seleccion.codigo} seleccionada | {seleccion.fecha.isoformat(timespec='seconds')} | Revisión {seleccion.revision}"))
            story.append(p(f"Justificación del analista: {seleccion.justificacion}"))
        for evaluacion in alternativas.alternativas:
            a = evaluacion.alternativa
            titulo(f"Alternativa {a.codigo} | S/ {formato(a.monto)} | {formato(a.meses)} meses | TEA supuesta {formato(a.tea)}%")
            estado_puntuacion = "Puntuación pendiente" if evaluacion.puntaje_global is None else f"{formato(evaluacion.puntaje_global)}/100"
            story.append(p(f"Promedio académico: {estado_puntuacion}." + (" Evaluación preliminar; revisar la evidencia disponible." if evaluacion.preliminar else "")))
            if evaluacion.motivo_pendiente:
                story.append(p(evaluacion.motivo_pendiente))
            if evaluacion.favorable and evaluacion.desfavorable:
                story.append(p(f"Por saldo mensual, más favorable: {evaluacion.favorable.nombre}. Más desfavorable: {evaluacion.desfavorable.nombre}."))
            for consecuencia in evaluacion.consecuencias:
                story.append(p(consecuencia))
            for s in evaluacion.escenarios:
                r = s.resultado
                titulo(f"{a.codigo} · {s.nombre} | Caída de ingreso supuesta: {formato(s.caida)}%")
                filas = [["Indicador", "Valor"]]
                for clave, etiqueta in (("cuota_base", "Cuota base"), ("cargos_mensuales", "Cargos mensuales"),
                                        ("cargos_iniciales", "Cargos iniciales"), ("pago_mensual_total", "Pago mensual"),
                                        ("dti_total", "Endeudamiento total"), ("saldo_post_cuota", "Saldo disponible"),
                                        ("capacidad_neta", "Capacidad neta"), ("intereses", "Intereses totales"),
                                        ("total_pagos", "Total de pagos")):
                    valor = r.cifras.get(clave)
                    filas.append([etiqueta, f"{valor:.2%}" if clave == "dti_total" and valor is not None else formato(valor)])
                filas.extend([["TCEA referencial", f"{r.tcea:.2%}" if r.tcea is not None else "Pendiente"],
                              ["Puntuación del escenario", formato(s.puntaje)]])
                tabla(filas, [255, 255])
                story.append(p("Componentes (0–100): " + ", ".join(f"{k} {formato(v)}" for k, v in s.componentes.items())))
                for alerta in r.reglas:
                    story.append(p(alerta["mensaje"]))
                for supuesto in r.supuestos:
                    story.append(p(supuesto))
    story.append(PageBreak())
    titulo("Cronograma (S/)")
    filas = [["Mes", "Inicial", "Base", "Interés", "Capital", "Cargos", "Total", "Final"]]
    for f in resultado.tabla:
        filas.append([formato(f[k]) for k in ("periodo", "saldo_inicial", "cuota_base", "interes", "amortizacion", "cargos", "pago_total", "saldo_final")])
    tabla(filas, [32, 73, 63, 55, 63, 45, 64, 75])
    def pie(canvas, doc):
        canvas.setFont("Helvetica", 8)
        canvas.drawString(42, 25, "Triple-T - Datos sintéticos - Revisión humana")
        canvas.drawRightString(A4[0] - 42, 25, f"Página {doc.page}")
    SimpleDocTemplate(buffer, pagesize=A4, rightMargin=42, leftMargin=42,
                      topMargin=36, bottomMargin=42, title="Triple-T - Informe académico").build(story, onFirstPage=pie, onLaterPages=pie)
    return buffer.getvalue()
