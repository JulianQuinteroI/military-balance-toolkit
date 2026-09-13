"""Tests de la interfaz de línea de comandos."""

import pytest

from mb2026 import cli


class TestMain:
    def test_construye_la_base_y_reporta(self, corpus_sintetico_completo, tmp_path, capsys):
        salida = tmp_path / "mb.sqlite"
        codigo = cli.main(["--corpus", str(corpus_sintetico_completo), "--salida", str(salida)])
        impreso = capsys.readouterr().out
        assert codigo == 0
        assert salida.exists()
        assert "Países cargados" in impreso
        assert "equipo" in impreso

    def test_informa_el_corpus_ausente_sin_traza(self, tmp_path, capsys):
        codigo = cli.main(
            ["--corpus", str(tmp_path / "no-existe.json"), "--salida", str(tmp_path / "x.sqlite")]
        )
        assert codigo == 1
        assert "Error:" in capsys.readouterr().out

    def test_informa_un_corpus_ilegible(self, tmp_path, capsys):
        malo = tmp_path / "malo.json"
        malo.write_text('{"sin_paginas": true}', encoding="utf8")
        codigo = cli.main(["--corpus", str(malo), "--salida", str(tmp_path / "x.sqlite")])
        assert codigo == 1
        assert "pages" in capsys.readouterr().out

    def test_ayuda(self, capsys):
        with pytest.raises(SystemExit) as salida:
            cli.main(["--help"])
        assert salida.value.code == 0
        assert "SQLite" in capsys.readouterr().out


class TestEtlCompleto:
    """Recorrido de punta a punta sobre el corpus sintético."""

    def test_carga_cada_tabla_del_esquema(self, corpus_sintetico_completo, tmp_path):
        import sqlite3

        from mb2026 import etl

        salida = tmp_path / "mb.sqlite"
        informe = etl.construir(corpus_sintetico_completo, salida)
        assert informe.paises == 2

        conexion = sqlite3.connect(salida)
        conexion.row_factory = sqlite3.Row
        try:
            resumen = conexion.execute(
                "SELECT * FROM v_resumen_pais WHERE codigo = 'RUR'"
            ).fetchone()
            assert resumen["activos"] == 285_000
            assert resumen["gendarmeria"] == 165_050
            assert resumen["presupuesto_usd_2025"] == 8.27e9
            assert resumen["lineas_equipo"] == 1
            assert resumen["unidades"] == 2

            assert conexion.execute(
                "SELECT definicion FROM abreviaturas WHERE sigla = 'bde'"
            ).fetchone()[0] == "brigade"
            assert conexion.execute(
                "SELECT codigo_pais FROM comparacion_gasto"
                " WHERE pais = 'Ruritania' AND anio = 2025"
            ).fetchone()[0] == "RUR"
            assert conexion.execute(
                "SELECT origen FROM fuerzas_extranjeras WHERE codigo_pais = 'RUR'"
            ).fetchone()[0] == "Borduria"
            assert conexion.execute(
                "SELECT valor FROM fuente WHERE clave = 'corte_datos'"
            ).fetchone()[0]
        finally:
            conexion.close()
