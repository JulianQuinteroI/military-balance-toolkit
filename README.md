# holo-mb2026

Convierte **The Military Balance 2026** del IISS en una base de datos
consultable, un CLI que responde con cifras y su página, y calcos con
simbología NATO APP-6D.

```
corpus del IISS  ──►  SQLite  ──►  mb <orden>  ──►  respuesta + cita
                        │
                        └────────►  mb calco  ──►  ORBAT JSON  ──►  símbolos APP-6D
```

> [!IMPORTANT]
> Este repositorio contiene **solo código de extracción**. Ni el corpus fuente
> ni la base generada se versionan: el volumen del IISS tiene todos los
> derechos reservados. La licencia MIT cubre el código, no los datos. Lee
> [FUENTE.md](FUENTE.md) antes de usar cualquier salida.

## Qué resuelve

Un LLM al que se le pregunta cuántos carros de combate tiene un país responde
de memoria, y suele equivocarse de edición o inventar. Aquí las cifras salen de
una consulta, conservan las salvedades del editor (`ε` estimado, `†`
operatividad dudosa) y vienen con el número de página para citarlas.

## Requisitos

- Python 3.13 y [uv](https://docs.astral.sh/uv/).
- El corpus del IISS parseado a JSON, en local. La ruta se configura con
  `MB2026_SOURCE`; por defecto `~/Downloads/Military Balance Parser 2026`.

## Uso

```bash
uv sync
uv run mb2026                                  # genera data/mb2026.sqlite
uv run mb ficha Colombia                       # consulta la base
uv run python scripts/informe_extraccion.py    # informe de calidad
uv run pytest -q --cov=mb2026                  # 375 tests, 98% de cobertura
uv run ruff check src scripts                  # lint
uv run mypy                                    # tipos en modo estricto
```

Sin el corpus no se puede construir la base, pero el código, los tests y el
lint corren igual: la suite usa un corpus sintético y solo
`tests/test_validacion_corpus.py` se salta si el corpus real no está.

## Consulta

El comando `mb` responde preguntas contra la base sin cargar el volumen en
contexto. Los países se aceptan por código del IISS, nombre inglés o español.

| Orden | Para qué |
|---|---|
| `ficha PAÍS` | Expediente: economía, personal, inventario, despliegues |
| `correlacion PAÍS PAÍS… [--dominio aire\|tierra\|mar]` | Comparación de fuerzas |
| `sistema TEXTO` | Quién opera un material |
| `gasto PAÍS… [--desde AÑO]` | Serie real del presupuesto |
| `orbat PAÍS [--fuerza F] [--profundidad N]` | Orden de batalla como árbol |
| `inventario PAÍS [--dominio D]` | Inventario detallado |
| `ranking REGIÓN` | Países ordenados por gasto |
| `presencia DESTINO` | Despliegues hacia allí y fuerzas extranjeras dentro |
| `calco PAÍS [--afiliacion hostil]` | ORBAT en JSON para simbología NATO |
| `paises [--region R]`, `abreviatura SIGLA`, `sql "…"` | Apoyo y consulta libre |

Con `--json` la salida es serializable. La conexión se abre en modo solo
lectura, así que `sql` no puede modificar nada.

Sin uv, desde cualquier directorio (el paquete solo usa la biblioteca estándar):

```bash
PYTHONPATH=~/Projects/holo-mb2026/src python3 -m mb2026.consulta ficha Colombia
```

El skill de Claude Code [`military-balance`](skills/) envuelve todo esto.

El corpus se busca en `~/Downloads/Military Balance Parser 2026`. Para moverlo:

```bash
export MB2026_SOURCE="/ruta/al/corpus"
```

## Qué se extrae

| Tabla | Filas | Contenido |
|---|---:|---|
| `paises` | 174 | Código, nombre, capítulo regional, página impresa |
| `economia` | 2.366 | PIB, crecimiento, presupuesto y gasto de defensa, ayuda militar de EE. UU., por año y unidad |
| `serie_presupuesto_real` | 2.744 | Serie 2008–2025 del presupuesto en términos reales |
| `personal` | 1.028 | Activos, reserva y gendarmería, con desglose por fuerza |
| `unidades` | 9.474 | Orden de batalla como árbol (`padre_id`), con rol, escalón y designación |
| `equipo` | 14.816 | Inventario por fuerza, dominio, categoría y sistema |
| `fuerzas_extranjeras` | 687 | Presencia de terceros Estados en cada país |
| `comparacion_gasto` | 567 | Tabla 9: presupuesto, per cápita y % del PIB, 2023–25 |
| `comparacion_personal` | 189 | Tabla 9: activos, reservistas y gendarmería |
| `abreviaturas` | 309 | Tabla 8: la clave para leer la notación del volumen |
| `poblacion` / `demografia` | 152 / 1.476 | Población total y pirámide por sexo y rango de edad |
| `codigos_territorio` | 184 | Tabla 10: códigos del IISS, incluidos territorios sin ficha |
| `renglones_sin_leer` | 308 | Renglones de `FORCES BY ROLE` sin escalón reconocible, conservados para auditoría |

Más la vista `v_resumen_pais` (presupuesto, efectivos y volumen de datos por país).

## Validación

El volumen compone dos veces el mismo dato por caminos independientes: la ficha
de cada país y la Tabla 9 comparativa. La suite contrasta ambos para los 28
países del capítulo 7 (América Latina y el Caribe):

- **Efectivos activos**: coinciden en los 26 países que declaran fuerzas
  armadas, dentro del redondeo a miles de la Tabla 9.
- **Presupuesto de defensa 2025 en USD**: coincide dentro del redondeo a tres
  cifras significativas. Colombia: 8.270 M (ficha) contra 8.268 M (Tabla 9).
- **Integridad referencial**: ninguna subunidad huérfana ni cruzada entre países.

Contrastes puntuales contra el impreso (Colombia, pp. 417-419): efectivos por
fuerza, presupuesto en COP y USD, moneda, inventario conocido, jerarquía de la
1.ª división mecanizada, presencia estadounidense y despliegues propios.

## Notación del IISS que se preserva

Las marcas de juicio del editor se guardan como banderas, no se descartan:
`estimado` (ε), `dudoso` (†), `minimo` (+), `indeterminado` (*some*), `maximo`
(*up to*). Cada línea de inventario y cada unidad conservan además su
`texto_crudo` y su `pagina`, para poder citar y para poder reinterpretar lo que
ninguna regla cubra.

## Límites conocidos

- **Corte de los datos: noviembre de 2025.** Línea base, no inteligencia actual.
- **13 países sin datos macro** (AFG, CUB, DPRK, ERI, KGZ, LAO, LBY, PT, SYR,
  UZB, VEN, YEM): el volumen no los publica. Denmark es distinto — su tabla
  económica perdió la cabecera en el parse de origen, y el informe lo señala;
  su presupuesto sigue disponible vía `comparacion_gasto`.
- **3 países sin unidades** (ISL, LBY, YEM) y **1 sin inventario**: sin sección
  correspondiente en el volumen.
- **Artillería con calibres anidados**: `TOWED 120: 105mm 107: 22 LG1 MkIII` se
  lee a dos niveles (`categoria` / `subcategoria`); un tercer nivel de calibre
  queda dentro del nombre del sistema. El `texto_crudo` permite refinarlo.
- **Tres renglones de inventario (de 14.816) no producen filas** porque el
  corpus dejó los marcadores de negrita descolocados (p. ej. Venezuela p. 449:
  `**AMPHIBIOUS • **LANDING CRAFT** • 1 **LCU**…`). Se prefiere no emitir nada
  antes que emitir una categoría inventada.
- **14 unidades (de 9.476) quedan huérfanas de su formación superior** porque el
  renglón se partió en un salto de página y llegó con los paréntesis
  descompensados (Colombia, 8.ª división de infantería, es el caso típico). La
  unidad existe y su `texto_crudo` lo muestra; lo que se pierde es el enlace
  `padre_id`.
- **El árbol de unidades llega a profundidad 3.** Las glosas no jerárquicas
  entre paréntesis se conservan en `designacion`, concatenadas si hay varias.
- **308 renglones de `FORCES BY ROLE` no se interpretan como unidades** (prosa,
  remisiones del tipo «(see USSOCOM)», notas de reorganización). No se descartan
  en silencio: quedan en `renglones_sin_leer` con su página.

## Estructura

```
src/mb2026/
├── config.py          rutas y constantes de la edición
├── corpus.py          corpus → flujo lineal de items con página
├── texto.py           notación numérica del IISS (ε, †, +, some, up to)
├── segmentacion.py    flujo → 174 fichas de país
├── schema.sql         esquema SQLite
├── db.py              creación y carga
├── etl.py             orquestador
├── cli.py             `mb2026`
└── parsers/
    ├── localizar.py       anclas de las tablas de referencia
    ├── estructura.py      vocabulario estructural compartido
    ├── secciones.py       acotado de secciones dentro de una ficha
    ├── indice_paises.py   Tablas 10 y 11
    ├── abreviaturas.py    Tabla 8
    ├── comparacion.py     Tabla 9
    ├── economia.py        economía, población y demografía
    ├── personal.py        efectivos
    ├── unidades.py        orden de batalla
    ├── equipo.py          inventario
    └── despliegues.py     despliegues y fuerzas extranjeras
```

## Calcos APP-6D (fase 3)

`calco` traduce el orden de batalla del IISS a un ORBAT JSON que el skill
`nato-symbology` convierte en símbolos APP-6D:

```bash
mb calco Venezuela --fuerza Army --afiliacion hostil --salida orbat.json
node ~/.claude/skills/nato-symbology/scripts/generate.mjs \
    --orbat orbat.json --out ./simbolos --demo
```

El mapeo es composicional, como el vocabulario del volumen: se lee el token de
función (`mech inf bn` → infantería mecanizada, `armd recce bn` →
reconocimiento blindado, `cbt engr bde` → ingenieros) y se recurre al rol del
IISS cuando el tipo describe la plataforma en vez de la función. Los códigos de
entidad que no tienen alias en español salen de `lookup.mjs` del propio skill;
ninguno se inventa.

| Ámbito | Unidades | Cobertura |
|---|---:|---:|
| Fuerzas terrestres | 4.553 | 98,0% |
| Fuerzas aéreas y aviación | 3.175 | 77,3% |
| Global | 9.476 | 88,7% |

Lo que no se reconoce **no se dibuja**: se reporta con su motivo. Un símbolo
equivocado en un calco es peor que un hueco. La brecha aérea viene del original
(el IISS nombra muchos escuadrones por su aeronave, y `TRAINING` no tiene
entidad en el conjunto terrestre de 2525D); `airborne`, `mountain` y `jungle`
son modificadores de sector que el generador no expone, así que esas unidades
reciben la entidad correcta sin el modificador.

El ORBAT sale sin coordenadas —el volumen no las publica—, de modo que el
GeoJSON queda vacío hasta que se añadan `lat`/`lon`.

## Saneo de dimensiones (fase 2)

Construir la capa de consulta obligó a corregir las dimensiones de `equipo`,
que salían contaminadas y habrían hecho mentir a cualquier consulta:

- `servicio` recogía sub-clasificaciones de maniobra: «Light» tenía 1.952 filas
  y «Other» 2.151, mientras «Army» apenas 514. Ahora Army tiene 4.603 y los
  sub-roles han desaparecido de esa columna.
- `dominio` arrastraba el total del rótulo (`ARTILLERY 9,580`), encadenaba
  sub-niveles (`AIR DEFENCE • SAM`) y repetía las erratas del original
  (`UNIHABITED AERIAL VEHICLES`). De ~250 valores se ha pasado a 23 dominios
  canónicos, con un nivel intermedio propio en la columna `grupo`.
- Los rótulos maquetados como subíndice (`<sub>HELICOPTERS</sub>`) se perdían
  enteros al limpiar el markdown, porque la regla de notas al pie borraba
  contenido además de etiquetas.
- `economia` perdía las etiquetas con espacio perdido o errata (`Real GDPgrowth`,
  `Def bgt`); ahora la búsqueda de indicador es insensible a espacios.

## Estructura añadida en la fase 3

```
src/mb2026/simbologia/
├── diccionario.py   vocabulario IISS → alias y entidades del skill
└── traductor.py     filas de `unidades` → ORBAT JSON, con informe de cobertura
```
