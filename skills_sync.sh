#!/usr/bin/env bash
set -euo pipefail

# ── Project root & config paths ──────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
CSV_FILE="$SCRIPT_DIR/skills_table.csv"

# ── Colors ───────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# ── Load .env ────────────────────────────────────────────────────
load_env() {
    if [[ ! -f "$ENV_FILE" ]]; then
        echo -e "${RED}Error: .env not found: $ENV_FILE${RESET}" >&2
        exit 1
    fi
    while IFS='=' read -r key value || [[ -n "$key" ]]; do
        [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
        key="$(echo "$key" | xargs)"
        value="$(echo "$value" | xargs)"
        value="${value/#\~/$HOME}"
        export "$key=$value"
    done < "$ENV_FILE"
}

# ── Parse CSV ────────────────────────────────────────────────────
# Output: skill_name,claude_flag,codex_flag,cursor_flag (one per line)
parse_csv() {
    if [[ ! -f "$CSV_FILE" ]]; then
        echo -e "${RED}Error: skills_table.csv not found: $CSV_FILE${RESET}" >&2
        exit 1
    fi
    local line_num=0
    while IFS=',' read -r skill claude codex cursor || [[ -n "$skill" ]]; do
        line_num=$((line_num + 1))
        [[ $line_num -eq 1 ]] && continue
        skill="$(echo "$skill" | xargs)"
        claude="$(echo "$claude" | xargs)"
        codex="$(echo "$codex" | xargs)"
        cursor="$(echo "$cursor" | xargs)"
        [[ -z "$skill" ]] && continue
        echo "$skill,$claude,$codex,$cursor"
    done < "$CSV_FILE"
}

# ── Target directory mapping ─────────────────────────────────────
get_target_dir() {
    local tool="$1"
    case "$tool" in
        claude) echo "$CLAUDE_SKILLS" ;;
        codex)  echo "$CODEX_SKILLS" ;;
        cursor) echo "$CURSOR_SKILLS" ;;
    esac
}

# ── sync ─────────────────────────────────────────────────────────
cmd_sync() {
    echo -e "${BOLD}${CYAN}▶ Syncing skill symlinks...${RESET}"
    echo ""

    local created=0 removed=0 skipped=0
    local expected_links=""

    while IFS=',' read -r skill csv_claude csv_codex csv_cursor; do
        local tools_list="claude codex cursor"
        local flag_claude="$csv_claude"
        local flag_codex="$csv_codex"
        local flag_cursor="$csv_cursor"

        for tool in $tools_list; do
            local flag
            case "$tool" in
                claude) flag="$flag_claude" ;;
                codex)  flag="$flag_codex" ;;
                cursor) flag="$flag_cursor" ;;
            esac
            local target_dir
            target_dir="$(get_target_dir "$tool")"
            local link_path="$target_dir/$skill"
            local source_path="$SKILLS/$skill"

            if [[ "$flag" == "1" ]]; then
                expected_links="$expected_links$tool:$skill
"

                if [[ ! -d "$source_path" ]]; then
                    echo -e "  ${RED}✗${RESET} ${BOLD}$skill${RESET} → $tool  (source not found: $source_path)"
                    continue
                fi

                if [[ -L "$link_path" ]]; then
                    local current_target
                    current_target="$(readlink "$link_path")"
                    if [[ "$current_target" == "$source_path" ]]; then
                        echo -e "  ${YELLOW}⊘${RESET} ${BOLD}$skill${RESET} → $tool  (already linked, skip)"
                        skipped=$((skipped + 1))
                    else
                        rm "$link_path"
                        ln -s "$source_path" "$link_path"
                        echo -e "  ${GREEN}✓${RESET} ${BOLD}$skill${RESET} → $tool  (relinked)"
                        created=$((created + 1))
                    fi
                else
                    mkdir -p "$target_dir"
                    if [[ -e "$link_path" ]]; then
                        echo -e "  ${RED}!${RESET} ${BOLD}$skill${RESET} → $tool  (target exists and is not a symlink, skip)"
                        continue
                    fi
                    ln -s "$source_path" "$link_path"
                    echo -e "  ${GREEN}✓${RESET} ${BOLD}$skill${RESET} → $tool  (created)"
                    created=$((created + 1))
                fi
            else
                if [[ -L "$link_path" ]]; then
                    rm "$link_path"
                    echo -e "  ${RED}✗${RESET} ${BOLD}$skill${RESET} → $tool  (removed)"
                    removed=$((removed + 1))
                fi
            fi
        done
    done <<< "$(parse_csv)"

    # ── Clean up orphan symlinks ─────────────────────────────────
    local orphan_removed=0
    for tool in claude codex cursor; do
        local target_dir
        target_dir="$(get_target_dir "$tool")"
        [[ ! -d "$target_dir" ]] && continue

        for entry in "$target_dir"/*; do
            [[ ! -e "$entry" && ! -L "$entry" ]] && continue
            local name
            name="$(basename "$entry")"
            [[ "$name" == .* ]] && continue
            [[ ! -L "$entry" ]] && continue
            if ! echo "$expected_links" | grep -qx "$tool:$name"; then
                rm "$entry"
                echo -e "  ${RED}✗${RESET} ${BOLD}$name${RESET} → $tool  (orphan removed)"
                orphan_removed=$((orphan_removed + 1))
            fi
        done
    done
    removed=$((removed + orphan_removed))

    echo ""
    echo -e "${BOLD}Done:${RESET} created ${GREEN}$created${RESET}, removed ${RED}$removed${RESET}, skipped ${YELLOW}$skipped${RESET}"
}

# ── status ───────────────────────────────────────────────────────
cmd_status() {
    echo -e "${BOLD}${CYAN}▶ Skills deployment status${RESET}"
    echo ""

    printf "  ${BOLD}%-24s %-12s %-12s %-12s${RESET}\n" "SKILL" "CLAUDE" "CODEX" "CURSOR"
    printf "  %-24s %-12s %-12s %-12s\n" "────────────────────────" "──────────" "──────────" "──────────"

    while IFS=',' read -r skill csv_claude csv_codex csv_cursor; do
        local cell_claude cell_codex cell_cursor

        for tool in claude codex cursor; do
            local flag target_dir link_path source_path cell
            case "$tool" in
                claude) flag="$csv_claude" ;;
                codex)  flag="$csv_codex" ;;
                cursor) flag="$csv_cursor" ;;
            esac
            target_dir="$(get_target_dir "$tool")"
            link_path="$target_dir/$skill"
            source_path="$SKILLS/$skill"

            if [[ "$flag" == "1" ]]; then
                if [[ -L "$link_path" ]]; then
                    local current_target
                    current_target="$(readlink "$link_path")"
                    if [[ "$current_target" == "$source_path" ]]; then
                        cell="${GREEN}✓ linked${RESET}"
                    else
                        cell="${YELLOW}⚠ wrong${RESET}"
                    fi
                else
                    cell="${RED}✗ missing${RESET}"
                fi
            else
                if [[ -L "$link_path" ]]; then
                    cell="${YELLOW}⚠ extra${RESET}"
                else
                    cell="  ─"
                fi
            fi

            case "$tool" in
                claude) cell_claude="$cell" ;;
                codex)  cell_codex="$cell" ;;
                cursor) cell_cursor="$cell" ;;
            esac
        done

        printf "  %-24s %-22b %-22b %-22b\n" "$skill" "$cell_claude" "$cell_codex" "$cell_cursor"
    done <<< "$(parse_csv)"

    echo ""
}

# ── Usage ────────────────────────────────────────────────────────
usage() {
    echo -e "${BOLD}Usage:${RESET} $0 <command>"
    echo ""
    echo -e "${BOLD}Commands:${RESET}"
    echo "  sync     Sync symlinks according to skills_table.csv"
    echo "  status   Show current deployment status"
    echo "  help     Show this help message"
    echo ""
    echo -e "${BOLD}Config files:${RESET}"
    echo "  .env              Directory path settings"
    echo "  skills_table.csv  Deployment matrix (skill x tool)"
}

# ── Entry ────────────────────────────────────────────────────────
load_env

case "${1:-help}" in
    sync)   cmd_sync ;;
    status) cmd_status ;;
    help|*) usage ;;
esac
