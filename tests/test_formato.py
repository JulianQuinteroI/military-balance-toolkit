"""Tests del render de resultados."""

import json

from mb2026.consulta.consultas import Resultado, Tabla
from mb2026.consulta.formato import como_json, como_texto

TABLA = Tabla(
    titulo="Personal",
    columnas=("Categoría", "Efectivos"),
    filas=(("Activos", 285000), ("Reserva", None)),
    nota="Cifras del volumen.",
)
RESULTADO = Resultado(tablas=(TABLA,), cita="IISS, The Military Balance 2026, p. 417")


class TestTexto:
    def test_incluye_titulo_y_columnas(self):
        salida = como_texto(RESULTADO)
        assert "Personal" in salida
        assert "Categoría" in salida and "Efectivos" in salida

    def test_separa_los_miles(self):
        assert "285,000" in como_texto(RESULTADO)

    def test_los_vacios_se_marcan(self):
        assert "—" in como_texto(RESULTADO)

    def test_alinea_las_columnas(self):
        lineas = [
            linea
            for linea in como_texto(RESULTADO).splitlines()
            if "Activos" in linea or "Reserva" in linea
        ]
        sangrias = {
            len(linea.rstrip()) - len(linea.rstrip().split()[-1]) for linea in lineas
        }
        assert len(sangrias) == 1

    def test_cierra_con_la_cita(self):
        assert como_texto(RESULTADO).rstrip().endswith("p. 417")

    def test_incluye_la_nota(self):
        assert "Cifras del volumen." in como_texto(RESULTADO)

    def test_tabla_vacia_lo_dice(self):
        vacio = Resultado(tablas=(Tabla("Nada", ("A",), ()),))
        assert "sin resultados" in como_texto(vacio).lower()


class TestColumnasSinSeparador:
    def test_los_anios_no_llevan_separador_de_miles(self):
        tabla = Tabla("Serie", ("País", "Año", "Valor"), (("Colombia", 2025, 7.02),))
        salida = como_texto(Resultado(tablas=(tabla,)))
        assert "2025" in salida
        assert "2,025" not in salida

    def test_la_pagina_tampoco(self):
        tabla = Tabla("Ficha", ("Campo", "Valor"), (("Página", 1417),))
        assert "1417" in como_texto(Resultado(tablas=(tabla,)))


class TestMagnitudes:
    def test_usa_los_sufijos_del_volumen(self):
        tabla = Tabla("Economía", ("Indicador", "Valor"), (("pib", 1.71e15),))
        salida = como_texto(Resultado(tablas=(tabla,)))
        assert "1.71 qrn" in salida

    def test_miles_de_millones(self):
        tabla = Tabla("Economía", ("Indicador", "Valor"), (("presupuesto", 8.27e9),))
        assert "8.27 bn" in como_texto(Resultado(tablas=(tabla,)))

    def test_los_porcentajes_quedan_como_estan(self):
        tabla = Tabla("Economía", ("Indicador", "Valor"), (("crecimiento", 2.5),))
        assert "2.5" in como_texto(Resultado(tablas=(tabla,)))

    def test_los_efectivos_llevan_separador(self):
        tabla = Tabla("Personal", ("Categoría", "Efectivos"), (("Activos", 285000),))
        assert "285,000" in como_texto(Resultado(tablas=(tabla,)))


class TestJson:
    def test_estructura_serializable(self):
        datos = json.loads(como_json(RESULTADO))
        assert datos["cita"].endswith("p. 417")
        assert datos["tablas"][0]["titulo"] == "Personal"
        assert datos["tablas"][0]["filas"][0] == ["Activos", 285000]

    def test_conserva_los_nulos(self):
        datos = json.loads(como_json(RESULTADO))
        assert datos["tablas"][0]["filas"][1][1] is None
