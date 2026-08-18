"""Supuestos: el rastro de todo lo que el servicio no recibio y tuvo que derivar."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

Fuente = Literal["entrada", "masterdata", "derivado", "parametro"]


@dataclass(frozen=True)
class Supuesto:
    """Un valor que el servicio no recibio explicitamente.

    La seccion 7.1 exige que todo entregable declare sus supuestos, y la 8 que
    toda cifra se pueda reconciliar contra su origen. Un servicio que rellena
    huecos en silencio rompe las dos.
    """

    campo: str
    valor: Decimal
    fuente: Fuente
    detalle: str

    def as_dict(self) -> dict[str, object]:
        return {
            "campo": self.campo,
            "valor": str(self.valor),
            "fuente": self.fuente,
            "detalle": self.detalle,
        }


@dataclass
class Supuestos:
    """Acumulador ordenado. El orden de registro es el orden de calculo."""

    items: list[Supuesto] = field(default_factory=list)

    def registrar(self, campo: str, valor: Decimal, fuente: Fuente, detalle: str) -> Decimal:
        self.items.append(Supuesto(campo=campo, valor=valor, fuente=fuente, detalle=detalle))
        return valor

    def __iter__(self):
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def as_list(self) -> list[dict[str, object]]:
        return [s.as_dict() for s in self.items]
