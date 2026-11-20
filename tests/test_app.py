"""Regresión funcional UI Sprints 1/2 adaptada a chat principal Sprint 3."""
import unittest
from pathlib import Path
try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None


@unittest.skipIf(AppTest is None, "Instalar requirements.txt para probar Streamlit")
class TestApp(unittest.TestCase):
    def iniciar(self):
        return AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=30)

    def enviar(self, app, texto):
        app.chat_input[0].set_value(texto).run(timeout=30)
        self.assertFalse(app.exception)
        return app.session_state["conversacion"]

    def boton(self, app, nombre):
        next(b for b in app.button if b.label == nombre).click().run(timeout=30)
        self.assertFalse(app.exception)

    def test_inicio_incompleto_y_escenarios(self):
        app = self.iniciar()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.chat_input), 1)
        self.assertEqual(len(app.tabs), 0)
        self.assertEqual(len(app.dataframe[-1].value), 9)
        c = self.enviar(app, "qué falta")
        self.assertIn("monto solicitado", c.mensajes[-1].texto)

    def test_casos_y_pd_sin_valores_inventados(self):
        for caso, monto in (("Optimista", 2000), ("Esperado", 10000), ("Pesimista", 20000)):
            app = self.iniciar()
            app.button(key="caso_" + caso).click().run()
            self.assertFalse(app.exception)
            self.assertIsNone(app.number_input(key="pd").value)
            self.assertEqual(app.session_state["conversacion"].expediente.monto, monto)

    def test_reinicio_y_entrada_chat_invalida(self):
        app = self.iniciar()
        c = self.enviar(app, "ingreso NaN")
        self.assertIsNone(c.expediente.ingreso)
        app.button(key="caso_Esperado").click().run()
        self.boton(app, "Confirmar acción")
        self.boton(app, "Iniciar evaluación nueva")
        self.assertEqual(app.session_state["conversacion"].expediente.monto, 10000)
        self.boton(app, "Confirmar acción")
        self.assertIsNone(app.session_state["conversacion"].expediente.monto)

    def test_simulacion_modificable_y_productos(self):
        app = self.iniciar()
        app.button(key="caso_Esperado").click().run()
        c = self.enviar(app, "¿Y a 24 meses con TEA 0%?")
        self.assertEqual(c.expediente.meses, 12)
        self.assertEqual(c.escenario.meses, 24)
        self.assertEqual(sum(f["interes"] for f in c.resultado_escenario.tabla), 0)
        for producto in ("vehicular", "hipotecario", "empresarial"):
            c = self.enviar(app, "evaluar crédito " + producto)
            self.assertEqual(c.resultado.estado, "DATOS INSUFICIENTES")
            self.assertFalse(c.resultado.cifras)

    def test_sesiones_aisladas_y_limpieza_evidencias(self):
        app = self.iniciar()
        self.enviar(app, "subir boletas")
        self.boton(app, "Añadir transcripción manual explícita")
        self.assertEqual(len(app.session_state["conversacion"].expediente.evidencias), 1)
        otra = self.iniciar()
        self.assertFalse(otra.session_state["conversacion"].expediente.evidencias)
        self.enviar(app, "reiniciar")
        self.boton(app, "Confirmar acción")
        c = app.session_state["conversacion"]
        self.assertFalse(c.expediente.evidencias)
        self.assertFalse(c.documentos)
        self.assertEqual(len(c.mensajes), 1)

    def test_confirmacion_obligatoria(self):
        app = self.iniciar()
        self.enviar(app, "subir boletas")
        self.boton(app, "Añadir transcripción manual explícita")
        self.boton(app, "Confirmar transcripción")
        self.assertTrue(app.error)
        self.assertEqual(app.session_state["conversacion"].expediente.evidencias[0].estado, "PENDIENTE")

    def test_reporte_y_modificacion_base(self):
        app = self.iniciar()
        app.button(key="caso_Esperado").click().run()
        c = self.enviar(app, "¿Qué pasa si baja el ingreso 20%?")
        self.assertEqual(c.expediente.ingreso, 3500)
        self.assertEqual(c.resultado_escenario.cifras["ingresos_admisibles"], 2800)
        c = self.enviar(app, "genera PDF")
        self.assertTrue(c.informe.startswith(b"%PDF"))
        self.enviar(app, "corrige ingreso a 0")
        self.boton(app, "Confirmar acción")
        c = app.session_state["conversacion"]
        self.assertIsNone(c.informe)
        self.assertIsNone(c.resultado.cifras["dti_total"])


if __name__ == "__main__":
    unittest.main()
