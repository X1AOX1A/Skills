#!/usr/bin/env bash
# Unattended daily run of the paper-suggestions skill (invoked by launchd or cron).
#
# It calls the Claude Code CLI in headless (-p) mode and asks it to run the
# paper-suggestions skill. All logic lives in the skill itself; this is just the launcher.
#
# Env overrides:
#   CLAUDE_CLI                 CLI binary to use (default: tclaude; use 'claude' if that's yours)
#   PAPER_SUGGESTIONS_LOG_DIR  where to write logs (default: ~/Local/CACHE/paper-suggestions/logs)
set -euo pipefail

# launchd/cron run with a minimal PATH — add Homebrew, node, user, and system bins so the
# CLI and its probes (ioreg, etc.) resolve.
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

LOG_DIR="${PAPER_SUGGESTIONS_LOG_DIR:-$HOME/Local/CACHE/paper-suggestions/logs}"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/run-$(date +%Y-%m-%d).log"

CLI="${CLAUDE_CLI:-tclaude}"
PROMPT="Use the paper-suggestions skill to generate today's paper digest now: follow its SKILL.md workflow and preferences.yaml end-to-end (fetch, match to topics, write the dated digest, and the optional Feishu upload if enabled). This is a scheduled, non-interactive run — do not ask questions."

{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S') START paper-suggestions (CLI=$CLI) ==="
  "$CLI" -p "$PROMPT" --dangerously-skip-permissions
  echo "=== $(date '+%Y-%m-%d %H:%M:%S') END exit=$? ==="
} >> "$LOG" 2>&1
