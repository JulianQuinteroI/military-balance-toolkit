"""Línea de comandos de consulta sobre The Military Balance 2026."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path

from mb2026 import config
from mb2026.consulta import consultas
from mb2026.consulta.formato import como_json, como_texto
from mb2026.consulta.resolver import dominios_de, region_de, resolver_pais
from mb2026.simbologia.traductor import Calco, traducir_orbat

#: Permite apuntar a otra base sin tocar el código.
VARIABLE_ENTORNO_BASE = "MB2026_DB"

#: Skill que renderiza los símbolos a partir del ORBAT.
RUTA_SKILL_SIMBOLOGIA = Path.home() / ".claude" / "skills" / "nato-symbology"

#: Cuántos tipos sin mapear se listan en el informe del calco.
_MUESTRA_SIN_MAPEAR = 8

_DESCRIPCION = (
    "Consulta la base derivada de The Military Balance 2026 (IISS). "
    "Los países se aceptan por código del IISS o por nombre en español o inglés."
)


def ruta_base(indicada: Path | None) -> Path:
    """Base a consultar: la indicada, la del entorno o la del proyecto."""
    if indicada is not None:
        return indicada
    configurada = os.environ.get(VARIABLE_ENTORNO_BASE)
    return Path(configurada).expanduser() if configurada else config.ruta_base_datos()


def _paises(conexion: sqlite3.Connection, valores: list[str]) -> tuple[str, ...]:
    catalogo = consultas.catalogo_paises(conexion)
    return tuple(resolver_pais(valor, catalogo) for valor in valores)


def _pais_unico(conexion: sqlite3.Connection, valor: str) -> str:
    return resolver_pais(valor, consultas.catalogo_paises(conexion))


def _dominios(valores: list[str] | None) -> tuple[str, ...]:
    if not valores:
        return ()
    return tuple(dict.fromkeys(d for valor in valores for d in dominios_de(valor)))


def _construir_analizador() -> argparse.ArgumentParser:
    analizador = argparse.ArgumentParser(prog="mb", description=_DESCRIPCION)
    analizador.add_argument("--base", type=Path, default=None, help="Ruta a la base SQLite")
    analizador.add_argument("--json", action="store_true", help="Salida serializada")
    ordenes = analizador.add_subparsers(dest="orden", required=True)

    ficha = ordenes.add_parser("ficha", help="Expediente completo de un país")
    ficha.add_argument("pais")

    correlacion = ordenes.add_parser("correlacion", help="Comparar dos o más países")
    correlacion.add_argument("paises", nargs="+")
    correlacion.add_argument("--dominio", action="append", help="aire, tierra, mar…")

    sistema = ordenes.add_parser("sistema", help="Quién opera un sistema")
    sistema.add_argument("texto")

    gasto = ordenes.add_parser("gasto", help="Serie real del presupuesto")
    gasto.add_argument("paises", nargs="+")
    gasto.add_argument("--desde", type=int, default=0)

    orbat = ordenes.add_parser("orbat", help="Orden de batalla")
    orbat.add_argument("pais")
    orbat.add_argument("--fuerza", default="", help="Army, Navy, Air Force…")
    orbat.add_argument("--profundidad", type=int, default=None)

    inventario = ordenes.add_parser("inventario", help="Inventario de equipo")
    inventario.add_argument("pais")
    inventario.add_argument("--dominio", action="append")
    inventario.add_argument("--limite", type=int, default=consultas.LIMITE_POR_DEFECTO)

    ranking = ordenes.add_parser("ranking", help="Gasto por país en una región")
    ranking.add_argument("region")
    ranking.add_argument("--anio", type=int, default=2025)

    presencia = ordenes.add_parser("presencia", help="Despliegues y fuerzas extranjeras")
    presencia.add_argument("destino")

    lista = ordenes.add_parser("paises", help="Fichas disponibles")
    lista.add_argument("--region", default="")

    abreviatura = ordenes.add_parser("abreviatura", help="Desarrollo de una sigla")
    abreviatura.add_argument("texto")

    calco = ordenes.add_parser(
        "calco", help="ORBAT en JSON para el skill nato-symbology"
    )
    calco.add_argument("pais")
    calco.add_argument("--fuerza", default="", help="Army, Navy, Air Force…")
    calco.add_argument("--profundidad", type=int, default=None)
    calco.add_argument(
        "--afiliacion", default="amigo", help="amigo, hostil, neutral, desconocido"
    )
    calco.add_argument("--salida", type=Path, default=None, help="Archivo .json")

    libre = ordenes.add_parser("sql", help="Consulta libre de solo lectura")
    libre.add_argument("consulta")
    libre.add_argument("--limite", type=int, default=consultas.LIMITE_POR_DEFECTO)
    return analizador


def _despachar(
    opciones: argparse.Namespace, conexion: sqlite3.Connection
) -> consultas.Resultado:
    ordenes: dict[str, Callable[[], consultas.Resultado]] = {
        "ficha": lambda: consultas.ficha(conexion, _pais_unico(conexion, opciones.pais)),
        "correlacion": lambda: consultas.correlacion(
            conexion, _paises(conexion, opciones.paises), _dominios(opciones.dominio)
        ),
        "sistema": lambda: consultas.buscar_sistema(conexion, opciones.texto),
        "gasto": lambda: consultas.gasto(
            conexion, _paises(conexion, opciones.paises), opciones.desde
        ),
        "orbat": lambda: consultas.orbat(
            conexion,
            _pais_unico(conexion, opciones.pais),
            servicio=opciones.fuerza,
            profundidad=opciones.profundidad,
        ),
        "inventario": lambda: consultas.inventario(
            conexion,
            _pais_unico(conexion, opciones.pais),
            dominios=_dominios(opciones.dominio),
            limite=opciones.limite,
        ),
        "ranking": lambda: consultas.ranking(
            conexion, region_de(opciones.region), opciones.anio
        ),
        "presencia": lambda: consultas.presencia(conexion, opciones.destino),
        "paises": lambda: consultas.paises(
            conexion, region_de(opciones.region) if opciones.region else ""
        ),
        "abreviatura": lambda: consultas.abreviatura(conexion, opciones.texto),
        "sql": lambda: consultas.sql(conexion, opciones.consulta, opciones.limite),
    }
    return ordenes[opciones.orden]()


def _generar_calco(opciones: argparse.Namespace, conexion: sqlite3.Connection) -> int:
    """Escribe el ORBAT y explica cómo convertirlo en símbolos."""
    codigo = _pais_unico(conexion, opciones.pais)
    filas = consultas.unidades_crudas(
        conexion, codigo, opciones.fuerza, opciones.profundidad
    )
    if not filas:
        print(
            f"Error: {codigo} sin unidades con ese filtro. "
            "Revisa --fuerza con la orden 'orbat'.",
            file=sys.stderr,
        )
        return 1

    calco = traducir_orbat(filas, opciones.afiliacion)
    contenido = json.dumps(calco.como_orbat(), ensure_ascii=False, indent=2)
    if opciones.salida is None:
        print(contenido)
        return 0

    opciones.salida.write_text(contenido, encoding="utf8")
    _informar_calco(calco, opciones.salida)
    return 0


def _informar_calco(calco: Calco, salida: Path) -> None:
    print(f"ORBAT escrito en {salida}")
    print(f"  unidades con símbolo : {len(calco.unidades)}")
    print(f"  sin mapear           : {len(calco.sin_mapear)}")
    print(f"  cobertura            : {calco.cobertura:.1%}")
    if calco.sin_mapear:
        tipos = Counter(unidad.tipo for unidad in calco.sin_mapear)
        print("  tipos sin símbolo (los más frecuentes):")
        for tipo, cuantas in tipos.most_common(_MUESTRA_SIN_MAPEAR):
            print(f"    {cuantas:>4}  {tipo[:60]}")
    print()
    print("Para generar los símbolos:")
    generador = RUTA_SKILL_SIMBOLOGIA / "scripts" / "generate.mjs"
    print(f'  node "{generador}" --orbat {salida} --out ./simbolos --demo')
    if not generador.exists():
        print(f"  (aún no está instalado el skill nato-symbology en {generador})")


def main(argumentos: list[str] | None = None) -> int:
    """Ejecuta una consulta y la imprime."""
    opciones = _construir_analizador().parse_args(argumentos)
    try:
        conexion = consultas.abrir(ruta_base(opciones.base))
    except FileNotFoundError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    try:
        if opciones.orden == "calco":
            return _generar_calco(opciones, conexion)
        resultado = _despachar(opciones, conexion)
    except (LookupError, ValueError, sqlite3.Error) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    finally:
        conexion.close()

    print(como_json(resultado) if opciones.json else como_texto(resultado))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
