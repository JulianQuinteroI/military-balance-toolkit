"""Informe de calidad de la extracción, con foco en el capítulo 7.

Uso: uv run python scripts/informe_extraccion.py [region]
"""

from __future__ import annotations

import sqlite3
import sys
from collections import Counter

from mb2026 import config
from mb2026.parsers.comparacion import ANIO_PERSONAL
from mb2026.simbologia.traductor import traducir_orbat

REGION_POR_DEFECTO = "Latin America and the Caribbean"


def _conectar() -> sqlite3.Connection:
    ruta = config.ruta_base_datos()
    if not ruta.exists():
        raise SystemExit(f"No existe la base {ruta}. Ejecuta 'uv run mb2026' primero.")
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    return conexion


def _titulo(texto: str) -> None:
    print(f"\n{texto}\n{'─' * len(texto)}")


def cobertura_global(conexion: sqlite3.Connection) -> None:
    _titulo("Cobertura global")
    fila = conexion.execute(
        "SELECT (SELECT COUNT(*) FROM paises) AS paises,"
        " (SELECT COUNT(*) FROM equipo) AS equipo,"
        " (SELECT COUNT(*) FROM unidades) AS unidades,"
        " (SELECT COUNT(*) FROM economia) AS economia,"
        " (SELECT COUNT(*) FROM despliegues) AS despliegues,"
        " (SELECT COUNT(*) FROM fuerzas_extranjeras) AS extranjeras,"
        " (SELECT COUNT(*) FROM abreviaturas) AS abreviaturas"
    ).fetchone()
    # sqlite3.Row itera valores, no nombres: keys() es obligatorio aquí.
    for clave in fila.keys():  # noqa: SIM118
        print(f"  {clave:<16}{fila[clave]:>8,}")


def fichas_incompletas(conexion: sqlite3.Connection) -> None:
    _titulo("Fichas sin alguna sección (el volumen tampoco la trae)")
    consultas = {
        "sin economía": "SELECT COUNT(*) FROM paises p WHERE NOT EXISTS"
                        " (SELECT 1 FROM economia e WHERE e.codigo_pais = p.codigo)",
        "sin personal": "SELECT COUNT(*) FROM paises p WHERE NOT EXISTS"
                        " (SELECT 1 FROM personal x WHERE x.codigo_pais = p.codigo)",
        "sin inventario": "SELECT COUNT(*) FROM paises p WHERE NOT EXISTS"
                          " (SELECT 1 FROM equipo x WHERE x.codigo_pais = p.codigo)",
        "sin unidades": "SELECT COUNT(*) FROM paises p WHERE NOT EXISTS"
                        " (SELECT 1 FROM unidades x WHERE x.codigo_pais = p.codigo)",
    }
    for etiqueta, consulta in consultas.items():
        print(f"  {etiqueta:<16}{conexion.execute(consulta).fetchone()[0]:>4} de 174")


def defectos_del_parse_de_origen(conexion: sqlite3.Connection) -> None:
    _titulo("Defectos heredados del parse de origen")
    filas = conexion.execute(
        # Si el volumen publicó la serie del presupuesto, publicó también la
        # tabla económica: que falte solo esta delata una pérdida en el parse.
        "SELECT p.codigo, p.nombre FROM paises p"
        " WHERE EXISTS (SELECT 1 FROM serie_presupuesto_real s"
        "   WHERE s.codigo_pais = p.codigo)"
        "   AND NOT EXISTS (SELECT 1 FROM economia e WHERE e.codigo_pais = p.codigo)"
        " ORDER BY p.nombre"
    ).fetchall()
    if not filas:
        print("  ninguno")
        return
    print("  tabla económica sin cabecera de años (el corpus la perdió):")
    for f in filas:
        print(f"    {f['codigo']}  {f['nombre']}")
    _inventario_naval_mal_atribuido(conexion)


def _inventario_naval_mal_atribuido(conexion: sqlite3.Connection) -> None:
    """Buques atribuidos a una fuerza terrestre: delata un encabezado perdido."""
    filas = conexion.execute(
        "SELECT p.codigo, p.nombre, e.categoria, e.servicio, e.pagina"
        " FROM equipo e JOIN paises p ON p.codigo = e.codigo_pais"
        " WHERE e.dominio IN ('SUBMARINES', 'PRINCIPAL SURFACE COMBATANTS')"
        "   AND e.servicio IN ('Army', 'Air Force')"
        " ORDER BY p.nombre"
    ).fetchall()
    if not filas:
        return
    print("  inventario naval atribuido a una fuerza terrestre:")
    for f in filas:
        print(
            f"    {f['codigo']}  {f['categoria']:<9} "
            f"fuerza={f['servicio']:<10} p.{f['pagina']}"
        )


def cobertura_de_simbologia(conexion: sqlite3.Connection) -> None:
    _titulo("Traducción a simbología NATO (orden `calco`)")
    filas = [
        dict(f)
        for f in conexion.execute(
            "SELECT id, padre_id, codigo_pais, profundidad, servicio, rol,"
            " cantidad, designacion, tipo, echelon, pagina FROM unidades"
        )
    ]
    calco = traducir_orbat(filas, "amigo")
    print(f"  unidades            {len(filas):>8,}")
    print(f"  con símbolo         {len(calco.unidades):>8,}")
    print(f"  cobertura           {calco.cobertura:>8.1%}")
    if calco.sin_mapear:
        tipos = Counter(unidad.tipo for unidad in calco.sin_mapear)
        print("  tipos sin símbolo más frecuentes:")
        for tipo, cuantas in tipos.most_common(6):
            print(f"    {cuantas:>5}  {tipo[:60]}")


def concordancia(conexion: sqlite3.Connection, region: str) -> None:
    _titulo(f"Concordancia ficha ↔ Tabla 9 · {region}")
    print(f"  {'país':<24}{'activos ficha':>14}{'T9':>10}{'USD ficha':>14}{'T9':>12}")
    filas = conexion.execute(
        "SELECT p.codigo, p.nombre,"
        " (SELECT cantidad FROM personal pe WHERE pe.codigo_pais = p.codigo"
        "   AND pe.categoria = 'activo' AND pe.componente = 'Total')      AS activos,"
        " (SELECT activos_miles * 1000 FROM comparacion_personal cp"
        "   WHERE cp.codigo_pais = p.codigo)                              AS activos_t9,"
        " (SELECT valor FROM economia e WHERE e.codigo_pais = p.codigo"
        "   AND e.indicador = 'presupuesto_defensa' AND e.unidad = 'USD'"
        "   AND e.anio = ?)                                               AS usd,"
        " (SELECT presupuesto_usd_m * 1e6 FROM comparacion_gasto cg"
        "   WHERE cg.codigo_pais = p.codigo AND cg.anio = ?)              AS usd_t9"
        " FROM paises p WHERE p.region = ? ORDER BY p.nombre",
        (ANIO_PERSONAL, ANIO_PERSONAL, region),
    ).fetchall()
    for f in filas:
        print(
            f"  {f['nombre'][:22]:<24}"
            f"{_entero(f['activos']):>14}{_entero(f['activos_t9']):>10}"
            f"{_millones(f['usd']):>14}{_millones(f['usd_t9']):>12}"
        )


def mayores_inventarios(conexion: sqlite3.Connection, region: str) -> None:
    _titulo(f"Inventario extraído · {region}")
    filas = conexion.execute(
        "SELECT p.nombre, COUNT(e.id) AS lineas,"
        " SUM(e.dudoso) AS dudosos,"
        " (SELECT COUNT(*) FROM unidades u WHERE u.codigo_pais = p.codigo) AS unidades"
        " FROM paises p LEFT JOIN equipo e ON e.codigo_pais = p.codigo"
        " WHERE p.region = ? GROUP BY p.codigo ORDER BY lineas DESC LIMIT 10",
        (region,),
    ).fetchall()
    print(f"  {'país':<24}{'líneas equipo':>14}{'dudosos':>9}{'unidades':>10}")
    for f in filas:
        print(
            f"  {f['nombre'][:22]:<24}{f['lineas']:>14}"
            f"{f['dudosos'] or 0:>9}{f['unidades']:>10}"
        )


def _entero(valor: float | None) -> str:
    return f"{int(valor):,}" if valor is not None else "—"


def _millones(valor: float | None) -> str:
    return f"{valor / 1e6:,.1f} m" if valor is not None else "—"


def main() -> None:
    region = sys.argv[1] if len(sys.argv) > 1 else REGION_POR_DEFECTO
    conexion = _conectar()
    try:
        cobertura_global(conexion)
        fichas_incompletas(conexion)
        defectos_del_parse_de_origen(conexion)
        cobertura_de_simbologia(conexion)
        concordancia(conexion, region)
        mayores_inventarios(conexion, region)
    finally:
        conexion.close()


if __name__ == "__main__":
    main()
