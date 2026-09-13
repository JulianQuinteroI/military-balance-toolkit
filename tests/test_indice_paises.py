"""Tests del índice autoritativo de países (Tabla 11) y de códigos (Tabla 10)."""

import pytest

from mb2026.corpus import Item
from mb2026.parsers.indice_paises import (
    EntradaIndice,
    parsear_codigos_pais,
    parsear_indice_paises,
)


def _tabla(filas, pagina=544):
    return Item(pagina=pagina, tipo="table", md="", texto="Table 11 Index", filas=filas)


def _heading(texto, pagina=544, nivel=2):
    return Item(pagina=pagina, tipo="heading", md=f"## {texto}", texto=texto, nivel=nivel)


class TestParsearIndicePaises:
    def test_lee_nombre_codigo_y_pagina(self):
        items = (
            _heading("Table 11 Index of countries and territories"),
            _tabla(
                (
                    (
                        "Afghanistan AFG . . . . . .240",
                        "Georgia GEO . . . . . .182",
                        "Nicaragua NIC . . . . . .436",
                    ),
                )
            ),
        )
        entradas = parsear_indice_paises(items)
        assert EntradaIndice("Afghanistan", "AFG", 240) in entradas
        assert EntradaIndice("Nicaragua", "NIC", 436) in entradas

    def test_soporta_nombres_con_comas_y_apostrofes(self):
        items = (
            _heading("Table 11 Index of countries and territories"),
            _tabla(
                (
                    (
                        "Korea, Democratic People's Republic of DPRK . . .259",
                        "Côte d'Ivoire CIV . . . . . .484",
                        "",
                    ),
                )
            ),
        )
        entradas = {e.codigo: e for e in parsear_indice_paises(items)}
        assert entradas["DPRK"].nombre == "Korea, Democratic People's Republic of"
        assert entradas["CIV"].nombre == "Côte d'Ivoire"

    def test_ignora_celdas_vacias(self):
        items = (
            _heading("Table 11 Index of countries and territories"),
            _tabla((("Zambia ZMB . . .521", "", ""),)),
        )
        assert len(parsear_indice_paises(items)) == 1

    def test_devuelve_tupla_ordenada_por_pagina(self):
        items = (
            _heading("Table 11 Index of countries and territories"),
            _tabla(
                (
                    ("Zambia ZMB . . .521", "Albania ALB . . .74", ""),
                )
            ),
        )
        entradas = parsear_indice_paises(items)
        assert isinstance(entradas, tuple)
        assert [e.codigo for e in entradas] == ["ALB", "ZMB"]

    def test_falla_si_no_encuentra_la_tabla(self):
        with pytest.raises(LookupError, match="Tabla 11"):
            parsear_indice_paises((_heading("Otra cosa"),))


class TestParsearCodigosPais:
    def test_lee_pares_codigo_nombre(self):
        items = (
            _heading("Table 10 Index of country/territory abbreviations", pagina=543),
            Item(
                pagina=543,
                tipo="text",
                md="",
                texto="AFG.......Afghanistan ALB....... Albania BIOT...British Indian Ocean Territory",
            ),
        )
        codigos = parsear_codigos_pais(items)
        assert codigos["AFG"] == "Afghanistan"
        assert codigos["BIOT"] == "British Indian Ocean Territory"

    def test_falla_si_no_encuentra_la_tabla(self):
        with pytest.raises(LookupError, match="Tabla 10"):
            parsear_codigos_pais((_heading("Otra cosa"),))
