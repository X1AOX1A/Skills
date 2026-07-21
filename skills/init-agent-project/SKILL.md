---
name: init-agent-project
description: Initialize or align repository-level AI collaboration scaffolding with AGENT.md, a delegating CLAUDE.md compatibility stub, and .agent/. Use when a user asks to bootstrap a new repository, onboard an existing repository, migrate Claude conventions, create project memory/workspace directories, or standardize stable collaboration preferences and a newest-first dated project progress log.
---

# Initialize Agent Project

Create a small, repository-specific collaboration entry point without turning it into a duplicate README. Support empty repositories, active repositories, and explicit migrations from other agent conventions.

## Workflow

### 1. Resolve and inspect the repository

1. Resolve the target root from the user-provided path. Otherwise use the Git root when present, then fall back to the current working directory.
2. Inspect before writing:
   - top-level tree and relevant source/document directories;
   - `README*`, package manifests, build files, and authoritative docs;
   - `AGENT.md`, `AGENTS.md`, `CLAUDE.md`, `.agent/`, `.claude/`, and equivalent guidance;
   - Git status when the directory is a repository.
3. Read existing guidance completely before editing it. Preserve unrelated user changes.
4. Infer the project goal and working conventions from real files. Ask a question only when the goal cannot be inferred and guessing would materially mislead future agents.

Treat the target as one of these cases:

- **New or empty repository**: derive a minimal goal from the user's description and initialize the collaboration files.
- **Existing repository**: summarize its actual structure and merge project-specific conventions without replacing useful rules.
- **Convention migration**: translate requested names and references, detect destination collisions, and preserve content that still applies.

### 2. Decide the file boundary

Keep each file focused:

#### `AGENT.md`: stable collaboration contract

Include only durable information:

- a one-paragraph project goal;
- communication and collaboration preferences;
- stable task, engineering, data, or safety principles;
- where progress, temporary artifacts, README material, and formal docs belong;
- the instruction to read `.agent/memory/project_progress.md` at the start of work.

Do not put volatile details in `AGENT.md`, including current metrics, dated status, long absolute-path inventories, output filenames, temporary blockers, or a detailed implementation roadmap. Keep it concise enough to reread every turn.

#### `CLAUDE.md`: compatibility entry point

Create a root `CLAUDE.md` containing only:

```markdown
Read `AGENT.md`.
```

Keep `AGENT.md` as the single source of truth. Do not duplicate collaboration rules in `CLAUDE.md`.

#### `.agent/memory/project_progress.md`: dated changing state

Use this file for:

- a top-level note explaining that it is a newest-first dated progress log;
- dated progress, decisions, verified conclusions, pitfalls, and current state;
- a short `相关目录` block inside the relevant dated entry when paths materially help continuation;
- exact paths for external dependencies or reference files that cannot be located reliably from the repository itself.

Do not create a global “常用路径速查” or a repository-wide file inventory by default. For project-owned code, outputs, docs, and workspaces, prefer a few repository-relative directories over detailed internal filenames. When an external file itself is authoritative—such as a benchmark, schema, submission-format example, or platform integration note—record its complete absolute path so a later agent can locate the exact dependency.

Order dated entries newest first. Keep one section per day and do not rewrite older entries. Record genuine project state, not administrative narration such as “created AGENT.md” unless that change itself matters to the project. Do not invent completed work or future plans. If the file already has a different user-approved style, preserve it unless the user explicitly asks to align or migrate it.

If the file already exists, preserve history and add or revise only what the user authorized. Follow its established style.

#### `.agent/workspace/<MM.DD>/`: temporary artifacts

Place one-off analyses, scratch scripts, generated HTML, raw discussion exports, and other non-product artifacts here. Create the current date directory when the initialization request includes a workspace or when a temporary artifact needs a destination.

#### README and docs

Do not create a README by default. Reserve README for changing project structure, setup, commands, data locations, and formal outputs when the user asks for it. Reserve `docs/` for stable interfaces, schemas, and detailed design specifications.

### 3. Implement safely

Default structure:

```text
<repo>/
├── CLAUDE.md
├── AGENT.md
└── .agent/
    ├── memory/
    │   └── project_progress.md
    └── workspace/
        └── <MM.DD>/
```

Follow these rules:

1. Use the exact filename and directory convention requested by the user. Default to `AGENT.md` and `.agent/` for this skill.
2. Create the one-line `CLAUDE.md` compatibility entry when it is absent. If an existing `CLAUDE.md` contains substantive rules, preserve and reconcile those rules before replacing it with the delegating stub.
3. Do not create competing root instructions when `AGENTS.md` or another active guide already exists. Reconcile the convention with the user's request and preserve the authoritative content.
4. Do not delete or rename `.claude/` merely because this skill triggered. Migrate it only when the user explicitly requests migration.
5. Before migration, check whether the destination exists. Merge safely instead of overwriting.
6. Update internal references after an authorized rename, including memory and workspace paths.
7. Move temporary artifacts only when their ownership and destination are clear. Confirm the source exists and the destination does not before moving.
8. Avoid copying large datasets, generated outputs, credentials, or user logs into the repository.
9. Preserve the existing language and tone unless the user requests a change. Default to Chinese when the user's request and repository context are Chinese.

Use repository-specific prose. Do not paste a generic template unchanged or copy details from the repository where this skill is stored.

### 4. Validate the result

Perform documentation-level validation:

1. Confirm the expected files and directories exist and are non-empty where applicable.
2. Confirm root `CLAUDE.md` delegates to `AGENT.md` and contains no duplicate policy text.
3. Search hidden files for stale names after an explicit directory migration, such as old `.claude/` references.
4. Check that every path mentioned in the new files is intentional: internal paths should normally be concise repository-relative directories, while necessary external files should have exact absolute paths. Distinguish currently unavailable external paths from broken repository-relative links.
5. Confirm `AGENT.md` contains stable preferences rather than a progress dump.
6. Confirm `project_progress.md` contains no fabricated history and follows newest-first ordering.
7. Run `git diff --check` when inside Git. Do not run application tests for documentation-only initialization unless another change requires them.
8. Report created, updated, moved, and deliberately untouched files separately.

## Minimal content outlines

Use these as outlines, not fixed text.

### `AGENT.md`

```markdown
# AGENT.md — <项目名> 协作指南

> 每次开工前先读本文件，再读 `.agent/memory/project_progress.md`。

## 1. 项目目标（一句话）
## 2. 协作风格
## 3. 稳定的任务或工程原则
## 4. 开发与数据约定
## 5. 文档与记忆约定
```

### `project_progress.md`

```markdown
# 项目进展 — <项目名>

> 最新在最上，一天一个 section；按日期记录阶段结论、关键决策、踩坑、相关目录和下一步。

## YYYY-MM-DD

### 相关目录

- 项目内部只列少量目录：`scripts/<stage>/`、`outputs/<stage>/`
- 必须精确定位的外部参考文件：`/absolute/external/path/reference.jsonl`

### <本阶段主题>

**背景 / 口径 / 结果 / 决策 / 踩坑 / 下一步**
```

Adapt sections to the repository. Omit empty or irrelevant headings.

## Reference examples

Real files from a working repository, useful for judging structure, tone, and the file boundary — study them, do not copy their content:

- `references/example-AGENT.md` — a concise, stable collaboration contract (goal, collaboration style, task/engineering principles, doc & memory conventions) with no volatile status.
- `references/example-project_progress.md` — a concise newest-first dated progress log with per-day related directories, exact paths only for necessary external dependencies, and no global path inventory.
