"""Tests del árbol de unidades (FORCES BY ROLE)."""

from mb2026.corpus import Item
from mb2026.parsers.unidades import parsear_unidades


def _unidades(items):
    return parsear_unidades(items).unidades


def _heading(texto, nivel=3):
    return Item(pagina=418, tipo="heading", md=f"{'#' * nivel} **{texto}**",
                texto=texto, nivel=nivel)


def _linea(texto):
    return Item(pagina=418, tipo="text", md=texto, texto=texto.replace("*", ""))


def _buscar(unidades, tipo):
    return next(u for u in unidades if u.tipo == tipo)


class TestUnidadSimple:
    def test_lee_cantidad_y_tipo(self):
        unidades = _unidades(
            (_heading("Army", 3), _heading("FORCES BY ROLE"), _linea("3 COIN mobile bde"))
        )
        assert len(unidades) == 1
        assert unidades[0].cantidad.valor == 3
        assert unidades[0].tipo == "COIN mobile bde"
        assert unidades[0].echelon == "bde"

    def test_separa_la_designacion(self):
        unidades = _unidades(
            (_heading("FORCES BY ROLE"), _linea("1 (10th) mech bde"))
        )
        assert unidades[0].designacion == "10th"
        assert unidades[0].tipo == "mech bde"

    def test_conserva_calificadores_no_numericos(self):
        unidades = _unidades(
            (_heading("FORCES BY ROLE"), _linea("1 (rapid reaction) sy bde"))
        )
        assert unidades[0].designacion == "rapid reaction"


class TestJerarquia:
    ORBAT = (
        _heading("Army 206,400", 3),
        _heading("FORCES BY ROLE"),
        _heading("SPECIAL FORCES"),
        _linea("1 SF div (1 (1st) SF regt (1 spec ops bn, 1 cdo bn); 1 (2nd) SF regt (3 SF bn))"),
    )

    def test_despliega_todos_los_niveles(self):
        unidades = _unidades(self.ORBAT)
        assert {u.tipo for u in unidades} == {
            "SF div", "SF regt", "spec ops bn", "cdo bn", "SF bn"
        }

    def test_asigna_la_profundidad(self):
        unidades = _unidades(self.ORBAT)
        assert _buscar(unidades, "SF div").profundidad == 0
        assert _buscar(unidades, "SF regt").profundidad == 1
        assert _buscar(unidades, "cdo bn").profundidad == 2

    def test_enlaza_con_el_padre(self):
        unidades = _unidades(self.ORBAT)
        division = _buscar(unidades, "SF div")
        regimiento = _buscar(unidades, "SF regt")
        assert division.padre is None
        assert regimiento.padre == division.orden

    def test_conserva_la_cantidad_de_las_subunidades(self):
        assert _buscar(_unidades(self.ORBAT), "SF bn").cantidad.valor == 3

    def test_arrastra_el_rol_y_el_servicio(self):
        division = _buscar(_unidades(self.ORBAT), "SF div")
        assert division.rol == "SPECIAL FORCES"
        assert division.servicio == "Army"

    def test_el_rol_se_hereda_en_las_subunidades(self):
        assert _buscar(_unidades(self.ORBAT), "cdo bn").rol == "SPECIAL FORCES"


class TestRolCompuesto:
    def test_concatena_el_subrol(self):
        unidades = _unidades(
            (
                _heading("FORCES BY ROLE"),
                _heading("MANOEUVRE"),
                _heading("Mechanised", nivel=4),
                _linea("1 (1st) mech div"),
            )
        )
        assert unidades[0].rol == "MANOEUVRE • Mechanised"


class TestAcotado:
    def test_ignora_el_inventario(self):
        items = (
            _heading("EQUIPMENT BY TYPE"),
            _linea("**RECCE** 121 EE-9 Cascavel"),
        )
        assert _unidades(items) == ()

    def test_se_detiene_en_la_seccion_siguiente(self):
        items = (
            _heading("FORCES BY ROLE"),
            _linea("1 armd bde"),
            _heading("EQUIPMENT BY TYPE"),
            _linea("**MBT** 40 Leopard"),
        )
        assert [u.tipo for u in _unidades(items)] == ["armd bde"]

    def test_conserva_el_renglon_crudo_y_la_pagina(self):
        unidades = _unidades((_heading("FORCES BY ROLE"), _linea("1 armd bde")))
        assert unidades[0].texto_crudo == "1 armd bde"
        assert unidades[0].pagina == 418

    def test_ficha_vacia(self):
        assert _unidades(()) == ()


class TestSeccionesEnNegrita:
    """Muchas fichas no usan encabezados: marcan las secciones con negritas."""

    FICHA = (
        Item(pagina=408, tipo="text", md="\n".join((
            "**Army** ε1,500",
            "**FORCES BY ROLE**",
            "**SPECIAL FORCES**",
            "1 SF unit",
            "**MANOEUVRE**",
            "**Light**",
            "2 inf bn (3 inf coy)",
            "**EQUIPMENT BY TYPE**",
            "**ANTI-TANK** • **RCL 84mm** *Carl Gustaf*",
        )), texto="irrelevante"),
    )

    def test_reconoce_el_inicio_de_la_seccion(self):
        assert {u.tipo for u in _unidades(self.FICHA)} == {
            "SF unit", "inf bn", "inf coy"
        }

    def test_arrastra_el_servicio_declarado_en_negrita(self):
        assert all(u.servicio == "Army" for u in _unidades(self.FICHA))

    def test_arrastra_el_rol_y_el_subrol(self):
        unidades = {u.tipo: u for u in _unidades(self.FICHA)}
        assert unidades["SF unit"].rol == "SPECIAL FORCES"
        assert unidades["inf bn"].rol == "MANOEUVRE • Light"

    def test_se_detiene_al_llegar_al_inventario(self):
        assert all(u.tipo != "RCL 84mm" for u in _unidades(self.FICHA))

    def test_rol_y_unidad_en_el_mismo_renglon(self):
        ficha = (
            Item(pagina=1, tipo="text", md="\n".join((
                "**FORCES BY ROLE**", "**MANOEUVRE** 1 armd bde",
            )), texto="irrelevante"),
        )
        unidad = _unidades(ficha)[0]
        assert unidad.tipo == "armd bde"
        assert unidad.rol == "MANOEUVRE"


class TestRenglonesSinLeer:
    """Lo que el parser no interpreta se devuelve aparte, no se descarta."""

    def test_registra_la_prosa_de_la_seccion(self):
        items = (
            _heading("FORCES BY ROLE"),
            _linea("Currently being reorganised"),
            _linea("1 armd bde"),
        )
        orbat = parsear_unidades(items)
        assert [u.tipo for u in orbat.unidades] == ["armd bde"]
        assert [r.texto for r in orbat.sin_leer] == ["Currently being reorganised"]

    def test_conserva_la_pagina_del_renglon_no_leido(self):
        items = (_heading("FORCES BY ROLE"), _linea("(see USSOCOM)"))
        assert parsear_unidades(items).sin_leer[0].pagina == 418


class TestGlosasMultiples:
    def test_conserva_todas_las_glosas_no_jerarquicas(self):
        items = (_heading("FORCES BY ROLE"), _linea("1 tk bn (forming) (non-op)"))
        assert _unidades(items)[0].designacion == "forming; non-op"
