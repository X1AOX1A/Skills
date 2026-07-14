---
name: paper-suggestions
description: |
  Curate a daily (or date-range) personalized paper digest from arXiv + HuggingFace.
  Fetches new & cross-listed papers, reads their abstracts, matches them against the
  user's preference topics (Agent / World Model / post-training / ...), and writes a
  grouped-by-topic Markdown digest with per-paper summaries. Self-contained: needs only
  python3 + the optional `hf` CLI, no other skill or external script.
  TRIGGER ONLY on an explicit request to run/generate/update the digest, e.g.
  "跑一下 paper-suggestions", "生成今天的论文日报", or when invoked by a scheduled/automated task.
  DO NOT auto-trigger. This skill is meant to run on a schedule (a daily cron/loop set up
  separately) OR on explicit demand — never run it proactively just because papers, arXiv,
  or research topics are mentioned in conversation. When unsure, ask before running.
  DO NOT TRIGGER when: user wants a raw keyword search, to read one specific paper's full
  text, to read a local paper folder, or to import papers into Zotero (those are separate
  skills) — and never as a side effect of an unrelated request.
---

# Paper Suggestions — 每日个性化论文推荐

Build a personalized daily paper digest. Data sources: **arXiv** (a category feed —
default `cs.CL`, including NEW submissions **and** cross-listed papers) plus **HuggingFace
daily papers** (trending signal + papers beyond the category). The skill fetches candidates
with abstracts, **you read the abstracts**, match them against the user's preference topics,
and emit a grouped Markdown digest.

The intelligent part — judging real relevance and writing summaries — is **your** job.
The bundled script only gathers raw candidates reliably.

## Execution policy — do not run proactively

This skill is designed for **scheduled, unattended daily runs** (a cron/`/loop` job set up
separately). Therefore:

- Run it **only** when the user explicitly asks, or when a scheduled task invokes it.
- Do **not** trigger it just because the conversation mentions papers/arXiv/a research area.
- It is fully non-interactive: it reads `preferences.yaml`, fetches, matches, writes the file.
  A scheduled run must complete end-to-end without asking questions.

## Prerequisites

- `python3` (stdlib only) — for `scripts/fetch_papers.py`. No third-party packages.
- `hf` CLI (optional but recommended) — HuggingFace papers signal. Degrades gracefully if absent.
- The **core** (fetch → match → write) is self-contained: no other skill or external script.
- *Optional only:* the step-6 Feishu push depends on the sibling **feishu-doc** skill (used
  solely when `feishu.enabled` is true). If you never enable it, this skill has no dependencies.

## Files

| File | Purpose |
| --- | --- |
| `preferences.yaml` | User's topics (name/keywords/desc) + output settings. **Read this first.** |
| `scripts/fetch_papers.py` | Fetch + merge + dedup arXiv & HF candidates → JSON |

---

## Workflow

### 1. Read preferences

Read `preferences.yaml` (in this skill's directory) to get the user's `topics` and `output`
settings. If the user named specific topics for *this run* only, use those instead (or in
addition) — the config is the default, an explicit request overrides it.

### 2. Fetch candidates

Run the fetch script with `--out-dir` so the output is auto-named by the **resolved batch date**
— `candidates-<batch-date>.json` — and never collides with past runs:

```bash
python3 scripts/fetch_papers.py --out-dir /tmp/paper-suggestions
```

The script prints the final file path on its own first line — read `candidates.json` from that
exact path (don't assume a fixed name). Pick the time scope from the user's request:

| User asks | Command |
| --- | --- |
| today / latest (default) | `python3 scripts/fetch_papers.py --out-dir /tmp/paper-suggestions` |
| a specific past date | `... --date 2026-07-13 --out-dir /tmp/paper-suggestions` |
| last N days | `... --days 3 --out-dir /tmp/paper-suggestions` |
| a different field | `... --category cs.LG ...` |
| also include updated papers | add `--include-replaced` |
| skip HuggingFace | add `--no-hf` |

(`--out-dir` names the file `candidates-<date>.json`; `--date` mode → that date, `--days` mode →
`<start>_<end>`, latest/RSS mode → the RSS batch date. Use `-o FILE` instead only if you need an
exact filename.)

**Note on "today":** arXiv's latest RSS batch is built overnight and usually reflects the
*previous business day* (weekends skipped). The script reports the actual batch date in
`date_token` (also in `range.build_date` / `range.date`) — always state that date in the output
and reuse it for the digest filename; don't assume it's the wall-clock date.

The JSON has:
- `date_token` — the resolved batch/range date; **use it for the digest filename** so the digest
  and its candidates file share the same date.
- `arxiv[]` — `{id, title, abstract, authors, categories, primary_category, announce_type
  (new|cross), url, hf_upvotes?}` — the main candidate pool, **with abstracts**.
- `hf_only[]` — `{id, title, upvotes, url, abstract?, categories?, primary_category?}` — HF
  trending papers NOT in the arXiv pool. The script back-fills their abstracts in one batched
  arXiv API call, so they usually **already have `abstract`** (unless `--no-hf-abstracts` or
  the API was unavailable — see `notes`).
- `counts`, `range`, `notes`.

### 3. Read abstracts & match to topics

Read `candidates.json`. For each paper in `arxiv[]` **and** `hf_only[]`, read its abstract and
decide which topic(s) it belongs to — use each topic's `desc` for the *semantic* bar,
`keywords` only as a hint. A paper may match multiple topics (list it under the best fit, or
note the overlap). List **all** matched papers (no cap), ordered within each topic by relevance
(break ties by `hf_upvotes`). Skip papers that clearly match no topic.

If some `hf_only[]` entries lack an abstract (see `notes` — e.g. the arXiv API was rate-limited),
judge them by title; if a title looks strongly relevant you may fetch its abstract yourself
(e.g. `hf papers info <id>`), but never block a scheduled run on it — degrade gracefully and
note the omission.

**其他推荐 (serendipity).** If `other.enabled` is true, after the defined topics, curate up to
`other.max` papers that match **no** defined topic but are still worth reading per `other.desc`
(novelty / standout HF traction / likely future interest / broad impact). This is a **curated
pick, not a dump** — quality over quantity; if nothing clears the bar, leave it out entirely.
Each such paper **must** state *why it's recommended despite being off-topic*. Never put a paper
here if it already fits a defined topic.

### 4. Write the digest

Write Markdown to `<output.dir>/<batch-date>.md` (expand `~`; create the dir). Group by topic,
one `##` section per topic (skip topics with zero matches, but note them at the end). Follow
`output.style`:

**`rich`** (default) — per paper:

```markdown
# 论文推荐 · <batch-date>

> 源: arXiv <category> (<N_new> new + <N_cross> cross) + HF Papers · 命中 <T> 领域 / <P> 篇

## 🤖 Agent
- **<title>** `<id>`
  - 摘要: <2-3 句中文,基于 abstract,说清做了什么>
  - 亮点: <一句话,为什么值得读 / 和该领域的关系>
  - 链接: https://arxiv.org/abs/<id> <if hf_upvotes: · HF ⬆️<n>>

## 🌍 Agent World Model
- ...

## ✨ 其他推荐
- **<title>** `<id>`
  - 摘要: <2-3 句>
  - 为什么推荐: <为何值得读,且为何破格——不属于已有领域却仍推荐的理由>
  - 链接: https://arxiv.org/abs/<id> <if hf_upvotes: · HF ⬆️<n>>
```

The `其他推荐` section comes **last** (after all defined topics) and is omitted entirely if
nothing qualifies. Use `other.title` / `other.emoji` from the config for its heading.

**`oneline`** — per paper: `- **<title>** \`<id>\` — <一句话概括>。 https://arxiv.org/abs/<id>`

End with a one-line footer noting anything skipped (topics with no hits, HF-only titles not
enriched, whether `replace` updates were excluded) — never silently drop coverage.

### 5. Report back

Print the digest path, then a compact in-chat summary (topic → count, and the single most
notable paper). Offer follow-ups: read a paper's full text, import to Zotero, or adjust
`preferences.yaml`. (When run by a scheduled task, just write the file and print the path/summary
— no interactive follow-ups.)

### 6. (Optional) Push to Feishu — via the `feishu-doc` skill

Only if `feishu.enabled` is true in `preferences.yaml`. This step is **not** internalized — it
delegates to the sibling **feishu-doc** skill. Run one line on the digest just written:

```bash
python ../feishu-doc/scripts/push_doc.py "<digest-path>" \
    --title "论文推荐 · <batch-date>" --folder-name "<feishu.folder_name>" <feishu.extra_args>
```

- Recipient, App ID/Secret, and other setup live in **feishu-doc**'s own `.env`; recipient/folder/
  permission flags are documented in its `SKILL.md` — refer there, don't duplicate here.
- Omit `--folder-name` if `feishu.folder_name` is empty. Append `feishu.extra_args` verbatim.
- On failure (missing creds, scope, network), **do not fail the whole run** — the digest file is
  the primary artifact; report that the Feishu push failed and continue.

---

## Recurring / automation

This skill is **built to be scheduled**. Each run is self-contained, non-interactive, and
idempotent (overwrites that date's file). The skill itself never creates schedules — a
system-level scheduler invokes it. Bundled assets live in `automation/`:

| File | Purpose |
| --- | --- |
| `automation/run_daily.sh` | Launcher — calls the CLI headless (`tclaude -p … --dangerously-skip-permissions`) and asks it to run this skill. Logs to `~/Local/CACHE/paper-suggestions/logs/`. |
| `automation/com.x1a.paper-suggestions.plist` | macOS **launchd** LaunchAgent — fires daily at 12:00 local. |

### Set up the daily 12:00 trigger (macOS, launchd — recommended)

Use launchd, **not** the in-session `/loop` or CronCreate: those only fire while a Claude REPL
is open, so they can't do true unattended daily runs. launchd fires even with no session.

```bash
SKILL_DIR="$HOME/.claude/skills/paper-suggestions"          # deployed symlink location
chmod +x "$SKILL_DIR/automation/run_daily.sh"
cp "$SKILL_DIR/automation/com.x1a.paper-suggestions.plist" ~/Library/LaunchAgents/
launchctl unload ~/Library/LaunchAgents/com.x1a.paper-suggestions.plist 2>/dev/null || true
launchctl load  ~/Library/LaunchAgents/com.x1a.paper-suggestions.plist
launchctl list | grep paper-suggestions                     # confirm it's registered
```

- **Change the time:** edit `StartCalendarInterval` (`Hour`/`Minute`) in the plist, then
  `launchctl unload` + `load` again. Omit `Minute` to run hourly; add multiple dicts for
  several times a day.
- **Run once now (test):** `launchctl start com.x1a.paper-suggestions`, then watch
  `~/Local/CACHE/paper-suggestions/logs/run-<today>.log`.
- **Uninstall:** `launchctl unload ~/Library/LaunchAgents/com.x1a.paper-suggestions.plist &&
  rm ~/Library/LaunchAgents/com.x1a.paper-suggestions.plist`.
- **Paths:** the plist hardcodes the repo path to `run_daily.sh` and the Label
  `com.x1a.paper-suggestions`; adjust both if the repo moves or you want a different label
  (Label must match the filename).

### Alternative: crontab

```cron
# every day at 12:00
0 12 * * * /bin/bash "$HOME/.claude/skills/paper-suggestions/automation/run_daily.sh"
```

### Auth caveat (important)

The launcher runs the CLI headless, so the CLI **must already be logged in** and its stored
credentials readable from a non-interactive launchd context (e.g. `tclaude login` done once;
`claude` OAuth token or `ANTHROPIC_API_KEY` present). If a scheduled run produces an auth error
in the log, that's the cause — re-login, or export the key inside `run_daily.sh`. Also verify
`feishu-doc/.env` is configured if `feishu.enabled` is true, or the push step will log a failure
(the digest still generates).

## When to Use This Skill

Run **only** on an explicit request or a scheduled invocation — never proactively. Explicit
requests look like:

- "跑一下 paper-suggestions"
- "生成今天的论文日报"

If the user merely mentions papers, arXiv, or a research topic without asking to generate the
digest, do **not** run this skill — use a search/read skill or just answer, or ask first.
