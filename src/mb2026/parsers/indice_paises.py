"""Índice de países: Tabla 11 (entradas con página) y Tabla 10 (códigos)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from mb2026.corpus import Item
from mb2026.parsers.localizar import (
    PREFIJO_TABLA_REFERENCIA,
    indice_de_ancla,
    tablas_tras,
)

ENCABEZADO_TABLA_11 = "Table 11 Index of countries and territories"
ENCABEZADO_TABLA_10 = "Table 10 Index of country/territory abbreviations"

#: Columnas de la Tabla 11 en el impreso.
COLUMNAS_TABLA_11 = 3

# "Korea, Democratic People's Republic of DPRK . . . . . .259"
_RE_ENTRADA = re.compile(
    r"^(?P<nombre>.+?)\s+(?P<codigo>[A-Z]{2,4})\s*[.\s]{2,}\s*(?P<pagina>\d{1,3})$"
)
# "AFG.......Afghanistan"  (la Tabla 10 llega como texto corrido)
_RE_CODIGO = re.compile(
    r"(?P<codigo>[A-Z]{2,4})\s*\.{2,}\s*(?P<nombre>[^.]+?)"
    r"(?=\s+[A-Z]{2,4}\s*\.{2,}|$)"
)


@dataclass(frozen=True, slots=True)
class EntradaIndice:
    """Un país con entrada propia y la página impresa donde empieza."""

    nombre: str
    codigo: str
    pagina_impresa: int


def parsear_indice_paises(items: tuple[Item, ...]) -> tuple[EntradaIndice, ...]:
    """Lee la Tabla 11: los países que tienen ficha y dónde empieza cada una."""
    inicio = indice_de_ancla(items, ENCABEZADO_TABLA_11, "Tabla 11")
    entradas: list[EntradaIndice] = []
    for tabla in tablas_tras(items, inicio, COLUMNAS_TABLA_11, ENCABEZADO_TABLA_11):
        for fila in tabla.filas:
            entradas.extend(
                _leer_celda(coincidencia)
                for celda in fila
                if (coincidencia := _RE_ENTRADA.match(celda))
            )
    return tuple(sorted(entradas, key=lambda e: (e.pagina_impresa, e.nombre)))


def _leer_celda(coincidencia: re.Match[str]) -> EntradaIndice:
    return EntradaIndice(
        nombre=coincidencia.group("nombre").strip(),
        codigo=coincidencia.group("codigo"),
        pagina_impresa=int(coincidencia.group("pagina")),
    )


def parsear_codigos_pais(items: tuple[Item, ...]) -> dict[str, str]:
    """Lee la Tabla 10: código → nombre, incluidos territorios sin ficha propia."""
    inicio = indice_de_ancla(items, ENCABEZADO_TABLA_10, "Tabla 10")
    codigos: dict[str, str] = {}
    for item in items[inicio + 1 :]:
        if item.es_encabezado and item.texto.startswith(PREFIJO_TABLA_REFERENCIA):
            break
        for coincidencia in _RE_CODIGO.finditer(item.texto):
            nombre = coincidencia.group("nombre").strip()
            if nombre:
                codigos.setdefault(coincidencia.group("codigo"), nombre)
    return codigos
