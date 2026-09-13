"""Localización de las tablas de referencia dentro del flujo de items.

Dos peculiaridades del corpus obligan a que esto sea más que un ``find``:
la Tabla 9 repite su encabezado en items consecutivos, y el título de la
Tabla 11 quedó absorbido dentro de la propia tabla.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from mb2026.corpus import Item

#: Prefijo común de los encabezados de las tablas de referencia.
PREFIJO_TABLA_REFERENCIA = "Table "


def indice_de_ancla(items: Iterable[Item], prefijo: str, etiqueta: str) -> int:
    """Posición del primer item cuyo texto de encabezado empieza por ``prefijo``.

    Lanza ``LookupError`` mencionando ``etiqueta`` si no aparece: es un fallo de
    integridad del corpus, no una condición normal.
    """
    for posicion, item in enumerate(items):
        if item.es_encabezado and item.texto.startswith(prefijo):
            return posicion
    raise LookupError(f"No se encontró la {etiqueta} en el corpus")


def tablas_tras(
    items: tuple[Item, ...], inicio: int, ancho: int, prefijo: str
) -> Iterator[Item]:
    """Tablas del ancho dado que pertenecen al ancla, incluida el ancla misma.

    La serie termina en el encabezado de otra tabla de referencia. Los items de
    texto intercalados (números de página sueltos, notas al pie) se atraviesan.
    """
    for item in items[inicio:]:
        if item.tipo == "table" and item.filas and len(item.filas[0]) == ancho:
            yield item
            continue
        if (
            item.es_encabezado
            and item.texto.startswith(PREFIJO_TABLA_REFERENCIA)
            and not item.texto.startswith(prefijo)
        ):
            return
