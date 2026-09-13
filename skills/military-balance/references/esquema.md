# Esquema de la base `mb2026.sqlite`

Generado desde la base real. Úsalo para escribir consultas con `sql`.
Todas las tablas de país se unen por `codigo_pais` → `paises.codigo`.

**`abreviaturas`** (309 filas) — `sigla`, `definicion`

**`codigos_territorio`** (184 filas) — `codigo`, `nombre`

**`comparacion_gasto`** (567 filas) — `pais`, `codigo_pais`, `region`, `anio`, `presupuesto_usd_m`, `per_capita_usd`, `pct_pib`, `es_agregado`

**`comparacion_personal`** (189 filas) — `pais`, `codigo_pais`, `region`, `anio`, `activos_miles`, `reservistas_miles`, `gendarmeria_miles`, `es_agregado`

**`conscripcion`** (60 filas) — `codigo_pais`, `nota`

**`demografia`** (1,476 filas) — `codigo_pais`, `sexo`, `rango`, `porcentaje`

**`despliegues`** (626 filas) — `id`, `codigo_pais`, `destino`, `organizacion`, `mision`, `efectivos`, `detalle`

**`economia`** (2,366 filas) — `codigo_pais`, `anio`, `indicador`, `unidad`, `valor`, `estimado`

**`equipo`** (14,815 filas) — `id`, `codigo_pais`, `servicio`, `dominio`, `grupo`, `categoria`, `subcategoria`, `sistema`, `cantidad`, `estimado`, `minimo`, `indeterminado`, `total_categoria`, `dudoso`, `texto_crudo`, `pagina`

**`fuente`** (4 filas) — `clave`, `valor`

**`fuerzas_extranjeras`** (687 filas) — `id`, `codigo_pais`, `origen`, `efectivos`, `detalle`

**`monedas`** (159 filas) — `codigo_pais`, `nombre`, `codigo_iso`

**`paises`** (174 filas) — `codigo`, `nombre`, `region`, `pagina`

**`personal`** (1,028 filas) — `codigo_pais`, `categoria`, `componente`, `cantidad`, `estimado`, `minimo`, `maximo`, `indeterminado`

**`poblacion`** (152 filas) — `codigo_pais`, `total`

**`renglones_sin_leer`** (308 filas) — `id`, `codigo_pais`, `seccion`, `texto`, `pagina`

**`serie_presupuesto_real`** (2,744 filas) — `codigo_pais`, `anio`, `valor`, `unidad`

**`unidades`** (9,476 filas) — `id`, `codigo_pais`, `padre_id`, `profundidad`, `servicio`, `rol`, `cantidad`, `estimado`, `designacion`, `tipo`, `echelon`, `texto_crudo`, `pagina`

## Vista

**`v_resumen_pais`** — `codigo`, `nombre`, `region`, `presupuesto_usd_2025`, `activos`, `gendarmeria`, `lineas_equipo`, `unidades`

## Vocabularios

### Dominios de `equipo.dominio`

- `AIRCRAFT` (2,344)
- `ARMOURED FIGHTING VEHICLES` (2,225)
- `ARTILLERY` (1,693)
- `HELICOPTERS` (1,476)
- `PATROL AND COASTAL COMBATANTS` (1,391)
- `AIR DEFENCE` (1,076)
- `LOGISTICS AND SUPPORT` (810)
- `AIR-LAUNCHED MISSILES` (626)
- `ANTI-TANK/ANTI-INFRASTRUCTURE` (622)
- `ENGINEERING & MAINTENANCE VEHICLES` (599)
- `UNINHABITED AERIAL VEHICLES` (386)
- `AMPHIBIOUS` (328)
- `BOMBS` (222)
- `SATELLITES` (188)
- `SURFACE-TO-SURFACE MISSILE LAUNCHERS` (152)
- `MINE WARFARE` (134)
- `PRINCIPAL SURFACE COMBATANTS` (125)
- `UNINHABITED MARITIME SYSTEMS` (121)
- `SUBMARINES` (74)
- `UNINHABITED MARITIME PLATFORMS` (73)
- `COASTAL DEFENCE` (73)
- `RADARS` (19)
- `MISSILE DEFENCE` (3)

### Regiones de `paises.region`

- `Asia` (29)
- `Europe` (38)
- `Latin America and the Caribbean` (28)
- `Middle East and North Africa` (20)
- `North America` (2)
- `Russia and Eurasia` (12)
- `Sub-Saharan Africa` (45)

### Indicadores de `economia.indicador`

- `ayuda_militar_us` (69)
- `crecimiento_real_pib` (478)
- `gasto_defensa` (126)
- `pib` (938)
- `presupuesto_defensa` (743)
- `presupuesto_seguridad` (12)

### Categorías de `personal.categoria`

- `activo` (687)
- `gendarmeria` (112)
- `reserva` (229)

### Categorías de `equipo.categoria` más frecuentes

Son los códigos de tipo del IISS (Tabla 8). Consúltalos con `abreviatura <código>` cuando no reconozcas uno.

- `TPT` (1,620)
- `TOWED` (498)
- `PB` (492)
- `MOR` (439)
- `MRH` (379)
- `TRG` (365)
- `TPT • Light` (353)
- `APC (W)` (326)
- `AUV` (320)
- `SP` (305)
- `MBT` (303)
- `IFV` (289)
- `ISR` (271)
- `ARV` (269)
- `PPV` (262)
- `MRL` (252)
- `PBF` (238)
- `FGA` (227)
- `ATK` (197)
- `RECCE` (194)
- `ASM` (194)
- `Point-defence` (178)
- `AAM • IR` (173)
- `APC (T)` (167)
- `MANPATS` (163)
- `APC` (150)
- `PCC` (144)
- `VLB` (130)
- `AShM` (127)
- `FTR` (122)
- `MW` (117)
- `AAM` (117)
- `SAM • Point-defence` (109)
- `Short-range` (104)
- `MSL • MANPATS` (102)
- `PCO` (95)
- `GUNS` (92)
- `ASW` (91)
- `AGS` (90)
- `AEV` (82)
