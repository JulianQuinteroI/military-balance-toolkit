"""Tests del flujo lineal de items del corpus."""

import pytest

from mb2026.corpus import CHAPTER_RUNNING_HEADS, Item, cargar_items


class TestCargarItems:
    def test_devuelve_flujo_inmutable(self, json_sintetico):
        items = cargar_items(json_sintetico)
        assert isinstance(items, tuple)
        assert all(isinstance(i, Item) for i in items)

    def test_conserva_el_numero_de_pagina_para_citacion(self, json_sintetico):
        items = cargar_items(json_sintetico)
        assert items[0].pagina == 10
        assert items[-1].pagina == 11

    def test_descarta_encabezados_y_pies_de_pagina(self, json_sintetico):
        textos = [i.texto for i in cargar_items(json_sintetico)]
        assert not any("THE MILITARY BALANCE" in t for t in textos)
        assert not any(t.startswith("Latin America 9") for t in textos)

    def test_descarta_titulillos_de_capitulo(self, json_sintetico):
        textos = [i.texto for i in cargar_items(json_sintetico)]
        assert "Latin America and the Caribbean" not in textos

    def test_limpia_el_markdown_pero_preserva_el_crudo(self, json_sintetico):
        recce = next(i for i in cargar_items(json_sintetico) if "RECCE" in i.texto)
        assert recce.texto == "RECCE 121 XR-9 Vigía"
        assert "**RECCE**" in recce.md

    def test_calcula_el_nivel_de_los_encabezados(self, json_sintetico):
        items = cargar_items(json_sintetico)
        pais = next(i for i in items if i.texto == "Ruritania RUR")
        assert pais.nivel == 1
        ejercito = next(i for i in items if i.texto.startswith("Army"))
        assert ejercito.nivel == 3

    def test_expone_las_filas_de_las_tablas(self, json_sintetico):
        tabla = next(i for i in cargar_items(json_sintetico) if i.tipo == "table")
        assert tabla.filas[0][0] == "Ruritanian Krone RUK"
        assert isinstance(tabla.filas, tuple)

    def test_items_sin_tabla_tienen_filas_vacias(self, json_sintetico):
        texto = next(i for i in cargar_items(json_sintetico) if i.tipo == "text")
        assert texto.filas == ()

    def test_expone_los_renglones_con_el_markdown_intacto(self, json_sintetico):
        recce = next(i for i in cargar_items(json_sintetico) if "RECCE" in i.texto)
        assert recce.lineas_md == ("**RECCE** 121 XR-9 *Vigía*",)

    def test_falla_con_ruta_inexistente(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            cargar_items(tmp_path / "no-existe.json")

    def test_falla_si_el_json_no_tiene_paginas(self, tmp_path):
        malo = tmp_path / "malo.json"
        malo.write_text('{"otra_cosa": []}', encoding="utf8")
        with pytest.raises(TypeError, match="pages"):
            cargar_items(malo)

    def test_falla_si_el_json_no_es_un_objeto(self, tmp_path):
        malo = tmp_path / "malo.json"
        malo.write_text("[1, 2, 3]", encoding="utf8")
        with pytest.raises(TypeError, match="objeto JSON"):
            cargar_items(malo)

    def test_ignora_una_pagina_que_no_es_un_objeto(self, tmp_path):
        raro = tmp_path / "raro.json"
        raro.write_text('{"pages": [null, "x"]}', encoding="utf8")
        assert cargar_items(raro) == ()


class TestTitulillos:
    def test_incluye_los_siete_capitulos_regionales(self):
        assert "Latin America and the Caribbean" in CHAPTER_RUNNING_HEADS
        assert "Sub-Saharan Africa" in CHAPTER_RUNNING_HEADS
        assert "Russia and Eurasia" in CHAPTER_RUNNING_HEADS
