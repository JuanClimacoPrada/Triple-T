import unittest
from dataclasses import replace
from decimal import Decimal

from motor import (Solicitud, evaluar, cuota_francesa, tabla_amortizacion,
                   solicitud_desde_datos, perdida_esperada_ilustrativa, comparar_alternativas)
from reglas_credito import PERFILES


class TestSprint1(unittest.TestCase):
    def setUp(self):
        self.s = Solicitud(3500, 1400, 300, 10000, 12, 25, 24, 0)

    def test_cuota_referencia_tem_uno_por_ciento(self):
        tea = ((1.01 ** 12) - 1) * 100
        self.assertAlmostEqual(cuota_francesa(10000, 12, tea), 888.4878867834, places=8)

    def test_tasa_muy_pequena(self):
        self.assertAlmostEqual(cuota_francesa(1200, 12, 1e-10), 100, places=8)

    def test_cuota_un_mes(self):
        self.assertAlmostEqual(cuota_francesa(1000, 1, 25), 1000 * 1.25 ** (1 / 12))

    def test_invalidos_en_cada_campo(self):
        for campo in self.s.__dataclass_fields__:
            if campo == "tipo_credito":
                continue
            for valor in (None, float("nan"), float("inf"), -1, True, "10"):
                with self.subTest(campo=campo, valor=valor), self.assertRaises(ValueError):
                    evaluar(replace(self.s, **{campo: valor}))
        for campo in ("meses", "dias_mora", "estabilidad_meses"):
            with self.subTest(campo=campo), self.assertRaises(ValueError):
                evaluar(replace(self.s, **{campo: 1.5}))

    def test_datos_incompletos(self):
        with self.assertRaisesRegex(ValueError, "Información incompleta.*ingreso"):
            solicitud_desde_datos({"monto": 1000})

    def test_perfiles_y_compatibilidad(self):
        base = evaluar(self.s)
        for tipo in PERFILES:
            r = evaluar(replace(self.s, tipo_credito=tipo))
            self.assertEqual(r["cuota"], base["cuota"])
            self.assertTrue(r["pendientes_producto"])
            self.assertIn("Revis", r["recomendacion"])
        with self.assertRaises(ValueError):
            evaluar(replace(self.s, tipo_credito="desconocido"))

    def test_configuracion_independiente(self):
        reglas = replace(PERFILES["personal"], limite_cuota_ingreso=0.1, limite_deuda_total=0.2)
        r = evaluar(self.s, reglas)
        self.assertEqual(r["capacidad_segun_reglas"], 350)
        self.assertTrue(any("servicio total" in a for a in r["alertas"]))
        self.assertEqual(PERFILES["vehicular"].limite_cuota_ingreso, 0.3)
        with self.assertRaises(ValueError):
            evaluar(self.s, replace(reglas, limite_deuda_total=1.1))

    def test_flujos_y_ratios(self):
        r = evaluar(self.s)
        self.assertEqual(r["capacidad_pago"], 1800)
        self.assertEqual(r["capacidad_segun_reglas"], 1050)
        self.assertAlmostEqual(r["ratio_deuda_actual"], 300 / 3500)
        self.assertAlmostEqual(r["disponible_despues"], 1800 - r["cuota"])
        self.assertAlmostEqual(r["cobertura_cuota"], 1800 / r["cuota"])

    def test_flujo_empresarial_sin_doble_descuento(self):
        r = evaluar(replace(self.s, ingreso=2100, gastos=0, tipo_credito="empresarial"))
        self.assertEqual(r["disponible_antes"], 1800)

    def test_deficit_y_sin_ingreso(self):
        r = evaluar(replace(self.s, ingreso=0))
        self.assertEqual(r["capacidad_pago"], 0)
        self.assertEqual(r["capacidad_segun_reglas"], 0)
        self.assertIsNone(r["ratio_total"])
        self.assertTrue(any("superan el ingreso" in a for a in r["alertas"]))

    def test_limites_alertas_existentes(self):
        s = Solicitud(1000, 0, 0, 300, 1, 0, 6, 30)
        self.assertFalse(evaluar(s)["alertas"])
        self.assertTrue(evaluar(replace(s, monto=300.01))["alertas"])
        self.assertIn("crítica", evaluar(replace(s, dias_mora=31))["clasificacion"])
        self.assertTrue(evaluar(replace(s, estabilidad_meses=5))["alertas"])

    def test_cronograma_identidades_y_cancelacion(self):
        for monto, meses, tea in ((1200, 12, 0), (1000, 3, 0), (10000, 12, 25),
                                  (500000, 360, 8), (100, 1, 200), (0.01, 360, 0)):
            with self.subTest(monto=monto, meses=meses, tea=tea):
                filas = tabla_amortizacion(monto, meses, tea)
                self.assertEqual(len(filas), meses)
                self.assertEqual(filas[-1]["saldo_pendiente"], 0)
                self.assertEqual(sum(Decimal(str(f["capital"])) for f in filas), Decimal(str(monto)))
                saldo = Decimal(str(monto))
                for f in filas:
                    self.assertEqual(Decimal(str(f["capital"])) + Decimal(str(f["interes"])), Decimal(str(f["cuota"])))
                    saldo -= Decimal(str(f["capital"]))
                    self.assertEqual(saldo, Decimal(str(f["saldo_pendiente"])))
                    self.assertGreaterEqual(saldo, 0)

    def test_ajuste_ultima_cuota(self):
        tabla = tabla_amortizacion(1000, 3, 0)
        self.assertEqual([f["cuota"] for f in tabla], [333.33, 333.33, 333.34])

    def test_cronograma_invalidos(self):
        for args in ((0, 12, 0), (1.001, 12, 0), (100, 1201, 10), (100, 1.5, 0)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                tabla_amortizacion(*args)

    def test_pd_solo_explicita_y_finita(self):
        for pd in (None, float("nan"), float("inf"), 101, -1):
            with self.subTest(pd=pd), self.assertRaises(ValueError):
                perdida_esperada_ilustrativa(1000, pd, 40)
        self.assertEqual(perdida_esperada_ilustrativa(1000, 0, 100), 0)

    def test_nueve_escenarios_identicos(self):
        filas = comparar_alternativas(1000, 30, 30, 250000)
        self.assertEqual({(f["alternativa"], f["escenario"]) for f in filas},
                         {(a, e) for a in "ABC" for e in ("Pesimista", "Esperado", "Optimista")})
        with self.assertRaises(ValueError):
            comparar_alternativas(1, float("nan"), 30, 100)


if __name__ == "__main__":
    unittest.main()
