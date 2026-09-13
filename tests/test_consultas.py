"""Tests de las consultas sobre la base."""

import sqlite3

import pytest

from mb2026 import etl
from mb2026.consulta import consultas


@pytest.fixture
def base(corpus_sintetico_completo, tmp_path):
    destino = tmp_path / "mb.sqlite"
    etl.construir(corpus_sintetico_completo, destino)
    conexion = consultas.abrir(destino)
    yield conexion
    conexion.close()


def _filas(resultado, titulo_parcial):
    tabla = next(t for t in resultado.tablas if titulo_parcial.lower() in t.titulo.lower())
    return tabla.filas


class TestApertura:
    def test_abre_en_solo_lectura(self, base):
        with pytest.raises(sqlite3.OperationalError):
            base.execute("DELETE FROM paises")

    def test_base_inexistente(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="mb2026"):
            consultas.abrir(tmp_path / "no-existe.sqlite")


class TestCatalogo:
    def test_devuelve_codigo_y_nombre(self, base):
        assert consultas.catalogo_paises(base)["RUR"] == "Ruritania"


class TestFicha:
    def test_reune_las_secciones(self, base):
        resultado = consultas.ficha(base, "RUR")
        titulos = " ".join(t.titulo for t in resultado.tablas)
        for seccion in ("Identificación", "Economía", "Personal", "Inventario"):
            assert seccion in titulos

    def test_incluye_la_cita_con_la_pagina(self, base):
        assert "p. 417" in consultas.ficha(base, "RUR").cita
        assert "Military Balance 2026" in consultas.ficha(base, "RUR").cita

    def test_pais_inexistente(self, base):
        with pytest.raises(LookupError, match="XXX"):
            consultas.ficha(base, "XXX")


class TestCorrelacion:
    def test_compara_por_categoria(self, base):
        resultado = consultas.correlacion(base, ("RUR", "BOR"), ("ARMOURED FIGHTING VEHICLES",))
        filas = _filas(resultado, "Correlación")
        assert any(fila[0] == "RECCE" for fila in filas)

    def test_incluye_el_personal(self, base):
        filas = _filas(consultas.correlacion(base, ("RUR", "BOR"), ()), "Personal")
        activos = next(f for f in filas if f[0] == "Activos")
        assert activos[1] == 285_000

    def test_exige_al_menos_dos_paises(self, base):
        with pytest.raises(ValueError, match="dos"):
            consultas.correlacion(base, ("RUR",), ())


class TestBuscarSistema:
    def test_encuentra_por_texto_parcial(self, base):
        filas = _filas(consultas.buscar_sistema(base, "XR-9"), "XR-9")
        assert filas and filas[0][0] == "Ruritania"

    def test_sin_resultados_no_falla(self, base):
        assert _filas(consultas.buscar_sistema(base, "Leopard"), "Leopard") == ()


class TestGasto:
    def test_serie_por_pais(self, base):
        filas = _filas(consultas.gasto(base, ("RUR",)), "Gasto")
        assert any(fila[1] == 2025 for fila in filas)

    def test_filtra_desde_un_anio(self, base):
        filas = _filas(consultas.gasto(base, ("RUR",), desde=2026), "Gasto")
        assert all(fila[1] >= 2026 for fila in filas)


class TestOrbat:
    def test_devuelve_el_arbol_indentado(self, base):
        filas = _filas(consultas.orbat(base, "RUR"), "Orden de batalla")
        assert any("mech div" in str(fila[0]) for fila in filas)
        assert any(str(fila[0]).startswith("  ") for fila in filas)

    def test_limita_la_profundidad(self, base):
        filas = _filas(consultas.orbat(base, "RUR", profundidad=0), "Orden de batalla")
        assert all(not str(fila[0]).startswith(" ") for fila in filas)


class TestInventario:
    def test_agrupa_por_dominio(self, base):
        filas = _filas(consultas.inventario(base, "RUR"), "Inventario")
        assert any("ARMOURED" in str(fila[0]) for fila in filas)


class TestRanking:
    def test_ordena_por_presupuesto(self, base):
        filas = _filas(
            consultas.ranking(base, "Latin America and the Caribbean"), "Ranking"
        )
        assert filas[0][1] == "Ruritania"

    def test_la_region_debe_coincidir_exactamente(self, base):
        """La Tabla 9 nombra las regiones igual que los capítulos."""
        filas = _filas(consultas.ranking(base, "Latin America"), "Ranking")
        assert filas == ()


class TestAbreviatura:
    def test_busca_la_sigla(self, base):
        filas = _filas(consultas.abreviatura(base, "bde"), "Abreviatura")
        assert filas[0][1] == "brigade"


class TestAbreviaturaCompuesta:
    """La Tabla 8 agrupa los códigos navales: 'FSGHM' se imprime 'FS/G/H/M'."""

    def test_recurre_a_la_forma_compuesta(self):
        conexion = sqlite3.connect(":memory:")
        conexion.row_factory = sqlite3.Row
        try:
            conexion.execute("CREATE TABLE abreviaturas (sigla TEXT, definicion TEXT)")
            conexion.execute(
                "INSERT INTO abreviaturas VALUES ('FS/G/H/M', 'corvette/with missiles')"
            )
            filas = _filas(consultas.abreviatura(conexion, "FSGHM"), "FSGHM")
        finally:
            conexion.close()
        assert filas[0][0] == "FS/G/H/M"

    def test_la_busqueda_directa_tiene_prioridad(self, base):
        filas = _filas(consultas.abreviatura(base, "bde"), "bde")
        assert filas[0][0] == "bde"


class TestSqlLibre:
    def test_ejecuta_una_consulta_de_lectura(self, base):
        filas = _filas(consultas.sql(base, "SELECT codigo FROM paises ORDER BY codigo"), "Consulta")
        assert filas == (("BOR",), ("RUR",))

    def test_rechaza_una_escritura(self, base):
        with pytest.raises(sqlite3.OperationalError):
            consultas.sql(base, "DELETE FROM paises")
