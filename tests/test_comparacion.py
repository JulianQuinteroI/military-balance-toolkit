"""Tests de la comparación internacional de presupuestos y personal (Tabla 9)."""

import pytest

from mb2026.corpus import Item
from mb2026.parsers.comparacion import ANIO_PERSONAL, ANIOS_GASTO, parsear_comparacion

CABECERA = (
    "",
    "Defence Budget (current USDm)2023",
    "Defence Budget (current USDm)2024",
    "Defence Budget (current USDm)2025",
    "Defence Budget per capita (current USD)2023",
    "Defence Budget per capita (current USD)2024",
    "Defence Budget per capita (current USD)2025",
    "Defence Budget % of GDP2023",
    "Defence Budget % of GDP2024",
    "Defence Budget % of GDP2025",
    "Active Armed Forces (000)2025",
    "Estimated Reservists (000)2025",
    "Gendarmerie & Paramilitary (000)2025",
)
CANADA = ("Canada", "24,056", "26,873", "31,213", "625", "693", "797",
          "1.11", "1.20", "1.37", "63", "29", "7")
REGION = ("North America",) + ("",) * 12
TOTAL = ("Total / Average", "943,821", "994,835", "952,233", "1,666", "1,762",
         "1,761", "2.21", "2.25", "2.19", "1,403", "833", "7")


def _heading(pagina=537):
    texto = "Table 9 International comparisons of defence budgets and military personnel"
    return Item(pagina=pagina, tipo="heading", md=f"# {texto}", texto=texto, nivel=1)


def _tabla(filas, pagina=537):
    return Item(pagina=pagina, tipo="table", md="", texto="tabla", filas=filas)


@pytest.fixture
def comparacion():
    return parsear_comparacion((_heading(), _tabla((CABECERA, REGION, CANADA, TOTAL))))


class TestGasto:
    def test_produce_una_fila_por_anio(self, comparacion):
        canada = [f for f in comparacion.gasto if f.pais == "Canada"]
        assert sorted(f.anio for f in canada) == list(ANIOS_GASTO)

    def test_convierte_cifras_con_separador_de_miles(self, comparacion):
        fila = next(f for f in comparacion.gasto if f.pais == "Canada" and f.anio == 2025)
        assert fila.presupuesto_usd_m == pytest.approx(31213.0)
        assert fila.per_capita_usd == pytest.approx(797.0)
        assert fila.pct_pib == pytest.approx(1.37)

    def test_arrastra_la_region_de_la_fila_de_cabecera(self, comparacion):
        fila = next(f for f in comparacion.gasto if f.pais == "Canada" and f.anio == 2023)
        assert fila.region == "North America"

    def test_marca_las_filas_agregadas(self, comparacion):
        agregados = {f.pais for f in comparacion.gasto if f.es_agregado}
        assert agregados == {"Total / Average"}

    def test_no_emite_filas_para_las_cabeceras_de_region(self, comparacion):
        assert "North America" not in {f.pais for f in comparacion.gasto}


class TestPersonal:
    def test_solo_emite_el_anio_disponible(self, comparacion):
        assert {f.anio for f in comparacion.personal} == {ANIO_PERSONAL}

    def test_lee_los_tres_componentes_en_miles(self, comparacion):
        canada = next(f for f in comparacion.personal if f.pais == "Canada")
        assert canada.activos_miles == pytest.approx(63.0)
        assert canada.reservistas_miles == pytest.approx(29.0)
        assert canada.gendarmeria_miles == pytest.approx(7.0)


class TestValidacion:
    def test_rechaza_una_cabecera_inesperada(self):
        mala = ("", "Otra cosa", *CABECERA[2:])
        with pytest.raises(ValueError, match="cabecera"):
            parsear_comparacion((_heading(), _tabla((mala, CANADA))))

    def test_tolera_espacios_perdidos_en_la_cabecera(self):
        """El corpus imprime 'Active ArmedForces' y 'Defence Budget(current...'."""
        apretada = tuple(c.replace(" ", "") for c in CABECERA)
        comparacion = parsear_comparacion((_heading(), _tabla((apretada, CANADA))))
        assert len(comparacion.gasto) == len(ANIOS_GASTO)

    def test_falla_si_no_encuentra_la_tabla(self):
        with pytest.raises(LookupError, match="Tabla 9"):
            parsear_comparacion((Item(pagina=1, tipo="text", md="", texto="nada"),))

    def test_tolera_celdas_vacias(self):
        parcial = ("Haiti", "", "", "", "", "", "", "", "", "", "0", "0", "0")
        comparacion = parsear_comparacion((_heading(), _tabla((CABECERA, parcial))))
        assert all(f.presupuesto_usd_m is None for f in comparacion.gasto)
        assert comparacion.personal[0].activos_miles == pytest.approx(0.0)
