"""Regresión UI del flujo guiado, panel de riesgo y funciones financieras."""
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

    def confirmar_caso(self, app):
        self.boton(app, "No dispongo por ahora")
        self.boton(app, "No declara bienes")
        self.boton(app, "Confirmar y calcular")

    def test_inicio_incompleto_y_escenarios(self):
        app = self.iniciar()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.chat_input), 1)
        self.assertEqual(len(app.tabs), 7)
        self.boton(app, "Comparación estratégica A/B/C")
        estrategia = next(d.value for d in app.dataframe if "Alternativa" in d.value.columns)
        self.assertEqual(len(estrategia), 9)
        c = self.enviar(app, "qué falta")
        self.assertEqual(c.campo_preguntado, "monto")
        self.assertIn("monto de financiamiento", c.mensajes[-1].texto)

    def test_casos_y_pd_sin_valores_inventados(self):
        for caso, monto in (("Optimista", 2000), ("Esperado", 10000), ("Pesimista", 20000)):
            app = self.iniciar()
            app.button(key="caso_" + caso).click().run()
            self.assertFalse(app.exception)
            self.assertTrue(all(n.value is None for n in app.number_input if n.label == "PD supuesta (%)"))
            self.assertEqual(app.session_state["conversacion"].expediente.monto, monto)

    def test_reinicio_y_entrada_chat_invalida(self):
        app = self.iniciar()
        c = self.enviar(app, "ingreso NaN")
        self.assertIsNone(c.expediente.ingreso)
        app.button(key="caso_Esperado").click().run()
        self.boton(app, "Confirmar acción")
        self.boton(app, "Nueva evaluación")
        self.assertEqual(app.session_state["conversacion"].expediente.monto, 10000)
        self.boton(app, "Confirmar acción")
        self.assertIsNone(app.session_state["conversacion"].expediente.monto)

    def test_simulacion_modificable_y_productos(self):
        app = self.iniciar()
        app.button(key="caso_Esperado").click().run()
        self.confirmar_caso(app)
        c = self.enviar(app, "¿Y a 24 meses con TEA 0%?")
        self.assertEqual(c.expediente.meses, 12)
        self.assertEqual(c.escenario.meses, 24)
        self.assertEqual(sum(f["interes"] for f in c.resultado_escenario.tabla), 0)
        for producto in ("vehicular", "hipotecario", "empresarial"):
            c = self.enviar(app, "evaluar crédito " + producto)
            self.boton(app, "Confirmar y calcular")
            self.assertEqual(c.resultado.estado, "DATOS INSUFICIENTES")
            self.assertFalse(c.resultado.cifras)

    def test_sesiones_aisladas_y_limpieza_evidencias(self):
        app = self.iniciar()
        self.enviar(app, "subir boletas")
        self.boton(app, "Agregar transcripción manual de boleta")
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
        self.boton(app, "Agregar transcripción manual de boleta")
        self.boton(app, "Confirmar transcripción")
        self.assertTrue(any("Revisa el documento" in w.value for w in app.warning))
        self.assertEqual(app.session_state["conversacion"].expediente.evidencias[0].estado, "PENDIENTE")

    def test_escenario_riesgo_horizonte_y_limpieza(self):
        app = self.iniciar()
        revision = app.session_state["conversacion"].revision
        app.number_input(key=f"pd_Esperado_{revision}").set_value(2.5)
        self.boton(app, "Guardar escenario esperado")
        self.assertTrue(any("horizonte" in w.value for w in app.warning))
        self.assertIsNone(app.session_state["riesgo_demo"]["escenarios"]["Esperado"].pd)
        app.number_input(key=f"horizonte_Esperado_{revision}").set_value(12)
        app.number_input(key=f"lgd_Esperado_{revision}").set_value(45.)
        app.number_input(key=f"exposicion_Esperado_{revision}").set_value(10000.)
        self.boton(app, "Guardar escenario esperado")
        e = app.session_state["riesgo_demo"]["escenarios"]["Esperado"]
        self.assertEqual(float(e.no_incumplimiento), 97.5)
        self.assertEqual(float(e.perdida_esperada), 112.5)
        self.assertIsNone(app.session_state["conversacion"].expediente.monto)
        self.enviar(app, "monto 5000")
        self.assertIsNone(app.session_state["riesgo_demo"]["escenarios"]["Esperado"].pd)

    def test_score_simulado_confirmacion_y_eliminacion(self):
        app = self.iniciar()
        revision = app.session_state["conversacion"].revision
        app.number_input(key=f"score_valor_{revision}").set_value(400)
        app.number_input(key=f"score_escala_{revision}").set_value(1000)
        self.boton(app, "Guardar score simulado")
        self.assertIsNone(app.session_state["riesgo_demo"]["score"])
        next(x for x in app.checkbox if "sin consulta ni datos reales" in x.label).set_value(True)
        self.boton(app, "Guardar score simulado")
        self.assertTrue(app.session_state["riesgo_demo"]["score"].simulado)
        self.assertTrue(any("No disponible" in m.value and "Score crediticio" in m.value for m in app.markdown))
        self.boton(app, "Eliminar score simulado")
        self.assertIsNone(app.session_state["riesgo_demo"]["score"])

    def test_reporte_y_modificacion_base(self):
        app = self.iniciar()
        app.button(key="caso_Esperado").click().run()
        self.confirmar_caso(app)
        c = self.enviar(app, "¿Qué pasa si baja el ingreso 20%?")
        self.assertEqual(c.expediente.ingreso, 3500)
        self.assertEqual(c.resultado_escenario.cifras["ingresos_admisibles"], 2800)
        c = self.enviar(app, "genera PDF")
        self.assertTrue(c.informe.startswith(b"%PDF"))
        self.enviar(app, "corrige ingreso a 0")
        self.boton(app, "Confirmar acción")
        c = app.session_state["conversacion"]
        self.assertIsNone(c.informe)
        self.boton(app, "Confirmar y calcular")
        self.assertIsNone(c.resultado.cifras["dti_total"])


if __name__ == "__main__":
    unittest.main()
