# Notación del IISS y cómo leerla

## Marcas de juicio del editor

El volumen no publica solo cifras: publica cifras con salvedades. La base las
conserva como banderas y el CLI las imprime en la columna `Marcas`. **Nunca las
omitas al citar**: convertir una estimación en dato firme es el error más común
al usar esta fuente.

| Marca | Columna | Significado |
|---|---|---|
| `ε` | `estimado` | Cifra estimada por el IISS, no declarada |
| `†` | `dudoso` | El IISS considera dudosa la operatividad del equipo |
| `+` | `minimo` | El total no es menor que la cifra dada |
| `some` | `indeterminado` | Inventario preciso no disponible al cierre |
| `*` | — | Aeronave contabilizada como apta para combate |
| `(-)` | — | Unidad bajo efectivos o con elementos destacados |

Ejemplo de lectura correcta: «Venezuela declara 21 Su-30MKV, de los cuales el
IISS marca 12 con operatividad dudosa (IISS, *The Military Balance 2026*, p. 448)».

## Jerarquía del inventario

Cada línea de `equipo` está situada en cuatro niveles más el renglón original:

```
servicio      Army · Navy · Air Force · Coast Guard · Naval Aviation…
  dominio     AIRCRAFT · ARMOURED FIGHTING VEHICLES · SUBMARINES…
    grupo     nivel intermedio cuando lo hay (MSL, CORVETTES, SAM…)
      categoria     código de tipo del IISS (MBT, IFV, FGA, SSK, PB…)
        subcategoria   calibre o variante del mismo renglón (105mm, Medium…)
          sistema      el material concreto
```

`texto_crudo` guarda el renglón tal como lo imprime el volumen y `pagina`
permite citarlo. Cuando una consulta dé un resultado raro, mira `texto_crudo`
antes de concluir nada.

## Escalones del orden de batalla

`unidades.echelon` usa los códigos de la Tabla 8: `army`, `corps`, `div`, `bde`,
`regt`, `bn`, `coy`, `bty`, `pl`, `sqn`, `flt`, `gp`, `comd`, `det`, `wg`, `unit`.
El árbol se recorre por `padre_id`; `profundidad` 0 son las formaciones de
primer nivel.

Cualquier sigla que no reconozcas está en la Tabla 8:
`abreviatura <sigla>` la desarrolla. **No adivines siglas.**

Los códigos navales se imprimen agrupados por familia (`FS/G/H/M` cubre FS, FSG,
FSGH, FSGM, FSGHM…). Si buscas uno concreto y no aparece literal, la orden
recurre sola a su familia: `abreviatura FSGHM` devuelve `FS/G/H/M`, corbeta con
misil superficie-superficie.

## Alias aceptados al preguntar

- **Países**: código del IISS (`COL`), nombre inglés (`Colombia`) o español
  (`Brasil`, `Estados Unidos`, `Corea del Sur`). Ojo con los códigos propios del
  IISS: Brasil es `BRZ` (no BRA), China `PRC`, Taiwán `ROC`, Reino Unido `UK`.
- **Dominios**: `aire`, `tierra`, `mar`, `defensa aerea`, `espacio`, `blindados`,
  `artilleria`, `submarinos`, `drones`, `aeronaves`, `helicopteros`, o el nombre
  canónico en inglés.
- **Regiones**: `latam`, `europa`, `asia`, `mena`, `africa`, `norteamerica`,
  `eurasia`.

## Cobertura de `calco` (traducción a simbología NATO)

El mapeo va por tokens de función (`mech inf bn` → infantería mecanizada,
`armd recce bn` → reconocimiento blindado) y recurre al rol del IISS cuando el
tipo describe la plataforma en vez de la función. Lo que no se reconoce **no se
dibuja**: aparece en el informe con su motivo.

| Ámbito | Unidades | Cobertura |
|---|---:|---:|
| Fuerzas terrestres (Army, Marines, National Guard) | 4.553 | 98,0% |
| Fuerzas aéreas y aviación | 3.175 | 77,3% |
| Global | 9.476 | 88,7% |

La brecha aérea es del original: el IISS nombra muchos escuadrones por su
aeronave («1 sqn with C-130 Hercules») y su rol `TRAINING` no tiene entidad en
el conjunto de símbolos terrestre de 2525D.

Lo que **no** se traduce por decisión, no por descuido:
- `airborne`, `mountain` y `jungle` son modificadores de sector en 2525D, y el
  generador no expone tablas de modificadores. Esas unidades reciben la entidad
  correcta (infantería) sin el modificador.
- `counter-narcotics`, `paramilitary` y similares no tienen entidad OTAN.

## Límites que hay que declarar al responder

- **Corte de los datos: noviembre de 2025.** Es línea base, no inteligencia
  actual. Si la pregunta es sobre algo posterior, dilo.
- **13 países sin datos macro**: AFG, CUB, DPRK, ERI, KGZ, LAO, LBY, PT, SYR,
  UZB, VEN, YEM. Para ellos, `comparacion_gasto` puede tener la cifra de la
  Tabla 9 aunque `economia` esté vacía.
- **El volumen no modela grupos armados organizados.** No hay ELN, disidencias
  ni Clan del Golfo: solo aparecen mencionados en prosa, que no está en la base.
- **Dinamarca** perdió la cabecera de su tabla económica en el parse de origen;
  su presupuesto está en `comparacion_gasto`.
- **Colombia, p. 419**: el corpus perdió los encabezados «Navy» y «SUBMARINES»,
  así que sus dos submarinos figuran con `servicio = Army`. El dominio sí es
  correcto.
- **Tres renglones de inventario** quedan fuera por marcadores rotos en el
  original (Venezuela p. 449 entre ellos). El parser prefiere no emitir nada a
  inventar una categoría.
- **14 unidades quedan sin enlace a su formación superior** por saltos de
  página que partieron el renglón. Si un ORBAT muestra una brigada suelta al
  final de una división, es esto.
- **`renglones_sin_leer`** guarda los renglones de `FORCES BY ROLE` que el
  parser no interpretó como unidades. Si un ORBAT parece incompleto, mira ahí.
