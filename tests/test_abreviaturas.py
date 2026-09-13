"""Tests del diccionario de abreviaturas del IISS (Tabla 8)."""

import pytest

from mb2026.corpus import Item
from mb2026.parsers.abreviaturas import parsear_abreviaturas


def _heading(texto, pagina=535):
    return Item(pagina=pagina, tipo="heading", md=f"## {texto}", texto=texto, nivel=2)


def _tabla(filas, pagina=535):
    return Item(pagina=pagina, tipo="table", md="", texto="tabla", filas=filas)


class TestParsearAbreviaturas:
    def test_desdobla_las_tres_parejas_por_fila(self):
        items = (
            _heading("Table 8 List of abbreviations for data sections"),
            _tabla(
                (
                    ("AAM", "air-to-air missile", "aslt", "assault", "def", "defence"),
                )
            ),
        )
        abreviaturas = parsear_abreviaturas(items)
        assert len(abreviaturas) == 3
        assert {a.sigla for a in abreviaturas} == {"AAM", "aslt", "def"}

    def test_conserva_definiciones_multilinea(self):
        items = (
            _heading("Table 8 List of abbreviations for data sections"),
            _tabla((("SLEP", "service-life-extension\nprogramme", "", "", "", ""),)),
        )
        abreviatura = parsear_abreviaturas(items)[0]
        assert abreviatura.definicion == "service-life-extension programme"

    def test_descarta_parejas_incompletas(self):
        items = (
            _heading("Table 8 List of abbreviations for data sections"),
            _tabla((("AAM", "air-to-air missile", "aslt", "", "", "defence"),)),
        )
        assert len(parsear_abreviaturas(items)) == 1

    def test_abarca_varias_tablas_consecutivas(self):
        items = (
            _heading("Table 8 List of abbreviations for data sections"),
            _tabla((("AAM", "air-to-air missile", "", "", "", ""),), pagina=535),
            _tabla((("LACM", "land-attack cruise missile", "", "", "", ""),), pagina=536),
            _heading("Table 9 International comparisons", pagina=537),
            _tabla((("Canada", "24,056"),), pagina=537),
        )
        siglas = {a.sigla for a in parsear_abreviaturas(items)}
        assert siglas == {"AAM", "LACM"}

    def test_no_duplica_siglas(self):
        items = (
            _heading("Table 8 List of abbreviations for data sections"),
            _tabla((("AAM", "air-to-air missile", "AAM", "air-to-air missile", "", ""),)),
        )
        assert len(parsear_abreviaturas(items)) == 1

    def test_falla_si_no_encuentra_la_tabla(self):
        with pytest.raises(LookupError, match="Tabla 8"):
            parsear_abreviaturas((_heading("Otra cosa"),))
