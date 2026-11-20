from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import uuid4

VERSION_REGLAS = "2.0.0-academico"
AVISO = "Uso académico con datos sintéticos. Recomendación para revisión del analista. Confirmar una transcripción no verifica autenticidad. Sin conexión a fuentes autorizadas."


@dataclass(frozen=True)
class Evidencia:
    documento_id: str = field(default_factory=lambda: uuid4().hex)
    tipo_documento: str = "BOLETA"
    nombre_archivo_sanitizado: str = "transcripcion-manual"
    pagina_o_region: str = "manual"
    texto_fuente_breve: str = ""
    campo: str = "ingreso_neto_estable"
    valor_extraido: Decimal | None = None
    estado: str = "PENDIENTE"
    fuente: str = "DECLARADO"
    fecha_documento: date | None = None
    observacion: str = ""
    extraordinarios_excluidos: Decimal = Decimal(0)


@dataclass(frozen=True)
class Cargo:
    concepto: str
    importe: Decimal
    momento: str = "MENSUAL"
    pagador: str = "SOLICITANTE"


@dataclass(frozen=True)
class Expediente:
    monto: Decimal | None = None
    meses: int | None = None
    tea: Decimal | None = None
    ingreso: Decimal | None = None
    gastos: Decimal | None = None
    otras_cuotas: Decimal | None = None
    estabilidad_meses: int | None = None
    historial: str = "DESCONOCIDO"
    dias_mora: int | None = None
    descuento_planilla: str = "SIN_ACLARAR"
    tipo_credito: str = "personal"
    moneda: str = "PEN"
    fecha: date = field(default_factory=date.today)
    evidencias: tuple[Evidencia, ...] = ()
    cargos: tuple[Cargo, ...] = ()
    cargos_completos: bool = False
    fecha_desembolso: date | None = None
    fechas_pago: tuple[date, ...] = ()
    resolucion_ingreso: str | None = None
    justificacion_ingreso: str = ""
    patrimonio: str = ""
    patrimonio_valor: Decimal | None = None
    patrimonio_fuente: str = "Declarado; verificación pendiente"
    observacion: str = ""
    origen_campos: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Configuracion:
    umbral_dti: Decimal = Decimal("0.30")
    discrepancia: Decimal = Decimal("0.10")
    tea_maxima: Decimal = Decimal("200")


@dataclass
class Resultado:
    estado: str = "DATOS INSUFICIENTES"
    reglas: list[dict] = field(default_factory=list)
    cifras: dict = field(default_factory=dict)
    tabla: list[dict] = field(default_factory=list)
    meses_ingreso: list[dict] = field(default_factory=list)
    tcea: Decimal | None = None
    version: str = VERSION_REGLAS
    supuestos: list[str] = field(default_factory=lambda: [
        "PEN, TEA fija, cuotas mensuales vencidas, sin gracia ni pagos extraordinarios.",
        "DTI sobre servicio mensual de deuda; umbrales didácticos, no políticas bancarias.",
        "Cargos introducidos como supuestos; no inferidos de tarifas bancarias.",
        "TCEA referencial: flujos fechados del prestatario, año de 365 días; no costo regulatorio definitivo.",
    ])
