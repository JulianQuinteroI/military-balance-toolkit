"""Validación cruzada contra el corpus real.

Se salta entero si el corpus no está disponible. Contrasta dos caminos
independientes del mismo dato —la ficha de país y la Tabla 9 comparativa— que
el IISS compone por separado: si coinciden, la extracción es fiel.
"""

from __future__ import annotations

import sqlite3

import pytest

from mb2026 import etl

REGION_VALIDADA = "Latin America and the Caribbean"

#: La Tabla 9 redondea el personal a miles.
TOLERANCIA_PERSONAL = 550
#: La Tabla 9 redondea el presupuesto a tres cifras significativas...
TOLERANCIA_PRESUPUESTO_RELATIVA = 0.02
#: ...y lo imprime en USDm enteros, así que en cifras pequeñas manda el absoluto.
TOLERANCIA_PRESUPUESTO_ABSOLUTA = 0.5e6

#: Panamá y Costa Rica abolieron sus fuerzas armadas: solo declaran gendarmería.
SIN_FUERZAS_ARMADAS = ("CRI", "PAN")


@pytest.fixture(scope="module")
def base(corpus_real, tmp_path_factory) -> sqlite3.Connection:
    destino = tmp_path_factory.mktemp("base") / "mb2026.sqlite"
    etl.construir(corpus_real, destino)
    conexion = sqlite3.connect(destino)
    conexion.row_factory = sqlite3.Row
    yield conexion
    conexion.close()


class TestCobertura:
    def test_carga_los_174_paises_del_volumen(self, base):
        assert base.execute("SELECT COUNT(*) FROM paises").fetchone()[0] == 174

    def test_el_capitulo_7_tiene_sus_28_fichas(self, base):
        total = base.execute(
            "SELECT COUNT(*) FROM paises WHERE region = ?", (REGION_VALIDADA,)
        ).fetchone()[0]
        assert total == 28

    def test_toda_ficha_del_capitulo_7_declara_efectivos(self, base):
        faltan = base.execute(
            "SELECT p.codigo FROM paises p WHERE p.region = ?"
            " AND NOT EXISTS (SELECT 1 FROM personal pe"
            "   WHERE pe.codigo_pais = p.codigo AND pe.categoria = 'activo')",
            (REGION_VALIDADA,),
        ).fetchall()
        assert [f["codigo"] for f in faltan] == list(SIN_FUERZAS_ARMADAS)

    def test_los_paises_sin_ejercito_declaran_su_gendarmeria(self, base):
        for codigo in SIN_FUERZAS_ARMADAS:
            cantidad = base.execute(
                "SELECT cantidad FROM personal WHERE codigo_pais = ?"
                " AND categoria = 'gendarmeria' AND componente = 'Total'",
                (codigo,),
            ).fetchone()
            assert cantidad is not None and cantidad["cantidad"] > 0

    def test_toda_ficha_del_capitulo_7_tiene_inventario(self, base):
        faltan = base.execute(
            "SELECT p.codigo FROM paises p WHERE p.region = ?"
            " AND NOT EXISTS (SELECT 1 FROM equipo e WHERE e.codigo_pais = p.codigo)",
            (REGION_VALIDADA,),
        ).fetchall()
        assert [f["codigo"] for f in faltan] == []


class TestConcordanciaConLaTabla9:
    def test_los_efectivos_activos_coinciden(self, base):
        filas = base.execute(
            "SELECT p.codigo, pe.cantidad AS ficha, cp.activos_miles * 1000 AS tabla9"
            "  FROM paises p"
            "  JOIN personal pe ON pe.codigo_pais = p.codigo"
            "   AND pe.categoria = 'activo' AND pe.componente = 'Total'"
            "  JOIN comparacion_personal cp ON cp.codigo_pais = p.codigo"
            " WHERE p.region = ? AND pe.cantidad IS NOT NULL",
            (REGION_VALIDADA,),
        ).fetchall()
        assert len(filas) >= 25
        discrepantes = [
            (f["codigo"], f["ficha"], f["tabla9"])
            for f in filas
            if abs(f["ficha"] - f["tabla9"]) > TOLERANCIA_PERSONAL
        ]
        assert discrepantes == []

    def test_el_presupuesto_de_defensa_coincide(self, base):
        filas = base.execute(
            "SELECT p.codigo, e.valor AS ficha, cg.presupuesto_usd_m * 1e6 AS tabla9"
            "  FROM paises p"
            "  JOIN economia e ON e.codigo_pais = p.codigo AND e.anio = 2025"
            "   AND e.indicador = 'presupuesto_defensa' AND e.unidad = 'USD'"
            "  JOIN comparacion_gasto cg ON cg.codigo_pais = p.codigo AND cg.anio = 2025"
            " WHERE p.region = ? AND cg.presupuesto_usd_m IS NOT NULL",
            (REGION_VALIDADA,),
        ).fetchall()
        assert len(filas) >= 15
        discrepantes = [
            (f["codigo"], f["ficha"], f["tabla9"])
            for f in filas
            if abs(f["ficha"] - f["tabla9"]) > max(
                f["tabla9"] * TOLERANCIA_PRESUPUESTO_RELATIVA,
                TOLERANCIA_PRESUPUESTO_ABSOLUTA,
            )
        ]
        assert discrepantes == []


class TestFichaDeColombia:
    """Contraste puntual contra el impreso (pp. 417-419)."""

    def test_datos_de_cabecera(self, base):
        fila = base.execute(
            "SELECT nombre, region, pagina FROM paises WHERE codigo = 'COL'"
        ).fetchone()
        assert fila["nombre"] == "Colombia"
        assert fila["region"] == REGION_VALIDADA
        assert fila["pagina"] == 417

    def test_efectivos_por_fuerza(self, base):
        efectivos = dict(
            base.execute(
                "SELECT componente, cantidad FROM personal"
                " WHERE codigo_pais = 'COL' AND categoria = 'activo'"
            ).fetchall()
        )
        assert efectivos["Total"] == 285_000
        assert efectivos["Army"] == 206_400
        assert efectivos["Navy"] == 60_300
        assert efectivos["Air"] == 18_300

    def test_presupuesto_en_moneda_local_y_en_dolares(self, base):
        valores = {
            (f["unidad"], f["anio"]): f["valor"]
            for f in base.execute(
                "SELECT unidad, anio, valor FROM economia"
                " WHERE codigo_pais = 'COL' AND indicador = 'presupuesto_defensa'"
            )
        }
        assert valores[("COP", 2025)] == pytest.approx(34.6e12)
        assert valores[("USD", 2025)] == pytest.approx(8.27e9)

    def test_moneda(self, base):
        fila = base.execute(
            "SELECT nombre, codigo_iso FROM monedas WHERE codigo_pais = 'COL'"
        ).fetchone()
        assert (fila["nombre"], fila["codigo_iso"]) == ("Colombian Peso", "COP")

    def test_inventario_conocido(self, base):
        filas = {
            (f["servicio"], f["sistema"]): f
            for f in base.execute(
                "SELECT servicio, sistema, cantidad, dudoso, dominio FROM equipo"
                " WHERE codigo_pais = 'COL'"
            )
        }
        assert filas[("Army", "EE-9 Cascavel")]["cantidad"] == 121
        assert filas[("Army", "M1117 Guardian")]["cantidad"] == 176
        assert filas[("Army", "UH-60L Black Hawk")]["cantidad"] == 46
        assert filas[("Army", "BTR-80")]["dudoso"] == 1

    def test_el_inventario_se_atribuye_a_su_fuerza(self, base):
        """El Ejército y la Policía Nacional operan el mismo modelo."""
        servicios = {
            f["servicio"]
            for f in base.execute(
                "SELECT servicio FROM equipo"
                " WHERE codigo_pais = 'COL' AND sistema = 'UH-60L Black Hawk'"
            )
        }
        assert servicios == {"Army", "National Police Force"}

    def test_orden_de_batalla(self, base):
        division = base.execute(
            "SELECT id, tipo, designacion, servicio FROM unidades"
            " WHERE codigo_pais = 'COL' AND tipo = 'mech div'"
        ).fetchone()
        assert division["designacion"] == "1st"
        assert division["servicio"] == "Army"
        brigadas = base.execute(
            "SELECT tipo FROM unidades WHERE padre_id = ?", (division["id"],)
        ).fetchall()
        assert [b["tipo"] for b in brigadas] == ["mech bde", "mech bde"]

    def test_presencia_extranjera(self, base):
        fila = base.execute(
            "SELECT origen, efectivos FROM fuerzas_extranjeras WHERE codigo_pais = 'COL'"
        ).fetchone()
        assert fila["origen"] == "United States"
        assert fila["efectivos"] == 50

    def test_despliegues_propios(self, base):
        destinos = {
            f["destino"]: f["efectivos"]
            for f in base.execute(
                "SELECT destino, efectivos FROM despliegues WHERE codigo_pais = 'COL'"
            )
        }
        assert destinos["EGYPT"] == 275
        assert "LEBANON" in destinos


class TestIntegridad:
    def test_ninguna_unidad_apunta_a_un_padre_inexistente(self, base):
        huerfanas = base.execute(
            "SELECT COUNT(*) FROM unidades u WHERE u.padre_id IS NOT NULL"
            " AND NOT EXISTS (SELECT 1 FROM unidades p WHERE p.id = u.padre_id)"
        ).fetchone()[0]
        assert huerfanas == 0

    def test_las_subunidades_pertenecen_al_mismo_pais(self, base):
        cruzadas = base.execute(
            "SELECT COUNT(*) FROM unidades u JOIN unidades p ON p.id = u.padre_id"
            " WHERE p.codigo_pais <> u.codigo_pais"
        ).fetchone()[0]
        assert cruzadas == 0

    def test_toda_linea_de_equipo_conserva_su_renglon_de_origen(self, base):
        sin_crudo = base.execute(
            "SELECT COUNT(*) FROM equipo WHERE texto_crudo = ''"
        ).fetchone()[0]
        assert sin_crudo == 0
