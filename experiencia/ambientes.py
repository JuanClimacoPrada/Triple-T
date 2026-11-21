import os


AVISO_DEMO = "Entorno de demostración · No introduzcas datos personales ni documentos reales"


def entorno(secrets=None):
    valor = os.environ.get("APP_ENV")
    if valor is None:
        try:
            valor = secrets.get("APP_ENV", "demo") if secrets is not None else "demo"
        except Exception:
            valor = "demo"
    if str(valor).strip().lower() != "demo":
        raise ValueError("Entorno bloqueado: solo está habilitada la demostración. Piloto privado y producción requieren controles y autorización formal.")
    return "demo"


def ia_permitida(secrets=None):
    valor = os.environ.get("GEMINI_ENABLED")
    if valor is None:
        try:
            valor = secrets.get("GEMINI_ENABLED", True) if secrets is not None else True
        except Exception:
            valor = True
    return str(valor).strip().lower() == "true"
