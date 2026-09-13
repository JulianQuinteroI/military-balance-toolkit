# Registro de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [0.3.0] — 2026-09-13

### Añadido
- `mb calco PAÍS`: traduce el orden de batalla a un ORBAT JSON para el skill
  `nato-symbology`, que lo convierte en símbolos APP-6D.
- Módulo `mb2026.simbologia` con el diccionario IISS → 2525D y el traductor.
- Cobertura de traducción en el informe de extracción.

### Cobertura de la traducción
- Fuerzas terrestres 98,0% · aéreas 77,3% · global 88,7%.
- Lo que no se reconoce no se dibuja: se reporta con su motivo.

## [0.2.0] — 2026-09-12

### Añadido
- Capa de consulta `mb` con once órdenes (`ficha`, `correlacion`, `sistema`,
  `gasto`, `orbat`, `inventario`, `ranking`, `presencia`, `paises`,
  `abreviatura`, `sql`), en modo solo lectura.
- Resolutor de nombres de país en español y de dominios del inventario.
- Skill `military-balance` para Claude Code.

### Corregido
- `equipo.servicio` recogía sub-clasificaciones de maniobra: «Light» tenía
  1.952 filas y «Army» 514. Ahora Army tiene 4.603.
- `equipo.dominio` arrastraba totales (`ARTILLERY 9,580`), encadenaba
  sub-niveles (`AIR DEFENCE • SAM`) y repetía erratas del original. De ~250
  valores a 23 dominios canónicos, con el nivel intermedio en `grupo`.
- Los rótulos maquetados como subíndice se perdían al limpiar el markdown.
- `economia` ignoraba etiquetas con espacio perdido o errata
  (`Real GDPgrowth`, `Def bgt`).

## [0.1.0] — 2026-09-12

### Añadido
- ETL del corpus a SQLite: 174 países, 14.816 líneas de inventario, 9.476
  unidades de orden de batalla, 2.366 valores económicos.
- Validación cruzada ficha ↔ Tabla 9 para los 28 países del capítulo 7.
- Informe de calidad de extracción.

### Corregido durante la validación
- Designaciones soviéticas: `9K31 Strela-1` se leía como nueve unidades de
  «K31».
- El dominio se arrastraba entre fuerzas (cazas venezolanos en
  `PATROL AND COASTAL COMBATANTS`).
- Sub-roles confundidos con fuerzas.
- Corte por `;` dentro de paréntesis, que partía en dos un submarino.
