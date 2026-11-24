"""Regresión UI del flujo guiado, panel de riesgo y funciones financieras."""
import unittest
from pathlib import Path
from unittest.mock import patch
try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None


@unittest.skipIf(AppTest is None, "Instalar requirements.txt para probar Streamlit")
@patch.dict("os.environ", {"TRIPLE_T_HERRAMIENTAS_DEV": "true", "GEMINI_ENABLED": "false"})
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

    def cargar_caso(self, app, caso="Esperado"):
        self.boton(app, "Desarrollo")
        app.button(key="caso_" + caso).click().run()
        self.assertFalse(app.exception)

    def test_inicio_incompleto_y_escenarios(self):
        app = self.iniciar()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.chat_input), 1)
        self.assertEqual(len(app.tabs), 7)
        self.boton(app, "Desarrollo")
        estrategia = next(d.value for d in app.dataframe if "Alternativa" in d.value.columns)
        self.assertEqual(len(estrategia), 9)
        self.boton(app, "Análisis crediticio")
        c = self.enviar(app, "qué falta")
        self.assertEqual(c.campo_preguntado, "monto")
        self.assertIn("monto de financiamiento", c.mensajes[-1].texto)

    def test_casos_y_pd_sin_valores_inventados(self):
        for caso, monto in (("Optimista", 2000), ("Esperado", 10000), ("Pesimista", 20000)):
            app = self.iniciar()
            self.cargar_caso(app, caso)
            self.assertFalse(app.exception)
            self.assertTrue(all(n.value is None for n in app.number_input if n.label == "PD supuesta (%)"))
            self.assertEqual(app.session_state["conversacion"].expediente.monto, monto)

    def test_reinicio_y_entrada_chat_invalida(self):
        app = self.iniciar()
        c = self.enviar(app, "ingreso NaN")
        self.assertIsNone(c.expediente.ingreso)
        self.cargar_caso(app)
        self.boton(app, "Confirmar acción")
        self.boton(app, "Nueva evaluación")
        self.assertEqual(app.session_state["conversacion"].expediente.monto, 10000)
        self.boton(app, "Confirmar acción")
        self.assertIsNone(app.session_state["conversacion"].expediente.monto)

    def test_simulacion_modificable_y_productos(self):
        app = self.iniciar()
        self.cargar_caso(app)
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
        self.boton(app, "Desarrollo")
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
        self.boton(app, "Análisis crediticio")
        self.enviar(app, "monto 5000")
        self.boton(app, "Desarrollo")
        self.assertIsNone(app.session_state["riesgo_demo"]["escenarios"]["Esperado"].pd)

    def test_score_simulado_confirmacion_y_eliminacion(self):
        app = self.iniciar()
        self.boton(app, "Desarrollo")
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
        self.cargar_caso(app)
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
        resumen_tab = next(tab for tab in app.tabs if tab.label == "Resumen")
        indicadores = next(tab for tab in app.tabs if tab.label == "Indicadores")
        self.assertTrue(any("Déficit mensual" in m.value and "−S/" in m.value for m in resumen_tab.markdown))
        self.assertTrue(any("No calculable" in m.value and "ingreso admisible es S/ 0" in m.value for m in indicadores.markdown))
        self.assertTrue(any("Causa, con el ingreso admisible en cero, yo esperaría" in m.value for m in resumen_tab.markdown))

    def test_navegacion_operativa_y_diagnostico_costos(self):
        app = self.iniciar()
        self.cargar_caso(app)
        self.assertFalse(any("Alertas financieras y documentales" in m.value for m in app.markdown))
        self.assertFalse(any(b.label == "Ver alternativas" for b in app.button))
        self.confirmar_caso(app)
        resumen_tab = next(tab for tab in app.tabs if tab.label == "Resumen")
        indicadores = next(tab for tab in app.tabs if tab.label == "Indicadores")
        datos = next(m.value for m in resumen_tab.markdown if "tt-metrics-compact" in m.value)
        for valor in ("3,500.00", "10,000.00", "25.00%", "12 meses"):
            self.assertIn(valor, datos)
        self.assertTrue(any("Sobreendeudamiento según el umbral académico" in m.value for m in resumen_tab.markdown))
        self.assertTrue(any("Sugerencia de Triple-T" in m.value and "Causa" in m.value for m in resumen_tab.markdown))
        self.assertFalse(any("Capacidad utilizada" in m.value for m in resumen_tab.markdown))
        self.assertTrue(any("Capacidad utilizada" in m.value for m in indicadores.markdown))
        self.assertTrue(any("Alertas financieras y documentales" in m.value for m in indicadores.markdown))
        self.assertFalse(any("Alertas financieras y documentales" in m.value for m in resumen_tab.markdown))
        self.assertFalse(any("Guardar escenario esperado" == b.label for b in app.button))
        self.assertFalse(any("Comparación estratégica" in b.label for b in app.button))
        self.assertFalse(any("Cargar caso" in b.label for b in app.button))
        self.assertTrue(any("fecha de desembolso" in t.value for t in app.text))
        app.button(key="costos_tcea").click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["pestana_analisis"], "Detalle")
        self.assertIsNotNone(next((b for b in app.button if b.label == "Guardar costos y fechas"), None))

    @patch.dict("os.environ", {"TRIPLE_T_HERRAMIENTAS_DEV": "false", "GEMINI_ENABLED": "true"})
    def test_consentimiento_en_informe_y_vigente_al_volver(self):
        app = self.iniciar()
        self.assertFalse(any(b.label == "Desarrollo" for b in app.button))
        informe = next(tab for tab in app.tabs if tab.label == "Informe e IA")
        self.assertEqual(len(app.checkbox), 1)
        self.assertEqual(len(informe.checkbox), 1)
        app.checkbox(key="consentimiento_gemini").set_value(True).run()
        self.boton(app, "Criterios")
        self.assertFalse(any("Consiento" in w.label for w in app.checkbox))
        self.boton(app, "Análisis crediticio")
        c = self.enviar(app, "hola")
        self.assertIn("hola", c.mensajes[-1].texto.lower())
        self.assertEqual(app.session_state["ia"].llamadas, 0)
        self.assertTrue(app.checkbox(key="consentimiento_gemini").value)


if __name__ == "__main__":
    unittest.main()
