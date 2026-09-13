"""Acotado de secciones dentro de una ficha de país."""

from __future__ import annotations

from collections.abc import Iterator

from mb2026.corpus import Item


def items_de_seccion(items: tuple[Item, ...], titulo: str) -> Iterator[Item]:
    """Items que siguen al encabezado ``titulo`` hasta el siguiente de igual rango.

    Las fichas alternan encabezados de varios niveles; una sección termina en el
    primer encabezado de nivel igual o superior al suyo.
    """
    nivel_seccion = 0
    dentro = False
    for item in items:
        if item.es_encabezado and item.texto == titulo:
            nivel_seccion = item.nivel
            dentro = True
            continue
        if not dentro:
            continue
        if item.es_encabezado and item.nivel <= nivel_seccion:
            return
        yield item
