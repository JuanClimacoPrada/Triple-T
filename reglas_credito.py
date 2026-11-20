"""Perfiles académicos independientes; no representan políticas bancarias."""
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class ReglasCredito:
    nombre: str
    pendientes: str
    limite_cuota_ingreso: float = 0.30
    dias_mora_alerta: int = 30
    estabilidad_minima: int = 6
    limite_deuda_total: float | None = None


PERFILES = MappingProxyType({
    "personal": ReglasCredito("Personal", "Definir límites de monto, plazo y endeudamiento total."),
    "vehicular": ReglasCredito("Vehicular", "Definir cuota inicial, valor del vehículo, garantía y límites de financiamiento."),
    "hipotecario": ReglasCredito("Hipotecario", "Definir cuota inicial, tasación, garantía y límites de financiamiento."),
    "empresarial": ReglasCredito("Empresarial", "Definir cobertura de deuda, estacionalidad, capital de trabajo y garantías."),
})
