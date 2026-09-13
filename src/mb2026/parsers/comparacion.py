"""Comparación internacional de presupuestos y personal (Tabla 9).

La tabla es la única fuente ya tabular que cubre los 174 países. Se normaliza a
dos series largas: gasto por año y personal (que el IISS solo publica para el
año más reciente).
"""

from __future__ import annotations

from dataclasses import dataclass

from mb2026.corpus import Item
from mb2026.parsers.localizar import indice_de_ancla, tablas_tras

ENCABEZADO_TABLA_9 = "Table 9 International comparisons"

#: Años de las series de gasto, en el orden en que aparecen las columnas.
ANIOS_GASTO: tuple[int, ...] = (2023, 2024, 2025)
#: El IISS publica personal solo para el año de cierre.
ANIO_PERSONAL = 2025

COLUMNAS_TABLA_9 = 13
_COL_PAIS = 0
_COL_PRESUPUESTO = 1
_COL_PER_CAPITA = 4
_COL_PCT_PIB = 7
_COL_ACTIVOS = 10
_COL_RESERVISTAS = 11
_COL_GENDARMERIA = 12

#: Cada tabla de la serie repite su cabecera en la primera fila; se valida ahí.
_CABECERA_ESPERADA: tuple[tuple[int, str], ...] = (
    (_COL_PRESUPUESTO, "Defence Budget"),
    (_COL_PER_CAPITA, "per capita"),
    (_COL_PCT_PIB, "% of GDP"),
    (_COL_ACTIVOS, "Active Armed Forces"),
    (_COL_RESERVISTAS, "Reservists"),
    (_COL_GENDARMERIA, "Gendarmerie"),
)

_ETIQUETAS_AGREGADO = ("Total", "Average")


@dataclass(frozen=True, slots=True)
class FilaGasto:
    """Gasto de defensa de un país en un año."""

    pais: str
    region: str
    anio: int
    presupuesto_usd_m: float | None
    per_capita_usd: float | None
    pct_pib: float | None
    es_agregado: bool = False


@dataclass(frozen=True, slots=True)
class FilaPersonal:
    """Efectivos de un país, en miles."""

    pais: str
    region: str
    anio: int
    activos_miles: float | None
    reservistas_miles: float | None
    gendarmeria_miles: float | None
    es_agregado: bool = False


@dataclass(frozen=True, slots=True)
class ComparacionInternacional:
    """Las dos series normalizadas que produce la Tabla 9."""

    gasto: tuple[FilaGasto, ...]
    personal: tuple[FilaPersonal, ...]


def parsear_comparacion(items: tuple[Item, ...]) -> ComparacionInternacional:
    """Normaliza la Tabla 9 a series largas de gasto y de personal."""
    inicio = indice_de_ancla(items, ENCABEZADO_TABLA_9, "Tabla 9")
    gasto: list[FilaGasto] = []
    personal: list[FilaPersonal] = []
    region = ""

    for tabla in tablas_tras(items, inicio, COLUMNAS_TABLA_9, ENCABEZADO_TABLA_9):
        _validar_cabecera(tabla.filas[0])
        for fila in tabla.filas[1:]:
            etiqueta = fila[_COL_PAIS].strip()
            if not etiqueta:
                continue
            if _es_cabecera_de_region(fila):
                region = etiqueta
                continue
            agregado = _es_agregado(etiqueta)
            gasto.extend(_filas_de_gasto(fila, etiqueta, region, agregado=agregado))
            personal.append(_fila_de_personal(fila, etiqueta, region, agregado=agregado))

    return ComparacionInternacional(gasto=tuple(gasto), personal=tuple(personal))


def _numero(celda: str) -> float | None:
    limpia = celda.replace(",", "").strip()
    if not limpia:
        return None
    try:
        return float(limpia)
    except ValueError:
        return None


def _sin_espacios(texto: str) -> str:
    return "".join(texto.split())


def _validar_cabecera(fila: tuple[str, ...]) -> None:
    """Comprueba que el layout de columnas es el esperado antes de leer datos.

    La comparación ignora los espacios: el corpus pierde algunos al cruzar de
    página ('Active ArmedForces', 'Defence Budget(current USDm)2023').
    """
    for columna, fragmento in _CABECERA_ESPERADA:
        if _sin_espacios(fragmento) not in _sin_espacios(fila[columna]):
            raise ValueError(
                f"cabecera inesperada en la Tabla 9: la columna {columna} "
                f"no contiene '{fragmento}' (dice '{fila[columna]}')"
            )


def _es_cabecera_de_region(fila: tuple[str, ...]) -> bool:
    return not any(celda.strip() for celda in fila[1:])


def _es_agregado(etiqueta: str) -> bool:
    return any(marca in etiqueta for marca in _ETIQUETAS_AGREGADO)


def _filas_de_gasto(
    fila: tuple[str, ...], pais: str, region: str, *, agregado: bool
) -> tuple[FilaGasto, ...]:
    return tuple(
        FilaGasto(
            pais=pais,
            region=region,
            anio=anio,
            presupuesto_usd_m=_numero(fila[_COL_PRESUPUESTO + desplazamiento]),
            per_capita_usd=_numero(fila[_COL_PER_CAPITA + desplazamiento]),
            pct_pib=_numero(fila[_COL_PCT_PIB + desplazamiento]),
            es_agregado=agregado,
        )
        for desplazamiento, anio in enumerate(ANIOS_GASTO)
    )


def _fila_de_personal(
    fila: tuple[str, ...], pais: str, region: str, *, agregado: bool
) -> FilaPersonal:
    return FilaPersonal(
        pais=pais,
        region=region,
        anio=ANIO_PERSONAL,
        activos_miles=_numero(fila[_COL_ACTIVOS]),
        reservistas_miles=_numero(fila[_COL_RESERVISTAS]),
        gendarmeria_miles=_numero(fila[_COL_GENDARMERIA]),
        es_agregado=agregado,
    )
