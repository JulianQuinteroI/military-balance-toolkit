-- Esquema de la base derivada de The Military Balance 2026 (IISS).
-- El contenido no se versiona: ver FUENTE.md.

PRAGMA foreign_keys = ON;

CREATE TABLE fuente (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);

CREATE TABLE paises (
    codigo  TEXT PRIMARY KEY,
    nombre  TEXT NOT NULL,
    region  TEXT NOT NULL,
    pagina  INTEGER NOT NULL
);

CREATE TABLE codigos_territorio (
    codigo TEXT PRIMARY KEY,
    nombre TEXT NOT NULL
);

CREATE TABLE abreviaturas (
    sigla      TEXT PRIMARY KEY,
    definicion TEXT NOT NULL
);

CREATE TABLE monedas (
    codigo_pais TEXT PRIMARY KEY REFERENCES paises(codigo),
    nombre      TEXT NOT NULL,
    codigo_iso  TEXT NOT NULL
);

CREATE TABLE economia (
    codigo_pais TEXT NOT NULL REFERENCES paises(codigo),
    anio        INTEGER NOT NULL,
    indicador   TEXT NOT NULL,
    unidad      TEXT NOT NULL,
    valor       REAL,
    estimado    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (codigo_pais, anio, indicador, unidad)
);

CREATE TABLE serie_presupuesto_real (
    codigo_pais TEXT NOT NULL REFERENCES paises(codigo),
    anio        INTEGER NOT NULL,
    valor       REAL NOT NULL,
    unidad      TEXT NOT NULL,
    PRIMARY KEY (codigo_pais, anio)
);

CREATE TABLE poblacion (
    codigo_pais TEXT PRIMARY KEY REFERENCES paises(codigo),
    total       INTEGER NOT NULL
);

CREATE TABLE demografia (
    codigo_pais TEXT NOT NULL REFERENCES paises(codigo),
    sexo        TEXT NOT NULL,
    rango       TEXT NOT NULL,
    porcentaje  REAL NOT NULL,
    PRIMARY KEY (codigo_pais, sexo, rango)
);

CREATE TABLE personal (
    codigo_pais    TEXT NOT NULL REFERENCES paises(codigo),
    categoria      TEXT NOT NULL,
    componente     TEXT NOT NULL,
    cantidad       INTEGER,
    estimado       INTEGER NOT NULL DEFAULT 0,
    minimo         INTEGER NOT NULL DEFAULT 0,
    maximo         INTEGER NOT NULL DEFAULT 0,
    indeterminado  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (codigo_pais, categoria, componente)
);

CREATE TABLE conscripcion (
    codigo_pais TEXT PRIMARY KEY REFERENCES paises(codigo),
    nota        TEXT NOT NULL
);

CREATE TABLE unidades (
    id           INTEGER PRIMARY KEY,
    codigo_pais  TEXT NOT NULL REFERENCES paises(codigo),
    padre_id     INTEGER REFERENCES unidades(id),
    profundidad  INTEGER NOT NULL,
    servicio     TEXT NOT NULL,
    rol          TEXT NOT NULL,
    cantidad     INTEGER,
    estimado     INTEGER NOT NULL DEFAULT 0,
    designacion  TEXT NOT NULL,
    tipo         TEXT NOT NULL,
    echelon      TEXT NOT NULL,
    texto_crudo  TEXT NOT NULL,
    pagina       INTEGER NOT NULL
);

CREATE TABLE equipo (
    id              INTEGER PRIMARY KEY,
    codigo_pais     TEXT NOT NULL REFERENCES paises(codigo),
    servicio        TEXT NOT NULL,
    dominio         TEXT NOT NULL,
    grupo           TEXT NOT NULL,
    categoria       TEXT NOT NULL,
    subcategoria    TEXT NOT NULL,
    sistema         TEXT NOT NULL,
    cantidad        INTEGER,
    estimado        INTEGER NOT NULL DEFAULT 0,
    minimo          INTEGER NOT NULL DEFAULT 0,
    indeterminado   INTEGER NOT NULL DEFAULT 0,
    total_categoria INTEGER,
    dudoso          INTEGER NOT NULL DEFAULT 0,
    texto_crudo     TEXT NOT NULL,
    pagina          INTEGER NOT NULL
);

-- Renglones de FORCES BY ROLE que no declaraban ningún escalón reconocible:
-- casi siempre prosa o remisiones, pero se conservan para poder auditarlos.
CREATE TABLE renglones_sin_leer (
    id           INTEGER PRIMARY KEY,
    codigo_pais  TEXT NOT NULL REFERENCES paises(codigo),
    seccion      TEXT NOT NULL,
    texto        TEXT NOT NULL,
    pagina       INTEGER NOT NULL
);

CREATE TABLE despliegues (
    id            INTEGER PRIMARY KEY,
    codigo_pais   TEXT NOT NULL REFERENCES paises(codigo),
    destino       TEXT NOT NULL,
    organizacion  TEXT NOT NULL,
    mision        TEXT NOT NULL,
    efectivos     INTEGER,
    detalle       TEXT NOT NULL
);

CREATE TABLE fuerzas_extranjeras (
    id           INTEGER PRIMARY KEY,
    codigo_pais  TEXT NOT NULL REFERENCES paises(codigo),
    origen       TEXT NOT NULL,
    efectivos    INTEGER,
    detalle      TEXT NOT NULL
);

CREATE TABLE comparacion_gasto (
    pais              TEXT NOT NULL,
    codigo_pais       TEXT REFERENCES paises(codigo),
    region            TEXT NOT NULL,
    anio              INTEGER NOT NULL,
    presupuesto_usd_m REAL,
    per_capita_usd    REAL,
    pct_pib           REAL,
    es_agregado       INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (pais, region, anio)
);

CREATE TABLE comparacion_personal (
    pais               TEXT NOT NULL,
    codigo_pais        TEXT REFERENCES paises(codigo),
    region             TEXT NOT NULL,
    anio               INTEGER NOT NULL,
    activos_miles      REAL,
    reservistas_miles  REAL,
    gendarmeria_miles  REAL,
    es_agregado        INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (pais, region, anio)
);

CREATE INDEX idx_economia_indicador ON economia (indicador, anio);
CREATE INDEX idx_equipo_pais        ON equipo (codigo_pais, dominio);
CREATE INDEX idx_equipo_sistema     ON equipo (sistema);
CREATE INDEX idx_unidades_pais      ON unidades (codigo_pais, servicio);
CREATE INDEX idx_unidades_padre     ON unidades (padre_id);
CREATE INDEX idx_despliegues_destino ON despliegues (destino);
CREATE INDEX idx_extranjeras_origen  ON fuerzas_extranjeras (origen);

-- Vista de uso frecuente: presupuesto y efectivos por país en el año de cierre.
-- El literal 2025 debe seguir a mb2026.parsers.comparacion.ANIO_PERSONAL: al
-- cargar una edición posterior hay que actualizar ambos.
CREATE VIEW v_resumen_pais AS
SELECT p.codigo,
       p.nombre,
       p.region,
       (SELECT valor FROM economia e
         WHERE e.codigo_pais = p.codigo AND e.indicador = 'presupuesto_defensa'
           AND e.unidad = 'USD' AND e.anio = 2025)                   AS presupuesto_usd_2025,
       (SELECT cantidad FROM personal pe
         WHERE pe.codigo_pais = p.codigo AND pe.categoria = 'activo'
           AND pe.componente = 'Total')                              AS activos,
       (SELECT cantidad FROM personal pe
         WHERE pe.codigo_pais = p.codigo AND pe.categoria = 'gendarmeria'
           AND pe.componente = 'Total')                              AS gendarmeria,
       (SELECT COUNT(*) FROM equipo eq WHERE eq.codigo_pais = p.codigo) AS lineas_equipo,
       (SELECT COUNT(*) FROM unidades u WHERE u.codigo_pais = p.codigo) AS unidades
  FROM paises p;
