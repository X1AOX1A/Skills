---
name: search-paper
description: |
  Search for academic papers online using HuggingFace Papers API and optionally read their full text.
  TRIGGER when: user asks to search for papers online, find recent papers, look up papers on a topic,
  search arXiv/HuggingFace for papers, check what's new in a research area, browse HuggingFace daily papers,
  get detailed info about a specific paper (authors, abstract, keywords, github), or quickly read a paper's full text by arXiv ID.
  DO NOT TRIGGER when: user wants to read a local paper folder (use read-paper skill), import papers into Zotero
  (use zotero-connector skill), convert a local PDF (use pdf-to-markdown skill), or work with already-downloaded papers.
---

# Online Paper Search

Search for academic papers via the HuggingFace Papers hub using the `hf` CLI. This skill covers **online discovery** — finding and previewing papers from the web.

## Prerequisites

- `huggingface_hub` CLI installed (`pip install -U huggingface_hub[cli]`)
- Internet connection

## 1. Searching Papers

```bash
hf papers search "<query>" [--limit N] [--format table|json] [-q]
```

**Options:**

| Flag | Default | Description |
| --- | --- | --- |
| `--limit N` | 20 | Max number of results |
| `--format` | table | Output format (`table` for display, `json` for parsing) |
| `-q, --quiet` | — | Print only paper IDs (one per line) |

**Examples:**

```bash
# Basic search
hf papers search "chain of thought reasoning"

# Search with limited results for quick overview
hf papers search "diffusion models" --limit 5
```

### Presenting Search Results

**Always use `--format table` (the default).** Table output is compact (ID, title, upvotes, date — one line per paper) and token-efficient. JSON output contains bloated author/avatar/org metadata that wastes context.

If the user needs the abstract of a specific paper, use `hf papers read <ID>` to fetch it — don't switch to JSON format for summaries.

After showing results, offer next steps: "Want me to read the full text of any of these?" or "Want me to import any into Zotero?"

---

## 2. Browsing Daily Papers

```bash
hf papers list [--date YYYY-MM-DD] [--sort publishedAt|trending] [--limit N]
```

**Only use when the user explicitly wants to browse HuggingFace daily papers** (e.g. "看看 hf papers", "今天有什么新论文", "show me today's papers"). This is a **browsing** command, not a search — do NOT use it as a search substitute.

**Options:**

| Flag | Default | Description |
| --- | --- | --- |
| `--date` | today | Specific date (`YYYY-MM-DD` or `today`) |
| `--week` | — | ISO week, e.g. `2025-W12` |
| `--month` | — | Month, e.g. `2025-03` |
| `--sort` | — | `publishedAt` or `trending` |
| `--submitter` | — | Filter by HF username |
| `--limit` | 50 | Max results |

**Examples:**

```bash
# Today's papers (default)
hf papers list --limit 10

# Trending papers
hf papers list --sort trending --limit 10

# Papers from a specific date
hf papers list --date 2025-03-20 --limit 10
```

---

## 3. Getting Paper Details

```bash
hf papers info <PAPER_ID>
```

Returns rich JSON metadata for a **single paper**: title, full author list, complete abstract, AI-generated summary, AI keywords, publication date, upvotes, github repo/stars, project page, and discussion info.

**Only use when detailed metadata is needed** — e.g. the user asks about a paper's authors, keywords, github repo, or wants the full abstract without reading the entire paper. Do NOT use as a routine step; search + read already cover most needs.

**Example:**

```bash
hf papers info 2509.22624
```

**Key fields in the output:**

| Field | What it provides |
| --- | --- |
| `title` | Full title (not truncated) |
| `summary` | Complete abstract |
| `ai_summary` | One-sentence AI summary |
| `ai_keywords` | Topic keywords list |
| `authors[].name` | Author names (ignore avatar/user fields) |
| `github_repo` | GitHub URL (if available) |
| `github_stars` | Star count (if available) |
| `project_page` | Project homepage (if available) |
| `upvotes` | Community upvote count |

---

## 4. Reading Paper Full Text

```bash
hf papers read <PAPER_ID>
```

Fetches the paper's full text as markdown from its arXiv HTML rendering. Use this when the user wants to:

- Quickly preview a paper found via search without downloading
- Read specific sections of an online paper
- Get the full content for summarization or analysis

**Example:**

```bash
hf papers read 2301.07041
```

### Reading Strategy for Full Papers

Since `hf papers read` outputs can be very long, follow this strategy:

1. **Pipe to a temp file** for large papers so you can read selectively:
   ```bash
   hf papers read <ID> > /tmp/papers/<ID>.md
   ```
2. **Read the beginning** (title, abstract, introduction) first using the Read tool with `limit`
3. **Jump to specific sections** based on user interest using the Read tool with `offset`
4. **For quick overview**: read just the first 100-200 lines (abstract + intro), then conclusion (last ~100 lines)

---

## Workflow Examples

### "Search for papers on topic X"

```bash
hf papers search "topic X" --limit 50
```

Show results in a clean format. Offer to read any paper or import into Zotero.

### "看看 hf papers" / "今天有什么新论文"

```bash
hf papers list
```

Browse mode — just show the table, let the user pick what interests them.

### "这篇论文的作者是谁？有没有代码？"

```bash
hf papers info <ID>
```

Extract authors, github_repo, project_page from the JSON output.

### "Search for X and read the most relevant one"

1. Search: `hf papers search "X" --limit <number>`
2. Pick the most relevant (by title match + upvotes)
3. Read: `hf papers read <best_id> > /tmp/paper_<best_id>.md`
4. Summarize key findings

## When to Use This Skill

Use when the user says things like:

- "Search for papers on reinforcement learning"
- "Find recent papers about LLM agents"
- "Look up papers on vision transformers"
- "Search arXiv for chain-of-thought"
- "Find papers about reward models, limit to 5"
- "Read paper 2301.07041 online"
- "看看 hf papers" / "今天有什么新论文"
- "这篇论文的作者是谁" / "有没有代码仓库"
- "搜索关于多模态的论文"
- "帮我找一下最近的强化学习论文"
- "在线看一下这篇论文"
