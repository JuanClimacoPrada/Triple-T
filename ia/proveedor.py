"""Gemini opcional, sin claves en sesión, sin logs ni reintentos automáticos."""
import asyncio
import json
import os
import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ConfigIA:
    api_key: str = field(default="", repr=False)
    modelo: str = ""
    gratuito_confirmado: bool = False

    @property
    def disponible(self):
        return bool(self.api_key and re.fullmatch(r"gemini-[a-z0-9.-]{1,80}", self.modelo) and self.gratuito_confirmado)

    @property
    def pendientes(self):
        campos = []
        if not self.api_key:
            campos.append("GEMINI_API_KEY")
        if not re.fullmatch(r"gemini-[a-z0-9.-]{1,80}", self.modelo):
            campos.append("GEMINI_MODEL (identificador gemini-…)")
        if not self.gratuito_confirmado:
            campos.append("GEMINI_FREE_TIER_CONFIRMED")
        return campos


def configuracion(secrets=None):
    def leer(nombre):
        if os.environ.get(nombre):
            return os.environ[nombre]
        try:
            return secrets.get(nombre, "") if secrets is not None else ""
        except Exception:
            return ""
    return ConfigIA(str(leer("GEMINI_API_KEY")).strip(), str(leer("GEMINI_MODEL")).strip().removeprefix("models/"),
                    str(leer("GEMINI_FREE_TIER_CONFIRMED")).strip().lower() == "true")


class ErrorProveedor(Exception):
    """Solo códigos seguros; nunca texto de la excepción remota."""


def codigo_error(error):
    codigo = getattr(error, "code", None)
    if codigo in (401, 403):
        return "ACCESO"
    if codigo == 429:
        return "CUOTA"
    if codigo == 404:
        return "MODELO"
    if codigo == 400:
        return "SOLICITUD"
    if isinstance(error, TimeoutError) or "timeout" in type(error).__name__.lower():
        return "TIEMPO"
    return "CONEXION"


class Gemini:
    def __init__(self, config):
        self.config = config

    def interpretar(self, mensaje, contexto):
        from ia.contrato_semantico import INSTRUCCION_SEMANTICA, ESQUEMA_SEMANTICO
        from ia.privacidad import consulta_remota_admisible
        if not consulta_remota_admisible(mensaje) or len(json.dumps(contexto, ensure_ascii=False)) > 24000:
            raise ErrorProveedor("SOLICITUD")
        if not self.config.disponible:
            raise ValueError("Configuración IA incompleta.")
        # Imports diferidos: sin SDK, la aplicación local sigue disponible.
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise ErrorProveedor("SDK") from None

        async def llamada():
            http = types.HttpOptions(
                timeout=12000,
                retry_options=types.HttpRetryOptions(attempts=1)
            )
            async with genai.Client(api_key=self.config.api_key, vertexai=False, http_options=http).aio as client:
                respuesta = await asyncio.wait_for(client.models.generate_content(
                    model=self.config.modelo,
                    contents=json.dumps({"pregunta_sintetica": mensaje, "contexto": contexto}, ensure_ascii=False, allow_nan=False),
                    config=types.GenerateContentConfig(system_instruction=INSTRUCCION_SEMANTICA, temperature=0,
                        max_output_tokens=2048, response_mime_type="application/json", response_json_schema=ESQUEMA_SEMANTICO,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))), timeout=15)
                return respuesta.text
        try:
            return asyncio.run(llamada())
        except Exception as error:
            raise ErrorProveedor(codigo_error(error)) from None
