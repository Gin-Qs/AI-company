"""Errores de la capa deterministica.

Cada error lleva un `codigo` estable. El codigo es lo que se escribe en la
bitacora y lo que un agente puede citar sin inventar texto: si manana cambia
el mensaje en espanol, el codigo sigue siendo el mismo.
"""

from __future__ import annotations


class ErrorDeServicio(Exception):
    """Raiz de todos los errores de la capa deterministica."""

    codigo = "SVC-ERROR"

    def __init__(self, mensaje: str, *, campo: str | None = None, **contexto: object) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.campo = campo
        self.contexto = contexto

    def as_dict(self) -> dict[str, object]:
        return {
            "codigo": self.codigo,
            "mensaje": self.mensaje,
            "campo": self.campo,
            **self.contexto,
        }

    def __str__(self) -> str:  # pragma: no cover - trivial
        campo = f" [{self.campo}]" if self.campo else ""
        return f"{self.codigo}{campo}: {self.mensaje}"


class EntradaFaltante(ErrorDeServicio):
    """Falta un dato obligatorio y no hay forma legitima de suponerlo.

    Regla dura de la Fase 0: un dato faltante detiene el calculo. No se
    sustituye por un promedio ni por un default silencioso, porque un costo
    por km inventado es peor que un costo por km ausente.
    """

    codigo = "SVC-INPUT-MISSING"


class ErrorDeValidacion(ErrorDeServicio):
    """Un dato existe pero es imposible o incoherente."""

    codigo = "SVC-INVALID"


class ErrorDeIntegridad(ErrorDeServicio):
    """Una referencia del catalogo apunta a algo que no existe."""

    codigo = "SVC-INTEGRITY"
