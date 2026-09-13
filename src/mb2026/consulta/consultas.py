"""Consultas sobre la base derivada del volumen.

Cada consulta devuelve tablas ya listas para imprimir o serializar, con la cita
de la fuente y la página. La conexión se abre en solo lectura: esta capa
responde preguntas, no modifica nada.

Varias consultas componen su texto con f-strings. Lo único que se interpola son
listas de marcadores posicionales ('?, ?, ?') generadas aquí mismo: ningún valor
del usuario entra en el texto de la sentencia, siempre viaja parametrizado.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

CITA_BASE = "IISS, The Military Balance 2026 (datos a noviembre de 2025)"

#: Sangría con la que se dibuja cada nivel del orden de batalla.
SANGRIA_ORBAT = "  "
#: Tope por defecto de filas en las consultas que pueden devolver muchas.
LIMITE_POR_DEFECTO = 200
#: Una correlación necesita al menos dos términos que comparar.
MINIMO_PARA_CORRELACION = 2


@dataclass(frozen=True, slots=True)
class Tabla:
    """Un bloque de resultados con su título."""

    titulo: str
    columnas: tuple[str, ...]
    filas: tuple[tuple[object, ...], ...]
    nota: str = ""


@dataclass(frozen=True, slots=True)
class Resultado:
    """Lo que devuelve una consulta, con su procedencia."""

    tablas: tuple[Tabla, ...] = field(default_factory=tuple)
    cita: str = CITA_BASE


def abrir(ruta: Path) -> sqlite3.Connection:
    """Abre la base en solo lectura."""
    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe la base mb2026 en {ruta}. "
            "Constrúyela con 'uv run mb2026' en el proyecto holo-mb2026."
        )
    conexion = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
    conexion.row_factory = sqlite3.Row
    return conexion


def catalogo_paises(conexion: sqlite3.Connection) -> dict[str, str]:
    """Mapa código → nombre de los países con ficha."""
    return {
        fila["codigo"]: fila["nombre"]
        for fila in conexion.execute("SELECT codigo, nombre FROM paises")
    }


def _marcadores(cantidad: int) -> str:
    """Lista de marcadores posicionales para una cláusula IN."""
    return ", ".join("?" * cantidad)


def _pais(conexion: sqlite3.Connection, codigo: str) -> sqlite3.Row:
    fila: sqlite3.Row | None = conexion.execute(
        "SELECT codigo, nombre, region, pagina FROM paises WHERE codigo = ?", (codigo,)
    ).fetchone()
    if fila is None:
        raise LookupError(f"La base no tiene ficha para el código {codigo}")
    return fila


def _cita(paginas: tuple[int, ...]) -> str:
    if not paginas:
        return CITA_BASE
    unicas = sorted(set(paginas))
    detalle = ", ".join(f"p. {pagina}" for pagina in unicas)
    return f"{CITA_BASE}, {detalle}"


def _marcas(fila: sqlite3.Row) -> str:
    """Las salvedades del editor, en la notación del volumen."""
    claves = fila.keys()
    signos = []
    if "estimado" in claves and fila["estimado"]:
        signos.append("ε")
    if "dudoso" in claves and fila["dudoso"]:
        signos.append("†")
    if "minimo" in claves and fila["minimo"]:
        signos.append("+")
    if "indeterminado" in claves and fila["indeterminado"]:
        signos.append("some")
    return " ".join(signos)


def ficha(conexion: sqlite3.Connection, codigo: str) -> Resultado:
    """Expediente de un país: identificación, economía, personal e inventario."""
    pais = _pais(conexion, codigo)
    return Resultado(
        tablas=(
            _tabla_identificacion(conexion, pais),
            _tabla_economia(conexion, codigo),
            _tabla_personal(conexion, codigo),
            _tabla_inventario_resumen(conexion, codigo),
            _tabla_despliegues(conexion, codigo),
            _tabla_extranjeras(conexion, codigo),
        ),
        cita=_cita((pais["pagina"],)),
    )


def _tabla_identificacion(conexion: sqlite3.Connection, pais: sqlite3.Row) -> Tabla:
    poblacion = conexion.execute(
        "SELECT total FROM poblacion WHERE codigo_pais = ?", (pais["codigo"],)
    ).fetchone()
    conscripcion = conexion.execute(
        "SELECT nota FROM conscripcion WHERE codigo_pais = ?", (pais["codigo"],)
    ).fetchone()
    filas = [
        ("Código", pais["codigo"]),
        ("Nombre", pais["nombre"]),
        ("Región", pais["region"]),
        ("Página", pais["pagina"]),
        ("Población", poblacion["total"] if poblacion else None),
    ]
    if conscripcion:
        filas.append(("Servicio obligatorio", conscripcion["nota"]))
    return Tabla("Identificación", ("Campo", "Valor"), tuple(filas))


def _tabla_economia(conexion: sqlite3.Connection, codigo: str) -> Tabla:
    filas = conexion.execute(
        "SELECT indicador, unidad, anio, valor, estimado FROM economia"
        " WHERE codigo_pais = ? ORDER BY indicador, unidad, anio",
        (codigo,),
    ).fetchall()
    return Tabla(
        "Economía de defensa",
        ("Indicador", "Unidad", "Año", "Valor", "Marcas"),
        tuple(
            (f["indicador"], f["unidad"], f["anio"], f["valor"], _marcas(f))
            for f in filas
        ),
        nota="" if filas else "El volumen no publica datos macro para este país.",
    )


def _tabla_personal(conexion: sqlite3.Connection, codigo: str) -> Tabla:
    filas = conexion.execute(
        "SELECT categoria, componente, cantidad, estimado, minimo, indeterminado"
        " FROM personal WHERE codigo_pais = ?"
        " ORDER BY categoria, componente <> 'Total', componente",
        (codigo,),
    ).fetchall()
    return Tabla(
        "Personal",
        ("Categoría", "Componente", "Efectivos", "Marcas"),
        tuple(
            (f["categoria"], f["componente"], f["cantidad"], _marcas(f)) for f in filas
        ),
    )


def _tabla_inventario_resumen(conexion: sqlite3.Connection, codigo: str) -> Tabla:
    filas = conexion.execute(
        "SELECT dominio, COUNT(*) AS lineas, SUM(dudoso) AS dudosos"
        " FROM equipo WHERE codigo_pais = ? AND dominio <> ''"
        " GROUP BY dominio ORDER BY lineas DESC",
        (codigo,),
    ).fetchall()
    return Tabla(
        "Inventario por dominio",
        ("Dominio", "Líneas", "Con operatividad dudosa"),
        tuple((f["dominio"], f["lineas"], f["dudosos"] or 0) for f in filas),
    )


def _tabla_despliegues(conexion: sqlite3.Connection, codigo: str) -> Tabla:
    filas = conexion.execute(
        "SELECT destino, organizacion, mision, efectivos FROM despliegues"
        " WHERE codigo_pais = ? ORDER BY destino",
        (codigo,),
    ).fetchall()
    return Tabla(
        "Despliegues propios",
        ("Destino", "Organización", "Misión", "Efectivos"),
        tuple(
            (f["destino"], f["organizacion"], f["mision"], f["efectivos"]) for f in filas
        ),
    )


def _tabla_extranjeras(conexion: sqlite3.Connection, codigo: str) -> Tabla:
    filas = conexion.execute(
        "SELECT origen, efectivos, detalle FROM fuerzas_extranjeras"
        " WHERE codigo_pais = ? ORDER BY origen",
        (codigo,),
    ).fetchall()
    return Tabla(
        "Fuerzas extranjeras en el país",
        ("Origen", "Efectivos", "Detalle"),
        tuple((f["origen"], f["efectivos"], f["detalle"]) for f in filas),
    )


def correlacion(
    conexion: sqlite3.Connection,
    codigos: tuple[str, ...],
    dominios: tuple[str, ...],
) -> Resultado:
    """Compara efectivos e inventario de dos o más países."""
    if len(codigos) < MINIMO_PARA_CORRELACION:
        raise ValueError("La correlación necesita al menos dos países")
    paises = [_pais(conexion, codigo) for codigo in codigos]
    nombres = tuple(p["nombre"] for p in paises)
    return Resultado(
        tablas=(
            _tabla_personal_comparado(conexion, codigos, nombres),
            _tabla_presupuesto_comparado(conexion, codigos, nombres),
            _tabla_equipo_comparado(conexion, codigos, nombres, dominios),
        ),
        cita=_cita(tuple(p["pagina"] for p in paises)),
    )


def _comparar(
    conexion: sqlite3.Connection,
    consulta: str,
    codigos: tuple[str, ...],
    parametros: tuple[object, ...],
) -> dict[str, dict[str, object]]:
    """Ejecuta una consulta que devuelve (clave, codigo_pais, valor)."""
    acumulado: dict[str, dict[str, object]] = {}
    for fila in conexion.execute(consulta, parametros):
        acumulado.setdefault(fila["clave"], {})[fila["codigo_pais"]] = fila["valor"]
    return acumulado


def _tabla_comparada(
    titulo: str, etiqueta: str, nombres: tuple[str, ...],
    codigos: tuple[str, ...], datos: dict[str, dict[str, object]],
) -> Tabla:
    return Tabla(
        titulo,
        (etiqueta, *nombres),
        tuple(
            (clave, *(valores.get(codigo) for codigo in codigos))
            for clave, valores in datos.items()
        ),
    )


def _tabla_personal_comparado(
    conexion: sqlite3.Connection, codigos: tuple[str, ...], nombres: tuple[str, ...]
) -> Tabla:
    marcadores = _marcadores(len(codigos))
    datos = _comparar(
        conexion,
        "SELECT CASE categoria WHEN 'activo' THEN 'Activos'"
        "   WHEN 'reserva' THEN 'Reserva' ELSE 'Gendarmería' END AS clave,"
        " codigo_pais, cantidad AS valor FROM personal"
        f" WHERE componente = 'Total' AND codigo_pais IN ({marcadores})",
        codigos,
        codigos,
    )
    return _tabla_comparada("Personal", "Categoría", nombres, codigos, datos)


def _tabla_presupuesto_comparado(
    conexion: sqlite3.Connection, codigos: tuple[str, ...], nombres: tuple[str, ...]
) -> Tabla:
    marcadores = _marcadores(len(codigos))
    datos = _comparar(
        conexion,
        "SELECT 'Presupuesto USD ' || anio AS clave, codigo_pais, valor"
        " FROM economia WHERE indicador = 'presupuesto_defensa' AND unidad = 'USD'"
        f" AND codigo_pais IN ({marcadores}) ORDER BY anio",
        codigos,
        codigos,
    )
    return _tabla_comparada("Presupuesto", "Concepto", nombres, codigos, datos)


def _tabla_equipo_comparado(
    conexion: sqlite3.Connection,
    codigos: tuple[str, ...],
    nombres: tuple[str, ...],
    dominios: tuple[str, ...],
) -> Tabla:
    marcadores = _marcadores(len(codigos))
    filtro = ""
    parametros: tuple[object, ...] = codigos
    if dominios:
        filtro = f" AND dominio IN ({_marcadores(len(dominios))})"
        parametros = codigos + dominios
    datos = _comparar(
        conexion,
        "SELECT categoria AS clave, codigo_pais,"
        " COALESCE(SUM(cantidad), 0) AS valor FROM equipo"
        f" WHERE codigo_pais IN ({marcadores}){filtro}"
        " GROUP BY categoria, codigo_pais ORDER BY categoria",
        codigos,
        parametros,
    )
    return _tabla_comparada(
        "Correlación de inventario", "Categoría", nombres, codigos, datos
    )


def buscar_sistema(
    conexion: sqlite3.Connection, texto: str, limite: int = LIMITE_POR_DEFECTO
) -> Resultado:
    """Qué países operan un sistema y en qué cantidad."""
    filas = conexion.execute(
        "SELECT p.nombre, e.codigo_pais, e.servicio, e.dominio, e.categoria,"
        " e.sistema, e.cantidad, e.dudoso, e.estimado, e.minimo, e.indeterminado,"
        " e.pagina FROM equipo e JOIN paises p ON p.codigo = e.codigo_pais"
        " WHERE e.sistema LIKE ? ORDER BY e.cantidad IS NULL, e.cantidad DESC LIMIT ?",
        (f"%{texto}%", limite),
    ).fetchall()
    return Resultado(
        tablas=(
            Tabla(
                f"Operadores de «{texto}»",
                ("País", "Fuerza", "Dominio", "Categoría", "Sistema", "Cantidad", "Marcas"),
                tuple(
                    (f["nombre"], f["servicio"], f["dominio"], f["categoria"],
                     f["sistema"], f["cantidad"], _marcas(f))
                    for f in filas
                ),
            ),
        ),
        cita=_cita(tuple(f["pagina"] for f in filas)),
    )


def gasto(
    conexion: sqlite3.Connection, codigos: tuple[str, ...], desde: int = 0
) -> Resultado:
    """Serie del presupuesto de defensa en términos reales."""
    marcadores = _marcadores(len(codigos))
    filas = conexion.execute(
        "SELECT p.nombre, s.anio, s.valor, s.unidad FROM serie_presupuesto_real s"
        f" JOIN paises p ON p.codigo = s.codigo_pais"
        f" WHERE s.codigo_pais IN ({marcadores})"
        " AND s.anio >= ? ORDER BY p.nombre, s.anio",
        (*codigos, desde),
    ).fetchall()
    unidades = {f["unidad"] for f in filas}
    return Resultado(
        tablas=(
            Tabla(
                "Gasto de defensa en términos reales",
                ("País", "Año", "Valor"),
                tuple((f["nombre"], f["anio"], f["valor"]) for f in filas),
                nota=" / ".join(sorted(u for u in unidades if u)),
            ),
        )
    )


def orbat(
    conexion: sqlite3.Connection,
    codigo: str,
    servicio: str = "",
    profundidad: int | None = None,
) -> Resultado:
    """Orden de batalla del país, dibujado como árbol."""
    pais = _pais(conexion, codigo)
    condicion = " AND servicio = ?" if servicio else ""
    parametros: tuple[object, ...] = (codigo, servicio) if servicio else (codigo,)
    if profundidad is not None:
        condicion += " AND profundidad <= ?"
        parametros = (*parametros, profundidad)
    filas = conexion.execute(
        "SELECT profundidad, servicio, rol, cantidad, designacion, tipo, echelon,"
        " pagina FROM unidades WHERE codigo_pais = ?"
        f"{condicion} ORDER BY id",
        parametros,
    ).fetchall()
    return Resultado(
        tablas=(
            Tabla(
                f"Orden de batalla · {pais['nombre']}",
                ("Unidad", "Fuerza", "Rol", "Escalón"),
                tuple(
                    (
                        SANGRIA_ORBAT * f["profundidad"] + _etiqueta_unidad(f),
                        f["servicio"],
                        f["rol"],
                        f["echelon"],
                    )
                    for f in filas
                ),
            ),
        ),
        cita=_cita(tuple(f["pagina"] for f in filas) or (pais["pagina"],)),
    )


def _etiqueta_unidad(fila: sqlite3.Row) -> str:
    cantidad = f"{fila['cantidad']} " if fila["cantidad"] is not None else ""
    designacion = f" ({fila['designacion']})" if fila["designacion"] else ""
    return f"{cantidad}{fila['tipo']}{designacion}"


def unidades_crudas(
    conexion: sqlite3.Connection,
    codigo: str,
    servicio: str = "",
    profundidad: int | None = None,
) -> list[dict[str, object]]:
    """Filas de `unidades` tal cual, para alimentar al traductor de simbología."""
    _pais(conexion, codigo)
    condicion = " AND servicio = ?" if servicio else ""
    parametros: tuple[object, ...] = (codigo, servicio) if servicio else (codigo,)
    if profundidad is not None:
        condicion += " AND profundidad <= ?"
        parametros = (*parametros, profundidad)
    filas = conexion.execute(
        "SELECT id, padre_id, codigo_pais, profundidad, servicio, rol, cantidad,"
        " designacion, tipo, echelon, pagina FROM unidades WHERE codigo_pais = ?"
        f"{condicion} ORDER BY id",
        parametros,
    ).fetchall()
    return [dict(fila) for fila in filas]


def inventario(
    conexion: sqlite3.Connection,
    codigo: str,
    dominios: tuple[str, ...] = (),
    limite: int = LIMITE_POR_DEFECTO,
) -> Resultado:
    """Inventario detallado de un país, opcionalmente acotado por dominio."""
    pais = _pais(conexion, codigo)
    filtro = ""
    parametros: tuple[object, ...] = (codigo,)
    if dominios:
        filtro = f" AND dominio IN ({_marcadores(len(dominios))})"
        parametros = (codigo, *dominios)
    filas = conexion.execute(
        "SELECT dominio, grupo, categoria, subcategoria, sistema, cantidad,"
        " total_categoria, dudoso, estimado, minimo, indeterminado, pagina"
        f" FROM equipo WHERE codigo_pais = ?{filtro}"
        " ORDER BY dominio, categoria, cantidad IS NULL, cantidad DESC LIMIT ?",
        (*parametros, limite),
    ).fetchall()
    return Resultado(
        tablas=(
            Tabla(
                f"Inventario · {pais['nombre']}",
                ("Dominio", "Grupo", "Categoría", "Sistema", "Cantidad", "Marcas"),
                tuple(
                    (f["dominio"], f["grupo"], _categoria(f), f["sistema"],
                     f["cantidad"], _marcas(f))
                    for f in filas
                ),
            ),
        ),
        cita=_cita(tuple(f["pagina"] for f in filas) or (pais["pagina"],)),
    )


def _categoria(fila: sqlite3.Row) -> str:
    if fila["subcategoria"]:
        return f"{fila['categoria']} · {fila['subcategoria']}"
    return str(fila["categoria"])


def ranking(
    conexion: sqlite3.Connection, region: str, anio: int = 2025
) -> Resultado:
    """Países de una región ordenados por presupuesto de defensa."""
    filas = conexion.execute(
        "SELECT cg.pais, cg.presupuesto_usd_m, cg.pct_pib, cp.activos_miles"
        " FROM comparacion_gasto cg"
        " LEFT JOIN comparacion_personal cp ON cp.pais = cg.pais AND cp.region = cg.region"
        " WHERE cg.region = ? AND cg.anio = ? AND cg.es_agregado = 0"
        " ORDER BY cg.presupuesto_usd_m IS NULL, cg.presupuesto_usd_m DESC",
        (region, anio),
    ).fetchall()
    return Resultado(
        tablas=(
            Tabla(
                f"Ranking de gasto · {region} ({anio})",
                ("#", "País", "Presupuesto USDm", "% PIB", "Activos (miles)"),
                tuple(
                    (orden, f["pais"], f["presupuesto_usd_m"], f["pct_pib"],
                     f["activos_miles"])
                    for orden, f in enumerate(filas, start=1)
                ),
                nota="Cifras de la Tabla 9 del volumen (comparación internacional).",
            ),
        )
    )


def _buscar_abreviatura(
    conexion: sqlite3.Connection, patron: str
) -> list[sqlite3.Row]:
    return conexion.execute(
        "SELECT sigla, definicion FROM abreviaturas"
        " WHERE sigla LIKE ? OR definicion LIKE ? ORDER BY LENGTH(sigla), sigla",
        (patron, patron),
    ).fetchall()


def presencia(conexion: sqlite3.Connection, destino: str) -> Resultado:
    """Quién despliega hacia un destino y qué terceros Estados hay en un país."""
    patron = f"%{destino}%"
    hacia = conexion.execute(
        "SELECT p.nombre AS origen, d.destino, d.organizacion, d.mision, d.efectivos"
        " FROM despliegues d JOIN paises p ON p.codigo = d.codigo_pais"
        " WHERE d.destino LIKE ? ORDER BY d.efectivos IS NULL, d.efectivos DESC",
        (patron,),
    ).fetchall()
    dentro = conexion.execute(
        "SELECT f.origen, p.nombre AS anfitrion, f.efectivos, f.detalle"
        " FROM fuerzas_extranjeras f JOIN paises p ON p.codigo = f.codigo_pais"
        " WHERE p.nombre LIKE ? OR p.codigo = ? ORDER BY f.origen",
        (patron, destino.upper()),
    ).fetchall()
    return Resultado(
        tablas=(
            Tabla(
                f"Despliegues hacia «{destino}»",
                ("Origen", "Destino", "Organización", "Misión", "Efectivos"),
                tuple(
                    (f["origen"], f["destino"], f["organizacion"], f["mision"],
                     f["efectivos"])
                    for f in hacia
                ),
            ),
            Tabla(
                f"Fuerzas extranjeras en «{destino}»",
                ("Origen", "Anfitrión", "Efectivos", "Detalle"),
                tuple(
                    (f["origen"], f["anfitrion"], f["efectivos"], f["detalle"])
                    for f in dentro
                ),
            ),
        )
    )


def paises(conexion: sqlite3.Connection, region: str = "") -> Resultado:
    """Listado de fichas disponibles, opcionalmente de una región."""
    filtro = " WHERE region = ?" if region else ""
    parametros: tuple[object, ...] = (region,) if region else ()
    filas = conexion.execute(
        "SELECT codigo, nombre, region, pagina FROM paises"
        f"{filtro} ORDER BY region, nombre",
        parametros,
    ).fetchall()
    return Resultado(
        tablas=(
            Tabla(
                "Países con ficha" + (f" · {region}" if region else ""),
                ("Código", "Nombre", "Región", "Página"),
                tuple(
                    (f["codigo"], f["nombre"], f["region"], f["pagina"]) for f in filas
                ),
            ),
        )
    )


#: Letras que bastan para localizar la familia de un código naval compuesto.
_RAIZ_CODIGO_COMPUESTO = 2


def abreviatura(conexion: sqlite3.Connection, texto: str) -> Resultado:
    """Desarrollo de una sigla del volumen.

    La Tabla 8 agrupa los códigos navales en una sola entrada con barras
    ('FS/G/H/M'), así que una sigla concreta como 'FSGHM' no aparece literal;
    si la búsqueda directa falla, se recurre a la familia del código.
    """
    filas = _buscar_abreviatura(conexion, f"%{texto}%")
    if not filas and len(texto) > _RAIZ_CODIGO_COMPUESTO:
        filas = _buscar_abreviatura(conexion, f"{texto[:_RAIZ_CODIGO_COMPUESTO]}/%")
    return Resultado(
        tablas=(
            Tabla(
                f"Abreviaturas que coinciden con «{texto}»",
                ("Sigla", "Definición"),
                tuple((f["sigla"], f["definicion"]) for f in filas),
                nota="Tabla 8 del volumen.",
            ),
        )
    )


def sql(
    conexion: sqlite3.Connection, consulta: str, limite: int = LIMITE_POR_DEFECTO
) -> Resultado:
    """Consulta libre de solo lectura.

    La garantía no está en inspeccionar el texto sino en que la conexión se
    abrió en modo ``ro``: cualquier escritura falla en el motor.
    """
    cursor = conexion.execute(consulta)
    filas = cursor.fetchmany(limite)
    columnas = tuple(descripcion[0] for descripcion in cursor.description or ())
    return Resultado(
        tablas=(Tabla("Consulta libre", columnas, tuple(tuple(f) for f in filas)),)
    )
