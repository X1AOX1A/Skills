# Skills

Centralized skill management for AI coding tools (Claude Code, Codex CLI, Cursor).

## Structure

```
skills/              # Skill definitions (source of truth)
  ├── read-paper/
  │   └── SKILL.md
  └── zotero-connector/
      ├── SKILL.md
      └── scripts/
skills_table.csv     # Deployment matrix (which skill → which tool)
.env                 # Directory path config
skills_sync.sh    # Symlink manager
```

## Quick Start

```bash
# Show current deployment status
./skills_sync.sh status

# Sync all symlinks according to skills_table.csv
./skills_sync.sh sync
```

## Configuration

### `.env`

Defines source and target directories:

```
SKILLS=/path/to/this/repo/skills
CLAUDE_SKILLS=~/.claude/skills
CODEX_SKILLS=~/.codex/skills
CURSOR_SKILLS=~/.cursor/skills
```

### `skills_table.csv`

Controls which skills are deployed to which tools. Set `1` to enable, `0` to disable:

```csv
skill, claude, codex, cursor
read-paper, 1, 1, 1
zotero-connector, 1, 1, 1
```

## Commands

| Command | Description |
|---------|-------------|
| `sync` | Create/remove symlinks to match `skills_table.csv`. Idempotent — safe to run repeatedly. Also cleans up orphan symlinks. |
| `status` | Print a table showing deployment state for each skill (`✓ linked`, `✗ missing`, `⚠ wrong`, `⚠ extra`). |
| `help` | Show usage info. |

## Adding a New Skill

1. Create `skills/<skill-name>/SKILL.md`
2. Add a row to `skills_table.csv`
3. Run `./skills_sync.sh sync`
