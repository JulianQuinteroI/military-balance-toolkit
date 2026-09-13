"""Vocabulario estructural compartido por los parsers de ficha."""

from __future__ import annotations

import re

#: Títulos de sección que el volumen repite en todas las fichas.
SECCION_EQUIPO = "EQUIPMENT BY TYPE"
SECCION_FUERZAS = "FORCES BY ROLE"
SECCION_ORGANIZACION = "ORGANISATIONS BY SERVICE"
SECCION_CAPACIDADES = "Capabilities"

#: Encabezados que cierran cualquier sección de datos de una fuerza.
CIERRES_DE_SECCION: frozenset[str] = frozenset(
    {SECCION_FUERZAS, "DEPLOYMENT", "FOREIGN FORCES", SECCION_ORGANIZACION,
     SECCION_CAPACIDADES}
)

#: Viñeta con la que el volumen encadena niveles dentro de un renglón.
_VINETA = "•"
_RE_NEGRITA = re.compile(r"\*\*(?P<etiqueta>[^*]+?)\*\*")
_RE_SERVICIO = re.compile(
    r"^(?P<nombre>[A-Z][A-Za-z&’'\-/() ]*?)\s*(?:ε?[\d,]+.*)?$"
)


#: Dominios de primer nivel del inventario, derivados de los encabezados que el
#: volumen repite en las fichas. Un rótulo de esta lista clasifica el renglón
#: aunque venga con su total ('AIRCRAFT 43 combat capable').
#: Códigos de tipo de la Tabla 8 que solo pueden pertenecer a un dominio, y que
#: por tanto lo fijan aunque el corpus haya perdido el encabezado de sección.
#: Deliberadamente corto: solo se incluyen códigos sin lectura alternativa
#: (p. ej. 'MCM' queda fuera, porque designa tanto buque como helicóptero).
DOMINIO_POR_CATEGORIA: dict[str, str] = {
    "SSK": "SUBMARINES",
    "SSC": "SUBMARINES",
    "SSN": "SUBMARINES",
    "SSB": "SUBMARINES",
    "SSBN": "SUBMARINES",
    "SSGN": "SUBMARINES",
    "SSI": "SUBMARINES",
    "SSW": "SUBMARINES",
}

#: Rótulos con forma de fuerza que en realidad encabezan datos demográficos.
ETIQUETAS_NO_FUERZA: frozenset[str] = frozenset({"Population", "Age", "Male", "Female"})

#: Erratas del original que hay que reconducir al dominio canónico.
ERRATAS_DE_DOMINIO: dict[str, str] = {
    "UNIHABITED AERIAL VEHICLES": "UNINHABITED AERIAL VEHICLES",
    "ANTI-TANK1/ANTI-INFRASTRUCTURE": "ANTI-TANK/ANTI-INFRASTRUCTURE",
    "ANTI-TANK/ANTI-INFRASTURCTURE": "ANTI-TANK/ANTI-INFRASTRUCTURE",
    "ANTI-TANK/ANTI-INFRASTUCTURE": "ANTI-TANK/ANTI-INFRASTRUCTURE",
    "ANTI-TANK-ANTI-INFRASTRUCTURE": "ANTI-TANK/ANTI-INFRASTRUCTURE",
    "AIR LAUNCHED MISSILES": "AIR-LAUNCHED MISSILES",
    "FIXED-WING AIRCRAFT": "AIRCRAFT",
    "RADAR": "RADARS",
}

DOMINIOS_DE_EQUIPO: frozenset[str] = frozenset(
    {
        "AIRCRAFT",
        "AIR DEFENCE",
        "AIR-LAUNCHED MISSILES",
        "AMPHIBIOUS",
        "ANTI-TANK/ANTI-INFRASTRUCTURE",
        "ARMOURED FIGHTING VEHICLES",
        "ARTILLERY",
        "BOMBS",
        "COASTAL DEFENCE",
        "ENGINEERING & MAINTENANCE VEHICLES",
        "HELICOPTERS",
        "LOGISTICS AND SUPPORT",
        "MINE WARFARE",
        "MISSILE DEFENCE",
        "PATROL AND COASTAL COMBATANTS",
        "PRINCIPAL SURFACE COMBATANTS",
        "RADARS",
        "SATELLITES",
        "SUBMARINES",
        "SURFACE-TO-SURFACE MISSILE LAUNCHERS",
        "UNINHABITED AERIAL VEHICLES",
        "UNINHABITED MARITIME PLATFORMS",
        "UNINHABITED MARITIME SYSTEMS",
    }
)

#: Papel que cumple el rótulo en negrita que abre un renglón.
ROTULO_FUERZAS = "fuerzas"
ROTULO_EQUIPO = "equipo"
ROTULO_CIERRE = "cierre"
ROTULO_SERVICIO = "servicio"
ROTULO_ROL = "rol"
ROTULO_SUBROL = "subrol"
ROTULO_DATO = "dato"

#: Nivel nominal que se atribuye a un rótulo incrustado en un párrafo.
NIVEL_ROTULO_EN_LINEA = 3


_RE_TOTAL_EN_ROTULO = re.compile(r"\s*[(ε]?[\d,]+\+?\)?:?$")
_SEPARADOR_NIVEL = "•"


def partir_rotulo(rotulo: str) -> tuple[str, ...]:
    """Descompone un rótulo de inventario en sus niveles, ya normalizados.

    El volumen lo imprime con el total ('ARTILLERY 9,580'), a veces encadenando
    varios niveles ('AIR DEFENCE • SAM') y con erratas de composición.
    """
    niveles = []
    for parte in rotulo.split(_SEPARADOR_NIVEL):
        sin_total = _RE_TOTAL_EN_ROTULO.sub("", parte.strip()).strip()
        if sin_total:
            niveles.append(ERRATAS_DE_DOMINIO.get(sin_total, sin_total))
    return tuple(niveles)


def normalizar_dominio(rotulo: str) -> str:
    """Primer nivel de un rótulo de inventario, o cadena vacía si no hay."""
    niveles = partir_rotulo(rotulo)
    return niveles[0] if niveles else ""


def clasificar_rotulo(etiqueta: str, contenido: str, *, en_roles: bool) -> str:  # noqa: PLR0911
    """Papel de un rótulo en negrita al principio de un renglón.

    Buena parte de las fichas no usa encabezados propios: marca las secciones
    con negritas dentro de un párrafo corrido, de modo que 'FORCES BY ROLE',
    'Army ε1,500' y 'MANOEUVRE' llegan como renglones de un item de texto.
    """
    if etiqueta == SECCION_FUERZAS:
        return ROTULO_FUERZAS
    if etiqueta == SECCION_EQUIPO:
        return ROTULO_EQUIPO
    if etiqueta in CIERRES_DE_SECCION:
        return ROTULO_CIERRE
    if etiqueta.isupper():
        # Los roles van en versales y las fuerzas en capitular; un rótulo en
        # versales con contenido es un rol con su primera unidad en el renglón.
        return ROTULO_ROL
    if es_encabezado_de_fuerza(
        f"{etiqueta} {contenido}".strip(), NIVEL_ROTULO_EN_LINEA, en_roles=en_roles
    ):
        return ROTULO_SERVICIO
    if not contenido:
        return ROTULO_SUBROL
    return ROTULO_DATO


def partir_respetando_parentesis(
    texto: str, separadores: tuple[str, ...]
) -> tuple[str, ...]:
    """Parte por los separadores que estén fuera de todo paréntesis.

    Hace falta tanto en el inventario como en el orden de batalla: el volumen
    usa los mismos signos dentro de las glosas ('1 Sabalo (in refit; 1 more
    non-operational)') que entre elementos de una lista. Un cierre sin apertura
    —ruido del parse de origen— se ignora en vez de dejar la profundidad en
    negativo, que haría pasar por interior todo el texto posterior.
    """
    piezas: list[str] = []
    profundidad = 0
    actual: list[str] = []
    for caracter in texto:
        if caracter == "(":
            profundidad += 1
        elif caracter == ")" and profundidad > 0:
            profundidad -= 1
        elif caracter in separadores and profundidad == 0:
            piezas.append("".join(actual))
            actual = []
            continue
        actual.append(caracter)
    piezas.append("".join(actual))
    return tuple(pieza.strip() for pieza in piezas if pieza.strip())


_RE_SOLO_CANTIDAD = re.compile(r"^ε?[\d,]+\+?$")


def es_servicio_en_linea(
    etiqueta: str, contenido: str, total_segmentos: int, *, en_roles: bool
) -> bool:
    """Detecta el rótulo de una fuerza incrustado en un párrafo de inventario.

    Las categorías de equipo van en versales ('RECCE', 'TPT'); una fuerza va en
    capitular y como único rótulo del renglón, sola o con su cifra de efectivos
    ('**Air Wing**', '**Army** ε1,500'). Dentro de FORCES BY ROLE esa misma
    forma la tienen las sub-clasificaciones de maniobra ('Light', 'Other'), que
    solo se distinguen porque no traen cifra de efectivos.
    """
    if etiqueta.isupper() or total_segmentos != 1:
        return False
    if contenido and not _RE_SOLO_CANTIDAD.match(contenido):
        return False
    if en_roles and not contenido:
        return False
    nombre = nombre_de_servicio(etiqueta)
    return bool(nombre) and nombre not in ETIQUETAS_NO_FUERZA


def segmentos_en_negrita(linea_md: str) -> tuple[tuple[str, str], ...]:
    """Parte un renglón en pares (etiqueta en negrita, contenido que la sigue).

    Las secciones de inventario usan la negrita como única marca de jerarquía:
    ``**TOWED** 120: **105mm** 107: 22 LG1 MkIII`` son dos niveles, no uno.
    """
    marcas = list(_RE_NEGRITA.finditer(linea_md))
    if not marcas:
        return ()
    segmentos: list[tuple[str, str]] = []
    for orden, marca in enumerate(marcas):
        fin = marcas[orden + 1].start() if orden + 1 < len(marcas) else len(linea_md)
        etiqueta = " ".join(marca.group("etiqueta").split()).strip(f" {_VINETA}")
        contenido = linea_md[marca.end() : fin].replace("*", "").strip()
        if not any(caracter.isalpha() for caracter in etiqueta) and segmentos:
            # Marcadores rotos en el original: el tramo pertenece al rótulo previo.
            previo, texto = segmentos[-1]
            segmentos[-1] = (previo, f"{texto} {etiqueta} {contenido}".strip())
            continue
        segmentos.append((etiqueta, contenido))
    return tuple(segmentos)


def nombre_de_servicio(texto: str) -> str:
    """Nombre de la fuerza a partir de su encabezado ('Army 206,400' → 'Army')."""
    coincidencia = _RE_SERVICIO.match(texto)
    return coincidencia.group("nombre").strip() if coincidencia else ""


def es_encabezado_de_fuerza(texto: str, nivel: int, *, en_roles: bool) -> bool:
    """Separa el encabezado de una fuerza del de una sub-clasificación de rol.

    Dentro de FORCES BY ROLE, 'Mechanised' o 'Light' clasifican maniobra; solo
    un encabezado con su cifra de efectivos ('Navy 60,300') abre otra fuerza.
    """
    if not es_encabezado_de_servicio(texto, nivel):
        return False
    return not en_roles or any(caracter.isdigit() for caracter in texto)


def es_encabezado_de_servicio(texto: str, nivel: int) -> bool:
    """Distingue el encabezado de una fuerza de los títulos de sección."""
    if nivel == 0 or texto in CIERRES_DE_SECCION or texto == SECCION_EQUIPO:
        return False
    if nombre_de_servicio(texto) in ETIQUETAS_NO_FUERZA:
        return False
    if texto.isupper():
        return False
    return bool(nombre_de_servicio(texto))
