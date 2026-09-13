"""Interfaz de línea de comandos."""

from __future__ import annotations

import argparse
from pathlib import Path

from mb2026 import config, etl


def main(argumentos: list[str] | None = None) -> int:
    """Construye la base y reporta lo que se cargó."""
    analizador = argparse.ArgumentParser(
        prog="mb2026",
        description="Extrae The Military Balance 2026 a una base SQLite consultable.",
    )
    analizador.add_argument(
        "--corpus", type=Path, default=None,
        help=f"JSON del corpus (por defecto: {config.ruta_json_corpus()})",
    )
    analizador.add_argument(
        "--salida", type=Path, default=None,
        help=f"Base a generar (por defecto: {config.ruta_base_datos()})",
    )
    opciones = analizador.parse_args(argumentos)

    try:
        informe = etl.construir(opciones.corpus, opciones.salida)
    except (FileNotFoundError, LookupError, TypeError, ValueError) as error:
        print(f"Error: {error}")
        return 1

    print(f"Base generada en {informe.ruta}")
    print(f"Países cargados: {informe.paises}")
    for tabla, filas in sorted(informe.conteos.items()):
        print(f"  {tabla:<24}{filas:>8,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
