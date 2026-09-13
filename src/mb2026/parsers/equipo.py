"""Inventario de equipo de una ficha (secciones EQUIPMENT BY TYPE).

El volumen no marca la jerarquía con sangrías sino con negritas: el primer
rótulo en negrita de un renglón es la categoría y los siguientes son
subcategorías del mismo renglón. Cada sistema conserva su renglón de origen,
porque la notación admite variantes que ninguna regla cubre por completo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from mb2026.corpus import Item
from mb2026.parsers.estructura import (
    CIERRES_DE_SECCION,
    DOMINIO_POR_CATEGORIA,
    DOMINIOS_DE_EQUIPO,
    SECCION_EQUIPO,
    SECCION_FUERZAS,
    es_encabezado_de_fuerza,
    es_servicio_en_linea,
    nombre_de_servicio,
    partir_respetando_parentesis,
    partir_rotulo,
    segmentos_en_negrita,
)
from mb2026.texto import Cantidad, parsear_cantidad

#: Marca con la que el IISS señala equipo de operatividad dudosa.
MARCA_DUDOSO = "†"

_SEPARADOR_SISTEMAS = ";"
#: Separador con el que el volumen encadena niveles dentro de un mismo rótulo.
_SEPARADOR_NIVEL = " • "
#: El volumen encadena los niveles de una misma línea con viñetas.
_VINETA = "•"
_RE_TOTAL_CON_LISTA = re.compile(r"^(?P<total>ε?[\d,]+\+?)\s*:\s*(?P<resto>.*)$")
_RE_SOLO_TOTAL = re.compile(r"^(?P<total>ε?[\d,]+\+?)$")
# La cantidad exige un espacio detrás: sin él, '9K31 Strela-1' se leería como
# nueve unidades de un sistema llamado 'K31'.
_RE_SISTEMA = re.compile(
    r"^(?:(?P<cantidad>ε?\d[\d,]*\+?|some|up to \d[\d,]*)\s+)?(?P<nombre>.+)$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class _Estado:
    """Dónde está el recorrido dentro de la ficha."""

    servicio: str = ""
    dominio: str = ""
    grupo: str = ""
    dentro: bool = False
    en_roles: bool = False


@dataclass(frozen=True, slots=True)
class Equipo:
    """Un sistema del inventario, situado en su jerarquía y en su página."""

    servicio: str
    dominio: str
    grupo: str
    categoria: str
    subcategoria: str
    sistema: str
    cantidad: Cantidad | None
    total_categoria: Cantidad | None
    dudoso: bool
    texto_crudo: str
    pagina: int


def parsear_equipo(items: tuple[Item, ...]) -> tuple[Equipo, ...]:
    """Recorre la ficha acumulando el inventario de cada fuerza."""
    equipos: list[Equipo] = []
    estado = _Estado()

    for item in items:
        if item.es_encabezado:
            estado = _aplicar_encabezado(estado, item)
            continue
        for linea in item.lineas_md:
            estado, nuevos = _leer_linea(linea, estado, item.pagina)
            equipos.extend(nuevos)
    return tuple(equipos)


def _aplicar_encabezado(estado: _Estado, item: Item) -> _Estado:
    if item.texto == SECCION_EQUIPO:
        return _Estado(servicio=estado.servicio, dentro=True)
    if item.texto == SECCION_FUERZAS:
        return _Estado(servicio=estado.servicio, en_roles=True)
    if item.texto in CIERRES_DE_SECCION:
        return _Estado(servicio=estado.servicio)
    if es_encabezado_de_fuerza(item.texto, item.nivel, en_roles=estado.en_roles):
        return _Estado(servicio=nombre_de_servicio(item.texto))
    if estado.dentro:
        return _con_rotulo(estado, item.texto)
    return estado


def _con_rotulo(estado: _Estado, rotulo: str) -> _Estado:
    """Sitúa un rótulo de inventario en su nivel: dominio o grupo dentro de él.

    'ARTILLERY 9,580' es un dominio; 'MSL' o 'CORVETTES 6', que aparecen bajo
    uno, son un nivel intermedio que no debe sustituirlo.
    """
    niveles = partir_rotulo(rotulo)
    if not niveles:
        return estado
    if niveles[0] in DOMINIOS_DE_EQUIPO:
        return _Estado(
            estado.servicio, niveles[0], _SEPARADOR_NIVEL.join(niveles[1:]), dentro=True
        )
    return _Estado(
        estado.servicio, estado.dominio, _SEPARADOR_NIVEL.join(niveles), dentro=True
    )


# Un retorno por caso es la forma más legible de un despacho sobre un conjunto
# cerrado de rótulos; de ahí el noqa a la regla de "demasiados return".
def _leer_linea(  # noqa: PLR0911
    linea: str, estado: _Estado, pagina: int
) -> tuple[_Estado, tuple[Equipo, ...]]:
    segmentos = segmentos_en_negrita(linea)
    if not segmentos:
        return estado, ()

    etiqueta, contenido = segmentos[0]
    if etiqueta == SECCION_EQUIPO:
        return _Estado(servicio=estado.servicio, dentro=True), ()
    if etiqueta == SECCION_FUERZAS:
        return _Estado(servicio=estado.servicio, en_roles=True), ()
    if etiqueta in CIERRES_DE_SECCION:
        return _Estado(servicio=estado.servicio), ()
    if es_servicio_en_linea(
        etiqueta, contenido, len(segmentos), en_roles=estado.en_roles
    ):
        return _Estado(servicio=nombre_de_servicio(etiqueta)), ()
    if not estado.dentro:
        return estado, ()
    if len(segmentos) == 1 and not contenido:
        return _con_rotulo(estado, etiqueta), ()

    niveles = partir_rotulo(etiqueta)
    if niveles and niveles[0] in DOMINIOS_DE_EQUIPO:
        estado = _Estado(estado.servicio, niveles[0], "", dentro=True)
        # Si el rótulo encadenaba más niveles ('AIRCRAFT • TPT'), el resto sigue
        # siendo la categoría del renglón y conserva su contenido.
        resto = _SEPARADOR_NIVEL.join(niveles[1:])
        segmentos = ((resto, contenido), *segmentos[1:]) if resto else segmentos[1:]
        if not segmentos:
            return estado, ()

    return estado, _leer_segmentos(segmentos, estado, linea, pagina)


def _leer_segmentos(
    segmentos: tuple[tuple[str, str], ...],
    estado: _Estado,
    linea: str,
    pagina: int,
) -> tuple[Equipo, ...]:
    categoria = segmentos[0][0]
    dominio = DOMINIO_POR_CATEGORIA.get(categoria, estado.dominio)
    equipos: list[Equipo] = []
    for orden, (etiqueta, contenido) in enumerate(segmentos):
        total, resto = _separar_total(contenido)
        sistemas = _leer_sistemas(resto)
        subcategoria = "" if orden == 0 else etiqueta
        if not sistemas:
            if total is None:
                continue
            sistemas = ((None, ""),)
        equipos.extend(
            Equipo(
                servicio=estado.servicio,
                dominio=dominio,
                grupo=estado.grupo,
                categoria=categoria,
                subcategoria=subcategoria,
                sistema=nombre.replace(MARCA_DUDOSO, "").strip(),
                cantidad=cantidad,
                total_categoria=total,
                dudoso=MARCA_DUDOSO in nombre,
                texto_crudo=linea,
                pagina=pagina,
            )
            for cantidad, nombre in sistemas
        )
    return tuple(equipos)


def _separar_total(contenido: str) -> tuple[Cantidad | None, str]:
    """Distingue el total declarado de la lista de sistemas.

    El total solo es explícito cuando lo siguen dos puntos; un número suelto al
    frente pertenece al primer sistema, salvo que sea todo el contenido.
    """
    con_lista = _RE_TOTAL_CON_LISTA.match(contenido)
    if con_lista:
        return parsear_cantidad(con_lista.group("total")), con_lista.group("resto")
    solo = _RE_SOLO_TOTAL.match(contenido)
    if solo:
        return parsear_cantidad(solo.group("total")), ""
    primero = _RE_SISTEMA.match(contenido)
    if primero and primero.group("cantidad") and _SEPARADOR_SISTEMAS not in contenido:
        return parsear_cantidad(primero.group("cantidad")), contenido
    return None, contenido


def _leer_sistemas(resto: str) -> tuple[tuple[Cantidad | None, str], ...]:
    sistemas: list[tuple[Cantidad | None, str]] = []
    for parte in partir_respetando_parentesis(resto, (_SEPARADOR_SISTEMAS,)):
        limpia = parte.strip(f" ,{_VINETA}")
        if not any(caracter.isalnum() for caracter in limpia):
            continue
        coincidencia = _RE_SISTEMA.match(limpia)
        if not coincidencia:
            continue
        nombre = coincidencia.group("nombre").strip()
        if not nombre:
            continue
        sistemas.append((parsear_cantidad(coincidencia.group("cantidad")), nombre))
    return tuple(sistemas)
