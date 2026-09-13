"""Corte del corpus en fichas de país.

El índice impreso (Tabla 11) dice qué países tienen ficha y en qué página
empieza cada una; aquí se localiza el encabezado correspondiente en el flujo de
items y se delimita el bloque que le pertenece.
"""

from __future__ import annotations

import re
import unicodedata
from bisect import bisect_right
from dataclasses import dataclass, field

from mb2026.corpus import Item
from mb2026.parsers.indice_paises import EntradaIndice

#: El parse numera las páginas del PDF; el impreso va una atrás.
DESFASE_PAGINA = 1

#: Primera página impresa de cada capítulo de datos regionales (índice del volumen).
INICIO_CAPITULOS: tuple[tuple[int, str], ...] = (
    (14, "North America"),
    (56, "Europe"),
    (160, "Russia and Eurasia"),
    (216, "Asia"),
    (322, "Middle East and North Africa"),
    (390, "Latin America and the Caribbean"),
    (450, "Sub-Saharan Africa"),
)

#: Primera página impresa de la sección de referencia: cierra el último capítulo.
PAGINA_INICIO_REFERENCIA = 525

_PAGINAS_CAPITULO = tuple(pagina for pagina, _ in INICIO_CAPITULOS)
_NOMBRES_CAPITULO = tuple(nombre for _, nombre in INICIO_CAPITULOS)

_RE_ENCABEZADO_PAIS = re.compile(r"^(?P<nombre>.+?)\s+(?P<codigo>[A-Z]{2,4})$")


@dataclass(frozen=True, slots=True)
class _Candidato:
    """Un encabezado del flujo que podría abrir la ficha de un país."""

    posicion: int
    pagina: int
    nombre: str


@dataclass(frozen=True, slots=True)
class FichaPais:
    """El bloque completo de items que el volumen dedica a un país."""

    codigo: str
    nombre: str
    region: str
    pagina_impresa: int
    pagina_json: int
    items: tuple[Item, ...] = field(default_factory=tuple)


def region_de_pagina(pagina_impresa: int) -> str:
    """Capítulo regional al que pertenece una página impresa."""
    posicion = bisect_right(_PAGINAS_CAPITULO, pagina_impresa)
    return _NOMBRES_CAPITULO[posicion - 1] if posicion else ""


def _limite_del_capitulo(pagina_impresa: int) -> int:
    """Primera página impresa que ya no pertenece al capítulo de esta página."""
    posicion = bisect_right(_PAGINAS_CAPITULO, pagina_impresa)
    if posicion < len(_PAGINAS_CAPITULO):
        return _PAGINAS_CAPITULO[posicion]
    return PAGINA_INICIO_REFERENCIA


def _clave(nombre: str) -> str:
    """Normaliza un nombre de país para comparar entre índice y encabezado.

    El corpus pierde espacios al cruzar de columna ('Trinidad andTobago') y
    alterna la acentuación, así que la comparación ignora ambos.
    """
    sin_acentos = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", sin_acentos.lower())


def _candidatos_por_codigo(items: tuple[Item, ...]) -> dict[str, list[_Candidato]]:
    """Indexa por código los encabezados con forma de ficha de país.

    El nombre se extrae aquí una sola vez: así el resto del módulo trabaja con
    datos ya validados en vez de volver a aplicar el mismo patrón.
    """
    candidatos: dict[str, list[_Candidato]] = {}
    for posicion, item in enumerate(items):
        if not item.es_encabezado:
            continue
        coincidencia = _RE_ENCABEZADO_PAIS.match(item.texto)
        if coincidencia:
            candidatos.setdefault(coincidencia.group("codigo"), []).append(
                _Candidato(posicion, item.pagina, coincidencia.group("nombre"))
            )
    return candidatos


def _localizar(
    entrada: EntradaIndice, candidatos: dict[str, list[_Candidato]]
) -> _Candidato:
    """Elige el encabezado de la ficha, desempatando por cercanía de página."""
    esperada = entrada.pagina_impresa + DESFASE_PAGINA
    clave_indice = _clave(entrada.nombre)
    coincidentes = [
        candidato
        for candidato in candidatos.get(entrada.codigo, ())
        if _clave(candidato.nombre) == clave_indice
    ]
    if not coincidentes:
        raise LookupError(
            f"No se localizó la ficha de {entrada.nombre} ({entrada.codigo}) "
            f"anunciada en la página {entrada.pagina_impresa}"
        )
    return min(coincidentes, key=lambda candidato: abs(candidato.pagina - esperada))


def _recortar_al_capitulo(
    bloque: tuple[Item, ...], pagina_impresa: int
) -> tuple[Item, ...]:
    """Corta el bloque donde empieza el capítulo siguiente.

    El último país de cada capítulo va seguido del análisis regional del
    siguiente, que no le pertenece.
    """
    limite = _limite_del_capitulo(pagina_impresa) + DESFASE_PAGINA
    return tuple(item for item in bloque if item.pagina < limite)


def segmentar_paises(
    items: tuple[Item, ...], indice: tuple[EntradaIndice, ...]
) -> tuple[FichaPais, ...]:
    """Reparte el flujo de items entre las fichas anunciadas en el índice."""
    candidatos = _candidatos_por_codigo(items)
    localizadas = [(entrada, _localizar(entrada, candidatos)) for entrada in indice]
    localizadas.sort(key=lambda par: par[1].posicion)
    _validar_cortes_unicos(localizadas)

    cortes = [candidato.posicion for _, candidato in localizadas] + [len(items)]
    return tuple(
        FichaPais(
            codigo=entrada.codigo,
            nombre=candidato.nombre,
            region=region_de_pagina(entrada.pagina_impresa),
            pagina_impresa=entrada.pagina_impresa,
            pagina_json=candidato.pagina,
            items=_recortar_al_capitulo(
                items[candidato.posicion + 1 : cortes[orden + 1]],
                entrada.pagina_impresa,
            ),
        )
        for orden, (entrada, candidato) in enumerate(localizadas)
    )


def _validar_cortes_unicos(
    localizadas: list[tuple[EntradaIndice, _Candidato]],
) -> None:
    """Dos fichas no pueden empezar en el mismo encabezado.

    Si ocurriera, una de ellas quedaría vacía sin que nada lo delatara.
    """
    vistas: dict[int, str] = {}
    for entrada, candidato in localizadas:
        previa = vistas.get(candidato.posicion)
        if previa is not None:
            raise LookupError(
                f"Las fichas de {previa} y {entrada.codigo} resuelven al mismo "
                f"encabezado (posición {candidato.posicion})"
            )
        vistas[candidato.posicion] = entrada.codigo
