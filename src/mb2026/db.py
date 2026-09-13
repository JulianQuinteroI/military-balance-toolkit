"""Creación y carga de la base SQLite derivada del volumen."""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterable, Sequence
from pathlib import Path

_RUTA_ESQUEMA = Path(__file__).with_name("schema.sql")

#: Los nombres de tabla y columna no pueden ir parametrizados, así que se
#: validan antes de interpolarlos: es la única defensa contra que un
#: identificador de otra procedencia acabe dentro del texto de la sentencia.
_RE_IDENTIFICADOR = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def crear_base(ruta: Path) -> sqlite3.Connection:
    """Crea la base desde cero. Sustituye cualquier archivo previo."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.unlink(missing_ok=True)
    conexion = sqlite3.connect(ruta)
    conexion.executescript(_RUTA_ESQUEMA.read_text(encoding="utf8"))
    return conexion


def _validar_identificador(nombre: str) -> str:
    if not _RE_IDENTIFICADOR.match(nombre):
        raise ValueError(f"Identificador SQL no válido: {nombre!r}")
    return nombre


def _sentencia_insert(tabla: str, columnas: Sequence[str]) -> str:
    _validar_identificador(tabla)
    campos = ", ".join(_validar_identificador(columna) for columna in columnas)
    marcadores = ", ".join("?" * len(columnas))
    # S608: los identificadores pasaron por _validar_identificador; los valores
    # viajan siempre parametrizados.
    return f"INSERT INTO {tabla} ({campos}) VALUES ({marcadores})"  # noqa: S608


def insertar(
    conexion: sqlite3.Connection,
    tabla: str,
    columnas: Sequence[str],
    filas: Iterable[Sequence[object]],
) -> int:
    """Inserta filas en una tabla y devuelve cuántas se escribieron."""
    sentencia = _sentencia_insert(tabla, columnas)
    materializadas = list(filas)
    conexion.executemany(sentencia, materializadas)
    return len(materializadas)


def insertar_uno(
    conexion: sqlite3.Connection,
    tabla: str,
    columnas: Sequence[str],
    valores: Sequence[object],
) -> int:
    """Inserta una fila y devuelve su identificador.

    Hace falta cuando la fila siguiente necesita referenciar a esta, como en el
    árbol de unidades.
    """
    cursor = conexion.execute(_sentencia_insert(tabla, columnas), valores)
    identificador = cursor.lastrowid
    if identificador is None:
        raise ValueError(f"La inserción en {tabla} no devolvió identificador")
    return identificador


def conteos(conexion: sqlite3.Connection) -> dict[str, int]:
    """Número de filas de cada tabla, para el informe de carga."""
    tablas = [
        str(fila[0])
        for fila in conexion.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        )
    ]
    return {
        tabla: conexion.execute(
            f"SELECT COUNT(*) FROM {_validar_identificador(tabla)}"  # noqa: S608
        ).fetchone()[0]
        for tabla in tablas
    }
