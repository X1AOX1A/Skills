# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

Centralized skill management for AI coding tools. Skills are defined once in `skills/` and deployed via symlinks to `~/.claude/skills/`, `~/.codex/skills/`, and `~/.cursor/skills/`.

## Common Commands

```bash
# Deploy all skills (create/remove symlinks based on skills_table.csv)
./skills_sync.sh sync

# Check which skills are linked where
./skills_sync.sh status
```

Always run `./skills_sync.sh sync` after renaming, adding, or removing a skill directory.

## Architecture

### Skill anatomy

Each skill lives in `skills/<skill-name>/` and must contain a `SKILL.md` with YAML frontmatter (`name` and `description`). Some skills also have a `scripts/` subdirectory with helper scripts (Python, Bash).

The `description` field in SKILL.md frontmatter is what AI tools see to decide when to trigger the skill — it must include TRIGGER/DO NOT TRIGGER guidance.

### Deployment flow

1. **`skills_table.csv`** — the deployment matrix. Each row maps a skill name to on/off flags for claude, codex, cursor.
2. **`skills_sync.sh sync`** — reads `.env` for paths, reads `skills_table.csv`, creates/removes symlinks, and cleans up orphans.
3. **Symlinks** in `~/.claude/skills/`, etc. point back to `skills/<skill-name>/` in this repo.

The skill directory name must match the name in `skills_table.csv` exactly.

### Cross-references between skills

Some skills reference others in their SKILL.md (e.g., "use read-paper-local skill" in read-paper-online's DO NOT TRIGGER section). When renaming a skill, grep the entire repo for the old name to catch all cross-references.

## Key Files

| File | Purpose |
|------|---------|
| `skills_table.csv` | Deployment matrix — which skill goes to which tool |
| `.env` | Source/target directory paths for symlink manager |
| `skills_sync.sh` | Symlink creation/removal/orphan cleanup |
| `README.md` | Documents skills table, directory structure, and CSV example (keep in sync with `skills_table.csv`) |

## Adding a New Skill

1. Create `skills/<skill-name>/SKILL.md` with frontmatter
2. Add a row to `skills_table.csv`
3. Update `README.md` (skills table, directory structure, CSV example)
4. Run `./skills_sync.sh sync`

## Renaming a Skill

1. Rename the directory under `skills/`
2. Update `name:` in the skill's SKILL.md frontmatter
3. Update `skills_table.csv`
4. Update `README.md` (three places: skills table, directory structure, CSV example)
5. Grep for the old name across all `SKILL.md` files to fix cross-references
6. Run `./skills_sync.sh sync` (creates new links, removes orphan old links)
