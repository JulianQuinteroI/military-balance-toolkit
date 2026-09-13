"""Tests de las utilidades de normalización de texto del corpus."""

import pytest

from mb2026.texto import (
    Cantidad,
    limpiar_markdown,
    nivel_heading,
    parsear_cantidad,
    parsear_magnitud,
)


class TestLimpiarMarkdown:
    def test_elimina_negritas_y_cursivas(self):
        assert limpiar_markdown("**Colombia** *COL*") == "Colombia COL"

    def test_elimina_subrayado_html(self):
        assert limpiar_markdown("<u>**Ukraine** UKR</u>") == "Ukraine UKR"

    def test_elimina_notas_al_pie_sup(self):
        assert limpiar_markdown("Def bdgt<sup>[a]</sup>") == "Def bdgt"

    def test_colapsa_espacios_y_recorta(self):
        assert limpiar_markdown("  ACTIVE   285,000  \n") == "ACTIVE 285,000"

    def test_preserva_marcas_de_incertidumbre_del_iiss(self):
        assert limpiar_markdown("**ε600,000**") == "ε600,000"
        assert limpiar_markdown("**BTR-80†**") == "BTR-80†"

    def test_desenvuelve_sup_y_sub_que_llevan_el_rotulo(self):
        """El volumen maqueta algunos encabezados como subíndice."""
        assert limpiar_markdown("<sub>HELICOPTERS</sub>") == "HELICOPTERS"
        assert limpiar_markdown("<sup>AIR DEFENCE</sup>") == "AIR DEFENCE"

    def test_elimina_imagenes_decorativas(self):
        """Tres fichas de país llevan el escudo incrustado en el encabezado."""
        crudo = "Cyprus CYP ![logo: Cyprus coat of arms](page84image1v2.jpg)"
        assert limpiar_markdown(crudo) == "Cyprus CYP"

    def test_cadena_vacia(self):
        assert limpiar_markdown("") == ""
        assert limpiar_markdown(None) == ""


class TestNivelHeading:
    @pytest.mark.parametrize(
        "md,esperado",
        [
            ("# Colombia COL", 1),
            ("## **Capabilities**", 2),
            ("### **Army** 206,400", 3),
            ("#### **Mechanised**", 4),
            ("texto suelto", 0),
            ("", 0),
        ],
    )
    def test_detecta_nivel(self, md, esperado):
        assert nivel_heading(md) == esperado


class TestParsearMagnitud:
    @pytest.mark.parametrize(
        "texto,esperado",
        [
            ("1.71qrn", 1.71e15),
            ("34.6trn", 3.46e13),
            ("8.27bn", 8.27e9),
            ("38.0m", 3.80e7),
            ("462bn", 4.62e11),
            ("7.02", 7.02),
            ("1,234", 1234.0),
        ],
    )
    def test_convierte_sufijos_iiss(self, texto, esperado):
        m = parsear_magnitud(texto)
        assert m is not None
        assert m.valor == pytest.approx(esperado)

    def test_marca_estimaciones(self):
        m = parsear_magnitud("ε8.27bn")
        assert m.valor == pytest.approx(8.27e9)
        assert m.estimado is True

    def test_valores_no_numericos_devuelven_none(self):
        assert parsear_magnitud("n.k.") is None
        assert parsear_magnitud("") is None
        assert parsear_magnitud(None) is None

    def test_es_inmutable(self):
        m = parsear_magnitud("1bn")
        with pytest.raises(AttributeError):
            m.valor = 2.0  # type: ignore[misc]


class TestParsearCantidad:
    def test_entero_simple(self):
        c = parsear_cantidad("121")
        assert c == Cantidad(valor=121)

    def test_separador_de_miles(self):
        assert parsear_cantidad("1,507").valor == 1507

    def test_sufijo_mas_marca_minimo(self):
        c = parsear_cantidad("13+")
        assert c.valor == 13
        assert c.minimo is True

    def test_epsilon_marca_estimado(self):
        c = parsear_cantidad("ε600,000")
        assert c.valor == 600000
        assert c.estimado is True

    def test_some_es_indeterminado(self):
        c = parsear_cantidad("some")
        assert c.valor is None
        assert c.indeterminado is True

    def test_up_to_marca_maximo(self):
        c = parsear_cantidad("up to 24")
        assert c.valor == 24
        assert c.maximo is True

    def test_nil_es_cero_explicito(self):
        assert parsear_cantidad("NIL").valor == 0

    def test_texto_sin_cantidad(self):
        assert parsear_cantidad("Cascavel") is None
        assert parsear_cantidad("") is None
