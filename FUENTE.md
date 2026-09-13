# Procedencia y restricciones de uso del corpus

## Fuente

**The Military Balance 2026**, International Institute for Strategic Studies (IISS),
publicado por Routledge / Taylor & Francis Group, febrero de 2026.
ISSN de la serie anual. Datos con corte de evaluación IISS a **noviembre de 2025**.

Cobertura declarada por el editor: **174 países y territorios**.

## Archivos de origen

Parse propio del volumen a cuatro formatos paralelos más imágenes:

| Archivo | Contenido |
|---|---|
| `… .json` | Parse por página (545 páginas), items tipados, tablas con `rows`/`html`/`csv` |
| `… .md`   | Texto completo, tablas en HTML embebido |
| `… .xlsx` | 643 hojas, una por tabla |
| `… .txt`  | Texto plano |
| `… -images.zip` | 1.278 JPG: 545 escaneos de página completa + 733 recortes |

Ubicación por defecto: `~/Downloads/Military Balance Parser 2026`.
Configurable con la variable de entorno `MB2026_SOURCE`.

## Restricciones (leer antes de usar cualquier salida)

La página de créditos del volumen establece:

> All rights reserved. No part of this publication may be reproduced, stored,
> transmitted, or disseminated, in any form, or by any means, without prior
> written permission from Taylor & Francis Group.

Regla operativa adoptada en este repositorio:

| Uso | Estado |
|---|---|
| Análisis interno y derivación de indicadores en local | Permitido |
| Citar cifras puntuales con atribución (*IISS, The Military Balance 2026*, p. N) | Permitido |
| Versionar el corpus fuente o la base de datos generada en git | **Prohibido** (ver `.gitignore`) |
| Publicar tablas, párrafos o imágenes del volumen | **Prohibido** |
| Empaquetar el corpus o un clon de su base de datos en un entregable a cliente | **Requiere licencia IISS** (*Military Balance+*) |

Los **hechos** (cantidades de equipo, cifras presupuestales) no son objeto de
apropiación; la **selección, redacción y compilación** del IISS sí lo son.
Este repositorio contiene únicamente **código de extracción**: ni el corpus ni la
base de datos resultante se versionan.

## Qué contenido derivado del volumen hay en este repositorio

Se documenta para que sea auditable, ya que el repositorio es público:

| Dónde | Qué | Por qué |
|---|---|---|
| `tests/test_equipo.py`, `test_unidades.py`, `test_personal.py`, `test_economia.py`, `test_despliegues.py` | Renglones sueltos con la **notación** del volumen (`**IFV** 60: 28 …; 32 …`) y designaciones de material de fabricante | Son el formato de entrada que el parser debe saber leer. Sin ellos no se puede probar que lo hace, ni detectar una regresión cuando cambie la edición. |
| `tests/test_validacion_corpus.py` | ~15 cifras de Colombia (efectivos por fuerza, presupuesto, inventario conocido) | Es el contraste contra el impreso que demuestra que la extracción es fiel. Solo se ejecuta si el corpus real está disponible. |
| `src/mb2026/consulta/catalogo.py` | Los 174 códigos de país del IISS | Sirve para que los tests comprueben que ningún alias apunta a un código inexistente. |
| `src/mb2026/parsers/estructura.py`, `simbologia/diccionario.py` | Nombres de dominio del inventario y siglas de escalón | Vocabulario necesario para interpretar la fuente. |
| `README.md` | Tres cifras de Colombia, citadas | Ilustran qué devuelve la herramienta. |

No hay tablas, figuras, mapas ni prosa del volumen. Los fixtures compartidos
usan material sintético; los que conservan notación real están donde esa
notación es lo que se prueba. Las cifras son hechos, que no son objeto de
apropiación; la selección, redacción y compilación del IISS sí lo son, y no se
reproducen.

## Marcas de incertidumbre del IISS

El parser preserva las marcas de juicio del editor. Descartarlas convierte
estimaciones en falsa precisión:

| Marca | Significado |
|---|---|
| `ε` | Cifra estimada |
| `†` | El IISS considera dudosa la operatividad del equipo |
| `*` | Aeronave contabilizada como apta para combate |
| `+` | Unidad reforzada / el total no es menor que la cifra dada |
| `(-)` | Unidad bajo efectivos o con elementos destacados |
| `some` | Inventario preciso no disponible al cierre de edición |
| `up to` | El total es como máximo la cifra dada, puede ser menor |
