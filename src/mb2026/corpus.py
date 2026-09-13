"""Lectura del corpus como un flujo lineal de items con número de página.

El parse de origen viene organizado por página. Aquí se aplana a una secuencia
única, se descartan encabezados, pies y titulillos de capítulo, y se conserva el
número de página de cada item para poder citar la fuente.

Los items de tipo ``image`` quedan fuera del flujo por diseño: son escudos,
banderas e infografías sin datos extraíbles, y su texto queda vacío al limpiar
el markdown decorativo.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from mb2026.texto import limpiar_markdown, nivel_heading

#: Titulillos que se repiten en el margen de cada página y no son contenido.
CHAPTER_RUNNING_HEADS: frozenset[str] = frozenset(
    {
        "North America",
        "Europe",
        "Russia and Eurasia",
        "Asia",
        "Middle East and North Africa",
        "Latin America and the Caribbean",
        "Sub-Saharan Africa",
        "Reference",
        "Defence and military analysis",
        "Global defence spending",
        "Contents",
    }
)

#: Tipos de item que nunca contienen contenido sustantivo.
TIPOS_DESCARTABLES: frozenset[str] = frozenset({"header", "footer"})

_MARCA_PIE = "THE MILITARY BALANCE"


@dataclass(frozen=True, slots=True)
class Item:
    """Un bloque del corpus, situado en su página de origen."""

    pagina: int
    tipo: str
    md: str
    texto: str
    nivel: int = 0
    filas: tuple[tuple[str, ...], ...] = field(default_factory=tuple)

    @property
    def es_encabezado(self) -> bool:
        return self.nivel > 0

    @property
    def lineas_md(self) -> tuple[str, ...]:
        """Renglones del item con el markdown intacto.

        Las secciones de inventario dependen de las negritas para distinguir la
        categoría del sistema, así que no se pueden leer del texto ya limpio.
        """
        return tuple(linea.strip() for linea in self.md.split("\n") if linea.strip())


def _normalizar_filas(crudas: object) -> tuple[tuple[str, ...], ...]:
    if not isinstance(crudas, list):
        return ()
    return tuple(
        tuple(limpiar_markdown(celda) if isinstance(celda, str) else "" for celda in fila)
        for fila in crudas
        if isinstance(fila, list)
    )


def _es_ruido(tipo: str, texto: str, *, tiene_filas: bool) -> bool:
    if tipo in TIPOS_DESCARTABLES:
        return True
    if tiene_filas:
        return False
    if not texto:
        return True
    if _MARCA_PIE in texto.upper():
        return True
    return texto in CHAPTER_RUNNING_HEADS


def _construir_item(pagina: int, crudo: dict[str, object]) -> Item | None:
    tipo = str(crudo.get("type") or "")
    md = str(crudo.get("md") or "")
    nivel = nivel_heading(md)
    texto = limpiar_markdown(md.lstrip("#") if nivel else md)
    filas = _normalizar_filas(crudo.get("rows"))
    if _es_ruido(tipo, texto, tiene_filas=bool(filas)):
        return None
    return Item(pagina=pagina, tipo=tipo, md=md, texto=texto, nivel=nivel, filas=filas)


def cargar_items(ruta: Path) -> tuple[Item, ...]:
    """Aplana el corpus a una secuencia de items limpios y ordenados por página."""
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el corpus en {ruta}")

    documento = json.loads(ruta.read_text(encoding="utf8"))
    if not isinstance(documento, dict):
        raise TypeError(f"El corpus {ruta} no es un objeto JSON")
    paginas = documento.get("pages")
    if not isinstance(paginas, list):
        raise TypeError(f"El corpus {ruta} no contiene una lista 'pages'")

    items: list[Item] = []
    for pagina in paginas:
        if not isinstance(pagina, dict):
            continue
        numero = pagina.get("page_number")
        if not isinstance(numero, int):
            continue
        for crudo in pagina.get("items") or []:
            if not isinstance(crudo, dict):
                continue
            item = _construir_item(numero, crudo)
            if item is not None:
                items.append(item)
    return tuple(items)
