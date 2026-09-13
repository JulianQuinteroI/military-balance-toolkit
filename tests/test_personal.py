"""Tests de la lectura de efectivos de una ficha."""

import pytest

from mb2026.corpus import Item
from mb2026.parsers.personal import (
    CATEGORIA_ACTIVO,
    CATEGORIA_GENDARMERIA,
    CATEGORIA_RESERVA,
    TOTAL,
    parsear_personal,
)


def _linea(texto, nivel=2):
    return Item(pagina=418, tipo="heading", md=f"## {texto}", texto=texto, nivel=nivel)


COLOMBIA = (
    _linea(
        "ACTIVE 285,000 (Army 206,400, Navy 60,300 Air 18,300) "
        "Gendarmerie & Paramilitary 165,050"
    ),
    Item(pagina=418, tipo="text", md="", texto="Conscript liability 18 months’ duration"),
    _linea("RESERVE 34,950 (Army 25,050 Navy 6,500 Air 3,400)"),
)


@pytest.fixture
def personal():
    return parsear_personal(COLOMBIA)


def _buscar(personal, categoria, componente):
    return next(
        e for e in personal.efectivos
        if e.categoria == categoria and e.componente == componente
    )


class TestTotales:
    def test_lee_el_total_activo(self, personal):
        assert _buscar(personal, CATEGORIA_ACTIVO, TOTAL).cantidad.valor == 285_000

    def test_lee_el_total_de_reserva(self, personal):
        assert _buscar(personal, CATEGORIA_RESERVA, TOTAL).cantidad.valor == 34_950

    def test_lee_la_gendarmeria_como_categoria_propia(self, personal):
        assert _buscar(personal, CATEGORIA_GENDARMERIA, TOTAL).cantidad.valor == 165_050


class TestComponentes:
    def test_desglosa_las_fuerzas(self, personal):
        assert _buscar(personal, CATEGORIA_ACTIVO, "Army").cantidad.valor == 206_400
        assert _buscar(personal, CATEGORIA_ACTIVO, "Navy").cantidad.valor == 60_300
        assert _buscar(personal, CATEGORIA_ACTIVO, "Air").cantidad.valor == 18_300

    def test_desglosa_tambien_la_reserva(self, personal):
        assert _buscar(personal, CATEGORIA_RESERVA, "Army").cantidad.valor == 25_050

    def test_componentes_con_nombre_compuesto(self):
        p = parsear_personal((_linea("ACTIVE 63,300 (Army 28,100 Air Force 15,800)"),))
        assert _buscar(p, CATEGORIA_ACTIVO, "Air Force").cantidad.valor == 15_800

    def test_componente_con_parentesis_interno(self):
        p = parsear_personal(
            (_linea("ACTIVE 42,900 (Army 40,000 Air/AD Aviation Forces (Joint) 1,100)"),)
        )
        assert _buscar(p, CATEGORIA_ACTIVO, "Air/AD Aviation Forces (Joint)").cantidad.valor == 1_100

    def test_ignora_las_glosas_sin_cifra(self):
        p = parsear_personal(
            (_linea("ACTIVE 5,950 (Army 5,400) (combined Jamaican Defence Force)"),)
        )
        componentes = {e.componente for e in p.efectivos}
        assert componentes == {TOTAL, "Army"}


class TestNotacionDelEditor:
    def test_preserva_la_marca_de_estimacion(self):
        p = parsear_personal((_linea("RESERVE ε600,000 (Armed Forces ε600,000)"),))
        assert _buscar(p, CATEGORIA_RESERVA, TOTAL).cantidad.estimado is True

    def test_nil_es_cero(self):
        p = parsear_personal((_linea("ACTIVE NIL Gendarmerie & Paramilitary 8,000"),))
        assert _buscar(p, CATEGORIA_ACTIVO, TOTAL).cantidad.valor == 0

    def test_no_conocido_queda_indeterminado(self):
        p = parsear_personal((_linea("RESERVE n.k."),))
        assert _buscar(p, CATEGORIA_RESERVA, TOTAL).cantidad.indeterminado is True

    def test_paramilitary_sin_gendarmerie(self):
        p = parsear_personal((_linea("ACTIVE 42,900 (Army 40,000) Paramilitary 4,300"),))
        assert _buscar(p, CATEGORIA_GENDARMERIA, TOTAL).cantidad.valor == 4_300


class TestPaisesSinFuerzasArmadas:
    """Costa Rica y Panamá no imprimen renglón ACTIVE: solo gendarmería."""

    def test_lee_la_gendarmeria_de_su_propio_encabezado(self):
        p = parsear_personal((_linea("Gendarmerie & Paramilitary 9,950"),))
        assert _buscar(p, CATEGORIA_GENDARMERIA, TOTAL).cantidad.valor == 9_950

    def test_no_inventa_efectivos_activos(self):
        p = parsear_personal((_linea("Gendarmerie & Paramilitary 9,950"),))
        assert not [e for e in p.efectivos if e.categoria == CATEGORIA_ACTIVO]

    def test_el_renglon_active_tiene_prioridad(self):
        p = parsear_personal((
            _linea("ACTIVE 285,000 (Army 206,400) Gendarmerie & Paramilitary 165,050"),
            _linea("Gendarmerie & Paramilitary 165,050"),
        ))
        gendarmeria = [e for e in p.efectivos if e.categoria == CATEGORIA_GENDARMERIA]
        assert len(gendarmeria) == 1


class TestConscripcion:
    def test_recoge_la_nota_de_servicio_obligatorio(self, personal):
        assert personal.conscripcion.startswith("Conscript liability 18 months")

    def test_ficha_sin_conscripcion(self):
        assert parsear_personal((_linea("ACTIVE 1,500 (Army 1,500)"),)).conscripcion == ""


class TestFichaSinPersonal:
    def test_devuelve_vacio_sin_fallar(self):
        p = parsear_personal((Item(pagina=1, tipo="text", md="", texto="otra cosa"),))
        assert p.efectivos == ()
