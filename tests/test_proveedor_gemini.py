import json
import socket
import ssl
import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch

from ia.proveedor import (ConfigIA, ErrorProveedor, Gemini, SERVICIO_GEMINI, VERSION_API,
                         _sdk_compatible, codigo_error, registrar_diagnostico)


class TestProveedorGemini(unittest.TestCase):
    def test_codigos_http_y_error_info(self):
        esperados = {400: "SOLICITUD", 401: "ACCESO", 403: "ACCESO", 404: "MODELO",
                     408: "TIEMPO", 429: "CUOTA", 503: "SERVICIO", 504: "TIEMPO"}
        for status_code, codigo in esperados.items():
            with self.subTest(status_code=status_code):
                self.assertEqual(codigo_error(NS(response=NS(status_code=status_code))), codigo)
        error = NS(code=400, details={"error": {"details": [{"reason": "API_KEY_INVALID"}]}})
        self.assertEqual(codigo_error(error), "CLAVE_INVALIDA")
        self.assertEqual(codigo_error(ssl.SSLError("dato sensible")), "TLS")
        self.assertEqual(codigo_error(socket.gaierror("dato sensible")), "DNS")

    def test_logs_no_incluyen_excepcion_ni_secretos(self):
        remoto = NS(code=400, details={"error": {"message": "TEXTO_OCULTO", "details": [{"reason": "API_KEY_INVALID"}]}})
        seguro = ErrorProveedor(codigo_error(remoto), http=remoto.code)
        with self.assertLogs("triple_t.gemini", "WARNING") as log:
            registrar_diagnostico(seguro)
            registrar_diagnostico(ErrorProveedor("otra clave oculta", etapa="solicitud privada", http="dato"))
        salida = " ".join(log.output)
        self.assertIn("codigo=CLAVE_INVALIDA http=400", salida)
        for privado in ("TEXTO_OCULTO", "clave oculta", "solicitud privada", "http=dato"):
            self.assertNotIn(privado, salida)

    def test_sdk_requiere_json_schema_y_control_de_reintentos(self):
        genai = NS(Client=lambda **_: None)
        campos = {"response_json_schema", "response_mime_type", "automatic_function_calling"}
        tipos = NS(GenerateContentConfig=NS(model_fields=campos),
                   HttpOptions=NS(model_fields={"timeout", "retry_options", "api_version", "base_url"}),
                   HttpRetryOptions=lambda **_: None, AutomaticFunctionCallingConfig=lambda **_: None)
        self.assertTrue(_sdk_compatible(genai, tipos))
        campos.remove("response_json_schema")
        self.assertFalse(_sdk_compatible(genai, tipos))

    def test_cliente_envia_un_json_estructurado_al_endpoint_previsto(self):
        capturado = {}

        class Cliente:
            def __init__(self, **kwargs):
                capturado["cliente"] = kwargs
                self.aio = self
                self.models = self

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def generate_content(self, **kwargs):
                capturado["solicitud"] = kwargs
                partes = [NS(text="razonamiento interno", thought=True), NS(text='{"solicitudes":[]}', thought=False)]
                return NS(candidates=[NS(content=NS(parts=partes))])

        tipos = NS(HttpOptions=dict, HttpRetryOptions=dict, GenerateContentConfig=dict, AutomaticFunctionCallingConfig=dict)
        cfg = ConfigIA("test-key", "gemini-test", True)
        with patch("ia.proveedor._cargar_sdk", return_value=(NS(Client=Cliente), tipos)):
            salida = Gemini(cfg).interpretar("¿Cuánto le quedaría después de pagar?", {"hechos": {}})
        self.assertEqual(salida, '{"solicitudes":[]}')
        opciones_http = capturado["cliente"]["http_options"]
        self.assertEqual(opciones_http["base_url"], SERVICIO_GEMINI)
        self.assertEqual(opciones_http["api_version"], VERSION_API)
        self.assertEqual(opciones_http["retry_options"], {"attempts": 1})
        self.assertEqual(opciones_http["timeout"], 12000)
        llamada = capturado["solicitud"]
        self.assertEqual(llamada["model"], cfg.modelo)
        self.assertEqual(llamada["config"]["response_mime_type"], "application/json")
        self.assertIn("response_json_schema", llamada["config"])
        self.assertEqual(llamada["config"]["automatic_function_calling"], {"disable": True})
        self.assertEqual(json.loads(llamada["contents"])["pregunta_sintetica"], "¿Cuánto le quedaría después de pagar?")
        self.assertNotIn(cfg.api_key, repr(cfg))

    def test_configuracion_incompleta_no_construye_cliente(self):
        for cfg in (ConfigIA("", "gemini-test", True), ConfigIA("tu_api_key", "gemini-test", True),
                    ConfigIA("test-key", "gpt", True), ConfigIA("test-key", "gemini-test", False)):
            with self.subTest(pendientes=cfg.pendientes), patch("ia.proveedor._cargar_sdk") as sdk:
                with self.assertRaisesRegex(ErrorProveedor, "CONFIGURACION"):
                    Gemini(cfg).interpretar("¿Cuál es la cuota?", {})
                sdk.assert_not_called()
