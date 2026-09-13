"""Catálogo de códigos de país del volumen, congelado para validar alias.

Se genera con scripts/regenerar_catalogo.py a partir de la base y se versiona
para que los tests puedan comprobar que ningún alias apunta a un código
inexistente sin depender de que la base esté construida.
"""

from __future__ import annotations

#: Códigos que el IISS usa para los países con ficha propia.
CODIGOS_CONOCIDOS: frozenset[str] = frozenset(
    {
        "AFG", "ALB", "ALG", "ANG", "ARG", "ARM", "ATG", "AUS",
        "AUT", "AZE", "BDI", "BEL", "BEN", "BFA", "BGD", "BHR",
        "BHS", "BIH", "BLG", "BLR", "BLZ", "BOL", "BRB", "BRN",
        "BRZ", "BWA", "CAM", "CAN", "CAR", "CHA", "CHE", "CHL",
        "CIV", "CMR", "COG", "COL", "CPV", "CRI", "CRO", "CUB",
        "CYP", "CZE", "DJB", "DNK", "DOM", "DPRK", "DRC", "ECU",
        "EGY", "EQG", "ERI", "ESP", "EST", "ETH", "FIN", "FJI",
        "FRA", "GAB", "GAM", "GEO", "GER", "GHA", "GNB", "GRC",
        "GUA", "GUI", "GUY", "HND", "HTI", "HUN", "IDN", "IND",
        "IRL", "IRN", "IRQ", "ISL", "ISR", "ITA", "JAM", "JOR",
        "JPN", "KAZ", "KEN", "KGZ", "KWT", "LAO", "LBN", "LBR",
        "LBY", "LKA", "LSO", "LTU", "LUX", "LVA", "MDA", "MDG",
        "MDV", "MEX", "MKD", "MLI", "MLT", "MMR", "MNE", "MNG",
        "MOR", "MOZ", "MRT", "MUS", "MWI", "MYS", "NAM", "NER",
        "NGA", "NIC", "NLD", "NOR", "NPL", "NZL", "OMN", "PAK",
        "PAN", "PER", "PHL", "PNG", "POL", "PRC", "PRT", "PRY",
        "PT", "QTR", "ROC", "ROK", "ROM", "RSA", "RUS", "RWA",
        "SAU", "SDN", "SEN", "SER", "SGP", "SLE", "SLV", "SOM",
        "SSD", "SUR", "SVK", "SVN", "SWE", "SYC", "SYR", "TGO",
        "THA", "TJK", "TKM", "TLS", "TON", "TTO", "TUN", "TUR",
        "TZA", "UAE", "UGA", "UK", "UKR", "URY", "US", "UZB",
        "VEN", "VNM", "XKX", "YEM", "ZMB", "ZWE",
    }
)
