"""Bloque económico y demográfico de una ficha de país.

Cubre cuatro tablas que el volumen imprime juntas: economía de defensa, serie
real del presupuesto, población y pirámide de edad. Las tres últimas faltan en
parte de las fichas, y doce países no tienen datos macro en absoluto; la
ausencia se representa con valores vacíos, no con una excepción.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from mb2026.corpus import Item
from mb2026.texto import parsear_magnitud

#: Etiquetas del volumen normalizadas a nombres de indicador estables.
INDICADORES: dict[str, str] = {
    "GDP": "pib",
    "Real GDP growth": "crecimiento_real_pib",
    "Def bdgt": "presupuesto_defensa",
    "Def exp": "gasto_defensa",
    "FMA (US)": "ayuda_militar_us",
    "Sy Bdgt": "presupuesto_seguridad",
    # Errata del original.
    "Def bgt": "presupuesto_defensa",
}

#: Búsqueda insensible a espacios: el original imprime 'Real GDPgrowth'.
_INDICADORES_COMPACTOS = {
    "".join(etiqueta.split()).lower(): indicador
    for etiqueta, indicador in INDICADORES.items()
}

_RE_NOTA_AL_PIE = re.compile(r"\s*\[[a-z0-9]\]\s*$", re.IGNORECASE)
_RE_ANIO = re.compile(r"^(\d{4})$")
_RE_MONEDA = re.compile(r"^(?P<nombre>.*?)\s*(?P<codigo>[A-Z]{2,3}[a-zA-Z]?)$")
_RE_UNIDAD_SERIE = re.compile(r"\((?P<unidad>USD[a-z]+,\s*constant\s*\d{4})\)")
_RE_POBLACION = re.compile(r"^Population\s+(?P<total>[\d,]+)")
_RE_PORCENTAJE = re.compile(r"^(?P<valor>[\d.]+)\s*%$")

_CABECERA_SERIE = "Year"
#: La serie necesita la columna del año y la del valor.
_MIN_COLUMNAS_SERIE = 2
_CABECERA_POBLACION = "Population"
_CABECERA_EDAD = "Age"
_SEXOS = ("Male", "Female")


@dataclass(frozen=True, slots=True)
class Moneda:
    """Moneda nacional en la que el volumen expresa las cifras locales."""

    nombre: str
    codigo: str


@dataclass(frozen=True, slots=True)
class ValorEconomico:
    """Un indicador, en una unidad y un año."""

    anio: int
    indicador: str
    unidad: str
    valor: float | None
    estimado: bool = False


@dataclass(frozen=True, slots=True)
class TramoDemografico:
    """Porcentaje de población de un sexo en un rango de edad."""

    sexo: str
    rango: str
    porcentaje: float


@dataclass(frozen=True, slots=True)
class Economia:
    """Todo el bloque económico y demográfico de una ficha."""

    moneda: Moneda | None = None
    valores: tuple[ValorEconomico, ...] = field(default_factory=tuple)
    serie_real: tuple[tuple[int, float], ...] = field(default_factory=tuple)
    unidad_serie: str = ""
    poblacion: int | None = None
    demografia: tuple[TramoDemografico, ...] = field(default_factory=tuple)
    notas: tuple[str, ...] = field(default_factory=tuple)


def parsear_economia(items: tuple[Item, ...]) -> Economia:
    """Extrae el bloque económico y demográfico de los items de una ficha."""
    tablas = tuple(i for i in items if i.tipo == "table" and i.filas)
    tabla_economia = next((t for t in tablas if _es_tabla_economia(t)), None)
    serie, unidad = _leer_serie_real(tablas)
    return Economia(
        moneda=_leer_moneda(tabla_economia),
        valores=_leer_valores(tabla_economia),
        serie_real=serie,
        unidad_serie=unidad,
        poblacion=_leer_poblacion(items, tablas),
        demografia=_leer_demografia(tablas),
        notas=_leer_notas(items),
    )


def _normalizar(etiqueta: str) -> str:
    return _RE_NOTA_AL_PIE.sub("", " ".join(etiqueta.split())).strip()


def _indicador_de(etiqueta: str) -> str | None:
    """Indicador canónico de una etiqueta de fila, si la reconoce."""
    return _INDICADORES_COMPACTOS.get("".join(etiqueta.split()).lower())


def _es_tabla_economia(tabla: Item) -> bool:
    """Una tabla es la de economía si alguna de sus filas nombra un indicador."""
    return any(_indicador_de(_normalizar(fila[0])) for fila in tabla.filas)


def _leer_moneda(tabla: Item | None) -> Moneda | None:
    if tabla is None:
        return None
    celda = _normalizar(tabla.filas[0][0])
    coincidencia = _RE_MONEDA.match(celda)
    if not coincidencia or not coincidencia.group("nombre"):
        return None
    return Moneda(
        nombre=coincidencia.group("nombre").strip(),
        codigo=coincidencia.group("codigo"),
    )


def _columnas_de_anio(cabecera: tuple[str, ...]) -> tuple[tuple[int, int], ...]:
    return tuple(
        (columna, int(coincidencia.group(1)))
        for columna, celda in enumerate(cabecera)
        if (coincidencia := _RE_ANIO.match(celda.strip()))
    )


def _leer_valores(tabla: Item | None) -> tuple[ValorEconomico, ...]:
    if tabla is None:
        return ()
    anios = _columnas_de_anio(tabla.filas[0])
    if not anios:
        return ()

    valores: list[ValorEconomico] = []
    indicador = ""
    for fila in tabla.filas[1:]:
        etiqueta = _normalizar(fila[0])
        if etiqueta:
            indicador = _indicador_de(etiqueta) or etiqueta
        if not indicador:
            continue
        unidad = _normalizar(fila[1]) if len(fila) > 1 else ""
        valores.extend(_valores_de_fila(fila, anios, indicador, unidad))
    return tuple(valores)


def _valores_de_fila(
    fila: tuple[str, ...],
    anios: tuple[tuple[int, int], ...],
    indicador: str,
    unidad: str,
) -> tuple[ValorEconomico, ...]:
    leidos: list[ValorEconomico] = []
    for columna, anio in anios:
        if columna >= len(fila):
            continue
        magnitud = parsear_magnitud(fila[columna])
        if magnitud is None:
            continue
        leidos.append(
            ValorEconomico(
                anio=anio,
                indicador=indicador,
                unidad=unidad,
                valor=magnitud.valor,
                estimado=magnitud.estimado,
            )
        )
    return tuple(leidos)


def _leer_serie_real(
    tablas: tuple[Item, ...],
) -> tuple[tuple[tuple[int, float], ...], str]:
    tabla = next(
        (t for t in tablas if _normalizar(t.filas[0][0]) == _CABECERA_SERIE), None
    )
    if tabla is None or len(tabla.filas[0]) < _MIN_COLUMNAS_SERIE:
        return (), ""
    coincidencia = _RE_UNIDAD_SERIE.search(tabla.filas[0][1])
    unidad = " ".join(coincidencia.group("unidad").split()) if coincidencia else ""

    puntos: list[tuple[int, float]] = []
    for fila in tabla.filas[1:]:
        anio = _RE_ANIO.match(fila[0].strip())
        magnitud = parsear_magnitud(fila[1]) if len(fila) > 1 else None
        if anio and magnitud is not None:
            puntos.append((int(anio.group(1)), magnitud.valor))
    return tuple(puntos), unidad


def _leer_poblacion(items: tuple[Item, ...], tablas: tuple[Item, ...]) -> int | None:
    for tabla in tablas:
        fila = tabla.filas[0]
        if _normalizar(fila[0]) == _CABECERA_POBLACION and len(fila) > 1:
            magnitud = parsear_magnitud(fila[1])
            if magnitud is not None:
                return int(magnitud.valor)
    for item in items:
        coincidencia = _RE_POBLACION.match(item.texto)
        if coincidencia:
            return int(coincidencia.group("total").replace(",", ""))
    return None


def _leer_demografia(tablas: tuple[Item, ...]) -> tuple[TramoDemografico, ...]:
    tabla = next(
        (t for t in tablas if _normalizar(t.filas[0][0]) == _CABECERA_EDAD), None
    )
    if tabla is None:
        return ()
    rangos = tabla.filas[0][1:]
    tramos: list[TramoDemografico] = []
    for fila in tabla.filas[1:]:
        sexo = _normalizar(fila[0])
        if sexo not in _SEXOS:
            continue
        for rango, celda in zip(rangos, fila[1:], strict=False):
            coincidencia = _RE_PORCENTAJE.match(celda.strip())
            if coincidencia:
                tramos.append(
                    TramoDemografico(
                        sexo=sexo,
                        rango=rango.strip(),
                        porcentaje=float(coincidencia.group("valor")),
                    )
                )
    return tuple(tramos)


def _leer_notas(items: tuple[Item, ...]) -> tuple[str, ...]:
    return tuple(i.texto for i in items if i.texto.startswith("[") and "]" in i.texto[:5])
