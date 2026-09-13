"""Tests del resolutor de nombres: país, dominio y región."""

import pytest

from mb2026.consulta.resolver import (
    ALIAS_PAIS,
    dominios_de,
    region_de,
    resolver_pais,
)


class TestResolverPais:
    @pytest.fixture
    def catalogo(self):
        return {"COL": "Colombia", "VEN": "Venezuela", "BRZ": "Brazil", "US": "United States"}

    def test_acepta_el_codigo_del_iiss(self, catalogo):
        assert resolver_pais("COL", catalogo) == "COL"

    def test_acepta_el_codigo_en_minuscula(self, catalogo):
        assert resolver_pais("col", catalogo) == "COL"

    def test_acepta_el_nombre_en_ingles(self, catalogo):
        assert resolver_pais("Brazil", catalogo) == "BRZ"

    def test_acepta_el_nombre_en_espanol(self, catalogo):
        assert resolver_pais("Brasil", catalogo) == "BRZ"
        assert resolver_pais("Estados Unidos", catalogo) == "US"

    def test_ignora_acentos_y_mayusculas(self, catalogo):
        assert resolver_pais("venezuela", catalogo) == "VEN"
        assert resolver_pais("BRASIL", catalogo) == "BRZ"

    def test_nombre_desconocido(self, catalogo):
        with pytest.raises(LookupError, match="Ruritania"):
            resolver_pais("Ruritania", catalogo)

    def test_el_mensaje_sugiere_alternativas(self, catalogo):
        with pytest.raises(LookupError, match="Colombia"):
            resolver_pais("Colomvia", catalogo)


class TestAliasPais:
    def test_cubre_america_latina(self):
        for nombre in ("Brasil", "Perú", "México", "Haití", "Belice"):
            assert nombre.lower() in {a.lower() for a in ALIAS_PAIS}

    def test_no_apunta_a_codigos_inventados(self):
        """Todo alias debe resolver a un código que el volumen realmente usa."""
        from mb2026.consulta.catalogo import CODIGOS_CONOCIDOS

        desconocidos = sorted(set(ALIAS_PAIS.values()) - CODIGOS_CONOCIDOS)
        assert desconocidos == []


class TestDominios:
    def test_alias_de_dominio_agrupado(self):
        assert "AIRCRAFT" in dominios_de("aire")
        assert "HELICOPTERS" in dominios_de("aire")

    def test_alias_maritimo(self):
        assert "SUBMARINES" in dominios_de("mar")
        assert "PATROL AND COASTAL COMBATANTS" in dominios_de("naval")

    def test_alias_de_un_solo_dominio(self):
        assert dominios_de("submarinos") == ("SUBMARINES",)

    def test_admite_el_nombre_canonico(self):
        assert dominios_de("AIR DEFENCE") == ("AIR DEFENCE",)

    def test_dominio_desconocido(self):
        with pytest.raises(LookupError, match="astronaves"):
            dominios_de("astronaves")


class TestRegiones:
    @pytest.mark.parametrize(
        "alias,region",
        [
            ("latam", "Latin America and the Caribbean"),
            ("europa", "Europe"),
            ("mena", "Middle East and North Africa"),
            ("africa", "Sub-Saharan Africa"),
            ("Asia", "Asia"),
        ],
    )
    def test_resuelve_los_alias(self, alias, region):
        assert region_de(alias) == region

    def test_region_desconocida(self):
        with pytest.raises(LookupError, match="oceania"):
            region_de("oceania")
