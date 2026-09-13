"""Vocabulario del IISS traducido al del skill `nato-symbology`.

El volumen compone los tipos de unidad con modificadores delante de una función
base (`mech inf bn`, `armd recce bn`, `cbt engr bde`), así que el mapeo va por
tokens y no por cadenas completas. Cuando el tipo describe la plataforma en vez
de la función (`sqn with F-16 Fighting Falcon`), se recurre al rol, que el IISS
sí publica como vocabulario controlado.

Nada se adivina: los códigos de entidad salen de `lookup.mjs` del propio skill y
lo que no se reconoce se devuelve sin traducir para que el llamador lo reporte.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Escalón del IISS → alias de escalón del skill.
ESCALONES: dict[str, str] = {
    "army": "ejercito",
    "corps": "cuerpo",
    "div": "division",
    "bde": "brigada",
    "regt": "regimiento",
    "gp": "grupo",
    "bn": "batallon",
    "sqn": "escuadron",
    "coy": "compania",
    "bty": "bateria",
    "pl": "peloton",
    "det": "peloton",
    "sect": "seccion",
    "team": "equipo",
    "tp": "compania",
    "comd": "mando",
}

#: Token de función base → alias de tipo del skill.
FUNCIONES: dict[str, str] = {
    "inf": "infanteria",
    "mne": "infanteria anfibia",
    "amph": "anfibio",
    "mech": "infanteria mecanizada",
    "mr": "infanteria mecanizada",
    "armd": "blindado",
    "tk": "blindado",
    "cav": "reconocimiento",
    "recce": "reconocimiento",
    "arty": "artilleria de campana",
    "mor": "mortero",
    "mrl": "misil",
    "msl": "misil",
    "at": "antitanque",
    "ad": "defensa antiaerea",
    "ada": "defensa antiaerea",
    "sam": "defensa antiaerea",
    "engr": "ingenieros",
    "sigs": "transmisiones",
    "sf": "fuerzas especiales",
    "ops": "operaciones especiales",
    "aslt": "asalto aereo",
    "cdo": "operaciones especiales",
    "para": "infanteria",
    "ab": "infanteria",
    "mp": "policia militar",
    "sy": "seguridad",
    "gd": "seguridad",
    "log": "logistica",
    "spt": "apoyo de combate",
    "css": "apoyo de servicio de combate",
    "maint": "mantenimiento",
    "med": "sanidad",
    "medical": "sanidad",
    "tpt": "transporte",
    "nbc": "cbrn",
    "cbrn": "cbrn",
    "hel": "aviacion",
    "avn": "aviacion",
    "c2": "comando y control",
}

#: Códigos de entidad de 2525D para funciones sin alias en el skill.
#: Verificados con `lookup.mjs`; no se inventa ninguno.
ENTIDADES: dict[str, str] = {
    "int": "151000",
    "ew": "150500",
    "eod": "140800",
    "ranger": "122000",
    "uav": "121900",
}

#: (modificador, función base) → tipo, cuando el par cambia el símbolo.
COMPUESTOS: dict[tuple[str, str], str] = {
    ("mech", "inf"): "infanteria mecanizada",
    ("armd", "inf"): "infanteria mecanizada",
    ("mot", "inf"): "infanteria motorizada",
    ("air", "inf"): "asalto aereo",
    ("armd", "recce"): "reconocimiento blindado",
    ("mech", "recce"): "reconocimiento blindado",
    ("armd", "cav"): "reconocimiento blindado",
    ("mech", "cav"): "reconocimiento blindado",
    ("spec", "ops"): "operaciones especiales",
    ("air", "aslt"): "asalto aereo",
}

#: Rol del IISS → tipo, para unidades descritas por su plataforma.
ROLES_AEREOS: dict[str, str] = {
    "FIGHTER": "aviacion de ala fija",
    "FIGHTER/GROUND ATTACK": "aviacion de ala fija",
    "GROUND ATTACK": "aviacion de ala fija",
    "BOMBER": "aviacion de ala fija",
    "ISR": "aviacion de ala fija",
    "TANKER": "aviacion de ala fija",
    "TANKER/TRANSPORT": "aviacion de ala fija",
    "TRANSPORT": "aviacion de ala fija",
    "MARITIME PATROL": "aviacion de ala fija",
    "ANTI-SUBMARINE WARFARE": "aviacion de ala fija",
    "AIRBORNE EARLY WARNING & CONTROL": "aviacion de ala fija",
    "SEARCH & RESCUE": "aviacion de ala fija",
    "ELECTRONIC WARFARE": "aviacion de ala fija",
    "TRANSPORT HELICOPTER": "aviacion",
    "ATTACK HELICOPTER": "aviacion",
    "ATTACK/TRANSPORT HELICOPTER": "aviacion",
    "HELICOPTER": "aviacion",
    "MULTI-ROLE HELICOPTER": "aviacion",
}

#: Rol del IISS → tipo, para unidades terrestres cuyo tipo no dice la función.
ROLES_TERRESTRES: dict[str, str] = {
    "MANOEUVRE • Light": "infanteria",
    "MANOEUVRE • Mechanised": "infanteria mecanizada",
    "MANOEUVRE • Armoured": "blindado",
    "MANOEUVRE • Air Manoeuvre": "asalto aereo",
    "MANOEUVRE • Amphibious": "infanteria anfibia",
    "MANOEUVRE • Aviation": "aviacion",
    "COMBAT SUPPORT": "apoyo de combate",
    "COMBAT SERVICE SUPPORT": "apoyo de servicio de combate",
    "SPECIAL FORCES": "fuerzas especiales",
    "AIR DEFENCE": "defensa antiaerea",
    "SURFACE-TO-SURFACE MISSILE": "misil",
    "COMMAND": "comando y control",
}

#: Roles de aeronave no tripulada, que tienen entidad propia.
ROLES_UAV: frozenset[str] = frozenset(
    {"ISR UAV", "COMBAT/ISR UAV", "UAV", "CISR UAV", "COMBAT UAV"}
)

#: Marca con la que el IISS describe una unidad por su material.
MARCA_PLATAFORMA = " with "

#: Palabras que identifican a una fuerza aérea o de aviación. El IISS nombra
#: muchos de sus escuadrones solo por la aeronave, así que el servicio es la
#: única señal de que un rol ambiguo como TRANSPORT se refiere al aire.
_SERVICIOS_AEREOS = ("air", "aviation", "aerospace", "aviación", "aérea")

_RE_PARENTESIS = re.compile(r"\([^)]*\)")
_RE_NO_ALFA = re.compile(r"[^a-z0-9/ ]")
_ESCALONES_EN_TIPO = frozenset({*ESCALONES, "unit", "hq", "wg", "flt", "base", "fleet"})


@dataclass(frozen=True, slots=True)
class Traduccion:
    """Tipo del skill o código de entidad; vacíos si no se reconoció nada."""

    tipo: str = ""
    entidad: str = ""

    @property
    def reconocida(self) -> bool:
        return bool(self.tipo or self.entidad)


def escalon_de(echelon: str) -> str:
    """Alias de escalón del skill, o cadena vacía si no tiene equivalente."""
    return ESCALONES.get(echelon.strip().lower(), "")


def _tokens(tipo: str) -> list[str]:
    """Tokens de función del tipo, sin escalones ni glosas entre paréntesis."""
    sin_glosas = _RE_PARENTESIS.sub(" ", tipo).lower()
    limpio = _RE_NO_ALFA.sub(" ", sin_glosas)
    return [
        palabra
        for palabra in limpio.split()
        if palabra not in _ESCALONES_EN_TIPO
    ]


def _por_tokens(tokens: list[str]) -> Traduccion:
    for posicion in range(len(tokens) - 1, -1, -1):
        base = tokens[posicion]
        if posicion > 0:
            compuesto = COMPUESTOS.get((tokens[posicion - 1], base))
            if compuesto:
                return Traduccion(tipo=compuesto)
        if base in FUNCIONES:
            return Traduccion(tipo=FUNCIONES[base])
        if base in ENTIDADES:
            return Traduccion(entidad=ENTIDADES[base])
    return Traduccion()


def es_servicio_aereo(servicio: str) -> bool:
    """Si la fuerza opera aeronaves, un rol ambiguo se lee en clave aérea."""
    nombre = servicio.lower()
    return any(palabra in nombre for palabra in _SERVICIOS_AEREOS)


def _por_rol(rol: str, *, aereo: bool) -> Traduccion:
    etiqueta = rol.strip().upper()
    if etiqueta in ROLES_UAV:
        return Traduccion(entidad=ENTIDADES["uav"])
    if aereo and etiqueta in ROLES_AEREOS:
        return Traduccion(tipo=ROLES_AEREOS[etiqueta])
    terrestre = ROLES_TERRESTRES.get(rol.strip())
    return Traduccion(tipo=terrestre) if terrestre else Traduccion()


def tipo_de(tipo: str, rol: str, servicio: str = "") -> Traduccion:
    """Traduce el tipo de unidad del IISS, apoyándose en el rol si hace falta."""
    plataforma = MARCA_PLATAFORMA in f" {tipo.lower()} "
    if not plataforma:
        por_tokens = _por_tokens(_tokens(tipo))
        if por_tokens.reconocida:
            return por_tokens
    return _por_rol(rol, aereo=plataforma or es_servicio_aereo(servicio))
