"""Artefactos sintéticos reproducibles de QA; nunca documentos del usuario."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dataclasses import replace
from datetime import date
from decimal import Decimal as D
from reportlab.pdfgen.canvas import Canvas
from PIL import Image, ImageDraw, ImageFont
from dominio.modelos import Expediente, Evidencia, Configuracion
from servicios.documentos import confirmar
from servicios.reglas import analizar
from servicios.simulacion import simular
from servicios.reporte import generar_pdf

destino = Path(__file__).resolve().parents[1] / "docs" / "evidencias-sprint2"
destino.mkdir(parents=True, exist_ok=True)
evidencias = []
for mes, importe in ((8, 3000), (9, 3300), (10, 3600)):
    nombre = f"boleta-sintetica-2026-{mes:02d}.pdf"
    c = Canvas(str(destino / nombre))
    c.setFont("Helvetica-Bold", 18)
    c.drawString(45, 780, "DEMOSTRACION SINTETICA - SIN VALIDEZ")
    c.setFont("Helvetica", 13)
    for i, texto in enumerate((f"Mes: 2026-{mes:02d}", f"Neto estable: {importe}.00",
                               "Bonos excluidos: 0.00", "Sin nombres, identificadores ni datos reales.")):
        c.drawString(45, 735 - i * 28, texto)
    c.save()
    evidencias.append(confirmar(Evidencia(nombre_archivo_sanitizado=nombre, pagina_o_region="página 1",
        texto_fuente_breve=f"Neto estable: {importe}.00"), importe, date(2026, mes, 1), "Fixture sintética revisada"))
imagen = Image.new("RGB", (1200, 400), "white")
draw = ImageDraw.Draw(imagen)
fuente = ImageFont.load_default(size=28)
draw.multiline_text((30, 30), "DEMOSTRACION SINTETICA\nMes: 2026-08\nNeto estable: 3000.00\nSin datos personales", fill="black", font=fuente, spacing=18)
imagen.save(destino / "boleta-sintetica.png")
exp = Expediente(monto=D(10000), meses=12, tea=D(25), ingreso=D(3300), gastos=D(1400), otras_cuotas=D(300),
    estabilidad_meses=24, historial="INSUFICIENTE", dias_mora=None, descuento_planilla="NO_DESCONTADAS",
    fecha=date(2026, 11, 20), evidencias=tuple(evidencias))
r = analizar(exp)
sim_exp, sim_r = simular(exp, D(10000), 24, D(25), D(20))
(destino / "informe-sintetico.pdf").write_bytes(generar_pdf(exp, r, [("Base", r), ("Caída 20%; plazo 24", sim_r)], Configuracion()))
print(destino)
