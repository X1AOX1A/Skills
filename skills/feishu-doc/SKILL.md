---
name: feishu-doc
description: |
  Turn a local Markdown file into a Feishu (Lark) Docx cloud document and push the link
  to a user via a private bot DM. Uses a Feishu self-built app (tenant_access_token) with
  the Drive import API and the im/v1 message API.
  TRIGGER when: user wants to send/push a Markdown file to Feishu/Lark as a cloud document,
  create a 飞书云文档 from local content, DM a doc link to themselves or someone via a Feishu
  bot, or publish a report/digest (e.g. a paper digest) into Feishu Docs.
  DO NOT TRIGGER when: user wants to drive a coding agent from Feishu (that is a different
  inbound bridge), or wants a generic Feishu API integration unrelated to importing docs
  or sending messages.
---

# Feishu Doc Push

Import a local `.md` into a **Feishu Docx cloud document** and DM the shareable link.

Pipeline: `upload media → create import task → poll → send interactive card`.

## Prerequisites

A **Feishu self-built app** (企业自建应用, created at https://open.feishu.cn):

1. Create the app → copy **App ID** and **App Secret**.
2. Enable permission scopes (权限管理):
   - `drive:drive` — upload media, create import task, read My Space root folder
   - `docx:document` — the imported doc type
   - `im:message` — send single-chat messages (发送单聊消息)
   - `contact:user.id:readonly` — **only** if resolving a recipient by `--mobile`
3. **Publish** the app (create a version and release) so the scopes take effect.
4. Make sure the recipient is inside the app's availability scope (可用范围), otherwise
   the DM is rejected.

`requests` must be installed (`pip install requests`).

## Configuration

Set via environment or a `.env` file placed in the skill directory (see `.env.example`):

| Var | Required | Purpose |
| --- | --- | --- |
| `FEISHU_APP_ID` | yes | Self-built app ID |
| `FEISHU_APP_SECRET` | yes | Self-built app secret |
| `FEISHU_TO_OPEN_ID` | no | Default recipient `open_id` (override with `--open-id`) |
| `FEISHU_TO_EMAIL` | no | Default recipient email (override with `--to`) |
| `FEISHU_TO_MOBILE` | no | Default recipient mobile (override with `--mobile`) |
| `FEISHU_FOLDER_TOKEN` | no | Target Drive folder by token; defaults to My Space root |
| `FEISHU_FOLDER_NAME` | no | Target folder by name under My Space root (created if missing), e.g. `PaperSuggess` |
| `FEISHU_GRANT_PERM` | no | Add recipient as collaborator: `view` / `edit` / `full_access` (可管理/admin) |
| `FEISHU_BASE` | no | `https://open.feishu.cn` (default) or `https://open.larksuite.com` for Lark Intl |

The `.env` never overrides real environment variables and should not be committed.

## Usage

```bash
python scripts/push_doc.py <path-to-markdown> [--open-id OU_... | --to EMAIL | --mobile +86...] \
    [--folder TOKEN | --folder-name NAME] [--grant view|edit|full_access] [--title TITLE] [--no-send]
```

Examples:

```bash
# Import and DM to the default recipient (from .env)
python scripts/push_doc.py /Users/x1a/Local/paper-suggestions/2026-07-13.md

# Send to a specific person by open_id (most reliable — no extra scope needed)
python scripts/push_doc.py digest.md --open-id ou_xxxxxxxx --title "Paper Digest 07-13"

# Save into a named folder (created under My Space root if missing) and make the recipient admin
python scripts/push_doc.py digest.md --folder-name PaperSuggess --grant full_access

# Send by email
python scripts/push_doc.py digest.md --to alice@example.com

# Send by mobile (needs the contact:user.id:readonly scope)
python scripts/push_doc.py digest.md --mobile +8613800138000

# Just create the cloud doc, print the URL, don't DM anyone
python scripts/push_doc.py notes.md --no-send
```

**Choosing a recipient identifier** (precedence: `open_id` → `email` → `mobile`):

- **`open_id`** (recommended) — no extra scope, always works. How to find one:
  https://open.feishu.cn/document/faq/trouble-shooting/how-to-obtain-openid
- **email** — the recipient's Feishu login email.
- **mobile** — requires the extra `contact:user.id:readonly` scope; the script resolves
  it to an `open_id` internally.

## Notes

- The doc **title** defaults to the file stem; override with `--title`.
- **Where it's saved** — `--folder-name NAME` finds/creates a folder by name under My Space
  root; `--folder TOKEN` targets a specific folder by token (open the folder in Feishu; the
  token is the last URL segment). Omit both to save in My Space root.
- **`--grant`** — the doc is created under the *app/bot* identity, so the recipient only has
  link access by default. `--grant full_access` adds them as a **可管理 (admin)** collaborator
  (also `view` / `edit`). Applied to the resolved recipient; works even with `--no-send`.
- The link is delivered as an **interactive card** with an "打开文档" button.

## Troubleshooting

- `code 99991679` / token errors → check App ID/Secret and that the app is published.
- Message send rejected → the recipient isn't in the app's 可用范围, or `im:message` scope
  isn't granted/published.
- Import stuck/failed → the script surfaces `job_error_msg`; verify `drive:drive` scope.
- Grant/collaborator errors → also covered by the `drive:drive` scope.
