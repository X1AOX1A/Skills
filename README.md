# Skills

Centralized skill management for AI coding tools (Claude Code, Codex CLI, Cursor, tclaude).

## Skills

| Skill | Description |
|-------|-------------|
| **read-paper-online** | Online paper discovery via HuggingFace Papers API. Search by keyword, browse daily/trending papers, get paper details (authors, abstract, GitHub), and read full text by arXiv ID. |
| **read-paper-local** | Read and work with local paper folders exported by ZoFiles. Each folder contains structured files: `paper.md`, `paper.bib`, `kimi.md`, etc. |
| **zotero-connector** | Import arXiv papers into a running Zotero instance. Supports batch import, duplicate detection, and collection targeting. |
| **pdf-to-markdown** | Convert PDF files to clean Markdown using pymupdf4llm. |
| **nano-banana-pro** | Generate and edit images using Google's Nano Banana Pro (Gemini 3 Pro Image) API. Supports text-to-image and image-to-image editing. |
| **arxiv-figures** | Extract, browse, and download figures from arXiv papers via HTML rendering. Parses figure environments with captions and saves structured metadata. |
| **paper-suggestions** | Curate a daily/date-range personalized paper digest. Fetches new & cross-listed papers from arXiv + HuggingFace, reads abstracts, matches them against preference topics (config in `preferences.yaml`), and writes a grouped-by-topic Markdown digest with summaries. |
| **feishu-doc** | Turn a local Markdown file into a Feishu (Lark) Docx cloud document and DM the link via a self-built app bot. Uses the Drive import API + im/v1 message API. |
| **init-agent-project** | Initialize or align repository-level AI collaboration scaffolding: `AGENT.md`, a delegating `CLAUDE.md` stub, and `.agent/` memory/workspace directories. Supports new repos, existing repos, and convention migrations. |

## Structure

```
skills/                  # Skill definitions (source of truth)
  ├── read-paper-online/
  │   └── SKILL.md
  ├── read-paper-local/
  │   └── SKILL.md
  ├── zotero-connector/
  │   ├── SKILL.md
  │   └── scripts/
  ├── pdf-to-markdown/
  │   ├── SKILL.md
  │   └── scripts/
  ├── nano-banana-pro/
  │   ├── SKILL.md
  │   └── scripts/
  └── arxiv-figures/
      ├── SKILL.md
      └── scripts/
  └── paper-suggestions/
      ├── SKILL.md
      ├── preferences.yaml
      └── scripts/
  └── feishu-doc/
      ├── SKILL.md
      ├── .env.example
      └── scripts/
  └── init-agent-project/
      ├── SKILL.md
      └── references/
skills_table.csv         # Deployment matrix (which skill -> which tool)
.env                     # Directory path config
skills_sync.sh           # Symlink manager
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
TCLAUDE_SKILLS=~/.tclaude/skills
```

### `skills_table.csv`

Controls which skills are deployed to which tools. Set `1` to enable, `0` to disable:

```csv
skill, claude, codex, cursor, tclaude
read-paper-online, 1, 1, 1, 1
read-paper-local, 1, 1, 1, 1
zotero-connector, 1, 1, 1, 1
pdf-to-markdown, 1, 1, 1, 1
nano-banana-pro, 1, 1, 1, 1
arxiv-figures, 1, 1, 1, 1
paper-suggestions, 1, 1, 1, 1
feishu-doc, 1, 1, 1, 1
```

## Commands

| Command | Description |
|---------|-------------|
| `sync` | Create/remove symlinks to match `skills_table.csv`. Idempotent — safe to run repeatedly. Also cleans up orphan symlinks. |
| `status` | Print a table showing deployment state for each skill. |
| `help` | Show usage info. |

## Adding a New Skill

1. Create `skills/<skill-name>/SKILL.md`
2. Add a row to `skills_table.csv`
3. Run `./skills_sync.sh sync`
