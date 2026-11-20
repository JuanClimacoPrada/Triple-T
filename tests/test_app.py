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
        datos = dict(ingreso=3500., gastos=1400., otras_cuotas=300., monto=10000.,
                     meses=12, tea=25., estabilidad_meses=24, dias_mora=0)
        for nombre, valor in datos.items():
            app.number_input(key="sim_" + nombre).set_value(valor)
        next(b for b in app.button if b.label == "Calcular simulación").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe[-1].value), 12)
        self.assertEqual(app.dataframe[-1].value.iloc[-1]["saldo_pendiente"], 0)
        app.number_input(key="sim_meses").set_value(24)
        app.number_input(key="sim_monto").set_value(5000.)
        app.number_input(key="sim_tea").set_value(0.)
        next(b for b in app.button if b.label == "Calcular simulación").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe[-1].value), 24)
        self.assertEqual(app.dataframe[-1].value["interes"].sum(), 0)
        for producto in ("vehicular", "hipotecario", "empresarial"):
            app.selectbox[0].select(producto).run()
            self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
