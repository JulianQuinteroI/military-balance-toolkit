"""Tests de la segmentación del corpus en fichas de país."""

import pytest

from mb2026.corpus import Item
from mb2026.parsers.indice_paises import EntradaIndice
from mb2026.segmentacion import (
    DESFASE_PAGINA,
    PAGINA_INICIO_REFERENCIA,
    region_de_pagina,
    segmentar_paises,
)


def _heading(texto, pagina, nivel=1):
    return Item(pagina=pagina, tipo="heading", md=f"{'#' * nivel} {texto}",
                texto=texto, nivel=nivel)


def _texto(texto, pagina):
    return Item(pagina=pagina, tipo="text", md=texto, texto=texto)


INDICE = (
    EntradaIndice("Colombia", "COL", 417),
    EntradaIndice("Costa Rica", "CRI", 419),
)
ITEMS = (
    _texto("cierre de la ficha anterior", 418),
    _heading("Colombia COL", 418),
    _texto("ACTIVE 285,000", 418),
    _texto("EQUIPMENT BY TYPE", 419),
    _heading("Costa Rica CRI", 420, nivel=2),
    _texto("ACTIVE NIL", 420),
)


class TestSegmentarPaises:
    def test_encuentra_todas_las_fichas_del_indice(self):
        fichas = segmentar_paises(ITEMS, INDICE)
        assert [f.codigo for f in fichas] == ["COL", "CRI"]

    def test_la_ficha_abarca_hasta_la_siguiente(self):
        colombia = segmentar_paises(ITEMS, INDICE)[0]
        assert [i.texto for i in colombia.items] == ["ACTIVE 285,000", "EQUIPMENT BY TYPE"]

    def test_la_ultima_ficha_llega_al_final_del_flujo(self):
        costa_rica = segmentar_paises(ITEMS, INDICE)[1]
        assert [i.texto for i in costa_rica.items] == ["ACTIVE NIL"]

    def test_excluye_el_propio_encabezado_de_la_ficha(self):
        colombia = segmentar_paises(ITEMS, INDICE)[0]
        assert all(i.texto != "Colombia COL" for i in colombia.items)

    def test_registra_ambas_paginas(self):
        colombia = segmentar_paises(ITEMS, INDICE)[0]
        assert colombia.pagina_impresa == 417
        assert colombia.pagina_json == 417 + DESFASE_PAGINA

    def test_asigna_la_region_del_capitulo(self):
        assert all(f.region == "Latin America and the Caribbean"
                   for f in segmentar_paises(ITEMS, INDICE))

    def test_tolera_espacios_perdidos_en_el_nombre_del_indice(self):
        indice = (EntradaIndice("Trinidad andTobago", "TTO", 443),)
        items = (_heading("Trinidad and Tobago TTO", 444), _texto("ACTIVE 4,050", 444))
        assert segmentar_paises(items, indice)[0].nombre == "Trinidad and Tobago"

    def test_tolera_acentos_divergentes(self):
        indice = (EntradaIndice("Cote d'Ivoire", "CIV", 484),)
        items = (_heading("Côte d'Ivoire CIV", 485), _texto("ACTIVE 25,400", 485))
        assert segmentar_paises(items, indice)[0].codigo == "CIV"

    def test_desambigua_por_proximidad_de_pagina(self):
        """El mismo par nombre+código puede aparecer en un titulillo o referencia."""
        indice = (EntradaIndice("Colombia", "COL", 417),)
        items = (
            _heading("Colombia COL", 40),
            _texto("mención suelta", 40),
            _heading("Colombia COL", 418),
            _texto("ACTIVE 285,000", 418),
        )
        ficha = segmentar_paises(items, indice)[0]
        assert ficha.items[0].texto == "ACTIVE 285,000"

    def test_la_ultima_ficha_de_un_capitulo_no_absorbe_el_siguiente(self):
        """Tras el último país de un capítulo viene el análisis regional del siguiente."""
        indice = (EntradaIndice("United States", "US", 39),)
        items = (
            _heading("United States US", 40),
            _texto("ACTIVE 1,339,750", 40),
            _texto("Europe: regional overview", 58),
        )
        ficha = segmentar_paises(items, indice)[0]
        assert [i.texto for i in ficha.items] == ["ACTIVE 1,339,750"]

    def test_la_ultima_ficha_del_volumen_no_absorbe_la_seccion_de_referencia(self):
        indice = (EntradaIndice("Zimbabwe", "ZWE", 523),)
        items = (
            _heading("Zimbabwe ZWE", 524),
            _texto("ACTIVE 29,000", 525),
            _texto("Explanatory notes", PAGINA_INICIO_REFERENCIA + DESFASE_PAGINA),
        )
        ficha = segmentar_paises(items, indice)[0]
        assert [i.texto for i in ficha.items] == ["ACTIVE 29,000"]

    def test_reporta_las_fichas_no_localizadas(self):
        indice = (*INDICE, EntradaIndice("Ruritania", "RUR", 999))
        with pytest.raises(LookupError, match="RUR"):
            segmentar_paises(ITEMS, indice)


class TestRegionDePagina:
    @pytest.mark.parametrize(
        "pagina,region",
        [
            (17, "North America"),
            (98, "Europe"),
            (167, "Russia and Eurasia"),
            (240, "Asia"),
            (338, "Middle East and North Africa"),
            (417, "Latin America and the Caribbean"),
            (503, "Sub-Saharan Africa"),
        ],
    )
    def test_ubica_cada_capitulo(self, pagina, region):
        assert region_de_pagina(pagina) == region

    def test_pagina_fuera_de_los_capitulos_de_datos(self):
        assert region_de_pagina(5) == ""


class TestCortesUnicos:
    def test_rechaza_dos_fichas_en_el_mismo_encabezado(self):
        """Una de las dos quedaría vacía sin que nada lo delatara."""
        indice = (
            EntradaIndice("Colombia", "COL", 417),
            EntradaIndice("Colombia", "COL", 418),
        )
        items = (_heading("Colombia COL", 418), _texto("ACTIVE 285,000", 418))
        with pytest.raises(LookupError, match="mismo"):
            segmentar_paises(items, indice)
