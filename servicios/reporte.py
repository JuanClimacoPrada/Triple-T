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


def generar_pdf(expediente, resultado, escenarios=(), config=None):
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
    story.append(p("Fechas de pago: " + (", ".join(map(str, expediente.fechas_pago)) or "Pendientes")))
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
