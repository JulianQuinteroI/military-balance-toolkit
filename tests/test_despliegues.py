"""Tests de las secciones DEPLOYMENT y FOREIGN FORCES."""

from mb2026.corpus import Item
from mb2026.parsers.despliegues import parsear_despliegues, parsear_fuerzas_extranjeras


def _heading(texto, nivel=2):
    return Item(pagina=418, tipo="heading", md=f"## {texto}", texto=texto, nivel=nivel)


def _texto(texto):
    return Item(pagina=418, tipo="text", md=texto, texto=texto)


class TestDespliegues:
    def test_separa_por_destino(self):
        items = (
            _heading("DEPLOYMENT"),
            _texto(
                "CENTRAL AFRICAN REPUBLIC: UN • MINUSCA 2 EGYPT: MFO 275; 1 inf bn "
                "LEBANON: UN • UNIFIL 1"
            ),
        )
        destinos = [d.destino for d in parsear_despliegues(items)]
        assert destinos == ["CENTRAL AFRICAN REPUBLIC", "EGYPT", "LEBANON"]

    def test_lee_organizacion_y_mision(self):
        items = (_heading("DEPLOYMENT"), _texto("CYPRUS: UN • UNFICYP 245; 2 inf coy"))
        despliegue = parsear_despliegues(items)[0]
        assert despliegue.organizacion == "UN"
        assert despliegue.mision == "UNFICYP"

    def test_lee_los_efectivos_antes_del_punto_y_coma(self):
        items = (_heading("DEPLOYMENT"), _texto("CYPRUS: UN • UNFICYP 245; 2 inf coy"))
        assert parsear_despliegues(items)[0].efectivos.valor == 245

    def test_no_confunde_un_conteo_de_instalaciones_con_efectivos(self):
        items = (
            _heading("DEPLOYMENT"),
            _texto("ARUBA: US Southern Command • 1 Cooperative Security Location"),
        )
        assert parsear_despliegues(items)[0].efectivos is None

    def test_conserva_el_detalle_crudo(self):
        items = (_heading("DEPLOYMENT"), _texto("EGYPT: MFO 275; 1 inf bn"))
        assert parsear_despliegues(items)[0].detalle == "MFO 275; 1 inf bn"

    def test_admite_destinos_compuestos(self):
        items = (
            _heading("DEPLOYMENT"),
            _texto("INDIA/PAKISTAN: UN • UNMOGIP 2 MIDDLE EAST: UN • UNTSO 3"),
        )
        assert [d.destino for d in parsear_despliegues(items)] == [
            "INDIA/PAKISTAN",
            "MIDDLE EAST",
        ]

    def test_se_detiene_en_la_seccion_siguiente(self):
        items = (
            _heading("DEPLOYMENT"),
            _texto("CYPRUS: UN • UNFICYP 6"),
            _heading("FOREIGN FORCES"),
            _texto("PERU: algo que no es un despliegue propio 99"),
        )
        assert len(parsear_despliegues(items)) == 1

    def test_ficha_sin_despliegues(self):
        assert parsear_despliegues((_texto("otra cosa"),)) == ()


NOMBRES = frozenset({"United States", "United Kingdom", "Germany", "Singapore", "Russia"})


class TestFuerzasExtranjeras:
    def test_separa_por_pais_de_origen(self):
        items = (
            Item(pagina=418, tipo="heading", md="## FOREIGN FORCES",
                 texto="FOREIGN FORCES", nivel=2),
            _texto("United Kingdom BATUS 70 United States 150"),
        )
        fuerzas = parsear_fuerzas_extranjeras(items, NOMBRES)
        assert [f.origen for f in fuerzas] == ["United Kingdom", "United States"]

    def test_lee_los_efectivos_al_final_del_tramo(self):
        items = (
            Item(pagina=418, tipo="heading", md="## FOREIGN FORCES",
                 texto="FOREIGN FORCES", nivel=2),
            _texto("United States US Southern Command: 50"),
        )
        fuerza = parsear_fuerzas_extranjeras(items, NOMBRES)[0]
        assert fuerza.efectivos.valor == 50
        assert fuerza.detalle == "US Southern Command:"

    def test_conserva_el_tramo_sin_cifra(self):
        items = (
            Item(pagina=418, tipo="heading", md="## FOREIGN FORCES",
                 texto="FOREIGN FORCES", nivel=2),
            _texto("Singapore 3 trg camp (incl inf and arty)"),
        )
        fuerza = parsear_fuerzas_extranjeras(items, NOMBRES)[0]
        assert fuerza.origen == "Singapore"
        assert "trg camp" in fuerza.detalle

    def test_ficha_sin_fuerzas_extranjeras(self):
        assert parsear_fuerzas_extranjeras((_texto("otra cosa"),), NOMBRES) == ()
