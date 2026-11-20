"""Lectura local en memoria. El contenido nunca se interpreta como instrucciones."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import PurePosixPath
import re
import shutil
import subprocess
import warnings
from uuid import uuid4
from dominio.modelos import Evidencia
from servicios.finanzas import numero

MAX_BYTES = 10 * 1024 * 1024
MAX_ARCHIVOS = 12
MAX_PAGINAS = 20
MAX_TEXTO = 100000


class ErrorDocumento(ValueError):
    """Mensajes controlados, sin datos internos del parser."""


def contiene_identificadores(texto):
    return bool(re.search(r"(?i)\b(?:DNI|RUC|pasaporte|nombre(?:s)?|apellido(?:s)?|titular)\s*[:#=]\s*\S+|\b\d{8}\b|\b\d{11}\b|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", texto))


def texto_seguro(texto):
    if contiene_identificadores(texto):
        raise ErrorDocumento("Posibles identificadores personales detectados. Archivo o texto bloqueado; utilice únicamente material sintético/anónimo.")
    if len(texto) > MAX_TEXTO:
        raise ErrorDocumento("Texto demasiado extenso para este prototipo.")
    return texto


def validar_archivo(nombre, contenido, sintetico, cantidad=1):
    if not sintetico:
        raise ErrorDocumento("Confirme explícitamente que todos los archivos son sintéticos/anónimos.")
    if cantidad > MAX_ARCHIVOS:
        raise ErrorDocumento("Máximo 12 archivos por sesión; reinicie para un caso nuevo.")
    if not contenido or len(contenido) > MAX_BYTES:
        raise ErrorDocumento("Archivo vacío o mayor de 10 MB.")
    texto_seguro(nombre)
    extension = PurePosixPath(nombre.replace("\\", "/")).suffix.lower()
    if extension not in (".pdf", ".png", ".jpg", ".jpeg"):
        raise ErrorDocumento("Formato no admitido: use PDF, PNG o JPG/JPEG.")
    # Se elimina completamente el nombre original, no solo separadores de ruta.
    return "documento-" + uuid4().hex[:12] + extension


def ocr_local(imagen):
    ejecutable = shutil.which("tesseract")
    if not ejecutable:
        return "", "OCR local no disponible; lectura no concluyente. Transcripción manual requerida."
    buffer = BytesIO()
    imagen.save(buffer, format="PNG")
    try:
        proceso = subprocess.run([ejecutable, "stdin", "stdout", "-l", "spa+eng"],
                                 input=buffer.getvalue(), capture_output=True, timeout=20, check=False)
        if proceso.returncode:
            return "", "OCR local falló; lectura no concluyente. Transcripción manual requerida."
        texto = proceso.stdout.decode("utf-8", errors="replace")
        return texto, "OCR local: transcripción pendiente de revisión; no acredita autenticidad."
    except (OSError, subprocess.TimeoutExpired):
        return "", "OCR no disponible o fuera de tiempo; transcripción manual requerida."


def candidatos(texto, documento_id, nombre, pagina):
    """Solo etiquetas estrictas Neto estable/Ingreso neto y mes ISO; sin inferencias."""
    texto_seguro(texto)
    mes = re.search(r"\b(20\d{2})-(0[1-9]|1[0-2])\b", texto)
    fecha = date(int(mes[1]), int(mes[2]), 1) if mes else None
    encontrados = []
    for linea in texto.splitlines():
        match = re.search(r"(?i)\b(?:neto estable|ingreso neto|neto a pagar)\s*[:=]\s*(?:S/\s*)?(\d+(?:[.,]\d{1,2})?)(?![\d.,])\s*$", linea)
        if match:
            encontrados.append(Evidencia(documento_id=documento_id, nombre_archivo_sanitizado=nombre,
                pagina_o_region=f"página/región {pagina}", texto_fuente_breve=linea[:240],
                valor_extraido=Decimal(match[1].replace(",", ".")), fuente="EXTRAIDO", fecha_documento=fecha))
    return encontrados


def leer_archivo(nombre, contenido, sintetico=False, cantidad=1):
    limpio = validar_archivo(nombre, contenido, sintetico, cantidad)
    documento_id = uuid4().hex
    paginas, avisos, previsualizaciones = [], [], []
    try:
        if limpio.endswith(".pdf"):
            if not contenido.startswith(b"%PDF-"):
                raise ErrorDocumento("PDF corrupto o formato incorrecto.")
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(contenido), strict=True)
            if reader.is_encrypted:
                raise ErrorDocumento("PDF cifrado no admitido; use un documento sintético sin contraseña.")
            if len(reader.pages) > MAX_PAGINAS:
                raise ErrorDocumento("PDF supera el límite de 20 páginas.")
            for i, pagina in enumerate(reader.pages, 1):
                # Limitar streams expandidos antes de extraer texto.
                stream = pagina.get_contents()
                if stream and len(stream.get_data()) > 2 * 1024 * 1024:
                    raise ErrorDocumento("Página PDF demasiado compleja para procesar de forma segura.")
                texto = pagina.extract_text() or ""
                texto_seguro(texto)
                paginas.append((i, texto))
            try:
                import pypdfium2 as pdfium
                with pdfium.PdfDocument(contenido) as render:
                    for i in range(min(3, len(render))):
                        page = render[i]
                        try:
                            ancho, alto = page.get_size()
                            escala = min(1.5, 1000 / max(ancho, alto))
                            bitmap = page.render(scale=escala)
                            imagen = bitmap.to_pil()
                            buffer = BytesIO()
                            imagen.save(buffer, format="PNG")
                            previsualizaciones.append(buffer.getvalue())
                            if not paginas[i][1].strip() and shutil.which("tesseract"):
                                texto, aviso = ocr_local(imagen)
                                texto_seguro(texto)
                                paginas[i] = (i + 1, texto)
                                avisos.append(aviso)
                            bitmap.close()
                        finally:
                            page.close()
                if len(reader.pages) > 3:
                    avisos.append("Vista previa y OCR de hasta 3 páginas; texto PDF extraído hasta 20. Para otras páginas escaneadas use transcripción manual.")
            except ImportError:
                avisos.append("Vista gráfica PDF no disponible; revise el texto o transcriba manualmente.")
            except ErrorDocumento:
                raise
            except Exception:
                avisos.append("Vista gráfica/OCR PDF no concluyente; revise el texto o transcriba manualmente.")
            if not any(t.strip() for _, t in paginas):
                avisos.append("PDF sin texto: lectura no concluyente; use transcripción manual o cargue una imagen sintética para OCR local.")
        else:
            from PIL import Image
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                imagen = Image.open(BytesIO(contenido))
                if imagen.format not in ("PNG", "JPEG") or imagen.width * imagen.height > 12000000:
                    raise ErrorDocumento("Imagen inválida o mayor de 12 megapíxeles.")
                imagen.load()
                texto, aviso = ocr_local(imagen)
                texto_seguro(texto)
                paginas.append((1, texto))
                avisos.append(aviso)
                preview = imagen.copy()
                preview.thumbnail((1000, 1000))
                buffer = BytesIO()
                preview.save(buffer, format="PNG")
                previsualizaciones.append(buffer.getvalue())
        evidencias = [e for pagina, texto in paginas for e in candidatos(texto, documento_id, limpio, pagina)]
        if not evidencias:
            avisos.append("No se identificó un neto inequívoco. Transcriba manualmente y confirme; no se ha importado ningún importe.")
        return dict(id=documento_id, nombre=limpio, paginas=paginas, evidencias=evidencias,
                    avisos=avisos, previews=previsualizaciones)
    except ImportError:
        return dict(id=documento_id, nombre=limpio, paginas=[], evidencias=[], previews=[],
                    avisos=["Paquete de lectura no disponible. Transcripción manual explícita requerida."])
    except ErrorDocumento:
        raise
    except Exception:
        # No incluir excepciones del parser ni contenido documental en mensajes/logs.
        raise ErrorDocumento("Archivo corrupto o ilegible. Lectura no concluyente; use transcripción manual.") from None


def confirmar(evidencia, valor, fecha, observacion, extraordinarios=0):
    texto_seguro(observacion)
    neto = numero(valor, "Neto estable confirmado")
    extra = numero(extraordinarios, "Extraordinarios excluidos")
    if not isinstance(fecha, date):
        raise ErrorDocumento("Fecha del documento requerida.")
    if evidencia.valor_extraido is not None and neto != evidencia.valor_extraido and not observacion.strip():
        raise ErrorDocumento("Justifique la corrección del importe extraído.")
    return replace(evidencia, valor_extraido=neto, fecha_documento=fecha, observacion=observacion,
                   extraordinarios_excluidos=extra, estado="CONFIRMADO", fuente="CONFIRMADO_ANALISTA")


def descartar(evidencia, justificacion):
    texto_seguro(justificacion)
    if not justificacion.strip():
        raise ErrorDocumento("Justifique el descarte (por ejemplo, duplicado o concepto extraordinario).")
    return replace(evidencia, estado="DESCARTADO", observacion=justificacion)
