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
