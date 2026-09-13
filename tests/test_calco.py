"""Tests de la orden `calco`, que enlaza con el skill nato-symbology."""

import json

import pytest

from mb2026 import etl
from mb2026.consulta import cli, consultas


@pytest.fixture
def base(corpus_sintetico_completo, tmp_path):
    destino = tmp_path / "mb.sqlite"
    etl.construir(corpus_sintetico_completo, destino)
    return destino


@pytest.fixture
def conexion(base):
    con = consultas.abrir(base)
    yield con
    con.close()


class TestFilasParaSimbologia:
    def test_devuelve_las_columnas_que_necesita_el_traductor(self, conexion):
        filas = consultas.unidades_crudas(conexion, "RUR")
        assert filas
        for campo in ("id", "padre_id", "codigo_pais", "servicio", "rol",
                      "cantidad", "designacion", "tipo", "echelon"):
            assert campo in filas[0]

    def test_filtra_por_fuerza(self, conexion):
        assert consultas.unidades_crudas(conexion, "RUR", servicio="Navy") == []

    def test_filtra_por_profundidad(self, conexion):
        filas = consultas.unidades_crudas(conexion, "RUR", profundidad=0)
        assert all(f["profundidad"] == 0 for f in filas)


class TestOrdenCalco:
    def test_escribe_el_orbat_json(self, base, tmp_path, capsys):
        salida = tmp_path / "calco.json"
        codigo = cli.main(
            ["--base", str(base), "calco", "RUR", "--salida", str(salida)]
        )
        assert codigo == 0
        orbat = json.loads(salida.read_text(encoding="utf8"))
        assert orbat[0]["afiliacion"] == "amigo"
        assert orbat[0]["tipo"] == "infanteria mecanizada"

    def test_informa_la_cobertura(self, base, tmp_path, capsys):
        cli.main(["--base", str(base), "calco", "RUR", "--salida", str(tmp_path / "c.json")])
        assert "cobertura" in capsys.readouterr().out.lower()

    def test_imprime_el_comando_de_generacion(self, base, tmp_path, capsys):
        cli.main(["--base", str(base), "calco", "RUR", "--salida", str(tmp_path / "c.json")])
        salida = capsys.readouterr().out
        assert "generate.mjs" in salida
        assert "--orbat" in salida

    def test_admite_afiliacion_hostil(self, base, tmp_path):
        salida = tmp_path / "calco.json"
        cli.main(["--base", str(base), "calco", "RUR", "--afiliacion", "hostil",
                  "--salida", str(salida)])
        orbat = json.loads(salida.read_text(encoding="utf8"))
        assert orbat[0]["afiliacion"] == "hostil"

    def test_rechaza_una_afiliacion_desconocida(self, base, tmp_path, capsys):
        codigo = cli.main(["--base", str(base), "calco", "RUR", "--afiliacion", "morado",
                           "--salida", str(tmp_path / "c.json")])
        assert codigo == 1
        assert "afiliación" in capsys.readouterr().err

    def test_sin_salida_imprime_el_json(self, base, capsys):
        codigo = cli.main(["--base", str(base), "calco", "RUR"])
        assert codigo == 0
        assert '"afiliacion"' in capsys.readouterr().out

    def test_pais_sin_unidades(self, base, tmp_path, capsys):
        codigo = cli.main(["--base", str(base), "calco", "BOR",
                           "--salida", str(tmp_path / "c.json")])
        assert codigo == 1
        assert "sin unidades" in capsys.readouterr().err.lower()
