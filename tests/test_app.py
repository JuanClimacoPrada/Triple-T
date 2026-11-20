"""Pruebas de interacción con Streamlit sin navegador ni servicios externos."""
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

    def test_inicio_incompleto_y_escenarios(self):
        app = self.iniciar()
        self.assertFalse(app.exception)
        self.assertTrue(any("Información incompleta" in x.value for x in app.warning))
        self.assertEqual(len(app.dataframe[0].value), 9)

    def test_casos_y_pd_sin_valores_inventados(self):
        app = self.iniciar()
        for caso in ("Optimista", "Esperado", "Pesimista"):
            app.button(key="caso_" + caso).click().run()
            self.assertFalse(app.exception)
            pd = next(n for n in app.number_input if n.label == "PD supuesta (%)")
            self.assertIsNone(pd.value)
            self.assertEqual(app.number_input(key="sim_monto").value,
                             {"Optimista": 2000, "Esperado": 10000, "Pesimista": 20000}[caso])

    def test_reinicio_y_entrada_chat_invalida(self):
        app = self.iniciar()
        app.chat_input[0].set_value("nan").run()
        self.assertTrue(app.error)
        self.assertEqual(app.session_state["indice"], 0)
        app.button(key="caso_Esperado").click().run()
        next(b for b in app.button if b.label == "Iniciar evaluación nueva").click().run()
        self.assertFalse(app.exception)
        self.assertIsNone(app.number_input(key="sim_monto").value)

    def test_simulacion_modificable_y_productos(self):
        app = self.iniciar()
        app.button(key="caso_Esperado").click().run()
        next(b for b in app.button if b.label == "Calcular simulación").click().run()
        self.assertFalse(app.exception)
        tabla = [d.value for d in app.dataframe if "saldo_final" in d.value.columns][-1]
        self.assertEqual(len(tabla), 12)
        self.assertEqual(tabla.iloc[-1]["saldo_final"], 0)
        app.number_input(key="sim_meses").set_value(24)
        app.number_input(key="sim_monto").set_value(5000.)
        app.number_input(key="sim_tea").set_value(0.)
        next(b for b in app.button if b.label == "Calcular simulación").click().run()
        self.assertFalse(app.exception)
        tabla = [d.value for d in app.dataframe if "saldo_final" in d.value.columns][-1]
        self.assertEqual(len(tabla), 24)
        self.assertEqual(tabla["interes"].sum(), 0)
        for producto in ("vehicular", "hipotecario", "empresarial"):
            app.selectbox(key="producto").select(producto).run()
            self.assertFalse(app.exception)
            self.assertTrue(any("no evaluable" in x.value for x in app.warning))
            self.assertFalse(app.metric)

    def test_sesiones_aisladas_y_limpieza_evidencias(self):
        app = self.iniciar()
        app.button(key="caso_Esperado").click().run()
        next(b for b in app.button if b.label == "Añadir transcripción manual explícita").click().run()
        self.assertEqual(len(app.session_state["evidencias"]), 1)
        otra = self.iniciar()
        self.assertEqual(otra.session_state["evidencias"], [])
        self.assertIsNone(otra.number_input(key="dato_ingreso").value)
        next(b for b in app.button if b.label == "Iniciar evaluación nueva").click().run()
        self.assertEqual(app.session_state["evidencias"], [])
        self.assertFalse(app.exception)

    def test_confirmacion_obligatoria(self):
        app = self.iniciar()
        next(b for b in app.button if b.label == "Añadir transcripción manual explícita").click().run()
        next(b for b in app.button if b.label == "Confirmar transcripción").click().run()
        self.assertTrue(app.error)
        self.assertEqual(app.session_state["evidencias"][0].estado, "PENDIENTE")

    def test_reporte_y_modificacion_base(self):
        app = self.iniciar()
        app.button(key="caso_Esperado").click().run()
        app.number_input(key="sim_caida").set_value(20.)
        next(b for b in app.button if b.label == "Calcular simulación").click().run()
        self.assertEqual(app.number_input(key="dato_ingreso").value, 3500.)
        next(b for b in app.button if b.label == "Generar reporte PDF").click().run(timeout=30)
        self.assertFalse(app.exception)
        app.number_input(key="dato_ingreso").set_value(0.).run()
        self.assertFalse(app.exception)
        self.assertTrue(any(m.value == "N/D" for m in app.metric))


if __name__ == "__main__":
    unittest.main()
