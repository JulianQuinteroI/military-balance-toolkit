"""Tests de la extracción económica y demográfica de una ficha."""

import pytest

from mb2026.corpus import Item
from mb2026.parsers.economia import INDICADORES, parsear_economia


def _tabla(filas, pagina=418):
    return Item(pagina=pagina, tipo="table", md="", texto="tabla", filas=filas)


def _texto(texto, pagina=418):
    return Item(pagina=pagina, tipo="text", md=texto, texto=texto)


TABLA_ECONOMIA = (
    ("Colombian Peso COP", "", "2024", "2025", "2026"),
    ("GDP", "COP", "1.71qrn", "1.83qrn", "1.94qrn"),
    ("", "USD", "419bn", "438bn", "462bn"),
    ("Real GDP growth", "%", "1.6", "2.5", "2.3"),
    ("Def bdgt [a]", "COP", "31.2trn", "34.6trn", "38.7trn"),
    ("", "USD", "7.65bn", "8.27bn", "9.20bn"),
    ("FMA (US)", "USD", "38.0m", "38.5m", "0.0m"),
)
TABLA_TENDENCIA = (
    ("Year", "Defence budget (USDbn, constant 2015)"),
    ("2024", "6.5"),
    ("2025", "7.02"),
)
TABLA_DEMOGRAFIA = (
    ("Age", "0–14", "15–19", "20–24", "25–29", "30–64", "65 plus"),
    ("Male", "11.3%", "3.8%", "3.9%", "4.0%", "20.8%", "5.0%"),
    ("Female", "10.8%", "3.6%", "3.7%", "3.9%", "22.6%", "6.5%"),
)


@pytest.fixture
def economia():
    return parsear_economia(
        (
            _tabla(TABLA_ECONOMIA),
            _texto("[a] Excludes security budget"),
            _tabla(TABLA_TENDENCIA),
            _tabla((("Population", "49,842,298", "", "", "", "", ""),)),
            _tabla(TABLA_DEMOGRAFIA),
        )
    )


class TestMoneda:
    def test_separa_nombre_y_codigo(self, economia):
        assert economia.moneda.nombre == "Colombian Peso"
        assert economia.moneda.codigo == "COP"

    def test_tolera_el_espacio_perdido(self):
        eco = parsear_economia((_tabla((("Chinese Yuan RenminbiCNY", "", "2025"),
                                        ("GDP", "CNY", "1bn"))),))
        assert eco.moneda.codigo == "CNY"
        assert eco.moneda.nombre == "Chinese Yuan Renminbi"


class TestValores:
    def test_una_fila_por_indicador_unidad_y_anio(self, economia):
        pib = [v for v in economia.valores if v.indicador == INDICADORES["GDP"]]
        assert len(pib) == 6  # 3 años x 2 unidades

    def test_arrastra_la_etiqueta_a_la_fila_de_continuacion(self, economia):
        usd = [
            v
            for v in economia.valores
            if v.indicador == INDICADORES["GDP"] and v.unidad == "USD"
        ]
        assert {v.anio for v in usd} == {2024, 2025, 2026}

    def test_convierte_a_unidades_absolutas(self, economia):
        bdgt = next(
            v
            for v in economia.valores
            if v.indicador == INDICADORES["Def bdgt"]
            and v.unidad == "USD"
            and v.anio == 2025
        )
        assert bdgt.valor == pytest.approx(8.27e9)

    def test_normaliza_las_etiquetas_con_nota_al_pie(self, economia):
        assert INDICADORES["Def bdgt"] in {v.indicador for v in economia.valores}

    def test_conserva_los_porcentajes_sin_escalar(self, economia):
        crecimiento = next(
            v for v in economia.valores
            if v.indicador == INDICADORES["Real GDP growth"] and v.anio == 2025
        )
        assert crecimiento.valor == pytest.approx(2.5)
        assert crecimiento.unidad == "%"

    def test_recoge_las_notas_al_pie(self, economia):
        assert "[a] Excludes security budget" in economia.notas


class TestEtiquetasDefectuosas:
    """El original pierde espacios al componer y trae alguna errata."""

    def test_espacio_perdido_en_la_etiqueta(self):
        eco = parsear_economia(
            (_tabla((("Krone KRO", "", "2025"), ("Real GDPgrowth", "%", "2.5"))),)
        )
        assert eco.valores[0].indicador == INDICADORES["Real GDP growth"]

    def test_errata_en_la_etiqueta_del_presupuesto(self):
        eco = parsear_economia(
            (_tabla((("Krone KRO", "", "2025"), ("Def bgt", "USD", "1bn"))),)
        )
        assert eco.valores[0].indicador == INDICADORES["Def bdgt"]


class TestSerieReal:
    def test_lee_la_serie_y_su_unidad(self, economia):
        assert economia.unidad_serie == "USDbn, constant 2015"
        assert dict(economia.serie_real) == {2024: 6.5, 2025: 7.02}


class TestPoblacionYDemografia:
    def test_lee_la_poblacion_de_la_tabla(self, economia):
        assert economia.poblacion == 49_842_298

    def test_lee_la_poblacion_del_texto_corrido(self):
        eco = parsear_economia((_texto("Population 421,960"),))
        assert eco.poblacion == 421_960

    def test_desdobla_la_piramide_por_sexo_y_rango(self, economia):
        assert len(economia.demografia) == 12
        varon = next(
            d for d in economia.demografia if d.sexo == "Male" and d.rango == "0–14"
        )
        assert varon.porcentaje == pytest.approx(11.3)


class TestFichasSinDatos:
    def test_ficha_sin_tabla_economica_no_falla(self):
        eco = parsear_economia(
            (_texto("Definitive macro- and defence economic data not available"),)
        )
        assert eco.moneda is None
        assert eco.valores == ()
        assert eco.poblacion is None
