"""Normalización del texto del corpus y lectura de la notación numérica del IISS.

Todas las funciones son puras y devuelven estructuras inmutables. Las marcas de
incertidumbre del editor (``ε``, ``†``, ``+``, ``some``, ``up to``) se conservan
como banderas: descartarlas convertiría estimaciones en falsa precisión.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Sufijos de magnitud usados en las tablas de economía de defensa.
SUFIJOS_MAGNITUD: dict[str, float] = {
    "qrn": 1e15,
    "trn": 1e12,
    "bn": 1e9,
    "m": 1e6,
}

#: Marca de estimación del IISS (épsilon).
MARCA_ESTIMADO = "ε"

_RE_IMAGEN = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_RE_SUP = re.compile(r"<(?P<tag>sup|sub)>(?P<contenido>.*?)</(?P=tag)>", re.DOTALL)
#: Una llamada a nota al pie es corta: '[a]', '†', '*', '1'. Un rótulo maquetado
#: como subíndice ('<sub>HELICOPTERS</sub>') no lo es, y hay que conservarlo.
_RE_LLAMADA_NOTA = re.compile(r"^[\[\(]?[a-z0-9†‡*§ ]{1,3}[\]\)]?$", re.IGNORECASE)
_RE_ETIQUETA_HTML = re.compile(r"</?(?:u|b|i|strong|em|br\s*/?)>", re.IGNORECASE)
_RE_ENFASIS = re.compile(r"[*_`]")
_RE_ESPACIOS = re.compile(r"\s+")
_RE_HEADING = re.compile(r"^(#{1,6})\s")

_RE_MAGNITUD = re.compile(
    rf"^(?P<eps>{MARCA_ESTIMADO})?\s*"
    r"(?P<num>-?[0-9][0-9,]*(?:\.[0-9]+)?)\s*"
    rf"(?P<suf>{'|'.join(SUFIJOS_MAGNITUD)})?$"
)

_RE_CANTIDAD = re.compile(
    rf"^(?P<hasta>up\s+to\s+)?(?P<eps>{MARCA_ESTIMADO})?\s*"
    r"(?P<num>[0-9][0-9,]*)\s*(?P<mas>\+)?$",
    re.IGNORECASE,
)

_INDETERMINADOS = frozenset({"some", "several", "a few", "n.k.", "nk"})
#: El volumen escribe NIL cuando la categoría existe pero está a cero.
_NULOS = frozenset({"nil", "none"})


@dataclass(frozen=True, slots=True)
class Magnitud:
    """Cifra económica ya convertida a unidades absolutas."""

    valor: float
    estimado: bool = False


@dataclass(frozen=True, slots=True)
class Cantidad:
    """Conteo de equipo o de personal, con las salvedades del editor."""

    valor: int | None = None
    estimado: bool = False
    minimo: bool = False
    maximo: bool = False
    indeterminado: bool = False


def _resolver_sup(coincidencia: re.Match[str]) -> str:
    contenido = coincidencia.group("contenido")
    return "" if _RE_LLAMADA_NOTA.match(contenido.strip()) else contenido


def limpiar_markdown(texto: str | None) -> str:
    """Quita imágenes, énfasis, HTML inline y notas al pie; colapsa espacios."""
    if not texto:
        return ""
    sin_imagenes = _RE_IMAGEN.sub("", texto)
    sin_sup = _RE_SUP.sub(_resolver_sup, sin_imagenes)
    sin_html = _RE_ETIQUETA_HTML.sub("", sin_sup)
    sin_enfasis = _RE_ENFASIS.sub("", sin_html)
    return _RE_ESPACIOS.sub(" ", sin_enfasis).strip()


def nivel_heading(md: str | None) -> int:
    """Devuelve el nivel del encabezado markdown, o 0 si la línea no lo es."""
    if not md:
        return 0
    coincidencia = _RE_HEADING.match(md.lstrip())
    return len(coincidencia.group(1)) if coincidencia else 0


def parsear_magnitud(texto: str | None) -> Magnitud | None:
    """Convierte ``"34.6trn"`` o ``"ε8.27bn"`` en su valor absoluto."""
    limpio = limpiar_markdown(texto)
    if not limpio:
        return None
    coincidencia = _RE_MAGNITUD.match(limpio)
    if not coincidencia:
        return None
    base = float(coincidencia.group("num").replace(",", ""))
    factor = SUFIJOS_MAGNITUD.get(coincidencia.group("suf") or "", 1.0)
    return Magnitud(valor=base * factor, estimado=bool(coincidencia.group("eps")))


def parsear_cantidad(texto: str | None) -> Cantidad | None:
    """Lee un conteo del inventario preservando las salvedades del IISS."""
    limpio = limpiar_markdown(texto)
    if not limpio:
        return None
    if limpio.lower() in _NULOS:
        return Cantidad(valor=0)
    if limpio.lower() in _INDETERMINADOS:
        return Cantidad(indeterminado=True)
    coincidencia = _RE_CANTIDAD.match(limpio)
    if not coincidencia:
        return None
    return Cantidad(
        valor=int(coincidencia.group("num").replace(",", "")),
        estimado=bool(coincidencia.group("eps")),
        minimo=bool(coincidencia.group("mas")),
        maximo=bool(coincidencia.group("hasta")),
    )
