# Skill `military-balance`

Envoltorio de Claude Code sobre la capa de consulta de este repositorio.

## Instalación

```bash
cp -R skills/military-balance ~/.claude/skills/
```

Luego, en el entorno donde lo uses:

```bash
export MB2026_HOME="/ruta/donde/clonaste/holo-mb2026"
export PYTHONPATH="$MB2026_HOME/src"
export MB2026_DB="$MB2026_HOME/data/mb2026.sqlite"   # opcional
```

## Dependencias

- La base `data/mb2026.sqlite`, que se genera con `uv run mb2026` y requiere el
  corpus del IISS en local. Ver [FUENTE.md](../FUENTE.md).
- Para la orden `calco`, el skill [`nato-symbology`](https://github.com/) debe
  estar instalado en `~/.claude/skills/nato-symbology`. No forma parte de este
  repositorio.

## Contenido

| Archivo | Qué es |
|---|---|
| `SKILL.md` | Instrucciones y órdenes disponibles |
| `references/notacion.md` | Marcas del editor, jerarquía, cobertura de `calco`, límites |
| `references/esquema.md` | Tablas y vocabularios de la base, para escribir `sql` |
