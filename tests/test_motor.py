import unittest
from motor import Solicitud, evaluar, cuota_francesa, perdida_esperada_ilustrativa, comparar_alternativas


class TestMotor(unittest.TestCase):
    def test_cuota_sin_interes(self):
        self.assertAlmostEqual(cuota_francesa(1200, 12, 0), 100)

    def test_cuota_interes(self):
        self.assertGreater(cuota_francesa(10000, 12, 25), 10000 / 12)

    def test_cuota_invalida(self):
        with self.assertRaises(ValueError):
            cuota_francesa(10000, 0, 20)

    def test_optimista(self):
        r = evaluar(Solicitud(45000, 10000, 0, 2000, 1, 18, 84, 0))
        self.assertEqual(r['clasificacion'], 'Condiciones preliminares favorables')
        self.assertFalse(r['alertas'])

    def test_mora(self):
        r = evaluar(Solicitud(3500, 1400, 300, 10000, 12, 25, 24, 45))
        self.assertIn('crítica', r['clasificacion'])

    def test_sin_ingreso(self):
        r = evaluar(Solicitud(0, 0, 0, 20000, 24, 25, 0, 60))
        self.assertIsNone(r['ratio_cuota'])
        self.assertIn('crítica', r['clasificacion'])

    def test_perdida_esperada_hypo(self):
        self.assertAlmostEqual(perdida_esperada_ilustrativa(10000, 2.5, 40), 100)

    def test_nueve_combinaciones(self):
        filas = comparar_alternativas(1000, 30, 30, 250000)
        self.assertEqual(len(filas), 9)
        x = next(x for x in filas if x['alternativa'] == 'B' and x['escenario'] == 'Esperado')
        self.assertAlmostEqual(x['horas_ahorradas_mes'], 225)
        self.assertAlmostEqual(x['beneficio_neto'], (225*30-3500)*12-120000)


if __name__ == '__main__':
    unittest.main()
