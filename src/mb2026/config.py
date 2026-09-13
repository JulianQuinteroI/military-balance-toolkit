"""Rutas y constantes de configuración del proyecto."""

from __future__ import annotations

import os
from pathlib import Path

#: Directorio del corpus fuente. Configurable con ``MB2026_SOURCE``.
VARIABLE_ENTORNO_CORPUS = "MB2026_SOURCE"
RUTA_CORPUS_POR_DEFECTO = Path.home() / "Downloads" / "Military Balance Parser 2026"

#: Nombres de archivo tal como los produjo el parser de origen.
ARCHIVO_JSON = "MIlitary Balance 2026 - HN .json"
ARCHIVO_MD = "MIlitary Balance 2026 - HN .md"

#: Edición y corte de los datos, para citación.
EDICION = 2026
CORTE_DATOS = "noviembre de 2025"
FUENTE_CITA = "IISS, The Military Balance 2026"

_RAIZ_PROYECTO = Path(__file__).resolve().parents[2]


def directorio_corpus() -> Path:
    """Directorio del corpus fuente, según entorno o valor por defecto."""
    configurado = os.environ.get(VARIABLE_ENTORNO_CORPUS)
    return Path(configurado).expanduser() if configurado else RUTA_CORPUS_POR_DEFECTO


def ruta_json_corpus() -> Path:
    """Ruta al parse JSON por páginas."""
    return directorio_corpus() / ARCHIVO_JSON


def ruta_md_corpus() -> Path:
    """Ruta al parse markdown."""
    return directorio_corpus() / ARCHIVO_MD


def ruta_base_datos() -> Path:
    """Ruta de la base SQLite generada (fuera de git, ver .gitignore)."""
    return _RAIZ_PROYECTO / "data" / "mb2026.sqlite"
