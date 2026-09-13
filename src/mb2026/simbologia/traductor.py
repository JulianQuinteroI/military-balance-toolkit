"""De filas de `unidades` a un ORBAT que el skill `nato-symbology` sabe leer.

Lo que no se puede traducir con certeza no se emite: aparece en `sin_mapear`
con su motivo. Un símbolo equivocado en un calco es peor que un hueco.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from mb2026.simbologia.diccionario import MARCA_PLATAFORMA, escalon_de, tipo_de

#: Afiliaciones que acepta el skill.
AFILIACIONES: frozenset[str] = frozenset(
    {"amigo", "hostil", "neutral", "desconocido", "presunto amigo", "sospechoso"}
)

#: Escalones del IISS que denotan un puesto de mando.
_ECHELONES_DE_MANDO = frozenset({"hq", "comd"})
_MOTIVO_SIN_FUNCION = "el tipo no declara función y el rol no la resuelve"


@dataclass(frozen=True, slots=True)
class UnidadOrbat:
    """Una unidad lista para el generador de simbología."""

    id: str
    label: str
    afiliacion: str
    escalon: str = ""
    tipo: str = ""
    entidad: str = ""
    designacion: str = ""
    formacion_superior: str = ""
    cantidad: int | None = None
    hq: bool = False
    info: str = ""

    def como_diccionario(self) -> dict[str, object]:
        """Forma que espera el ORBAT JSON del skill, sin campos vacíos."""
        crudo: dict[str, object] = {
            "id": self.id,
            "label": self.label,
            "afiliacion": self.afiliacion,
        }
        opcionales: Mapping[str, object] = {
            "escalon": self.escalon,
            "tipo": self.tipo,
            "entidad": self.entidad,
            "designacion": self.designacion,
            "formacionSuperior": self.formacion_superior,
            "info": self.info,
        }
        crudo.update({clave: valor for clave, valor in opcionales.items() if valor})
        if self.cantidad is not None and self.cantidad > 1:
            crudo["cantidad"] = self.cantidad
        if self.hq:
            crudo["hq"] = True
        return crudo


@dataclass(frozen=True, slots=True)
class UnidadSinMapear:
    """Una fila que no se pudo traducir, con el motivo."""

    id: str
    tipo: str
    rol: str
    motivo: str


@dataclass(frozen=True, slots=True)
class Calco:
    """El resultado de traducir un orden de batalla."""

    unidades: tuple[UnidadOrbat, ...] = field(default_factory=tuple)
    sin_mapear: tuple[UnidadSinMapear, ...] = field(default_factory=tuple)

    @property
    def cobertura(self) -> float:
        """Fracción de filas que obtuvieron símbolo."""
        total = len(self.unidades) + len(self.sin_mapear)
        return len(self.unidades) / total if total else 0.0

    def como_orbat(self) -> list[dict[str, object]]:
        """El ORBAT JSON que consume `nato-symbology`."""
        return [unidad.como_diccionario() for unidad in self.unidades]


def _identificador(fila: Mapping[str, object]) -> str:
    return f"{fila['codigo_pais']}-{fila['id']}"


def _etiqueta(fila: Mapping[str, object]) -> str:
    designacion = str(fila["designacion"] or "")
    tipo = str(fila["tipo"] or "")
    return f"{designacion} {tipo}".strip() if designacion else tipo


def _plataforma(tipo: str) -> str:
    if MARCA_PLATAFORMA not in f" {tipo.lower()} ":
        return ""
    _, _, cola = tipo.partition(MARCA_PLATAFORMA.strip())
    return cola.strip()


def traducir_orbat(
    filas: Iterable[Mapping[str, object]], afiliacion: str
) -> Calco:
    """Traduce filas de `unidades` a un calco con simbología NATO."""
    if afiliacion not in AFILIACIONES:
        raise ValueError(
            f"afiliación «{afiliacion}» no reconocida; usa una de: "
            f"{', '.join(sorted(AFILIACIONES))}"
        )

    unidades: list[UnidadOrbat] = []
    sin_mapear: list[UnidadSinMapear] = []
    for fila in filas:
        tipo_iiss = str(fila["tipo"] or "")
        rol = str(fila["rol"] or "")
        traduccion = tipo_de(tipo_iiss, rol, str(fila["servicio"] or ""))
        identificador = _identificador(fila)
        if not traduccion.reconocida:
            sin_mapear.append(
                UnidadSinMapear(identificador, tipo_iiss, rol, _MOTIVO_SIN_FUNCION)
            )
            continue
        echelon = str(fila["echelon"] or "").lower()
        padre = fila["padre_id"]
        unidades.append(
            UnidadOrbat(
                id=identificador,
                label=_etiqueta(fila),
                afiliacion=afiliacion,
                escalon=escalon_de(echelon),
                tipo=traduccion.tipo,
                entidad=traduccion.entidad,
                designacion=str(fila["designacion"] or ""),
                formacion_superior=(
                    f"{fila['codigo_pais']}-{padre}" if padre is not None else ""
                ),
                cantidad=fila["cantidad"] if isinstance(fila["cantidad"], int) else None,
                hq=echelon in _ECHELONES_DE_MANDO,
                info=_plataforma(tipo_iiss),
            )
        )
    return Calco(unidades=tuple(unidades), sin_mapear=tuple(sin_mapear))
