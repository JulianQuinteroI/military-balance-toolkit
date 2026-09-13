"""Orquestador: del corpus a la base SQLite.

Cada parser devuelve estructuras inmutables; aquí solo se aplanan a filas y se
escriben. La resolución de identificadores (el padre de cada unidad, el código
de país de la Tabla 9) también ocurre en esta capa, no en los parsers.
"""

from __future__ import annotations

import sqlite3
import unicodedata
from collections.abc import Callable, Hashable, Iterable
from dataclasses import dataclass
from pathlib import Path

from mb2026 import config, db
from mb2026.corpus import Item, cargar_items
from mb2026.parsers.abreviaturas import parsear_abreviaturas
from mb2026.parsers.comparacion import ComparacionInternacional, parsear_comparacion
from mb2026.parsers.despliegues import parsear_despliegues, parsear_fuerzas_extranjeras
from mb2026.parsers.economia import parsear_economia
from mb2026.parsers.equipo import parsear_equipo
from mb2026.parsers.estructura import SECCION_FUERZAS
from mb2026.parsers.indice_paises import (
    EntradaIndice,
    parsear_codigos_pais,
    parsear_indice_paises,
)
from mb2026.parsers.personal import parsear_personal
from mb2026.parsers.unidades import parsear_unidades
from mb2026.segmentacion import FichaPais, segmentar_paises
from mb2026.texto import Cantidad


@dataclass(frozen=True, slots=True)
class Informe:
    """Resultado de una corrida de carga."""

    ruta: Path
    paises: int
    conteos: dict[str, int]


def construir(ruta_corpus: Path | None = None, ruta_base: Path | None = None) -> Informe:
    """Ejecuta la extracción completa y deja la base lista para consultar."""
    origen = ruta_corpus or config.ruta_json_corpus()
    destino = ruta_base or config.ruta_base_datos()

    items = cargar_items(origen)
    indice = parsear_indice_paises(items)
    fichas = segmentar_paises(items, indice)
    nombres_pais = frozenset(entrada.nombre for entrada in indice)

    conexion = db.crear_base(destino)
    try:
        _cargar_referencia(conexion, items, indice, origen)
        for ficha in fichas:
            _cargar_ficha(conexion, ficha, nombres_pais)
        _cargar_comparacion(conexion, parsear_comparacion(items), fichas)
        conexion.commit()
        return Informe(ruta=destino, paises=len(fichas), conteos=db.conteos(conexion))
    finally:
        conexion.close()


def _clave(nombre: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    return "".join(caracter for caracter in sin_acentos.lower() if caracter.isalnum())


def _cantidad(cantidad: Cantidad | None) -> int | None:
    return cantidad.valor if cantidad else None


def _cargar_referencia(
    conexion: sqlite3.Connection,
    items: tuple[Item, ...],
    indice: tuple[EntradaIndice, ...],
    origen: Path,
) -> None:
    db.insertar(
        conexion,
        "fuente",
        ("clave", "valor"),
        (
            ("cita", config.FUENTE_CITA),
            ("edicion", str(config.EDICION)),
            ("corte_datos", config.CORTE_DATOS),
            ("archivo_origen", origen.name),
        ),
    )
    codigos = parsear_codigos_pais(items)
    for entrada in indice:
        codigos.setdefault(entrada.codigo, entrada.nombre)
    db.insertar(conexion, "codigos_territorio", ("codigo", "nombre"), codigos.items())
    db.insertar(
        conexion,
        "abreviaturas",
        ("sigla", "definicion"),
        ((a.sigla, a.definicion) for a in parsear_abreviaturas(items)),
    )


def _cargar_ficha(
    conexion: sqlite3.Connection, ficha: FichaPais, nombres_pais: frozenset[str]
) -> None:
    db.insertar(
        conexion,
        "paises",
        ("codigo", "nombre", "region", "pagina"),
        ((ficha.codigo, ficha.nombre, ficha.region, ficha.pagina_impresa),),
    )
    _cargar_economia(conexion, ficha)
    _cargar_personal(conexion, ficha)
    _cargar_unidades(conexion, ficha)
    _cargar_equipo(conexion, ficha)
    _cargar_despliegues(conexion, ficha, nombres_pais)


def _cargar_economia(conexion: sqlite3.Connection, ficha: FichaPais) -> None:
    economia = parsear_economia(ficha.items)
    if economia.moneda:
        db.insertar(
            conexion,
            "monedas",
            ("codigo_pais", "nombre", "codigo_iso"),
            ((ficha.codigo, economia.moneda.nombre, economia.moneda.codigo),),
        )
    db.insertar(
        conexion,
        "economia",
        ("codigo_pais", "anio", "indicador", "unidad", "valor", "estimado"),
        (
            (ficha.codigo, v.anio, v.indicador, v.unidad, v.valor, int(v.estimado))
            for v in _sin_duplicados(
                economia.valores, lambda v: (v.anio, v.indicador, v.unidad)
            )
        ),
    )
    db.insertar(
        conexion,
        "serie_presupuesto_real",
        ("codigo_pais", "anio", "valor", "unidad"),
        ((ficha.codigo, anio, valor, economia.unidad_serie)
         for anio, valor in dict(economia.serie_real).items()),
    )
    if economia.poblacion is not None:
        db.insertar(conexion, "poblacion", ("codigo_pais", "total"),
                    ((ficha.codigo, economia.poblacion),))
    db.insertar(
        conexion,
        "demografia",
        ("codigo_pais", "sexo", "rango", "porcentaje"),
        ((ficha.codigo, d.sexo, d.rango, d.porcentaje)
         for d in _sin_duplicados(economia.demografia, lambda d: (d.sexo, d.rango))),
    )


def _cargar_personal(conexion: sqlite3.Connection, ficha: FichaPais) -> None:
    personal = parsear_personal(ficha.items)
    db.insertar(
        conexion,
        "personal",
        ("codigo_pais", "categoria", "componente", "cantidad", "estimado",
         "minimo", "maximo", "indeterminado"),
        (
            (ficha.codigo, e.categoria, e.componente, e.cantidad.valor,
             int(e.cantidad.estimado), int(e.cantidad.minimo),
             int(e.cantidad.maximo), int(e.cantidad.indeterminado))
            for e in _sin_duplicados(
                personal.efectivos, lambda e: (e.categoria, e.componente)
            )
        ),
    )
    if personal.conscripcion:
        db.insertar(conexion, "conscripcion", ("codigo_pais", "nota"),
                    ((ficha.codigo, personal.conscripcion),))


def _cargar_unidades(conexion: sqlite3.Connection, ficha: FichaPais) -> None:
    columnas = (
        "codigo_pais", "padre_id", "profundidad", "servicio", "rol", "cantidad",
        "estimado", "designacion", "tipo", "echelon", "texto_crudo", "pagina",
    )
    orbat = parsear_unidades(ficha.items)
    identificadores: dict[int, int] = {}
    for unidad in orbat.unidades:
        identificadores[unidad.orden] = db.insertar_uno(
            conexion,
            "unidades",
            columnas,
            (
                ficha.codigo,
                identificadores.get(unidad.padre) if unidad.padre is not None else None,
                unidad.profundidad,
                unidad.servicio,
                unidad.rol,
                _cantidad(unidad.cantidad),
                int(bool(unidad.cantidad and unidad.cantidad.estimado)),
                unidad.designacion,
                unidad.tipo,
                unidad.echelon,
                unidad.texto_crudo,
                unidad.pagina,
            ),
        )
    db.insertar(
        conexion,
        "renglones_sin_leer",
        ("codigo_pais", "seccion", "texto", "pagina"),
        ((ficha.codigo, SECCION_FUERZAS, r.texto, r.pagina) for r in orbat.sin_leer),
    )


def _cargar_equipo(conexion: sqlite3.Connection, ficha: FichaPais) -> None:
    db.insertar(
        conexion,
        "equipo",
        ("codigo_pais", "servicio", "dominio", "grupo", "categoria", "subcategoria",
         "sistema",
         "cantidad", "estimado", "minimo", "indeterminado", "total_categoria",
         "dudoso", "texto_crudo", "pagina"),
        (
            (
                ficha.codigo, e.servicio, e.dominio, e.grupo, e.categoria,
                e.subcategoria, e.sistema, _cantidad(e.cantidad),
                int(bool(e.cantidad and e.cantidad.estimado)),
                int(bool(e.cantidad and e.cantidad.minimo)),
                int(bool(e.cantidad and e.cantidad.indeterminado)),
                _cantidad(e.total_categoria), int(e.dudoso), e.texto_crudo, e.pagina,
            )
            for e in parsear_equipo(ficha.items)
        ),
    )


def _cargar_despliegues(
    conexion: sqlite3.Connection, ficha: FichaPais, nombres_pais: frozenset[str]
) -> None:
    db.insertar(
        conexion,
        "despliegues",
        ("codigo_pais", "destino", "organizacion", "mision", "efectivos", "detalle"),
        (
            (ficha.codigo, d.destino, d.organizacion, d.mision,
             _cantidad(d.efectivos), d.detalle)
            for d in parsear_despliegues(ficha.items)
        ),
    )
    db.insertar(
        conexion,
        "fuerzas_extranjeras",
        ("codigo_pais", "origen", "efectivos", "detalle"),
        (
            (ficha.codigo, f.origen, _cantidad(f.efectivos), f.detalle)
            for f in parsear_fuerzas_extranjeras(ficha.items, nombres_pais)
        ),
    )


def _cargar_comparacion(
    conexion: sqlite3.Connection,
    comparacion: ComparacionInternacional,
    fichas: tuple[FichaPais, ...],
) -> None:
    por_nombre = {_clave(f.nombre): f.codigo for f in fichas}
    db.insertar(
        conexion,
        "comparacion_gasto",
        ("pais", "codigo_pais", "region", "anio", "presupuesto_usd_m",
         "per_capita_usd", "pct_pib", "es_agregado"),
        (
            (f.pais, por_nombre.get(_clave(f.pais)), f.region, f.anio,
             f.presupuesto_usd_m, f.per_capita_usd, f.pct_pib, int(f.es_agregado))
            for f in _sin_duplicados(
                comparacion.gasto, lambda f: (f.pais, f.region, f.anio)
            )
        ),
    )
    db.insertar(
        conexion,
        "comparacion_personal",
        ("pais", "codigo_pais", "region", "anio", "activos_miles",
         "reservistas_miles", "gendarmeria_miles", "es_agregado"),
        (
            (f.pais, por_nombre.get(_clave(f.pais)), f.region, f.anio, f.activos_miles,
             f.reservistas_miles, f.gendarmeria_miles, int(f.es_agregado))
            for f in _sin_duplicados(
                comparacion.personal, lambda f: (f.pais, f.region, f.anio)
            )
        ),
    )


def _sin_duplicados[T](filas: Iterable[T], clave: Callable[[T], Hashable]) -> list[T]:
    """Conserva la primera aparición de cada clave.

    El volumen repite algún renglón al cruzar de página; la clave primaria de la
    tabla no lo admitiría y perder la corrida entera por eso sería peor.
    """
    vistas: set[Hashable] = set()
    unicas: list[T] = []
    for fila in filas:
        identidad = clave(fila)
        if identidad in vistas:
            continue
        vistas.add(identidad)
        unicas.append(fila)
    return unicas
