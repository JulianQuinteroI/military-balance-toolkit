"""Render de resultados: texto alineado para leer, JSON para encadenar."""

from __future__ import annotations

import json
from dataclasses import asdict

from mb2026.consulta.consultas import Resultado, Tabla
from mb2026.texto import SUFIJOS_MAGNITUD

#: Marca para una celda sin dato, para no confundirla con un cero.
VACIO = "—"
#: A partir de esta magnitud se separan los miles.
UMBRAL_MILES = 1000
#: Rótulos cuyos enteros son identificadores, no cantidades. Valen tanto como
#: nombre de columna como de etiqueta de fila, porque hay tablas en ambos ejes.
ROTULOS_SIN_SEPARADOR: frozenset[str] = frozenset(
    {"Año", "Year", "Página", "Page", "#"}
)
_SEPARACION = "  "
_SUFIJOS_DESCENDENTES = sorted(
    SUFIJOS_MAGNITUD.items(), key=lambda par: par[1], reverse=True
)


def _magnitud(valor: float) -> str:
    """Escribe una cifra grande con los sufijos del propio volumen."""
    for sufijo, factor in _SUFIJOS_DESCENDENTES:
        if abs(valor) >= factor:
            return f"{valor / factor:,.2f}".rstrip("0").rstrip(".") + f" {sufijo}"
    return f"{valor:,.0f}"


def _celda(valor: object, *, separar_miles: bool = True) -> str:
    if valor is None or valor == "":
        return VACIO
    if isinstance(valor, bool):
        return "sí" if valor else "no"
    if isinstance(valor, int):
        return f"{valor:,}" if separar_miles and abs(valor) >= UMBRAL_MILES else str(valor)
    if isinstance(valor, float):
        if abs(valor) >= min(SUFIJOS_MAGNITUD.values()):
            return _magnitud(valor)
        return f"{valor:,.0f}" if abs(valor) >= UMBRAL_MILES else f"{valor:g}"
    return str(valor)


def _fila_a_texto(fila: tuple[object, ...], tabla: Tabla) -> list[str]:
    etiqueta = str(fila[0]) if fila else ""
    return [
        _celda(
            valor,
            separar_miles=(
                columna not in ROTULOS_SIN_SEPARADOR
                and etiqueta not in ROTULOS_SIN_SEPARADOR
            ),
        )
        for valor, columna in zip(fila, tabla.columnas, strict=False)
    ]


def _tabla_a_texto(tabla: Tabla) -> str:
    lineas = [tabla.titulo, "─" * len(tabla.titulo)]
    if not tabla.filas:
        lineas.append("(sin resultados)")
    else:
        celdas = [
            list(tabla.columnas),
            *(_fila_a_texto(fila, tabla) for fila in tabla.filas),
        ]
        anchos = [max(len(fila[i]) for fila in celdas) for i in range(len(celdas[0]))]
        lineas.extend(
            _SEPARACION.join(
                texto.ljust(ancho)
                for texto, ancho in zip(fila, anchos, strict=False)
            ).rstrip()
            for fila in celdas
        )
    if tabla.nota:
        lineas.append(f"  {tabla.nota}")
    return "\n".join(lineas)


def como_texto(resultado: Resultado) -> str:
    """Resultado legible en terminal."""
    bloques = [_tabla_a_texto(tabla) for tabla in resultado.tablas]
    return "\n\n".join([*bloques, f"Fuente: {resultado.cita}"])


def como_json(resultado: Resultado) -> str:
    """Resultado serializado, para encadenar con otra herramienta."""
    return json.dumps(asdict(resultado), ensure_ascii=False, indent=2)
