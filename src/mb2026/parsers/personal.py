"""Efectivos declarados en una ficha de país.

El volumen los imprime en dos renglones (``ACTIVE`` y ``RESERVE``) con el total,
el desglose por fuerza entre paréntesis y, al final del renglón de activos, la
gendarmería. Los tres se normalizan a la misma estructura.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from mb2026.corpus import Item
from mb2026.texto import Cantidad, parsear_cantidad

CATEGORIA_ACTIVO = "activo"
CATEGORIA_RESERVA = "reserva"
CATEGORIA_GENDARMERIA = "gendarmeria"

#: Nombre del componente que representa el agregado de la categoría.
TOTAL = "Total"

_PREFIJOS = {"ACTIVE": CATEGORIA_ACTIVO, "RESERVE": CATEGORIA_RESERVA}
_MARCA_CONSCRIPCION = "Conscript liability"

# "ACTIVE 285,000 ..." / "ACTIVE NIL ..." / "RESERVE ε600,000 ..."
_RE_ENCABEZADO = re.compile(
    r"^(?P<categoria>ACTIVE|RESERVE)\s+(?P<total>NIL|n\.k\.|ε?[\d,]+)",
    re.IGNORECASE,
)
# "Gendarmerie & Paramilitary 165,050" o "Paramilitary 4,300", al final del renglón
_RE_GENDARMERIA = re.compile(
    r"(?:Gendarmerie\s*&\s*)?Paramilitary\s+(?P<cantidad>ε?[\d,]+)"
)
# Los países sin fuerzas armadas no imprimen renglón ACTIVE: la gendarmería
# aparece sola, como encabezado de su propia sección.
_RE_GENDARMERIA_SUELTA = re.compile(
    r"^(?:Gendarmerie\s*&\s*)?Paramilitary\s+(?P<cantidad>ε?[\d,]+)\s*$"
)
# "Army 206,400" / "Air/AD Aviation Forces (Joint) 1,100"
_RE_COMPONENTE = re.compile(
    r"(?P<nombre>[A-Za-z][A-Za-z/&'’\- ]*(?:\([^()\d]*\))?[A-Za-z/&'’\- ]*?)\s*"
    r"(?P<cantidad>ε?\d[\d,]*)"
)


@dataclass(frozen=True, slots=True)
class Efectivo:
    """Personal de un componente dentro de una categoría."""

    categoria: str
    componente: str
    cantidad: Cantidad


@dataclass(frozen=True, slots=True)
class Personal:
    """Los efectivos de una ficha y la nota de servicio obligatorio."""

    efectivos: tuple[Efectivo, ...] = field(default_factory=tuple)
    conscripcion: str = ""


def parsear_personal(items: tuple[Item, ...]) -> Personal:
    """Lee los renglones de efectivos de una ficha de país."""
    efectivos: list[Efectivo] = []
    conscripcion = ""
    suelta: Efectivo | None = None
    for item in items:
        texto = item.texto
        if texto.startswith(_MARCA_CONSCRIPCION) and not conscripcion:
            conscripcion = texto
            continue
        coincidencia = _RE_ENCABEZADO.match(texto)
        if coincidencia:
            efectivos.extend(_leer_renglon(texto, coincidencia))
            continue
        if suelta is None:
            suelta = _leer_gendarmeria_suelta(texto)

    if suelta is not None and not any(
        e.categoria == CATEGORIA_GENDARMERIA for e in efectivos
    ):
        efectivos.append(suelta)
    return Personal(efectivos=tuple(efectivos), conscripcion=conscripcion)


def _leer_gendarmeria_suelta(texto: str) -> Efectivo | None:
    coincidencia = _RE_GENDARMERIA_SUELTA.match(texto)
    if not coincidencia:
        return None
    cantidad = parsear_cantidad(coincidencia.group("cantidad"))
    return Efectivo(CATEGORIA_GENDARMERIA, TOTAL, cantidad) if cantidad else None


def _leer_renglon(texto: str, coincidencia: re.Match[str]) -> tuple[Efectivo, ...]:
    categoria = _PREFIJOS[coincidencia.group("categoria").upper()]
    total = parsear_cantidad(coincidencia.group("total"))
    leidos: list[Efectivo] = []
    if total is not None:
        leidos.append(Efectivo(categoria, TOTAL, total))

    resto = texto[coincidencia.end() :]
    desglose, cola = _separar_desglose(resto)
    leidos.extend(
        Efectivo(categoria, nombre, cantidad)
        for nombre, cantidad in _leer_componentes(desglose)
    )

    if categoria == CATEGORIA_ACTIVO:
        gendarmeria = _RE_GENDARMERIA.search(cola)
        if gendarmeria:
            cantidad = parsear_cantidad(gendarmeria.group("cantidad"))
            if cantidad is not None:
                leidos.append(Efectivo(CATEGORIA_GENDARMERIA, TOTAL, cantidad))
    return tuple(leidos)


def _separar_desglose(resto: str) -> tuple[str, str]:
    """Extrae el primer grupo de paréntesis balanceado y lo que queda tras él.

    Los nombres de componente pueden llevar paréntesis propios
    ('Air/AD Aviation Forces (Joint)'), así que no sirve una expresión regular.
    """
    inicio = resto.find("(")
    if inicio < 0:
        return "", resto
    profundidad = 0
    for posicion in range(inicio, len(resto)):
        if resto[posicion] == "(":
            profundidad += 1
        elif resto[posicion] == ")":
            profundidad -= 1
            if profundidad == 0:
                return resto[inicio + 1 : posicion], resto[posicion + 1 :]
    return resto[inicio + 1 :], ""


def _leer_componentes(desglose: str) -> tuple[tuple[str, Cantidad], ...]:
    componentes: list[tuple[str, Cantidad]] = []
    for coincidencia in _RE_COMPONENTE.finditer(desglose):
        nombre = coincidencia.group("nombre").strip(" ,;")
        cantidad = parsear_cantidad(coincidencia.group("cantidad"))
        if nombre and cantidad is not None:
            componentes.append((nombre, cantidad))
    return tuple(componentes)
