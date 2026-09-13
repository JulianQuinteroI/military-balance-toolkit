"""Tests de la línea de comandos de consulta."""

import json

import pytest

from mb2026 import etl
from mb2026.consulta import cli


@pytest.fixture
def base(corpus_sintetico_completo, tmp_path):
    destino = tmp_path / "mb.sqlite"
    etl.construir(corpus_sintetico_completo, destino)
    return destino


def _correr(base, *argumentos, capsys):
    codigo = cli.main(["--base", str(base), *argumentos])
    return codigo, capsys.readouterr()


class TestOrdenes:
    def test_ficha(self, base, capsys):
        codigo, salida = _correr(base, "ficha", "RUR", capsys=capsys)
        assert codigo == 0
        assert "Ruritania" in salida.out
        assert "Fuente: IISS" in salida.out

    def test_correlacion(self, base, capsys):
        codigo, salida = _correr(base, "correlacion", "RUR", "BOR", capsys=capsys)
        assert codigo == 0
        assert "Correlación de inventario" in salida.out

    def test_correlacion_con_dominio(self, base, capsys):
        codigo, salida = _correr(
            base, "correlacion", "RUR", "BOR", "--dominio", "tierra", capsys=capsys
        )
        assert codigo == 0
        assert "RECCE" in salida.out

    def test_sistema(self, base, capsys):
        codigo, salida = _correr(base, "sistema", "XR-9", capsys=capsys)
        assert codigo == 0
        assert "Ruritania" in salida.out

    def test_gasto(self, base, capsys):
        codigo, salida = _correr(base, "gasto", "RUR", "--desde", "2025", capsys=capsys)
        assert codigo == 0
        assert "2025" in salida.out

    def test_orbat(self, base, capsys):
        codigo, salida = _correr(base, "orbat", "RUR", capsys=capsys)
        assert codigo == 0
        assert "mech div" in salida.out

    def test_inventario(self, base, capsys):
        codigo, salida = _correr(base, "inventario", "RUR", capsys=capsys)
        assert codigo == 0
        assert "XR-9" in salida.out

    def test_ranking(self, base, capsys):
        codigo, salida = _correr(base, "ranking", "latam", capsys=capsys)
        assert codigo == 0
        assert "Ruritania" in salida.out

    def test_presencia(self, base, capsys):
        codigo, salida = _correr(base, "presencia", "EGYPT", capsys=capsys)
        assert codigo == 0
        assert "Ruritania" in salida.out

    def test_paises(self, base, capsys):
        codigo, salida = _correr(base, "paises", capsys=capsys)
        assert codigo == 0
        assert "Borduria" in salida.out

    def test_abreviatura(self, base, capsys):
        codigo, salida = _correr(base, "abreviatura", "bde", capsys=capsys)
        assert codigo == 0
        assert "brigade" in salida.out

    def test_sql(self, base, capsys):
        codigo, salida = _correr(
            base, "sql", "SELECT codigo FROM paises ORDER BY codigo", capsys=capsys
        )
        assert codigo == 0
        assert "BOR" in salida.out


class TestSalidaSerializada:
    def test_json(self, base, capsys):
        codigo, salida = _correr(base, "--json", "ficha", "RUR", capsys=capsys)
        datos = json.loads(salida.out)
        assert codigo == 0
        assert datos["tablas"][0]["titulo"] == "Identificación"


class TestErrores:
    def test_base_inexistente(self, tmp_path, capsys):
        codigo = cli.main(["--base", str(tmp_path / "no.sqlite"), "ficha", "RUR"])
        assert codigo == 1
        assert "Error" in capsys.readouterr().err

    def test_pais_desconocido(self, base, capsys):
        codigo, salida = _correr(base, "ficha", "Ruritanina", capsys=capsys)
        assert codigo == 1
        assert "No reconozco" in salida.err

    def test_dominio_desconocido(self, base, capsys):
        codigo, salida = _correr(
            base, "inventario", "RUR", "--dominio", "astronaves", capsys=capsys
        )
        assert codigo == 1
        assert "dominio" in salida.err

    def test_correlacion_con_un_solo_pais(self, base, capsys):
        codigo, salida = _correr(base, "correlacion", "RUR", capsys=capsys)
        assert codigo == 1
        assert "dos países" in salida.err

    def test_sql_de_escritura(self, base, capsys):
        codigo, salida = _correr(base, "sql", "DELETE FROM paises", capsys=capsys)
        assert codigo == 1
        assert "Error" in salida.err


class TestRutaDeLaBase:
    def test_prefiere_la_indicada(self, tmp_path):
        assert cli.ruta_base(tmp_path / "x.sqlite") == tmp_path / "x.sqlite"

    def test_usa_la_variable_de_entorno(self, monkeypatch, tmp_path):
        monkeypatch.setenv(cli.VARIABLE_ENTORNO_BASE, str(tmp_path / "y.sqlite"))
        assert cli.ruta_base(None) == tmp_path / "y.sqlite"

    def test_por_defecto_la_del_proyecto(self, monkeypatch):
        monkeypatch.delenv(cli.VARIABLE_ENTORNO_BASE, raising=False)
        assert cli.ruta_base(None).name == "mb2026.sqlite"
