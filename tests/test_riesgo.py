import json
import os
import unittest
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal as D
from unittest.mock import patch
from html.parser import HTMLParser
from servicios.riesgo import EscenarioHipotetico, NOMBRES, advertencias
from servicios.proveedores_riesgo import ScoreDemostracion, SentinelNoIntegrado, ModeloNoDisponible, SENTINEL_REFERENCIA
from triple_t_pro_layout import sentinel_config, url_segura, score_html, construir_vm
from conversacion.gestor import nuevo, aplicar, evaluar_actual
from experiencia.ayuda_ia import responder, hechos
from ia.politicas import EstadoIA
from ia.proveedor import ConfigIA
from casos import CASOS


def caso_confirmado():
    c = nuevo(guiado=True)
    datos = dict(CASOS["Esperado"], historial="SIN_MORA_DECLARADA", descuento_planilla="NO_DESCONTADAS")
    aplicar(c, datos)
    evaluar_actual(c, responder=False)
    c.flujo.revision_confirmada = c.revision
    c.flujo.ia_revision = c.revision
    return c


class TestRiesgo(unittest.TestCase):
    def test_ausencia_no_es_cero(self):
        for n in NOMBRES:
            e = EscenarioHipotetico(n)
            self.assertIsNone(e.no_incumplimiento)
            self.assertIsNone(e.perdida_esperada)

    def test_calculo_y_extremos(self):
        for pd, no, perdida in ((0, 100, 0), (100, 0, 4500), ("2.5", "97.5", "112.5")):
            e = EscenarioHipotetico("Esperado", pd, 12, 45, 10000)
            self.assertEqual(e.no_incumplimiento, D(str(no)))
            self.assertEqual(e.perdida_esperada, D(str(perdida)))
        self.assertEqual(EscenarioHipotetico("Esperado", 100, 12, 0, 10000).perdida_esperada, 0)
        self.assertIsNone(EscenarioHipotetico("Esperado", 0, 12).perdida_esperada)

    def test_validaciones_fuente_horizonte(self):
        for valor in (-1, 101, "NaN", "Infinity", True):
            for campo in ("pd", "lgd"):
                with self.subTest(valor=valor, campo=campo), self.assertRaises(ValueError):
                    EscenarioHipotetico("Esperado", horizonte_meses=12, **{campo: valor})
        for kw in ({"pd": 2}, {"horizonte_meses": 0}, {"horizonte_meses": 1.5}, {"exposicion": -1}):
            with self.assertRaises(ValueError):
                EscenarioHipotetico("Esperado", **kw)
        with self.assertRaises(TypeError):
            EscenarioHipotetico("Esperado", fuente="Modelo validado")
        self.assertIn("sin modelo validado", EscenarioHipotetico("Esperado").naturaleza)

    def test_horizontes_y_orden_no_se_reescriben(self):
        es = [EscenarioHipotetico("Optimista", 50, 12), EscenarioHipotetico("Esperado", 10, 24)]
        self.assertEqual(len(advertencias(es)), 2)
        self.assertEqual(es[0].pd, 50)

    def test_score_solo_simulado_y_fecha_valida(self):
        s = ScoreDemostracion(400, 1000, date.today(), True)
        self.assertIn("no consultado en Sentinel", s.fuente)
        for args in ((400, 1000, date.today(), False), (1001, 1000, date.today(), True), (400, 1000, date.today()+timedelta(days=1), True), (None, 1000, date.today(), True)):
            with self.assertRaises(ValueError):
                ScoreDemostracion(*args)
        with self.assertRaises(NotImplementedError):
            SentinelNoIntegrado().consultar("autorizacion-ficticia")
        with self.assertRaises(NotImplementedError):
            ModeloNoDisponible().estimar({})

    def test_enlace_fijo_sin_identidad_y_nueva_pestana(self):
        class Enlaces(HTMLParser):
            def handle_starttag(self, tag, attrs):
                if tag == "a":
                    self.enlace = dict(attrs)
        p = Enlaces()
        p.feed(score_html(SENTINEL_REFERENCIA))
        self.assertEqual(p.enlace["href"], SENTINEL_REFERENCIA)
        self.assertEqual(p.enlace["target"], "_blank")
        self.assertEqual(p.enlace["referrerpolicy"], "no-referrer")
        self.assertIn("noreferrer", p.enlace["rel"])
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(sentinel_config({}), SENTINEL_REFERENCIA)
            self.assertEqual(sentinel_config({"SENTINEL_URL": ""}), SENTINEL_REFERENCIA)
            self.assertEqual(sentinel_config({"SENTINEL_URL": "https://example.org/portal"}), "https://example.org/portal")
        for url in ("javascript:alert(1)", "http://example.org", "https://x.org/?dni=123", "https://x.org/#identidad", "https://user:pass@x.org", "https://127.0.0.1", 'https://x.org/\"onclick=foo'):
            self.assertIsNone(url_segura(url))
            self.assertNotIn("href=", score_html(url))

    def test_capacidad_no_se_confunde_con_pd(self):
        c = caso_confirmado()
        r = c.resultado
        vm = construir_vm(c)
        self.assertEqual(r.cifras["capacidad_neta"], 1800)
        self.assertEqual(vm.metrics[1].value, "S/ 1,800.00")
        EscenarioHipotetico("Esperado", 99, 12, 100, 50000)
        self.assertIs(c.resultado, r)
        self.assertNotIn("pd", hechos(c))

    def test_proveedor_recibe_consulta_admisible_y_contexto_acotado(self):
        c = caso_confirmado()
        # Marcadores sintéticos para demostrar que ni notas ni OCR se filtran.
        c.expediente = replace(c.expediente, observacion="MARCADOR_PRIVADO", patrimonio="PATRIMONIO_PRIVADO")
        c.documentos.append({"nombre": "ARCHIVO_PRIVADO.pdf", "ocr": "OCR_PRIVADO"})
        class Proveedor:
            llamadas = []
            def interpretar(self, pregunta, contexto):
                self.llamadas.append((pregunta, contexto))
                return json.dumps({"solicitudes": [{
                    "intencion": "EXPLICAR_RESULTADO", "referencia": {"objetivo": "BASE", "escenario": ""},
                    "entidades": [], "incertidumbres": [], "hechos": ["cuota_base"], "respuesta": "{{cuota_base}}",
                }]})
        p = Proveedor()
        estado = EstadoIA(habilitado=True, consentimiento=True)
        cfg = ConfigIA("clave-ficticia", "gemini-test", True)
        with patch("socket.create_connection", side_effect=AssertionError("Red no permitida")):
            responder(c, "¿cuánto tendría que soltar cada mes?", estado, cfg, permitido=True, proveedor=p)
        self.assertEqual(len(p.llamadas), 1)
        salida = json.dumps(p.llamadas)
        for secreto in ("PRIVADO", "clave-ficticia"):
            self.assertNotIn(secreto, salida)
        self.assertEqual(p.llamadas[0][0], "¿cuánto tendría que soltar cada mes?")
        responder(c, "dni 12345678", estado, cfg, permitido=True, proveedor=p)
        self.assertEqual(len(p.llamadas), 1)

