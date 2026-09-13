"""Fixtures compartidos. El corpus real no se versiona (ver FUENTE.md)."""

import json
from pathlib import Path

import pytest

from mb2026.config import ruta_json_corpus


def _pagina(numero: int, items: list[dict]) -> dict:
    return {
        "page_number": numero,
        "items": items,
        "page_width": 535.7,
        "page_height": 697.275,
        "success": True,
    }


@pytest.fixture
def json_sintetico(tmp_path: Path) -> Path:
    """Miniatura del corpus con la forma real de una entrada de país."""
    documento = {
        "pages": [
            _pagina(
                10,
                [
                    {"type": "header", "md": "**Latin America** 9"},
                    {"type": "heading", "md": "# Ruritania RUR"},
                    {
                        "type": "table",
                        "md": "",
                        "rows": [
                            ["Ruritanian Krone RUK", "", "2024", "2025", "2026"],
                            ["GDP", "RUK", "1.71qrn", "1.83qrn", "1.94qrn"],
                            ["", "USD", "419bn", "438bn", "462bn"],
                            ["Def bdgt", "RUK", "31.2trn", "34.6trn", "38.7trn"],
                            ["", "USD", "7.65bn", "8.27bn", "9.20bn"],
                        ],
                    },
                    {"type": "heading", "md": "## Capabilities"},
                    {"type": "text", "md": "Las fuerzas de Ruritania son ligeras."},
                    {
                        "type": "heading",
                        "md": "## **ACTIVE 285,000 (Army 206,400, Navy 60,300 Air 18,300) "
                        "Gendarmerie & Paramilitary 165,050**",
                    },
                    {"type": "heading", "md": "# **Latin America and the Caribbean**"},
                ],
            ),
            _pagina(
                11,
                [
                    {"type": "heading", "md": "### **Army** 206,400"},
                    {"type": "heading", "md": "### **EQUIPMENT BY TYPE**"},
                    {"type": "text", "md": "**RECCE** 121 XR-9 *Vigía*"},
                    {"type": "footer", "md": "**10 THE MILITARY BALANCE** 2026"},
                    {"type": "heading", "md": "## Borduria BOR"},
                ],
            ),
        ]
    }
    destino = tmp_path / "corpus.json"
    destino.write_text(json.dumps(documento), encoding="utf8")
    return destino


@pytest.fixture
def corpus_sintetico_completo(tmp_path: Path) -> Path:
    """Corpus mínimo pero completo: fichas más las cuatro tablas de referencia."""
    cabecera_t9 = [
        "",
        "Defence Budget (current USDm)2023",
        "Defence Budget (current USDm)2024",
        "Defence Budget (current USDm)2025",
        "Defence Budget per capita (current USD)2023",
        "Defence Budget per capita (current USD)2024",
        "Defence Budget per capita (current USD)2025",
        "Defence Budget % of GDP2023",
        "Defence Budget % of GDP2024",
        "Defence Budget % of GDP2025",
        "Active Armed Forces (000)2025",
        "Estimated Reservists (000)2025",
        "Gendarmerie & Paramilitary (000)2025",
    ]
    documento = {
        "pages": [
            _pagina(
                418,
                [
                    {"type": "heading", "md": "# Ruritania RUR"},
                    {
                        "type": "table",
                        "md": "",
                        "rows": [
                            ["Ruritanian Krone RUK", "", "2024", "2025", "2026"],
                            ["GDP", "RUK", "1.71trn", "1.83trn", "1.94trn"],
                            ["Def bdgt", "USD", "7.65bn", "8.27bn", "9.20bn"],
                        ],
                    },
                    {
                        "type": "table",
                        "md": "Real-terms defence budget trend (USDbn, constant 2015)",
                        "rows": [
                            ["Year", "Defence budget (USDbn, constant 2015)"],
                            ["2024", "6.5"],
                            ["2025", "7.02"],
                            ["2026", "7.4"],
                        ],
                    },
                    {"type": "table", "md": "", "rows": [["Population", "49,842,298"]]},
                    {
                        "type": "heading",
                        "md": "## **ACTIVE 285,000 (Army 206,400) "
                        "Gendarmerie & Paramilitary 165,050**",
                    },
                    {"type": "heading", "md": "### **Army** 206,400"},
                    {"type": "heading", "md": "### **FORCES BY ROLE**"},
                    {"type": "text", "md": "1 (1st) mech div (2 mech bde)"},
                    {"type": "heading", "md": "### **EQUIPMENT BY TYPE**"},
                    {"type": "heading", "md": "### **ARMOURED FIGHTING VEHICLES**"},
                    {"type": "text", "md": "**RECCE** 121 XR-9 *Vigía*"},
                    {"type": "heading", "md": "## **DEPLOYMENT**"},
                    {"type": "text", "md": "**EGYPT:** MFO 275; 1 inf bn"},
                    {"type": "heading", "md": "## **FOREIGN FORCES**"},
                    {"type": "text", "md": "Borduria 50"},
                ],
            ),
            _pagina(
                420,
                [
                    {"type": "heading", "md": "# Borduria BOR"},
                    {"type": "heading", "md": "## **ACTIVE 12,000 (Army 12,000)**"},
                ],
            ),
            _pagina(
                536,
                [
                    {"type": "heading", "md": "## Table 8 List of abbreviations for data sections"},
                    {
                        "type": "table",
                        "md": "",
                        "rows": [["bde", "brigade", "bn", "battalion", "div", "division"]],
                    },
                ],
            ),
            _pagina(
                538,
                [
                    {
                        "type": "heading",
                        "md": "# Table 9 International comparisons of defence budgets "
                        "and military personnel",
                    },
                    {
                        "type": "table",
                        "md": "",
                        "rows": [
                            cabecera_t9,
                            ["Latin America and the Caribbean"] + [""] * 12,
                            ["Ruritania", "5,573", "7,652", "8,268", "113", "154",
                             "166", "1.52", "1.83", "1.89", "285", "35", "165"],
                            ["Borduria", "100", "110", "120", "10", "11", "12",
                             "0.50", "0.55", "0.60", "12", "0", "0"],
                        ],
                    },
                ],
            ),
            _pagina(
                544,
                [
                    {
                        "type": "heading",
                        "md": "## Table 10 Index of country/territory abbreviations",
                    },
                    {"type": "text", "md": "**RUR**.....Ruritania **BOR**.....Borduria"},
                ],
            ),
            _pagina(
                545,
                [
                    {
                        "type": "table",
                        "md": "### Table 11 Index of countries and territories",
                        "rows": [
                            ["Ruritania RUR . . . . . .417", "Borduria BOR . . . . . .419", ""]
                        ],
                    }
                ],
            ),
        ]
    }
    destino = tmp_path / "corpus-completo.json"
    destino.write_text(json.dumps(documento), encoding="utf8")
    return destino


@pytest.fixture(scope="session")
def corpus_real() -> Path:
    """Ruta al corpus completo; salta la prueba si no está disponible."""
    ruta = ruta_json_corpus()
    if not ruta.exists():
        pytest.skip(f"corpus no disponible en {ruta}")
    return ruta
