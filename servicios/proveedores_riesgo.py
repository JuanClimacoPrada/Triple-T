"""Contratos futuros sin red, scraping, credenciales ni proveedores activos."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping, Protocol
from servicios.finanzas import entero

SENTINEL_REFERENCIA = "https://www.misentinel.com.pe/home"


@dataclass(frozen=True)
class ScoreDemostracion:
    valor: int
    escala_maxima: int
    fecha: date
    simulado: bool

    def __post_init__(self):
        if self.simulado is not True:
            raise ValueError("La instancia pública solo admite scores simulados.")
        object.__setattr__(self, "escala_maxima", entero(self.escala_maxima, "Máximo de escala ilustrativa", 1, 100000))
        object.__setattr__(self, "valor", entero(self.valor, "Score simulado", 0, self.escala_maxima))
        if type(self.fecha) is not date or self.fecha > date.today():
            raise ValueError("Indique una fecha de registro válida, no futura.")

    @property
    def fuente(self):
        return "Registro manual de demostración; no consultado en Sentinel"


@dataclass(frozen=True)
class EvidenciaValidacion:
    modelo_version: str
    datos_autorizados_referencia: str
    definicion_incumplimiento: str
    horizonte_meses: int
    discriminacion_referencia: str
    calibracion_referencia: str
    evaluacion_fuera_muestra_referencia: str
    aprobacion_referencia: str


@dataclass(frozen=True)
class EstimacionModelo:
    pd_porcentaje: Decimal
    fuente: str
    fecha: date
    validacion: EvidenciaValidacion


class ProveedorPD(Protocol):
    def estimar(self, variables_autorizadas: Mapping[str, Decimal]) -> EstimacionModelo: ...


@dataclass(frozen=True)
class ConsultaScoreVerificable:
    valor: Decimal
    escala: str
    fuente: str
    fecha: date
    evidencia_consulta: str


class ProveedorScore(Protocol):
    def consultar(self, referencia_autorizacion: str) -> ConsultaScoreVerificable: ...


class SentinelNoIntegrado:
    def consultar(self, referencia_autorizacion: str) -> ConsultaScoreVerificable:
        raise NotImplementedError("No hay API autorizada integrada. Utilice el portal externo para una consulta legítima.")


class ModeloNoDisponible:
    def estimar(self, variables_autorizadas: Mapping[str, Decimal]) -> EstimacionModelo:
        raise NotImplementedError("No existe un modelo entrenado, calibrado y autorizado en Triple-T.")
