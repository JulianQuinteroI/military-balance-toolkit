---
name: military-balance
description: >-
  Consulta datos de fuerzas armadas de 174 países desde The Military Balance
  2026 (IISS): efectivos, presupuestos de defensa, inventario de equipo, orden
  de batalla, despliegues en el exterior y presencia de fuerzas extranjeras.
  Úsalo cuando el usuario pregunte por el poder militar de un país, pida una
  correlación de fuerzas, quiera saber quién opera un sistema de armas, necesite
  cifras de gasto de defensa o un ORBAT, o mencione Military Balance, IISS,
  capacidades militares comparadas, orden de batalla o balance militar.
allowed-tools: Bash(python3 *), Bash(uv run *), Read
---

# The Military Balance 2026 (IISS)

Responde con cifras verificables y su página, sin cargar el volumen en contexto.

```
pregunta en español  ──►  mb <orden> <argumentos>  ──►  tabla + cita de página
                          (consulta SQLite local)
```

## Antes de responder

1. **Ejecuta la consulta. No contestes de memoria.** Las cifras militares que
   un modelo recuerda suelen ser de otra edición o directamente inventadas.
2. **Cita siempre** lo que devuelve la línea `Fuente:`, con la página.
3. **Conserva las marcas del editor** (`ε`, `†`, `+`, `some`). Están explicadas
   en `references/notacion.md`; omitirlas convierte estimaciones en datos firmes.
4. **Declara el corte**: los datos son de noviembre de 2025.

## Invocación

```bash
python3 -m mb2026.consulta <orden> [argumentos]
```

Requiere `PYTHONPATH` apuntando al paquete (solo usa la biblioteca estándar):

```bash
export MB2026_HOME="$HOME/Projects/military-balance-toolkit"  # el repo clonado
export PYTHONPATH="$MB2026_HOME/src"
python3 -m mb2026.consulta ficha Colombia
```

Alternativa con uv, desde cualquier directorio:

```bash
uv run --project "$MB2026_HOME" mb ficha Colombia
```

Si la base no existe, constrúyela una vez:
`cd "$MB2026_HOME" && uv run mb2026`. Necesita el corpus del IISS en local;
la ruta se configura con `MB2026_SOURCE`.

## Órdenes

| Orden | Para qué | Ejemplo |
|---|---|---|
| `ficha PAÍS` | Expediente completo: economía, personal, inventario por dominio, despliegues, fuerzas extranjeras | `ficha Colombia` |
| `correlacion PAÍS PAÍS…` | Comparar efectivos, presupuesto e inventario | `correlacion Colombia Venezuela --dominio aire` |
| `sistema TEXTO` | Quién opera un material y cuánto | `sistema "Type-209"` |
| `gasto PAÍS…` | Serie real del presupuesto, 2008–2025 | `gasto Colombia Peru --desde 2015` |
| `orbat PAÍS` | Orden de batalla como árbol | `orbat Colombia --fuerza Army --profundidad 1` |
| `inventario PAÍS` | Inventario detallado | `inventario Venezuela --dominio aire` |
| `ranking REGIÓN` | Países ordenados por gasto | `ranking latam` |
| `presencia DESTINO` | Quién despliega hacia allí y qué terceros hay dentro | `presencia HAITI` |
| `paises` | Fichas disponibles | `paises --region latam` |
| `abreviatura SIGLA` | Desarrollo de una sigla del volumen | `abreviatura SSK` |
| `calco PAÍS` | ORBAT en JSON para generar simbología NATO | `calco Venezuela --afiliacion hostil --salida orbat.json` |
| `sql "CONSULTA"` | Consulta libre de solo lectura | ver abajo |

Opciones generales: `--json` para salida serializable, `--base RUTA` para otra
base. `--dominio` admite `aire`, `tierra`, `mar`, `defensa aerea`, `espacio`,
`blindados`, `artilleria`, `submarinos`, `drones`, y se puede repetir.

Los países se aceptan por código del IISS, nombre inglés o nombre español.
Cuidado: el IISS usa `BRZ` para Brasil, `PRC` para China, `UK` para el Reino
Unido. Si te equivocas de nombre, el CLI sugiere alternativas.

## Calcos con simbología NATO

`calco` traduce el orden de batalla a un ORBAT JSON que el skill
**`nato-symbology`** convierte en símbolos APP-6D. Es el camino para producir
calcos de una fuerza adversaria o propia sin dibujarlos a mano:

```bash
python3 -m mb2026.consulta calco Venezuela --fuerza Army \
    --afiliacion hostil --salida orbat-ven.json
node "$HOME/.claude/skills/nato-symbology/scripts/generate.mjs" \
    --orbat orbat-ven.json --out ./simbolos --demo
```

`--afiliacion` acepta `amigo` (por defecto), `hostil`, `neutral` y
`desconocido`; `--fuerza` y `--profundidad` acotan igual que en `orbat`.

La orden informa de la **cobertura**: qué porcentaje de las unidades obtuvo
símbolo y qué tipos se quedaron sin él. **Comunica siempre esa cifra**: lo que
no se pudo traducir no se dibuja, en vez de dibujarse mal. En el Ejército
colombiano la cobertura es del 98,6%; en fuerzas aéreas baja, porque el IISS
describe muchos escuadrones por su aeronave y no por su función.

El ORBAT sale sin coordenadas —el volumen no las publica—, así que el GeoJSON
queda vacío hasta que alguien añada `lat`/`lon` a las unidades que interesen.

## Cuándo usar `sql`

Las órdenes cubren lo habitual. Para cruces que no cubren —«qué países de
Suramérica operan fragatas con misil antibuque», «qué sistemas rusos siguen en
inventarios de la OTAN»— escribe SQL directo. Lee primero
`references/esquema.md`, que trae las tablas, columnas y vocabularios reales.

```bash
python3 -m mb2026.consulta sql "
  SELECT p.nombre, e.sistema, e.cantidad
    FROM equipo e JOIN paises p ON p.codigo = e.codigo_pais
   WHERE p.region = 'Latin America and the Caribbean'
     AND e.dominio = 'SUBMARINES'
   ORDER BY e.cantidad DESC"
```

La conexión se abre en modo solo lectura: una escritura falla en el motor, no
hace falta que lo vigiles.

## Cómo redactar la respuesta

- Da la cifra y su salvedad en la misma frase, no en una nota al pie.
- Si comparas países, di explícitamente qué **no** compara la tabla: el volumen
  cuenta plataformas, no disponibilidad, entrenamiento ni sostenimiento.
- Cuando el dato falte, dilo y explica por qué (ver los límites en
  `references/notacion.md`), en vez de rellenarlo con otra fuente de memoria.
- Para preguntas sobre grupos armados organizados, aclara que este volumen solo
  cubre fuerzas estatales.

## Referencias

- `references/notacion.md` — marcas del editor, jerarquía del inventario,
  escalones, alias aceptados y límites que hay que declarar.
- `references/esquema.md` — tablas, columnas y vocabularios, para escribir `sql`.
