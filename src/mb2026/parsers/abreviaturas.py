"""Diccionario de abreviaturas del IISS (Tabla 8).

Es la piedra Rosetta de la notación abreviada de las secciones de datos:
sin ella, ``1 (10th) mech bde (1 armd recce bn...)`` no es interpretable.
"""

from __future__ import annotations

from dataclasses import dataclass

from mb2026.corpus import Item
from mb2026.parsers.localizar import indice_de_ancla, tablas_tras
from mb2026.texto import limpiar_markdown

ENCABEZADO_TABLA_8 = "Table 8 List of abbreviations"

#: La tabla imprime tres parejas sigla/definición por fila.
PAREJAS_POR_FILA = 3
COLUMNAS_TABLA_8 = PAREJAS_POR_FILA * 2


@dataclass(frozen=True, slots=True)
class Abreviatura:
    """Una sigla del volumen y su desarrollo."""

    sigla: str
    definicion: str


def parsear_abreviaturas(items: tuple[Item, ...]) -> tuple[Abreviatura, ...]:
    """Desdobla las columnas apareadas de la Tabla 8 en una lista plana."""
    inicio = indice_de_ancla(items, ENCABEZADO_TABLA_8, "Tabla 8")
    encontradas: dict[str, Abreviatura] = {}
    for tabla in tablas_tras(items, inicio, COLUMNAS_TABLA_8, ENCABEZADO_TABLA_8):
        for fila in tabla.filas:
            for pareja in range(PAREJAS_POR_FILA):
                abreviatura = _leer_pareja(fila, pareja)
                if abreviatura is not None:
                    encontradas.setdefault(abreviatura.sigla, abreviatura)
    return tuple(encontradas.values())


def _leer_pareja(fila: tuple[str, ...], pareja: int) -> Abreviatura | None:
    sigla = limpiar_markdown(fila[pareja * 2])
    definicion = limpiar_markdown(fila[pareja * 2 + 1])
    if not sigla or not definicion:
        return None
    return Abreviatura(sigla=sigla, definicion=definicion)
