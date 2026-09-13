"""Traducción de lo que escribe el usuario a las claves de la base.

La base guarda los nombres en inglés y los códigos del IISS; las preguntas
llegan en español. Aquí se resuelve país, dominio y región, con tolerancia a
acentos y mayúsculas, y sin adivinar: lo que no se reconoce falla con una
sugerencia.
"""

from __future__ import annotations

import difflib
import unicodedata

#: Nombres en español que difieren del inglés del volumen.
ALIAS_PAIS: dict[str, str] = {
    # América
    "Estados Unidos": "US", "EEUU": "US", "EE.UU.": "US", "Canadá": "CAN",
    "Brasil": "BRZ", "Perú": "PER", "México": "MEX", "Belice": "BLZ",
    "Haití": "HTI", "República Dominicana": "DOM", "Trinidad y Tobago": "TTO",
    "Antigua y Barbuda": "ATG", "Surinam": "SUR", "Guyana": "GUY",
    # Europa
    "Reino Unido": "UK", "Alemania": "GER", "Francia": "FRA", "España": "ESP",
    "Italia": "ITA", "Países Bajos": "NLD", "Holanda": "NLD", "Bélgica": "BEL",
    "Suiza": "CHE", "Suecia": "SWE", "Noruega": "NOR", "Dinamarca": "DNK",
    "Finlandia": "FIN", "Islandia": "ISL", "Irlanda": "IRL", "Grecia": "GRC",
    "Turquía": "TUR", "Polonia": "POL", "Chequia": "CZE",
    "República Checa": "CZE", "Eslovaquia": "SVK", "Eslovenia": "SVN",
    "Croacia": "CRO", "Hungría": "HUN", "Rumanía": "ROM", "Rumania": "ROM",
    "Bosnia y Herzegovina": "BIH", "Macedonia del Norte": "MKD",
    "Luxemburgo": "LUX", "Chipre": "CYP", "Ucrania": "UKR",
    # Rusia y Eurasia
    "Rusia": "RUS", "Bielorrusia": "BLR", "Moldavia": "MDA",
    "Azerbaiyán": "AZE", "Kazajistán": "KAZ", "Uzbekistán": "UZB",
    "Turkmenistán": "TKM", "Kirguistán": "KGZ", "Tayikistán": "TJK",
    # Asia y Pacífico
    "China": "PRC", "Japón": "JPN", "Corea del Sur": "ROK",
    "Corea del Norte": "DPRK", "Pakistán": "PAK", "Bangladés": "BGD",
    "Malasia": "MYS", "Singapur": "SGP", "Tailandia": "THA",
    "Filipinas": "PHL", "Camboya": "CAM", "Birmania": "MMR",
    "Taiwán": "ROC", "Nueva Zelanda": "NZL", "Afganistán": "AFG",
    "Brunéi": "BRN", "Maldivas": "MDV",
    "Timor Oriental": "TLS", "Papúa Nueva Guinea": "PNG", "Fiyi": "FJI",
    # Oriente Medio y Norte de África
    "Egipto": "EGY", "Argelia": "ALG", "Marruecos": "MOR", "Túnez": "TUN",
    "Libia": "LBY", "Sudán": "SDN", "Arabia Saudí": "SAU",
    "Arabia Saudita": "SAU", "Emiratos Árabes Unidos": "UAE",
    "Catar": "QTR", "Baréin": "BHR", "Omán": "OMN", "Irak": "IRQ",
    "Irán": "IRN", "Siria": "SYR", "Líbano": "LBN", "Jordania": "JOR",
    "Territorios Palestinos": "PT",
    # África subsahariana
    "Sudáfrica": "RSA", "Etiopía": "ETH", "Kenia": "KEN", "Camerún": "CMR",
    "Costa de Marfil": "CIV", "Zimbabue": "ZWE", "Botsuana": "BWA",
    "Ruanda": "RWA", "Malí": "MLI", "Níger": "NER", "Mauritania": "MRT",
    "Yibuti": "DJB", "Sudán del Sur": "SSD",
    "República del Congo": "COG", "República Democrática del Congo": "DRC",
    "Gabón": "GAB", "Guinea Ecuatorial": "EQG", "Mauricio": "MUS",
    "Cabo Verde": "CPV", "Guinea-Bisáu": "GNB", "Sierra Leona": "SLE",
    "Benín": "BEN", "Lesoto": "LSO", "Malaui": "MWI",
    "República Centroafricana": "CAR", "Tanzania": "TZA",
}

#: Agrupaciones de dominios por el lenguaje con el que se pregunta.
ALIAS_DOMINIO: dict[str, tuple[str, ...]] = {
    "aire": ("AIRCRAFT", "HELICOPTERS", "UNINHABITED AERIAL VEHICLES",
             "AIR-LAUNCHED MISSILES", "BOMBS"),
    "tierra": ("ARMOURED FIGHTING VEHICLES", "ARTILLERY",
               "ANTI-TANK/ANTI-INFRASTRUCTURE",
               "ENGINEERING & MAINTENANCE VEHICLES",
               "SURFACE-TO-SURFACE MISSILE LAUNCHERS"),
    "mar": ("SUBMARINES", "PRINCIPAL SURFACE COMBATANTS",
            "PATROL AND COASTAL COMBATANTS", "AMPHIBIOUS", "MINE WARFARE",
            "LOGISTICS AND SUPPORT", "COASTAL DEFENCE",
            "UNINHABITED MARITIME SYSTEMS", "UNINHABITED MARITIME PLATFORMS"),
    "defensa aerea": ("AIR DEFENCE", "MISSILE DEFENCE"),
    "espacio": ("SATELLITES",),
    "blindados": ("ARMOURED FIGHTING VEHICLES",),
    "artilleria": ("ARTILLERY",),
    "submarinos": ("SUBMARINES",),
    "drones": ("UNINHABITED AERIAL VEHICLES",),
    "aeronaves": ("AIRCRAFT",),
    "helicopteros": ("HELICOPTERS",),
}

_SINONIMOS_DOMINIO = {
    "aereo": "aire", "aerea": "aire", "aeroespacial": "aire",
    "naval": "mar", "maritimo": "mar", "marina": "mar",
    "terrestre": "tierra", "uav": "drones", "uas": "drones",
    "antiaerea": "defensa aerea", "defensa antiaerea": "defensa aerea",
    "satelites": "espacio",
}

#: Regiones tal como las nombra el volumen.
ALIAS_REGION: dict[str, str] = {
    "latam": "Latin America and the Caribbean",
    "america latina": "Latin America and the Caribbean",
    "latinoamerica": "Latin America and the Caribbean",
    "caribe": "Latin America and the Caribbean",
    "europa": "Europe",
    "asia": "Asia",
    "mena": "Middle East and North Africa",
    "medio oriente": "Middle East and North Africa",
    "oriente medio": "Middle East and North Africa",
    "africa": "Sub-Saharan Africa",
    "africa subsahariana": "Sub-Saharan Africa",
    "norteamerica": "North America",
    "america del norte": "North America",
    "rusia y eurasia": "Russia and Eurasia",
    "eurasia": "Russia and Eurasia",
}

_SUGERENCIAS = 3


def clave(texto: str) -> str:
    """Forma comparable: sin acentos, sin puntuación y en minúscula."""
    sin_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(
        "".join(c if c.isalnum() else " " for c in sin_acentos).lower().split()
    )


def _fallar(que: str, valor: str, candidatos: list[str]) -> LookupError:
    parecidos = difflib.get_close_matches(valor, candidatos, n=_SUGERENCIAS, cutoff=0.5)
    sugerencia = f" ¿Quisiste decir {', '.join(parecidos)}?" if parecidos else ""
    return LookupError(f"No reconozco {que} «{valor}».{sugerencia}")


def resolver_pais(valor: str, catalogo: dict[str, str]) -> str:
    """Código del IISS a partir de un código, un nombre inglés o uno español.

    ``catalogo`` es el mapa código → nombre que trae la base.
    """
    pedido = valor.strip()
    if pedido.upper() in catalogo:
        return pedido.upper()

    indice = {clave(nombre): codigo for codigo, nombre in catalogo.items()}
    indice.update({clave(alias): codigo for alias, codigo in ALIAS_PAIS.items()})
    encontrado = indice.get(clave(pedido))
    if encontrado is not None:
        return encontrado
    raise _fallar("el país", pedido, sorted(catalogo.values()) + sorted(ALIAS_PAIS))


def dominios_de(valor: str) -> tuple[str, ...]:
    """Dominios del inventario que cubre un término del usuario."""
    pedido = clave(valor)
    pedido = _SINONIMOS_DOMINIO.get(pedido, pedido)
    if pedido in ALIAS_DOMINIO:
        return ALIAS_DOMINIO[pedido]
    canonicos = {dominio for grupo in ALIAS_DOMINIO.values() for dominio in grupo}
    for dominio in canonicos:
        if clave(dominio) == pedido:
            return (dominio,)
    raise _fallar("el dominio", valor, sorted(canonicos) + sorted(ALIAS_DOMINIO))


def region_de(valor: str) -> str:
    """Región del volumen a partir de su nombre o de un alias en español."""
    pedido = clave(valor)
    if pedido in ALIAS_REGION:
        return ALIAS_REGION[pedido]
    for region in set(ALIAS_REGION.values()):
        if clave(region) == pedido:
            return region
    candidatos = sorted(set(ALIAS_REGION.values())) + sorted(ALIAS_REGION)
    raise _fallar("la región", valor, candidatos)
