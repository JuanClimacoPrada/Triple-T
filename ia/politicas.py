"""Enrutamiento con opt-in, presupuesto por sesión y corte ante fallos."""
from dataclasses import dataclass, field
from conversacion.intenciones import interpretar

ERRORES = {
    "ACCESO": "Gemini no autorizó el acceso. El responsable debe revisar la clave y los permisos del proyecto.",
    "CLAVE_INVALIDA": "Google rechazó la clave configurada. El responsable debe revisar su vigencia y restricciones.",
    "CONFIGURACION": "Falta completar la configuración de Gemini en el servidor.",
    "CUOTA": "Gemini indicó un límite de cuota. Continúa en modo local y vuelve a intentarlo más tarde.",
    "MODELO": "Gemini no encontró el modelo configurado. Revisa GEMINI_MODEL y su disponibilidad en la cuenta.",
    "SOLICITUD": "Gemini rechazó el formato de la solicitud. El responsable debe revisar la versión de la API y el soporte de salida estructurada del modelo.",
    "TIEMPO": "Gemini tardó demasiado en responder. Puedes continuar en modo local.",
    "SDK": "No se pudo cargar la dependencia de Gemini en el servidor. El responsable debe revisar google-genai y sus dependencias.",
    "SDK_COMPATIBILIDAD": "La versión del SDK de Gemini no es compatible con este cliente. El responsable debe revisar la instalación del servidor.",
    "CONEXION": "No se pudo completar la conexión con Gemini. Puedes continuar en modo local.",
    "DNS": "El servidor no pudo localizar la API de Gemini. Puedes continuar en modo local.",
    "TLS": "El servidor no pudo establecer la conexión segura con Gemini. Puedes continuar en modo local.",
    "SERVICIO": "El servicio de Gemini devolvió un error temporal. Puedes continuar en modo local.",
    "SIN_CONTENIDO": "Gemini no devolvió texto utilizable. Puedes continuar en modo local.",
    "CONTEXTO": "No fue posible preparar esta consulta para Gemini. Puedes continuar en modo local.",
    "RESPUESTA": "La respuesta de Gemini no superó la validación. Puedes continuar con el asistente local.",
}


@dataclass
class EstadoIA:
    habilitado: bool = False
    consentimiento: bool = False
    llamadas: int = 0
    errores: int = 0
    circuito_abierto: bool = False
    ultima_ruta: str = "LOCAL"
    ultimo_error: str = ""
    respuestas_validas: int = 0
    revision_contexto: int | None = None
    contexto_semantico: dict = field(default_factory=dict)


def resolver(c, texto, estado, config, proveedor=None):
    """Compatibilidad Sprint 4: captura exclusivamente local, sin llamadas remotas."""
    estado.ultima_ruta = "LOCAL"
    return interpretar(texto, c.campo_preguntado), None, ""
