"""Tests del localizador de tablas de referencia.

Los dos casos límite provienen del corpus real: la Tabla 9 repite su encabezado
en dos items consecutivos y la Tabla 11 lleva el título dentro de la propia tabla.
"""

import pytest

from mb2026.corpus import Item
from mb2026.parsers.localizar import indice_de_ancla, tablas_tras


def _heading(texto, pagina=1, nivel=2):
    return Item(pagina=pagina, tipo="heading", md=f"## {texto}", texto=texto, nivel=nivel)


def _tabla(ancho, pagina=1, texto="tabla", nivel=0):
    filas = ((("x",) * ancho),)
    return Item(pagina=pagina, tipo="table", md="", texto=texto, nivel=nivel, filas=filas)


class TestIndiceDeAncla:
    def test_encuentra_un_encabezado(self):
        items = (_heading("Otra"), _heading("Table 9 International comparisons"))
        assert indice_de_ancla(items, "Table 9", "Tabla 9") == 1

    def test_encuentra_un_ancla_que_es_la_propia_tabla(self):
        items = (_heading("Otra"), _tabla(3, texto="Table 11 Index of countries", nivel=3))
        assert indice_de_ancla(items, "Table 11", "Tabla 11") == 1

    def test_falla_con_mensaje_util(self):
        with pytest.raises(LookupError, match="Tabla 42"):
            indice_de_ancla((_heading("Otra"),), "Table 42", "Tabla 42")


class TestTablasTras:
    def test_tolera_el_encabezado_repetido(self):
        items = (
            _heading("Table 9 International comparisons"),
            _heading("Table 9 International comparisons"),
            _tabla(13),
            _tabla(13),
        )
        assert len(tuple(tablas_tras(items, 0, 13, "Table 9"))) == 2

    def test_incluye_el_ancla_cuando_es_tabla(self):
        items = (_tabla(3, texto="Table 11 Index of countries", nivel=3),)
        assert len(tuple(tablas_tras(items, 0, 3, "Table 11"))) == 1

    def test_se_detiene_en_la_siguiente_tabla_de_referencia(self):
        items = (
            _heading("Table 8 List of abbreviations"),
            _tabla(6),
            _heading("Table 9 International comparisons"),
            _tabla(6),
        )
        assert len(tuple(tablas_tras(items, 0, 6, "Table 8"))) == 1

    def test_atraviesa_items_de_texto_intercalados(self):
        items = (
            _heading("Table 9 International comparisons"),
            _tabla(13),
            Item(pagina=2, tipo="text", md="", texto="537"),
            _tabla(13, pagina=3),
        )
        assert len(tuple(tablas_tras(items, 0, 13, "Table 9"))) == 2

    def test_descarta_tablas_de_otro_ancho(self):
        items = (_heading("Table 9 International comparisons"), _tabla(3), _tabla(13))
        assert len(tuple(tablas_tras(items, 0, 13, "Table 9"))) == 1
