import unittest
from dataclasses import replace
from datetime import date
from decimal import Decimal as D

from dominio.modelos import Cargo, Configuracion, Evidencia, Expediente
from servicios.alternativas import EscalaPuntuacion, PESOS, comparar, generar_alternativas
from servicios.finanzas import cronograma, fechas_mensuales


def caso(**cambios):
    original = Expediente(monto=D(10000), meses=12, tea=D(25), ingreso=D(3500), gastos=D(1400),
                          otras_cuotas=D(300), estabilidad_meses=24, historial="SIN_MORA_DECLARADA",
                          dias_mora=0, descuento_planilla="NO_DESCONTADAS", fecha=date(2026, 6, 25))
    return replace(original, **cambios)


def boletas(importes, meses=(1, 2, 3)):
    return tuple(Evidencia(fecha_documento=date(2026, mes, 1), valor_extraido=D(valor),
                           estado="CONFIRMADO", fuente="CONFIRMADO_ANALISTA")
                 for mes, valor in zip(meses, importes))


class TestAlternativas(unittest.TestCase):
    def test_matriz_reutiliza_calculo_financiero_y_compara_con_base(self):
        exp = caso()
        alternativas = generar_alternativas(exp)
        comparativa = comparar(exp, alternativas)
        self.assertEqual([(a.monto, a.meses, a.tea) for a in alternativas],
                         [(D(10000), 12, D(25)), (D(10000), 24, D(25)), (D(8000), 12, D(25))])
        self.assertEqual(sum(len(e.escenarios) for e in comparativa.alternativas), 9)
        for e in comparativa.alternativas:
            a = e.alternativa
            esperado, _ = cronograma(a.monto, a.meses, a.tea)
            self.assertEqual([s.caida for s in e.escenarios], [0, 10, 30])
            self.assertEqual(e.favorable.nombre, "Optimista")
            self.assertEqual(e.desfavorable.nombre, "Pesimista")
            for escenario in e.escenarios:
                r = escenario.resultado
                ingreso = D(3500) * (1 - escenario.caida / 100)
                self.assertEqual(r.cifras["cuota_base"], esperado)
                self.assertAlmostEqual(r.cifras["dti_total"], (D(300) + esperado) / ingreso, places=24)
                self.assertAlmostEqual(r.cifras["saldo_post_cuota"], ingreso - 1400 - 300 - esperado, places=22)
                self.assertIsNone(r.tcea)
            self.assertTrue(e.preliminar)
        a, b, c = comparativa.alternativas
        self.assertLess(b.escenarios[0].resultado.cifras["cuota_base"], a.escenarios[0].resultado.cifras["cuota_base"])
        self.assertGreater(b.escenarios[0].resultado.cifras["intereses"], a.escenarios[0].resultado.cifras["intereses"])
        self.assertIn("Pago mensual con cargos: baja", " ".join(b.consecuencias))
        self.assertIn("Intereses: sube", " ".join(b.consecuencias))
        self.assertIn("S/ 2,000.00 por financiar", " ".join(c.consecuencias))
        self.assertEqual(exp, replace(exp))
        self.assertEqual(exp.monto, 10000)
        self.assertEqual(exp.meses, 12)
        self.assertEqual(exp.ingreso, 3500)

    def test_formula_y_contribuciones(self):
        exp = caso()
        comparativa = comparar(exp, generar_alternativas(exp))
        self.assertEqual(sum(PESOS.values()), 1)
        a, b, c = comparativa.alternativas
        e = b.escenarios[2]
        dti = e.resultado.cifras["dti_total"]
        saldo = e.resultado.cifras["saldo_post_cuota"]
        intereses = e.resultado.cifras["intereses"]
        self.assertGreater(dti, D(".30"))
        self.assertLess(dti, D(".60"))
        self.assertAlmostEqual(e.componentes["DTI"], 100 * (D(".60") - dti) / D(".30"), places=24)
        self.assertEqual(e.componentes["Capacidad"], 100 * min(D(1), saldo / D(1050)))
        self.assertEqual(e.componentes["Resistencia"], D(100) * b.resisten / 3)
        self.assertEqual(e.componentes["Intereses"], 100 * (1 - intereses / D(5000)))
        self.assertEqual(c.escenarios[0].componentes["Cobertura"], 80)
        self.assertEqual(e.puntaje, sum(v * PESOS[k] for k, v in e.componentes.items()))
        self.assertEqual(b.puntaje_global, sum(e.puntaje for e in b.escenarios) / 3)
        self.assertEqual(len(set(e.componentes["Resistencia"] for e in b.escenarios)), 1)
        self.assertEqual(a.escenarios[0].componentes["Cobertura"], 100)

    def test_extremos_faltantes_duplicados_y_sin_ingreso(self):
        sin_ingreso = caso(ingreso=D(0))
        for exp in (sin_ingreso, caso(ingreso=None), caso(evidencias=boletas((3500, 3500, 3500), (1, 1, 2))),
                    caso(historial="INSUFICIENTE", dias_mora=None), caso(evidencias=(Evidencia(),))):
            with self.subTest(exp=exp):
                comparativa = comparar(exp, generar_alternativas(exp))
                self.assertFalse(comparativa.recomendadas)
                for a in comparativa.alternativas:
                    self.assertIsNone(a.puntaje_global)
                    self.assertIsNotNone(a.motivo_pendiente)
                    for e in a.escenarios:
                        self.assertIsNone(e.componentes["DTI"])
        examinado = comparar(sin_ingreso, generar_alternativas(sin_ingreso))
        self.assertEqual(examinado.alternativas[0].escenarios[0].componentes["Capacidad"], None)
        self.assertIn("RN-02", {r["regla"] for r in examinado.alternativas[0].escenarios[0].resultado.reglas})
        exp = caso()
        a, b, c = generar_alternativas(exp)
        comparativa = comparar(exp, (replace(a, monto=D(90000), caidas=(0, 50, 100)), b, c))
        examen = comparativa.alternativas[0]
        self.assertEqual(examen.escenarios[0].componentes["DTI"], 0)
        self.assertEqual(examen.escenarios[0].componentes["Capacidad"], 0)
        self.assertEqual(examen.escenarios[0].componentes["Cobertura"], 100)
        self.assertIsNone(examen.escenarios[2].puntaje)
        self.assertIsNone(examen.puntaje_global)

    def test_alertas_y_recomendacion_preliminar(self):
        exp = caso()
        resultado = comparar(exp, generar_alternativas(exp))
        self.assertFalse(resultado.recomendadas)
        self.assertIn("Ninguna alternativa", resultado.recomendacion)
        alto = caso(ingreso=D(10000))
        recomendado = comparar(alto, generar_alternativas(alto))
        self.assertTrue(recomendado.recomendadas)
        self.assertIn("preliminar", recomendado.recomendacion)
        mora = replace(alto, historial="MORA_DECLARADA", dias_mora=31)
        con_mora = comparar(mora, generar_alternativas(mora))
        self.assertFalse(con_mora.recomendadas)
        self.assertGreater(con_mora.alternativas[0].puntaje_global, 80)
        self.assertIn("RN-11", {r["regla"] for r in con_mora.alternativas[0].escenarios[0].resultado.reglas})

    def test_descuento_planilla_cargos_y_tcea_por_flujo(self):
        desembolso = date(2026, 5, 31)
        exp = caso(ingreso=D(3200), descuento_planilla="YA_DESCONTADAS", evidencias=boletas((3200, 3200, 3200)),
                   patrimonio="Bien sintético", patrimonio_valor=D(1000000),
                   cargos=(Cargo("Seguro supuesto", D(10), "MENSUAL", "SOLICITANTE"),
                           Cargo("Cargo inicial", D(25), "INICIAL", "SOLICITANTE")),
                   cargos_completos=True, fecha_desembolso=desembolso,
                   fechas_pago=fechas_mensuales(desembolso, 12))
        comparativa = comparar(exp, generar_alternativas(exp))
        self.assertEqual(comparativa.base.cifras["ingresos_admisibles"], 3500)
        for e in comparativa.alternativas:
            self.assertFalse(e.preliminar)
            r = e.escenarios[1].resultado
            self.assertIsNotNone(r.tcea)
            self.assertEqual(r.cifras["ingresos_admisibles"], 3150)
            self.assertEqual(r.cifras["cargos_mensuales"], 10)
            self.assertEqual(r.cifras["cargos_iniciales"], 25)
            self.assertEqual(r.cifras["saldo_post_cuota"], 3150 - 1400 - 300 - r.cifras["pago_mensual_total"])
        incompleto = replace(exp, fechas_pago=exp.fechas_pago[:2])
        self.assertTrue(all(e.escenarios[0].resultado.tcea is None for e in comparar(incompleto, generar_alternativas(incompleto)).alternativas))

    def test_limites_y_edicion(self):
        limite = caso(meses=360, monto=D(".01"), tea=D(0))
        a, b, c = generar_alternativas(limite)
        resultado = comparar(limite, (a, b, c))
        self.assertIsNone(b.meses)
        self.assertIsNone(c.monto)
        self.assertFalse(resultado.alternativas[1].seleccionable)
        with self.assertRaisesRegex(ValueError, "mismo monto"):
            comparar(limite, (a, replace(a, codigo="B"), c))
        exp = caso()
        a, b, c = generar_alternativas(exp)
        for kw in (dict(caidas=(0, 30, 10)), dict(caidas=(0, 1, 101)), dict(tea=D(201)), dict(monto=D("0.009"))):
            with self.assertRaises(ValueError):
                comparar(exp, (a, replace(b, **kw), c))
        with self.assertRaisesRegex(ValueError, "superar"):
            comparar(exp, (a, b, c), Configuracion(umbral_dti=D(".60")))
        modificado = comparar(exp, (a, replace(b, tea=D(18), caidas=(5, 15, 35)), c),
                              Configuracion(umbral_dti=D(".60")), EscalaPuntuacion(dti_minimo=D(".90")))
        self.assertEqual(modificado.alternativas[1].escenarios[0].caida, 5)
        self.assertEqual(modificado.alternativas[1].escenarios[0].componentes["DTI"], 100)
