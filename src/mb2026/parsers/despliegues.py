"""Despliegues propios en el exterior y fuerzas extranjeras en el país.

Ambas secciones llegan como un párrafo corrido en el que los tramos se
distinguen por una marca tipográfica: el destino va en versales seguido de dos
puntos, y el país de origen es un nombre del índice del volumen.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from mb2026.corpus import Item
from mb2026.parsers.secciones import items_de_seccion
from mb2026.texto import Cantidad, parsear_cantidad

SECCION_DESPLIEGUE = "DEPLOYMENT"
SECCION_FUERZAS_EXTRANJERAS = "FOREIGN FORCES"

_SEPARADOR_ORGANIZACION = "•"

# Una palabra del destino: versales, sin cifras. "INDIA/PAKISTAN" cuenta como una.
_RE_PALABRA_DESTINO = re.compile(r"^[A-Z][A-Z'’.\-]*(?:/[A-Z][A-Z'’.\-]*)*$")
# La cifra de efectivos cierra su tramo, antes de un punto y coma o del final.
_RE_EFECTIVOS = re.compile(r"(?:^|\s)(?P<cantidad>ε?\d[\d,]*)\s*(?=;|$)")
_RE_INICIO_CIFRA = re.compile(r"\s*ε?\d")


@dataclass(frozen=True, slots=True)
class Despliegue:
    """Presencia propia en el exterior."""

    destino: str
    organizacion: str
    mision: str
    efectivos: Cantidad | None
    detalle: str


@dataclass(frozen=True, slots=True)
class FuerzaExtranjera:
    """Presencia de un tercer Estado en el país de la ficha."""

    origen: str
    efectivos: Cantidad | None
    detalle: str


def parsear_despliegues(items: tuple[Item, ...]) -> tuple[Despliegue, ...]:
    """Lee la sección DEPLOYMENT de una ficha."""
    texto = " ".join(i.texto for i in items_de_seccion(items, SECCION_DESPLIEGUE))
    if not texto:
        return ()

    cortes = _cortes_de_destino(texto)
    despliegues: list[Despliegue] = []
    for orden, (_inicio, destino, tras_destino) in enumerate(cortes):
        fin = cortes[orden + 1][0] if orden + 1 < len(cortes) else len(texto)
        despliegues.append(_leer_despliegue(destino, texto[tras_destino:fin].strip()))
    return tuple(despliegues)


def _cortes_de_destino(texto: str) -> list[tuple[int, str, int]]:
    """Localiza cada destino retrocediendo desde sus dos puntos.

    El destino va en versales, pero lo precede el nombre de la misión anterior,
    que a veces también lo está; el retroceso se detiene en la primera palabra
    con minúsculas o cifras, que nunca forma parte de un topónimo del volumen.
    """
    cortes: list[tuple[int, str, int]] = []
    for posicion, caracter in enumerate(texto):
        if caracter != ":":
            continue
        palabras = texto[:posicion].split(" ")
        tomadas = 0
        while tomadas < len(palabras) and _RE_PALABRA_DESTINO.match(
            palabras[len(palabras) - 1 - tomadas]
        ):
            tomadas += 1
        if not tomadas:
            continue
        destino = " ".join(palabras[len(palabras) - tomadas :])
        cortes.append((posicion - len(destino), destino, posicion + 1))
    return cortes


def _leer_despliegue(destino: str, detalle: str) -> Despliegue:
    partes = [p.strip() for p in detalle.split(_SEPARADOR_ORGANIZACION)]
    organizacion = partes[0] if len(partes) > 1 else ""
    # Algunas entradas encadenan mando y misión ('NATO • KFOR • Joint Enterprise'):
    # todo lo que sigue al primer separador forma la misión.
    resto = (
        f" {_SEPARADOR_ORGANIZACION} ".join(partes[1:]) if len(partes) > 1 else detalle
    )
    efectivos = _RE_EFECTIVOS.search(detalle)
    return Despliegue(
        destino=destino,
        organizacion=organizacion,
        mision=_RE_INICIO_CIFRA.split(resto)[0].strip(" ;,"),
        efectivos=parsear_cantidad(efectivos.group("cantidad")) if efectivos else None,
        detalle=detalle,
    )


def parsear_fuerzas_extranjeras(
    items: tuple[Item, ...], nombres_pais: frozenset[str]
) -> tuple[FuerzaExtranjera, ...]:
    """Lee la sección FOREIGN FORCES apoyándose en el índice de países.

    El párrafo no marca los tramos: la única señal fiable de que empieza uno es
    que aparezca el nombre de un país del volumen.
    """
    texto = " ".join(i.texto for i in items_de_seccion(items, SECCION_FUERZAS_EXTRANJERAS))
    if not texto:
        return ()

    cortes = sorted(_ocurrencias_de_pais(texto, nombres_pais))
    fuerzas: list[FuerzaExtranjera] = []
    for orden, (inicio, nombre) in enumerate(cortes):
        fin = cortes[orden + 1][0] if orden + 1 < len(cortes) else len(texto)
        detalle = texto[inicio + len(nombre) : fin].strip()
        efectivos = _RE_EFECTIVOS.search(detalle)
        fuerzas.append(
            FuerzaExtranjera(
                origen=nombre,
                efectivos=parsear_cantidad(efectivos.group("cantidad"))
                if efectivos
                else None,
                detalle=detalle[: efectivos.start()].strip() if efectivos else detalle,
            )
        )
    return tuple(fuerzas)


def _ocurrencias_de_pais(
    texto: str, nombres_pais: frozenset[str]
) -> list[tuple[int, str]]:
    """Posiciones donde empieza el nombre de un país, sin solapamientos."""
    encontradas = sorted(
        (coincidencia.start(), nombre)
        for nombre in nombres_pais
        for coincidencia in re.finditer(rf"(?<!\w){re.escape(nombre)}(?!\w)", texto)
    )
    encontradas.sort(key=lambda par: (par[0], -len(par[1])))

    sin_solape: list[tuple[int, str]] = []
    limite = -1
    for inicio, nombre in encontradas:
        if inicio >= limite:
            sin_solape.append((inicio, nombre))
            limite = inicio + len(nombre)
    return sin_solape
