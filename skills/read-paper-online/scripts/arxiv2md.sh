#!/usr/bin/env bash
set -euo pipefail

usage() {
echo "Usage: $(basename "$0") <arxiv_id> [-o output.md]"
echo "  arxiv_id    ArXiv paper ID (e.g. 2301.07041)"
echo "  -o FILE     Write output to FILE (default: stdout)"
exit 1
}

[[ $# -lt 1 ]] && usage

ARXIV_ID="$1"
shift

OUTPUT=""
while [[ $# -gt 0 ]]; do
case "$1" in
    -o)
    [[ $# -lt 2 ]] && { echo "Error: -o requires a path"; exit 1; }
    OUTPUT="$2"
    shift 2
    ;;
    *)
    usage
    ;;
esac
done

# If user passed just an ID, convert to full arxiv URL
if [[ "$ARXIV_ID" != http* ]]; then
ARXIV_ID="https://arxiv.org/abs/${ARXIV_ID}"
fi

# URL-encode the arxiv URL for the query parameter
ENCODED_URL=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$ARXIV_ID', safe=''))")

URL="https://arxiv2md.org/api/markdown?url=${ENCODED_URL}&remove_refs=false&remove_toc=false&remove_citations=false&frontmatter=true"

if [[ -n "$OUTPUT" ]]; then
curl -fsSL "$URL" -o "$OUTPUT"
echo "Saved to $OUTPUT"
else
curl -fsSL "$URL"
fi

