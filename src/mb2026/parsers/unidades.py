"""Orden de batalla de una ficha (secciones FORCES BY ROLE).

El volumen escribe la estructura de fuerzas en una notación anidada:
``1 SF div (1 (1st) SF regt (1 spec ops bn, 1 cdo bn); 1 (2nd) SF regt (3 SF bn))``.
Los paréntesis cumplen dos papeles —designación y lista de subunidades— y se
distinguen por si el grupo contiene o no un escalón de mando.

Los renglones de la sección que no declaran ningún escalón conocido (prosa,
remisiones a otra ficha) no se descartan en silencio: se devuelven aparte para
que el informe de carga pueda mostrarlos.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from mb2026.corpus import Item
from mb2026.parsers.estructura import (
    CIERRES_DE_SECCION,
    ROTULO_CIERRE,
    ROTULO_EQUIPO,
    ROTULO_FUERZAS,
    ROTULO_ROL,
    ROTULO_SERVICIO,
    ROTULO_SUBROL,
    SECCION_EQUIPO,
    SECCION_FUERZAS,
    clasificar_rotulo,
    es_encabezado_de_fuerza,
    nombre_de_servicio,
    partir_respetando_parentesis,
    segmentos_en_negrita,
)
from mb2026.texto import Cantidad, parsear_cantidad

#: Escalones de mando de la Tabla 8. Su presencia distingue una lista de
#: subunidades de un simple calificativo entre paréntesis.
ESCALONES: tuple[str, ...] = (
    "army", "corps", "div", "bde", "regt", "bn", "coy", "bty", "pl", "sqn",
    "flt", "gp", "comd", "det", "tp", "sect", "wg", "unit", "cdo", "bde-sized",
    "base", "fleet", "sqn-sized", "team", "HQ",
)

#: Separador con el que se muestra la sub-clasificación de un rol.
SEPARADOR_ROL = " • "

_RE_ESCALON = re.compile(rf"\b({'|'.join(ESCALONES)})\b", re.IGNORECASE)
_RE_CANTIDAD_INICIAL = re.compile(r"^(?P<cantidad>ε?\d[\d,]*\+?|some|up to \d+)\s+")
_SEPARADORES = (";", ",")


@dataclass(frozen=True, slots=True)
class Unidad:
    """Una formación del orden de batalla, situada en su árbol."""

    orden: int
    padre: int | None
    profundidad: int
    servicio: str
    rol: str
    cantidad: Cantidad | None
    designacion: str
    tipo: str
    echelon: str
    texto_crudo: str
    pagina: int


@dataclass(frozen=True, slots=True)
class RenglonSinLeer:
    """Renglón de la sección que no declaraba ningún escalón reconocible."""

    texto: str
    pagina: int


@dataclass(frozen=True, slots=True)
class Orbat:
    """Lo leído y lo no leído de las secciones FORCES BY ROLE de una ficha."""

    unidades: tuple[Unidad, ...] = field(default_factory=tuple)
    sin_leer: tuple[RenglonSinLeer, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class _Estado:
    """Dónde está el recorrido dentro de la ficha."""

    servicio: str = ""
    rol: str = ""
    subrol: str = ""
    dentro: bool = False

    @property
    def rol_completo(self) -> str:
        return SEPARADOR_ROL.join(parte for parte in (self.rol, self.subrol) if parte)


@dataclass(frozen=True, slots=True)
class _Contexto:
    """Lo que no cambia mientras se desciende por un mismo renglón."""

    servicio: str
    rol: str
    pagina: int
    desplazamiento: int
    crudo: str


def parsear_unidades(items: tuple[Item, ...]) -> Orbat:
    """Recorre la ficha construyendo el orden de batalla de cada fuerza."""
    unidades: list[Unidad] = []
    sin_leer: list[RenglonSinLeer] = []
    estado = _Estado()

    for item in items:
        if item.es_encabezado:
            estado = _aplicar_encabezado(estado, item)
            continue
        for linea in item.lineas_md:
            estado, expresion = _aplicar_rotulo(estado, linea)
            if not estado.dentro or not expresion:
                continue
            leidas = _leer_linea(
                expresion,
                _Contexto(
                    servicio=estado.servicio,
                    rol=estado.rol_completo,
                    pagina=item.pagina,
                    desplazamiento=len(unidades),
                    crudo=expresion,
                ),
            )
            if leidas:
                unidades.extend(leidas)
            else:
                sin_leer.append(RenglonSinLeer(texto=expresion, pagina=item.pagina))
    return Orbat(unidades=tuple(unidades), sin_leer=tuple(sin_leer))


def _aplicar_encabezado(estado: _Estado, item: Item) -> _Estado:
    if item.texto == SECCION_FUERZAS:
        return _Estado(servicio=estado.servicio, dentro=True)
    if item.texto == SECCION_EQUIPO or item.texto in CIERRES_DE_SECCION:
        return _Estado(servicio=estado.servicio, rol=estado.rol, subrol=estado.subrol)
    if es_encabezado_de_fuerza(item.texto, item.nivel, en_roles=estado.dentro):
        return _Estado(servicio=nombre_de_servicio(item.texto))
    if not estado.dentro:
        return estado
    if item.texto.isupper():
        return _Estado(estado.servicio, item.texto, "", dentro=True)
    return _Estado(estado.servicio, estado.rol, item.texto, dentro=True)


def _aplicar_rotulo(estado: _Estado, linea: str) -> tuple[_Estado, str]:  # noqa: PLR0911
    """Actualiza el estado según el rótulo en negrita que abra el renglón.

    Devuelve además la expresión de unidades que queda por leer, vacía si el
    renglón era solo un marcador de sección.
    """
    segmentos = segmentos_en_negrita(linea)
    if not segmentos:
        return estado, linea.replace("*", "").strip()

    etiqueta, contenido = segmentos[0]
    clase = clasificar_rotulo(etiqueta, contenido, en_roles=estado.dentro)
    if clase == ROTULO_FUERZAS:
        return _Estado(servicio=estado.servicio, dentro=True), ""
    if clase in (ROTULO_EQUIPO, ROTULO_CIERRE):
        return _Estado(estado.servicio, estado.rol, estado.subrol), ""
    if clase == ROTULO_SERVICIO:
        return _Estado(nombre_de_servicio(f"{etiqueta} {contenido}".strip())), ""
    if clase == ROTULO_ROL:
        return _Estado(estado.servicio, etiqueta, "", dentro=estado.dentro), contenido
    if clase == ROTULO_SUBROL:
        nuevo = _Estado(estado.servicio, estado.rol, etiqueta, dentro=estado.dentro)
        return nuevo, contenido
    return estado, linea.replace("*", "").strip()


def _leer_linea(linea: str, contexto: _Contexto) -> tuple[Unidad, ...]:
    if not linea or not _RE_ESCALON.search(linea):
        return ()
    acumuladas: list[Unidad] = []
    _construir(linea, None, 0, contexto, acumuladas)
    return tuple(acumuladas)


def _construir(
    expresion: str,
    padre: int | None,
    profundidad: int,
    contexto: _Contexto,
    acumuladas: list[Unidad],
) -> None:
    for fragmento in partir_respetando_parentesis(expresion, _SEPARADORES):
        cantidad, designacion, tipo, hijas = _leer_unidad(fragmento)
        if not tipo:
            continue
        orden = contexto.desplazamiento + len(acumuladas)
        acumuladas.append(
            Unidad(
                orden=orden,
                padre=padre,
                profundidad=profundidad,
                servicio=contexto.servicio,
                rol=contexto.rol,
                cantidad=cantidad,
                designacion=designacion,
                tipo=tipo,
                echelon=_echelon_de(tipo),
                texto_crudo=contexto.crudo,
                pagina=contexto.pagina,
            )
        )
        if hijas:
            _construir(hijas, orden, profundidad + 1, contexto, acumuladas)


def _leer_unidad(fragmento: str) -> tuple[Cantidad | None, str, str, str]:
    """Descompone una unidad en cantidad, designación, tipo y subunidades."""
    resto = fragmento
    cabecera = _RE_CANTIDAD_INICIAL.match(resto)
    cantidad = parsear_cantidad(cabecera.group("cantidad")) if cabecera else None
    if cabecera:
        resto = resto[cabecera.end() :]

    glosas: list[str] = []
    hijas = ""
    tipo: list[str] = []
    for texto_plano, grupo in _recorrer_parentesis(resto):
        tipo.append(texto_plano)
        if grupo is None:
            continue
        if _RE_ESCALON.search(grupo) and _RE_CANTIDAD_INICIAL.match(grupo.strip()):
            hijas = grupo
        else:
            glosas.append(grupo.strip())
    designacion = "; ".join(glosa for glosa in glosas if glosa)
    return cantidad, designacion, " ".join(" ".join(tipo).split()), hijas


def _recorrer_parentesis(texto: str) -> tuple[tuple[str, str | None], ...]:
    """Alterna tramos de texto llano y contenidos de paréntesis de primer nivel."""
    tramos: list[tuple[str, str | None]] = []
    profundidad = 0
    llano: list[str] = []
    grupo: list[str] = []
    for caracter in texto:
        if caracter == "(":
            profundidad += 1
            if profundidad == 1:
                continue
        elif caracter == ")" and profundidad > 0:
            profundidad -= 1
            if profundidad == 0:
                tramos.append(("".join(llano).strip(), "".join(grupo)))
                llano, grupo = [], []
                continue
        (grupo if profundidad else llano).append(caracter)
    if llano or grupo:
        tramos.append(("".join(llano).strip(), "".join(grupo) or None))
    return tuple(tramos)


def _echelon_de(tipo: str) -> str:
    coincidencias = _RE_ESCALON.findall(tipo)
    return coincidencias[-1].lower() if coincidencias else ""
