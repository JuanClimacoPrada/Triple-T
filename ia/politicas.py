"""Enrutamiento con opt-in, presupuesto por sesión y corte ante fallos."""
from dataclasses import dataclass
from conversacion.intenciones import interpretar

ERRORES = {
    "ACCESO": "Gemini no autorizó el acceso. El responsable debe revisar la clave y los permisos del proyecto.",
    "CUOTA": "Gemini indicó un límite de cuota. Continúa en modo local y vuelve a intentarlo más tarde.",
    "MODELO": "Gemini no encontró el modelo configurado. Revisa GEMINI_MODEL y su disponibilidad en la cuenta.",
    "SOLICITUD": "Gemini no aceptó la solicitud. Revisa la compatibilidad del modelo con la salida estructurada.",
    "TIEMPO": "Gemini tardó demasiado en responder. Puedes continuar en modo local.",
    "SDK": "Falta la dependencia de Gemini en el servidor. El responsable debe revisar requirements.txt.",
    "CONEXION": "No se pudo completar la conexión con Gemini. Puedes continuar en modo local.",
    "RESPUESTA": "La respuesta de Gemini no superó la validación. Reformula con cifras y campos explícitos.",
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


def resolver(c, texto, estado, config, proveedor=None):
    """Compatibilidad Sprint 4: captura exclusivamente local, sin llamadas remotas."""
    estado.ultima_ruta = "LOCAL"
    return interpretar(texto, c.campo_preguntado), None, ""
