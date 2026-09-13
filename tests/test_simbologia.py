"""Tests de la traducción de unidades del IISS a ORBAT con simbología NATO."""

import pytest

from mb2026.simbologia.diccionario import ESCALONES, escalon_de, tipo_de
from mb2026.simbologia.traductor import Calco, traducir_orbat


def _fila(**campos):
    base = {
        "id": 1,
        "padre_id": None,
        "codigo_pais": "COL",
        "profundidad": 0,
        "servicio": "Army",
        "rol": "MANOEUVRE • Light",
        "cantidad": 1,
        "designacion": "",
        "tipo": "inf bde",
        "echelon": "bde",
        "pagina": 417,
    }
    return {**base, **campos}


class TestEscalones:
    @pytest.mark.parametrize(
        "iiss,esperado",
        [
            ("div", "division"),
            ("bde", "brigada"),
            ("regt", "regimiento"),
            ("bn", "batallon"),
            ("coy", "compania"),
            ("bty", "bateria"),
            ("sqn", "escuadron"),
            ("pl", "peloton"),
            ("corps", "cuerpo"),
            ("army", "ejercito"),
        ],
    )
    def test_traduce_los_escalones_del_iiss(self, iiss, esperado):
        assert escalon_de(iiss) == esperado

    def test_escalon_desconocido_queda_vacio(self):
        assert escalon_de("base") == ""
        assert escalon_de("") == ""

    def test_todos_los_escalones_son_alias_del_skill(self):
        alias = {
            "equipo", "escuadra", "seccion", "peloton", "compania", "bateria",
            "escuadron", "batallon", "grupo", "regimiento", "brigada", "division",
            "cuerpo", "ejercito", "mando",
        }
        assert set(ESCALONES.values()) <= alias


class TestTipos:
    @pytest.mark.parametrize(
        "tipo,rol,esperado",
        [
            ("inf bn", "", "infanteria"),
            ("mech inf bn", "", "infanteria mecanizada"),
            ("armd inf bn", "", "infanteria mecanizada"),
            ("mot inf bn", "", "infanteria motorizada"),
            ("mtn inf bn", "", "infanteria"),
            ("jungle inf bn", "", "infanteria"),
            ("armd bde", "", "blindado"),
            ("tk bn", "", "blindado"),
            ("armd recce bn", "", "reconocimiento blindado"),
            ("mech cav gp", "", "reconocimiento blindado"),
            ("recce bn", "", "reconocimiento"),
            ("arty bn", "", "artilleria de campana"),
            ("sp arty bn", "", "artilleria de campana"),
            ("cbt engr bde", "", "ingenieros"),
            ("engr bn", "", "ingenieros"),
            ("SF bn", "", "fuerzas especiales"),
            ("spec ops bn", "", "operaciones especiales"),
            ("air aslt div", "", "asalto aereo"),
            ("ADA bn", "", "defensa antiaerea"),
            ("MP bn", "", "policia militar"),
            ("sigs bn", "", "transmisiones"),
            ("log bn", "", "logistica"),
            ("maint bn", "", "mantenimiento"),
            ("medical bn", "", "sanidad"),
            ("sy bn", "", "seguridad"),
        ],
    )
    def test_mapea_por_token_de_funcion(self, tipo, rol, esperado):
        assert tipo_de(tipo, rol).tipo == esperado

    def test_usa_la_entidad_cuando_no_hay_alias(self):
        traduccion = tipo_de("int bde", "")
        assert traduccion.tipo == ""
        assert traduccion.entidad == "151000"

    def test_recurre_al_rol_cuando_el_tipo_no_dice_la_funcion(self):
        assert tipo_de("sqn with F-16 Fighting Falcon", "FIGHTER").tipo == (
            "aviacion de ala fija"
        )

    def test_distingue_el_ala_rotatoria(self):
        assert tipo_de("sqn with Mi-17 Hip", "TRANSPORT HELICOPTER").tipo == "aviacion"

    def test_el_transporte_terrestre_no_es_aviacion(self):
        assert tipo_de("tpt bn", "TRANSPORT", "Army").tipo == "transporte"

    def test_el_servicio_aereo_desambigua_el_transporte(self):
        """El IISS nombra algunos escuadrones solo por su aeronave."""
        assert tipo_de("Gulfstream V", "TRANSPORT", "Air Force").tipo == (
            "aviacion de ala fija"
        )

    def test_el_helicoptero_sin_marca_de_plataforma(self):
        assert tipo_de("Mi-8 Hip", "TRANSPORT HELICOPTER", "Air Force").tipo == "aviacion"

    def test_un_servicio_terrestre_no_hereda_el_rol_aereo(self):
        assert tipo_de("Gulfstream V", "TRANSPORT", "Army").tipo == ""

    def test_no_inventa_cuando_no_reconoce_nada(self):
        traduccion = tipo_de("sqn with T-38 Talon", "TRAINING")
        assert traduccion.tipo == ""
        assert traduccion.entidad == ""


class TestTraducirOrbat:
    def test_produce_una_unidad_por_fila_mapeable(self):
        calco = traducir_orbat([_fila()], afiliacion="amigo")
        assert len(calco.unidades) == 1
        assert calco.unidades[0].tipo == "infanteria"
        assert calco.unidades[0].escalon == "brigada"
        assert calco.unidades[0].afiliacion == "amigo"

    def test_el_identificador_es_unico_y_trazable(self):
        calco = traducir_orbat([_fila(id=7)], afiliacion="amigo")
        assert calco.unidades[0].id == "COL-7"

    def test_enlaza_con_la_formacion_superior(self):
        filas = [_fila(id=1), _fila(id=2, padre_id=1, tipo="inf bn", echelon="bn")]
        calco = traducir_orbat(filas, afiliacion="amigo")
        assert calco.unidades[1].formacion_superior == "COL-1"

    def test_conserva_designacion_y_cantidad(self):
        calco = traducir_orbat(
            [_fila(designacion="10th", cantidad=3)], afiliacion="amigo"
        )
        assert calco.unidades[0].designacion == "10th"
        assert calco.unidades[0].cantidad == 3

    def test_la_etiqueta_es_legible(self):
        calco = traducir_orbat([_fila(designacion="1st", tipo="mech div", echelon="div")],
                               afiliacion="hostil")
        assert calco.unidades[0].label == "1st mech div"

    def test_marca_los_puestos_de_mando(self):
        calco = traducir_orbat([_fila(tipo="corps HQ", echelon="hq")], afiliacion="amigo")
        assert calco.unidades[0].hq is True

    def test_guarda_la_plataforma_como_informacion(self):
        calco = traducir_orbat(
            [_fila(tipo="sqn with F-16 Fighting Falcon", echelon="sqn", rol="FIGHTER")],
            afiliacion="hostil",
        )
        assert "F-16" in calco.unidades[0].info

    def test_lo_no_mapeable_se_reporta_no_se_descarta(self):
        calco = traducir_orbat(
            [_fila(tipo="sqn with T-38 Talon", echelon="sqn", rol="TRAINING")],
            afiliacion="amigo",
        )
        assert calco.unidades == ()
        assert calco.sin_mapear[0].tipo == "sqn with T-38 Talon"

    def test_calcula_la_cobertura(self):
        filas = [_fila(id=1), _fila(id=2, tipo="sqn with T-38 Talon", rol="TRAINING")]
        calco = traducir_orbat(filas, afiliacion="amigo")
        assert calco.cobertura == pytest.approx(0.5)

    def test_cobertura_de_un_calco_vacio(self):
        assert traducir_orbat([], afiliacion="amigo").cobertura == 0.0

    def test_rechaza_una_afiliacion_desconocida(self):
        with pytest.raises(ValueError, match="afiliación"):
            traducir_orbat([_fila()], afiliacion="morado")


class TestSerializacion:
    def test_omite_los_campos_vacios(self):
        calco = traducir_orbat([_fila()], afiliacion="amigo")
        crudo = calco.como_orbat()[0]
        assert "designacion" not in crudo
        assert crudo["tipo"] == "infanteria"

    def test_usa_el_nombre_de_campo_del_skill(self):
        filas = [_fila(id=1), _fila(id=2, padre_id=1)]
        crudo = traducir_orbat(filas, afiliacion="amigo").como_orbat()[1]
        assert crudo["formacionSuperior"] == "COL-1"

    def test_la_entidad_viaja_cuando_no_hay_alias(self):
        crudo = traducir_orbat([_fila(tipo="int bde")], afiliacion="amigo").como_orbat()[0]
        assert crudo["entidad"] == "151000"
        assert "tipo" not in crudo


class TestCalco:
    def test_es_inmutable(self):
        calco = traducir_orbat([_fila()], afiliacion="amigo")
        assert isinstance(calco, Calco)
        with pytest.raises(AttributeError):
            calco.unidades = ()  # type: ignore[misc]
