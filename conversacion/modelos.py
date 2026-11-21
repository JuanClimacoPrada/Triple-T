from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo
from dominio.modelos import Expediente, Resultado, Configuracion


@dataclass(frozen=True)
class Interpretacion:
    intent: str
    entities: dict = field(default_factory=dict)
    source_text: str = ""
    requires_clarification: bool = False
    warnings: tuple[str, ...] = ()
    acciones: tuple[str, ...] = ()
    bloqueado: bool = False


@dataclass(frozen=True)
class Mensaje:
    rol: str
    texto: str
    revision: int


@dataclass
class Conversacion:
    expediente: Expediente = field(default_factory=lambda: Expediente(fecha=datetime.now(ZoneInfo("America/Lima")).date()))
    config: Configuracion = field(default_factory=Configuracion)
    mensajes: list[Mensaje] = field(default_factory=list)
    estado: str = "SIN_CASO"
    pendiente: dict | None = None
    revision: int = 0
    resultado: Resultado | None = None
    escenario: Expediente | None = None
    resultado_escenario: Resultado | None = None
    parametros_escenario: dict = field(default_factory=dict)
    vista: str = "RESUMEN"
    documentos: list[dict] = field(default_factory=list)
    informe: bytes | None = None
    informe_revision: int | None = None
    campo_preguntado: str | None = None
    flujo: object | None = None
