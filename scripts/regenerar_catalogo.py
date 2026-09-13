"""Regenera el catálogo congelado de códigos de país desde la base.

Uso: uv run python scripts/regenerar_catalogo.py
Ejecutarlo solo al cargar una edición nueva del volumen.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from mb2026 import config

_RAIZ = Path(__file__).resolve().parents[1]
_DESTINO = _RAIZ / "src" / "mb2026" / "consulta" / "catalogo.py"
_POR_LINEA = 8

_CABECERA = '''"""Catálogo de códigos de país del volumen, congelado para validar alias.

Se genera con scripts/regenerar_catalogo.py a partir de la base y se versiona
para que los tests puedan comprobar que ningún alias apunta a un código
inexistente sin depender de que la base esté construida.
"""

from __future__ import annotations

#: Códigos que el IISS usa para los países con ficha propia.
CODIGOS_CONOCIDOS: frozenset[str] = frozenset(
    {
'''


def main() -> None:
    ruta = config.ruta_base_datos()
    if not ruta.exists():
        raise SystemExit(f"No existe la base {ruta}. Ejecuta 'uv run mb2026' primero.")
    conexion = sqlite3.connect(ruta)
    try:
        codigos = sorted(fila[0] for fila in conexion.execute("SELECT codigo FROM paises"))
    finally:
        conexion.close()

    lineas = [_CABECERA]
    for inicio in range(0, len(codigos), _POR_LINEA):
        tramo = codigos[inicio : inicio + _POR_LINEA]
        lineas.append("        " + ", ".join(f'"{codigo}"' for codigo in tramo) + ",\n")
    lineas.append("    }\n)\n")
    _DESTINO.write_text("".join(lineas), encoding="utf8")
    print(f"{len(codigos)} códigos escritos en {_DESTINO}")


if __name__ == "__main__":
    main()
