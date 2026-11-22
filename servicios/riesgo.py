"""Escenarios educativos puros. No estima PD de personas ni habilita modelos."""
from dataclasses import dataclass
from decimal import Decimal
from servicios.finanzas import numero, entero

NOMBRES = ("Optimista", "Esperado", "Pesimista")
FUENTE = "Supuesto manual del analista para demostración"


@dataclass(frozen=True)
class EscenarioHipotetico:
    nombre: str
    pd: Decimal | None = None  # Porcentaje, no fracción.
    horizonte_meses: int | None = None
    lgd: Decimal | None = None
    exposicion: Decimal | None = None

    def __post_init__(self):
        if self.nombre not in NOMBRES:
            raise ValueError("Seleccione uno de los tres escenarios de demostración.")
        for campo in ("pd", "lgd", "exposicion"):
            valor = getattr(self, campo)
            if valor is not None:
                object.__setattr__(self, campo, numero(valor, campo.upper(), 0, 100 if campo != "exposicion" else Decimal("1e10")))
        if self.horizonte_meses is not None:
            object.__setattr__(self, "horizonte_meses", entero(self.horizonte_meses, "Horizonte en meses", 1, 1200))
        if self.pd is not None and self.horizonte_meses is None:
            raise ValueError("Indique el horizonte de evaluación de la PD supuesta.")

    @property
    def fuente(self):
        return FUENTE

    @property
    def naturaleza(self):
        return "HIPOTÉTICA · sin modelo validado"

    @property
    def no_incumplimiento(self):
        return None if self.pd is None else Decimal(100) - self.pd

    @property
    def perdida_esperada(self):
        if any(v is None for v in (self.pd, self.lgd, self.exposicion)):
            return None
        return self.exposicion * self.pd / 100 * self.lgd / 100


def advertencias(escenarios):
    completos = [e for e in escenarios if e.pd is not None]
    avisos = []
    if len({e.horizonte_meses for e in completos}) > 1:
        avisos.append("Los horizontes difieren: las probabilidades no son directamente comparables.")
    por_nombre = {e.nombre: e.pd for e in completos}
    presentes = [por_nombre[n] for n in NOMBRES if n in por_nombre]
    if presentes != sorted(presentes):
        avisos.append("Las PD no siguen el orden optimista ≤ esperado ≤ pesimista. Revisa los supuestos; no se reordenan automáticamente.")
    return avisos
