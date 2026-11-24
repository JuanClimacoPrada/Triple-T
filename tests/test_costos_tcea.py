from dataclasses import replace
from datetime import date
from decimal import Decimal as D
from unittest import TestCase

from streamlit.testing.v1 import AppTest

from dominio.modelos import Cargo, Configuracion
from servicios.costos import CATEGORIAS, diagnostico_tcea
from servicios.finanzas import fechas_mensuales, problemas_flujo_fechado
from servicios.reglas import analizar
from servicios.simulacion import evaluar_escenario
from tests.test_sprint2 import caso


class TestCostosTCEA(TestCase):
    def setUp(self):
        self.fecha = date(2026, 1, 31)
        self.exp = replace(caso(), fecha_desembolso=self.fecha,
                           fechas_pago=fechas_mensuales(self.fecha, 12), origen_fechas_pago="CONFIRMADAS")

    def test_cero_explicito_y_cargos_desconocidos(self):
        exp = replace(self.exp, cargos=(Cargo("Seguro", D(0), "MENSUAL", "NO_APLICA"),))
        parcial = analizar(exp)
        causas = diagnostico_tcea(exp, parcial)
        self.assertIsNone(parcial.tcea)
        self.assertNotIn("Registra seguro · mensual", " ".join(causas))
        self.assertIn("Registra seguro · inicial", " ".join(causas))
        self.assertIn("Registra otros gastos · mensual", " ".join(causas))
        self.assertIn("cuota_base", parcial.cifras)
        cargos = tuple(Cargo(concepto, D(0), momento, "NO_APLICA") for concepto, momento in CATEGORIAS)
        exp = replace(exp, cargos=cargos, cargos_completos=True)
        final = analizar(exp)
        self.assertIsNotNone(final.tcea)
        self.assertEqual(diagnostico_tcea(exp, final), ())

    def test_pagador_pendiente_preserva_cuota_y_exige_identificacion(self):
        exp = replace(self.exp, cargos_completos=True,
                      cargos=(Cargo("Seguro", D(40), "MENSUAL", "PENDIENTE"),))
        pendiente = analizar(exp)
        self.assertAlmostEqual(pendiente.cifras["pago_mensual_total"], pendiente.cifras["cuota_base"], places=24)
        self.assertIsNone(pendiente.tcea)
        self.assertEqual(diagnostico_tcea(exp, pendiente), ("Indica quién paga Seguro · mensual.",))
        exp = replace(exp, cargos=(replace(exp.cargos[0], pagador="TERCERO"),))
        self.assertIsNotNone(analizar(exp).tcea)

    def test_diagnostica_fechas_y_desembolso_por_separado(self):
        exp = replace(self.exp, cargos_completos=True, fecha_desembolso=None,
                      origen_fechas_pago="PROPUESTAS", fechas_pago=(self.fecha, self.fecha),
                      cargos=(Cargo("Comisiones", D(10000), "INICIAL"),))
        causas = diagnostico_tcea(exp, analizar(exp))
        self.assertEqual(len(causas), 5)
        self.assertTrue(any("fecha de desembolso" in causa for causa in causas))
        self.assertTrue(any("2 vencimientos" in causa for causa in causas))
        self.assertTrue(any("sin duplicados" in causa for causa in causas))
        self.assertTrue(any("neto positivo" in causa for causa in causas))
        self.assertTrue(any("vencimiento propuestas" in causa for causa in causas))

    def test_flujos_positivos_y_un_pago_por_vencimiento(self):
        causas = problemas_flujo_fechado(D(100), [D(0)], (date(2026, 2, 28),), self.fecha, 2)
        self.assertEqual(len(causas), 3)
        self.assertTrue(any("por cada pago" in causa for causa in causas))
        self.assertTrue(any("importe positivo" in causa for causa in causas))

    def test_calendario_proyectado_requiere_base_calculable(self):
        exp = replace(self.exp, cargos_completos=True)
        cfg = Configuracion()
        copia, r = evaluar_escenario(exp, exp.monto, 24, exp.tea, 0, cfg, analizar(exp), conservar_calendario=True)
        self.assertIsNotNone(r.tcea)
        self.assertEqual(copia.origen_fechas_pago, "PROYECTADAS")
        self.assertTrue(any("Vencimientos proyectados" in supuesto for supuesto in r.supuestos))
        self.assertEqual(exp.origen_fechas_pago, "CONFIRMADAS")
        exp = replace(exp, origen_fechas_pago="PROPUESTAS")
        _, r = evaluar_escenario(exp, exp.monto, 24, exp.tea, 0, cfg, analizar(exp), conservar_calendario=True)
        self.assertIsNone(r.tcea)
        self.assertEqual(r.pendientes_tcea, ("Completa y confirma las fechas de vencimiento.",))

    def test_formulario_guarda_ceros_y_recalcula_sin_perder_confirmacion(self):
        app = AppTest.from_string('''
import streamlit as st
from conversacion.gestor import evaluar_actual, nuevo
from tests.test_sprint2 import caso
from ui_chat import editor_costos

if "c" not in st.session_state:
    c = nuevo(guiado=True)
    c.expediente = caso()
    c.flujo.iniciado = True
    evaluar_actual(c, responder=False)
    c.flujo.revision_confirmada = c.revision
    c.informe = b"anterior"
    c.informe_revision = c.revision
    st.session_state.c = c
editor_costos(st.session_state.c)
''').run()
        self.assertFalse(app.exception)
        self.assertTrue(all(campo.value is None for campo in app.number_input))
        for campo in app.number_input:
            campo.set_value(0.0)
        app.date_input[0].set_value(self.fecha)
        for control in app.checkbox:
            control.set_value(True)
        app.button[0].click().run()
        self.assertFalse(app.exception)
        c = app.session_state["c"]
        self.assertEqual(c.expediente.origen_fechas_pago, "CONFIRMADAS")
        self.assertEqual(c.expediente.fechas_pago, fechas_mensuales(self.fecha, 12))
        self.assertTrue(all(cargo.importe == 0 for cargo in c.expediente.cargos))
        self.assertIsNotNone(c.resultado.tcea)
        self.assertEqual(c.flujo.revision_confirmada, c.revision)
        self.assertIsNone(c.informe)
