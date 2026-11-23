"""Integración de la matriz, elección humana, PDF y edición desde Streamlit."""
from io import BytesIO
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from pypdf import PdfReader
from streamlit.testing.v1 import AppTest


class TestAlternativasUI(TestCase):
    def pulsar(self, app, etiqueta):
        boton = next(b for b in app.button if b.label == etiqueta)
        boton.click().run(timeout=30)
        self.assertFalse(app.exception)

    @patch.dict("os.environ", {"GEMINI_ENABLED": "false"})
    def test_matriz_seleccion_pdf_y_edicion(self):
        ruta = Path(__file__).resolve().parents[1] / "app.py"
        app = AppTest.from_file(str(ruta)).run(timeout=30)
        self.pulsar(app, "Cargar caso esperado")
        self.pulsar(app, "No dispongo por ahora")
        self.pulsar(app, "No declara bienes")
        self.pulsar(app, "Confirmar y calcular")
        c = app.session_state["conversacion"]
        expediente = c.expediente
        matriz = next(t.value for t in app.dataframe if "Caída de ingreso" in t.value.columns and len(t.value) == 9)
        self.assertEqual(matriz["Alternativa"].tolist(), ["A"] * 3 + ["B"] * 3 + ["C"] * 3)
        self.assertEqual(matriz["Caída de ingreso"].tolist(), ["0.00%", "10.00%", "30.00%"] * 3)

        app.button(key="ver_alternativa_B").click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(c.alternativa_en_contexto, "B")
        self.assertIn("Pago mensual con cargos: baja", c.mensajes[-1].texto)
        self.pulsar(app, "Seleccionar alternativa B")
        self.assertEqual(c.alternativa_propuesta, "B")
        self.assertIsNone(c.seleccion_alternativa)
        self.pulsar(app, "Cancelar selección")
        self.assertIsNone(c.alternativa_propuesta)
        self.pulsar(app, "Seleccionar alternativa C")
        self.pulsar(app, "Confirmar selección")
        self.assertIsNone(c.seleccion_alternativa)
        justificacion = "Se prioriza una cuota más baja con menor monto."
        next(i for i in app.text_area if i.label == "Justificación breve, sin datos personales").set_value(justificacion)
        self.pulsar(app, "Confirmar selección")
        self.assertEqual(c.seleccion_alternativa.codigo, "C")
        self.assertTrue(any("Alternativa C seleccionada" in aviso.value for aviso in app.success))
        self.pulsar(app, "Preparar informe PDF")
        texto = " ".join(p.extract_text() for p in PdfReader(BytesIO(c.informe)).pages)
        self.assertIn(justificacion, " ".join(texto.split()))

        esperado_c = next(i for i in app.number_input if i.key and "_C_" in i.key and i.label == "Esperado · caída (%)")
        esperado_c.set_value(15.0)
        self.pulsar(app, "Aplicar cambios a C")
        self.assertIsNone(c.seleccion_alternativa)
        self.assertIsNone(c.informe)
        self.assertEqual(c.expediente, expediente)
        matriz = next(t.value for t in app.dataframe if "Caída de ingreso" in t.value.columns and len(t.value) == 9)
        self.assertEqual(matriz.loc[(matriz["Alternativa"] == "C") & (matriz["Escenario"] == "Esperado"),
                                   "Caída de ingreso"].item(), "15.00%")
