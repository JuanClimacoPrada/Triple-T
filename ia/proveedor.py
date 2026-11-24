"""Cliente Gemini con diagnósticos acotados y sin reintentos de aplicación."""
import asyncio
import json
import logging
import os
import re
import socket
import ssl
from dataclasses import dataclass, field
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version


LOG = logging.getLogger("triple_t.gemini")
SERVICIO_GEMINI = "https://generativelanguage.googleapis.com/"
VERSION_API = "v1beta"
_HTTP = {400: "SOLICITUD", 401: "ACCESO", 403: "ACCESO", 404: "MODELO", 408: "TIEMPO",
         429: "CUOTA", 500: "SERVICIO", 502: "SERVICIO", 503: "SERVICIO", 504: "TIEMPO"}
_MOTIVOS_CLAVE = {"API_KEY_INVALID", "API_KEY_SERVICE_BLOCKED", "API_KEY_HTTP_REFERRER_BLOCKED",
                  "API_KEY_IP_ADDRESS_BLOCKED", "API_KEY_EXPIRED"}
_ETAPAS = {"configuracion", "sdk", "solicitud", "red", "respuesta", "contexto", "validacion"}
_CODIGOS = set(_HTTP.values()) | {"CLAVE_INVALIDA", "CONFIGURACION", "SDK", "SDK_COMPATIBILIDAD",
                                 "CONEXION", "DNS", "TLS", "RESPUESTA", "SIN_CONTENIDO", "CONTEXTO"}


@dataclass(frozen=True)
class ConfigIA:
    api_key: str = field(default="", repr=False)
    modelo: str = ""
    gratuito_confirmado: bool = False

    @property
    def disponible(self):
        return not self.pendientes

    @property
    def pendientes(self):
        campos = []
        if (not isinstance(self.api_key, str) or not re.fullmatch(r"[A-Za-z0-9_\-]+", self.api_key)
            or self.api_key.lower() in {"tu_clave", "tu_api_key", "your_api_key", "none", "null"}):
            campos.append("GEMINI_API_KEY")
        if not isinstance(self.modelo, str) or not re.fullmatch(r"gemini-[a-z0-9.-]{1,80}", self.modelo):
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
    clave = leer("GEMINI_API_KEY")
    return ConfigIA(clave.strip() if isinstance(clave, str) else "", str(leer("GEMINI_MODEL")).strip().removeprefix("models/"),
                    str(leer("GEMINI_FREE_TIER_CONFIRMED")).strip().lower() == "true")


class ErrorProveedor(Exception):
    """Solo códigos seguros; nunca texto de la excepción remota."""

    def __init__(self, codigo, *, etapa="red", http=None):
        self.codigo = codigo if codigo in _CODIGOS else "RESPUESTA"
        self.etapa = etapa if etapa in _ETAPAS else "red"
        self.http = http if type(http) is int and 100 <= http <= 599 else None
        super().__init__(self.codigo)


def _estado_http(error):
    for valor in (getattr(error, "code", None), getattr(error, "status_code", None),
                  getattr(getattr(error, "response", None), "status_code", None)):
        if type(valor) is int and 100 <= valor <= 599:
            return valor
    return None


def _clave_rechazada(error):
    # ErrorInfo es metadata estructurada. Solo se compara con motivos conocidos.
    cuerpo = getattr(error, "details", None)
    if not isinstance(cuerpo, dict):
        return False
    detalle = cuerpo.get("error", cuerpo)
    if not isinstance(detalle, dict) or not isinstance(detalle.get("details"), list):
        return False
    return any(isinstance(dato, dict) and isinstance(dato.get("reason"), str) and dato["reason"] in _MOTIVOS_CLAVE
               for dato in detalle["details"])


def codigo_error(error):
    codigo = _estado_http(error)
    if codigo is not None:
        if codigo in (400, 401, 403) and _clave_rechazada(error):
            return "CLAVE_INVALIDA"
        return _HTTP.get(codigo, "SERVICIO" if codigo >= 500 else "SOLICITUD")
    actual = error
    for _ in range(5):
        if actual is None:
            break
        if isinstance(actual, TimeoutError) or "timeout" in type(actual).__name__.lower():
            return "TIEMPO"
        if isinstance(actual, socket.gaierror):
            return "DNS"
        if isinstance(actual, ssl.SSLError):
            return "TLS"
        actual = actual.__cause__ or actual.__context__
    return "CONEXION"


@lru_cache(maxsize=1)
def version_sdk():
    try:
        instalada = version("google-genai")
    except PackageNotFoundError:
        return "ausente"
    return instalada if re.fullmatch(r"\d+\.\d+\.\d+(?:[A-Za-z0-9.]{1,15})?", instalada) else "desconocida"


def _sdk_compatible(genai, tipos):
    generacion = getattr(getattr(tipos, "GenerateContentConfig", None), "model_fields", {})
    http = getattr(getattr(tipos, "HttpOptions", None), "model_fields", {})
    return (callable(getattr(genai, "Client", None)) and callable(getattr(tipos, "HttpRetryOptions", None))
            and callable(getattr(tipos, "AutomaticFunctionCallingConfig", None))
            and {"response_json_schema", "response_mime_type", "automatic_function_calling"} <= set(generacion)
            and {"timeout", "retry_options", "api_version", "base_url"} <= set(http))


def _cargar_sdk():
    # Importación diferida para que la captura local no dependa de Gemini.
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise ErrorProveedor("SDK", etapa="sdk") from None
    except Exception:
        raise ErrorProveedor("SDK_COMPATIBILIDAD", etapa="sdk") from None
    if not _sdk_compatible(genai, types):
        raise ErrorProveedor("SDK_COMPATIBILIDAD", etapa="sdk")
    return genai, types


@lru_cache(maxsize=1)
def diagnostico_sdk():
    """Revisa la dependencia y sus opciones locales sin crear un cliente."""
    try:
        _cargar_sdk()
    except ErrorProveedor as error:
        return error.codigo
    return None


def registrar_diagnostico(error):
    LOG.warning("Gemini fase=%s codigo=%s http=%s sdk=%s api=%s",
                error.etapa, error.codigo, error.http or "-", version_sdk(), VERSION_API)


class Gemini:
    def __init__(self, config):
        self.config = config

    def interpretar(self, mensaje, contexto):
        from ia.contrato_semantico import INSTRUCCION_SEMANTICA, ESQUEMA_SEMANTICO
        from ia.privacidad import consulta_remota_admisible
        if not consulta_remota_admisible(mensaje) or len(json.dumps(contexto, ensure_ascii=False)) > 24000:
            raise ErrorProveedor("CONTEXTO", etapa="contexto")
        if not self.config.disponible:
            raise ErrorProveedor("CONFIGURACION", etapa="configuracion")
        genai, tipos = _cargar_sdk()
        try:
            http = tipos.HttpOptions(
                base_url=SERVICIO_GEMINI,
                api_version=VERSION_API,
                timeout=12000,
                retry_options=tipos.HttpRetryOptions(attempts=1),
            )
            configuracion_salida = tipos.GenerateContentConfig(
                system_instruction=INSTRUCCION_SEMANTICA,
                max_output_tokens=2048,
                response_mime_type="application/json",
                response_json_schema=ESQUEMA_SEMANTICO,
                automatic_function_calling=tipos.AutomaticFunctionCallingConfig(disable=True),
            )
        except (TypeError, ValueError, AttributeError):
            raise ErrorProveedor("SDK_COMPATIBILIDAD", etapa="solicitud") from None

        async def llamada():
            try:
                cliente = genai.Client(api_key=self.config.api_key, vertexai=False, http_options=http)
            except (TypeError, ValueError, AttributeError):
                raise ErrorProveedor("SDK_COMPATIBILIDAD", etapa="sdk") from None
            async with cliente.aio as client:
                respuesta = await asyncio.wait_for(client.models.generate_content(
                    model=self.config.modelo,
                    contents=json.dumps({"pregunta_sintetica": mensaje, "contexto": contexto}, ensure_ascii=False, allow_nan=False),
                    config=configuracion_salida), timeout=15)
                # La propiedad SDK .text puede registrar avisos si la salida
                # contiene partes no textuales. Solo se interpreta texto plano.
                candidatos = respuesta.candidates or []
                contenido = candidatos[0].content if candidatos else None
                partes = (contenido.parts or []) if contenido else []
                salida = "".join(p.text for p in partes if p.text and not p.thought)
                if not salida.strip():
                    raise ErrorProveedor("SIN_CONTENIDO", etapa="respuesta")
                return salida
        try:
            return asyncio.run(llamada())
        except ErrorProveedor:
            raise
        except Exception as error:
            raise ErrorProveedor(codigo_error(error), http=_estado_http(error)) from None
