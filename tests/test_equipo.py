"""Tests de la extracción de inventario (EQUIPMENT BY TYPE)."""

from mb2026.corpus import Item
from mb2026.parsers.equipo import parsear_equipo


def _heading(texto, nivel=3):
    return Item(pagina=418, tipo="heading", md=f"{'#' * nivel} **{texto}**",
                texto=texto, nivel=nivel)


def _bloque(*lineas):
    md = "\n".join(lineas)
    return Item(pagina=418, tipo="text", md=md, texto=md.replace("*", ""))


FICHA = (
    _heading("Army 206,400", nivel=3),
    _heading("EQUIPMENT BY TYPE", nivel=3),
    _heading("ARMOURED FIGHTING VEHICLES", nivel=3),
    _bloque(
        "**RECCE** 121 EE-9 *Cascavel*",
        "**IFV** 60: 28 *Commando Advanced*; 32 LAV III",
        "**APC** 111",
        "**APC (W)** 56 EE-11 *Urutu*; BTR-80†",
        "**PPV** 13+: some *Hunter* XL; 4 RG-31 *Nyala*",
    ),
    _heading("ARTILLERY", nivel=3),
    _bloque("**TOWED** 120: **105mm** 107: 22 LG1 MkIII; 85 M101; **155mm** 13 M-71"),
)


def _buscar(equipos, sistema):
    return next(e for e in equipos if e.sistema == sistema)


class TestSistemas:
    def test_sistema_unico_en_el_renglon(self):
        equipo = _buscar(parsear_equipo(FICHA), "EE-9 Cascavel")
        assert equipo.categoria == "RECCE"
        assert equipo.cantidad.valor == 121

    def test_lista_separada_por_punto_y_coma(self):
        equipos = parsear_equipo(FICHA)
        assert _buscar(equipos, "Commando Advanced").cantidad.valor == 28
        assert _buscar(equipos, "LAV III").cantidad.valor == 32

    def test_conserva_el_total_de_la_categoria(self):
        assert _buscar(parsear_equipo(FICHA), "LAV III").total_categoria.valor == 60

    def test_categoria_sin_sistemas_declarados(self):
        equipo = next(e for e in parsear_equipo(FICHA) if e.categoria == "APC" and not e.sistema)
        assert equipo.total_categoria.valor == 111

    def test_sistema_sin_cantidad(self):
        assert _buscar(parsear_equipo(FICHA), "BTR-80").cantidad is None

    def test_cantidad_indeterminada(self):
        assert _buscar(parsear_equipo(FICHA), "Hunter XL").cantidad.indeterminado is True

    def test_total_con_marca_de_minimo(self):
        assert _buscar(parsear_equipo(FICHA), "RG-31 Nyala").total_categoria.minimo is True


class TestGlosasEntreParentesis:
    def test_no_parte_la_lista_dentro_de_un_parentesis(self):
        ficha = (
            _heading("Navy", nivel=3),
            _heading("EQUIPMENT BY TYPE", nivel=3),
            _bloque("**SSK** 2: 1 *Sabalo* (in refit; 1 more non-operational); 1 *Caribe*"),
        )
        sistemas = [e.sistema for e in parsear_equipo(ficha)]
        assert sistemas == ["Sabalo (in refit; 1 more non-operational)", "Caribe"]


class TestDesignacionesConCifraInicial:
    """Muchos sistemas soviéticos empiezan por dígito: no es una cantidad."""

    def test_no_confunde_la_designacion_con_un_conteo(self):
        ficha = (
            _heading("Army", nivel=3),
            _heading("EQUIPMENT BY TYPE", nivel=3),
            _bloque("**SAM** 9K31 *Strela-1*; 4 9K33 *Osa*"),
        )
        equipos = parsear_equipo(ficha)
        suelto = _buscar(equipos, "9K31 Strela-1")
        assert suelto.cantidad is None
        contado = _buscar(equipos, "9K33 Osa")
        assert contado.cantidad.valor == 4


class TestMarcasDelEditor:
    def test_marca_de_operatividad_dudosa(self):
        equipo = _buscar(parsear_equipo(FICHA), "BTR-80")
        assert equipo.dudoso is True
        assert "†" not in equipo.sistema

    def test_equipo_sin_marca_no_queda_como_dudoso(self):
        assert _buscar(parsear_equipo(FICHA), "LAV III").dudoso is False


class TestJerarquia:
    def test_arrastra_el_dominio_del_encabezado(self):
        assert _buscar(parsear_equipo(FICHA), "LAV III").dominio == "ARMOURED FIGHTING VEHICLES"

    def test_arrastra_el_servicio(self):
        assert _buscar(parsear_equipo(FICHA), "LAV III").servicio == "Army"

    def test_lee_las_subcategorias_del_mismo_renglon(self):
        equipos = parsear_equipo(FICHA)
        m71 = _buscar(equipos, "M-71")
        assert m71.categoria == "TOWED"
        assert m71.subcategoria == "155mm"
        assert _buscar(equipos, "M101").subcategoria == "105mm"

    def test_conserva_el_renglon_crudo(self):
        assert _buscar(parsear_equipo(FICHA), "LAV III").texto_crudo.startswith("**IFV**")

    def test_registra_la_pagina_para_citar(self):
        assert _buscar(parsear_equipo(FICHA), "LAV III").pagina == 418


class TestServicioFrenteASubrol:
    """'Light' clasifica maniobra dentro de FORCES BY ROLE; no es una fuerza."""

    def test_el_subrol_no_sustituye_al_servicio(self):
        ficha = (
            _heading("Army 206,400", nivel=3),
            _heading("FORCES BY ROLE", nivel=3),
            _heading("MANOEUVRE", nivel=3),
            _heading("Light", nivel=4),
            _bloque("1 (2nd) inf div"),
            _heading("EQUIPMENT BY TYPE", nivel=3),
            _heading("HELICOPTERS", nivel=3),
            _bloque("**TPT** 53: 46 UH-60L *Black Hawk*"),
        )
        assert _buscar(parsear_equipo(ficha), "UH-60L Black Hawk").servicio == "Army"


class TestNormalizacionDelDominio:
    """El rótulo del dominio llega con el total, con sub-nivel y con erratas."""

    def _dominio(self, encabezado):
        ficha = (
            _heading("Army", nivel=3),
            _heading("EQUIPMENT BY TYPE", nivel=3),
            _heading(encabezado, nivel=3),
            _bloque("**MBT** 40 *Leopard*"),
        )
        return _buscar(parsear_equipo(ficha), "Leopard").dominio

    def test_descarta_el_total_del_rotulo(self):
        assert self._dominio("ARTILLERY 9,580") == "ARTILLERY"

    def test_se_queda_con_el_primer_nivel(self):
        assert self._dominio("AIR DEFENCE • SAM") == "AIR DEFENCE"

    def test_corrige_las_erratas_del_original(self):
        assert self._dominio("UNIHABITED AERIAL VEHICLES") == "UNINHABITED AERIAL VEHICLES"
        assert self._dominio("ANTI-TANK/ANTI-INFRASTURCTURE") == "ANTI-TANK/ANTI-INFRASTRUCTURE"

    def test_un_subnivel_no_sustituye_al_dominio(self):
        ficha = (
            _heading("Army", nivel=3),
            _heading("EQUIPMENT BY TYPE", nivel=3),
            _heading("ANTI-TANK/ANTI-INFRASTRUCTURE", nivel=3),
            _bloque("**MSL**", "**SP** 77 *Nimrod*"),
        )
        misil = _buscar(parsear_equipo(ficha), "Nimrod")
        assert misil.dominio == "ANTI-TANK/ANTI-INFRASTRUCTURE"
        assert misil.grupo == "MSL"


class TestCategoriaInequivoca:
    """En Colombia (p. 419) el corpus perdió los encabezados 'Navy' y 'SUBMARINES'."""

    def test_un_codigo_de_submarino_fija_su_dominio(self):
        ficha = (
            _heading("Army", nivel=3),
            _heading("EQUIPMENT BY TYPE", nivel=3),
            _heading("AIR DEFENCE", nivel=3),
            _bloque("**GUNS • TOWED 40mm** 4 M1A1", "**SSK** 2 *Pijao*"),
        )
        equipos = parsear_equipo(ficha)
        assert _buscar(equipos, "Pijao").dominio == "SUBMARINES"
        assert _buscar(equipos, "M1A1").dominio == "AIR DEFENCE"

    def test_no_toca_las_categorias_ambiguas(self):
        """'MCM' es cazaminas: puede ser buque o helicóptero."""
        ficha = (
            _heading("Naval Aviation", nivel=3),
            _heading("EQUIPMENT BY TYPE", nivel=3),
            _heading("HELICOPTERS", nivel=3),
            _bloque("**MCM** 8 MH-53E *Sea Dragon*"),
        )
        assert _buscar(parsear_equipo(ficha), "MH-53E Sea Dragon").dominio == "HELICOPTERS"


class TestSubrolNoEsFuerza:
    """'Light' y 'Other' clasifican maniobra; no son fuerzas."""

    def test_el_subrol_en_negrita_no_abre_una_fuerza(self):
        ficha = (
            Item(pagina=1, tipo="text", md="\n".join((
                "**Army** 206,400",
                "**FORCES BY ROLE**",
                "**MANOEUVRE**",
                "**Light**",
                "2 inf bn",
                "**EQUIPMENT BY TYPE**",
                "**MBT** 40 *Leopard*",
            )), texto="irrelevante"),
        )
        assert _buscar(parsear_equipo(ficha), "Leopard").servicio == "Army"

    def test_una_fuerza_con_efectivos_si_abre_seccion(self):
        ficha = (
            Item(pagina=1, tipo="text", md="\n".join((
                "**Army** 206,400",
                "**FORCES BY ROLE**",
                "**MANOEUVRE**",
                "**Navy** 60,300",
                "**EQUIPMENT BY TYPE**",
                "**FFGHM** 4 *Almirante Padilla*",
            )), texto="irrelevante"),
        )
        assert _buscar(parsear_equipo(ficha), "Almirante Padilla").servicio == "Navy"


class TestRotulosQueNoSonFuerzas:
    def test_population_no_abre_una_fuerza(self):
        ficha = (
            Item(pagina=1, tipo="text", md="\n".join((
                "**Army** 206,400",
                "**Population** 11,000,000",
                "**EQUIPMENT BY TYPE**",
                "**MBT** 40 *Leopard*",
            )), texto="irrelevante"),
        )
        assert _buscar(parsear_equipo(ficha), "Leopard").servicio == "Army"


class TestAcotado:
    def test_ignora_lo_que_no_es_inventario(self):
        ficha = (
            _heading("Army 206,400", nivel=3),
            _heading("FORCES BY ROLE", nivel=3),
            _bloque("**MANOEUVRE** 1 armd bde"),
        )
        assert parsear_equipo(ficha) == ()

    def test_reconoce_la_seccion_dentro_de_un_parrafo_corrido(self):
        ficha = (
            _heading("Air Wing", nivel=3),
            _bloque("**EQUIPMENT BY TYPE**", "**AIRCRAFT • TPT** 3: 1 BN-2B *Defender*†"),
        )
        equipos = parsear_equipo(ficha)
        assert _buscar(equipos, "BN-2B Defender").servicio == "Air Wing"

    def test_ficha_vacia(self):
        assert parsear_equipo(()) == ()


class TestServicioEnNegrita:
    """Fichas breves declaran la fuerza como rótulo de un párrafo, sin encabezado."""

    FICHA = (
        Item(pagina=408, tipo="text", md="\n".join((
            "**Army** ε1,500",
            "**EQUIPMENT BY TYPE**",
            "**ARTILLERY** • **MOR 81mm** 6",
            "**Air Wing**",
            "**EQUIPMENT BY TYPE**",
            "**AIRCRAFT**",
            "**TPT • Light** 3: 1 BN-2B *Defender*†",
        )), texto="irrelevante"),
    )

    def test_atribuye_el_inventario_a_su_fuerza(self):
        equipos = parsear_equipo(self.FICHA)
        mortero = next(e for e in equipos if e.categoria == "MOR 81mm")
        assert mortero.servicio == "Army"
        assert mortero.total_categoria.valor == 6
        assert _buscar(equipos, "BN-2B Defender").servicio == "Air Wing"

    def test_no_confunde_una_subcategoria_con_una_fuerza(self):
        ficha = (
            _heading("Army", nivel=3),
            _heading("EQUIPMENT BY TYPE", nivel=3),
            _bloque("**TPT** 75: **Medium** 53: 46 UH-60L *Black Hawk*"),
        )
        assert _buscar(parsear_equipo(ficha), "UH-60L Black Hawk").servicio == "Army"


class TestNegritasMalFormadas:
    """El corpus rompe a veces los marcadores: '**AMPHIBIOUS • **LANDING CRAFT**'."""

    def test_un_rotulo_sin_letras_no_llega_a_categoria(self):
        ficha = (
            _heading("Navy", nivel=3),
            _heading("EQUIPMENT BY TYPE", nivel=3),
            _bloque("**AMPHIBIOUS • **LANDING CRAFT** • 1 **LCU**; 1 LCM; 12 LCVP**"),
        )
        categorias = {e.categoria for e in parsear_equipo(ficha)}
        assert all(any(c.isalpha() for c in cat) for cat in categorias)

    def test_prefiere_no_emitir_nada_a_emitir_basura(self):
        """Con los marcadores rotos no se puede saber dónde acaba cada rótulo."""
        ficha = (
            _heading("Navy", nivel=3),
            _heading("EQUIPMENT BY TYPE", nivel=3),
            _bloque("**AMPHIBIOUS • **LANDING CRAFT** • 1 **LCU**; 1 LCM; 12 LCVP**"),
        )
        assert parsear_equipo(ficha) == ()


class TestDominio:
    """El dominio no puede arrastrarse de una fuerza a la siguiente."""

    def test_se_reinicia_al_cambiar_de_fuerza(self):
        ficha = (
            _heading("Coast Guard 1,000", nivel=2),
            _heading("EQUIPMENT BY TYPE", nivel=3),
            _bloque("**PATROL AND COASTAL COMBATANTS** 25: 25 *Peykaap*"),
            _heading("Air Force 11,500", nivel=2),
            _heading("EQUIPMENT BY TYPE", nivel=3),
            _bloque("**FTR** 18: 15 F-16A *Fighting Falcon*"),
        )
        caza = _buscar(parsear_equipo(ficha), "F-16A Fighting Falcon")
        assert caza.servicio == "Air Force"
        assert caza.dominio != "PATROL AND COASTAL COMBATANTS"

    def test_reconoce_un_dominio_que_trae_su_propio_total(self):
        ficha = (
            _heading("Air Force", nivel=2),
            _heading("EQUIPMENT BY TYPE", nivel=3),
            _bloque("**AIRCRAFT** 43 combat capable", "**FTR** 18: 15 F-16A *Fighting Falcon*"),
        )
        assert _buscar(parsear_equipo(ficha), "F-16A Fighting Falcon").dominio == "AIRCRAFT"

    def test_el_dominio_no_desplaza_a_la_categoria(self):
        ficha = (
            _heading("Army", nivel=2),
            _heading("EQUIPMENT BY TYPE", nivel=3),
            _bloque("**AIR DEFENCE** • **SAM** • **Point-defence** 9K31 *Strela-1*"),
        )
        misil = _buscar(parsear_equipo(ficha), "9K31 Strela-1")
        assert misil.dominio == "AIR DEFENCE"
        assert misil.categoria == "SAM"
