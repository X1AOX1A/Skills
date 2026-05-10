#!/usr/bin/env python3
"""Convert PDF to Markdown using pymupdf4llm."""

import argparse
import math
import pathlib
import re
import sys


def estimate_tokens(text: str) -> str:
    """Estimate token count using ~4 characters per token heuristic.

    Returns a human-friendly string like "14.5k" or "850".
    """
    token_count = len(text) / 4
    if token_count >= 1000:
        val = token_count / 1000
        # Round to 1 decimal, drop trailing .0
        formatted = f"{val:.1f}".rstrip("0").rstrip(".")
        return f"{formatted}k"
    return str(int(math.ceil(token_count)))


def extract_toc(md_text: str) -> list[dict]:
    """Extract headings from markdown text and build a TOC structure.

    Returns a list of dicts with keys: level, title.
    """
    toc = []
    # Match markdown headings (# to ######)
    heading_re = re.compile(r"^(#{1,6})\s+(.+?)(?:\s*#*\s*)?$", re.MULTILINE)
    for m in heading_re.finditer(md_text):
        level = len(m.group(1))
        title = m.group(2).strip()
        toc.append({"level": level, "title": title})
    return toc


def build_frontmatter(sections: int, estimated_tokens: str, toc: list[dict]) -> str:
    """Build YAML frontmatter + Contents section.

    Example output:
    ---
    sections: 27
    estimated_tokens: "14.5k"
    ---

    ## Contents
    - 1 Introduction
      - 1.1 Background
    """
    lines = []
    # YAML frontmatter
    lines.append("---")
    lines.append(f"sections: {sections}")
    lines.append(f'estimated_tokens: "{estimated_tokens}"')
    lines.append("---")
    lines.append("")

    # Table of Contents
    if toc:
        lines.append("## Contents")
        # Find the minimum heading level to use as base indentation
        min_level = min(h["level"] for h in toc)
        for heading in toc:
            indent = "  " * (heading["level"] - min_level)
            lines.append(f"{indent}- {heading['title']}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Convert PDF to Markdown using pymupdf4llm")
    parser.add_argument("-i", "--input", help="Path to the input PDF file")
    parser.add_argument("-o", "--output", help="Path to the output Markdown file (default: same name as input with .md extension)")
    parser.add_argument("--no-toc", action="store_true", help="Disable TOC and frontmatter generation")
    parser.add_argument("--no-figures", action="store_true", help="Disable image extraction")
    parser.add_argument("--figures-dir", default="figures", help="Directory name (relative to output md) to store figures (default: figures)")
    parser.add_argument("--image-format", default="png", choices=["png", "jpg"], help="Extracted image format (default: png)")
    parser.add_argument("--dpi", type=int, default=200, help="DPI for extracted images (default: 200)")
    args = parser.parse_args()

    input_path = pathlib.Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} does not exist", file=sys.stderr)
        sys.exit(1)

    if args.output:
        output_path = pathlib.Path(args.output)
    else:
        output_path = input_path.with_suffix(".md")

    import pymupdf4llm

    if args.no_figures:
        md_text = pymupdf4llm.to_markdown(str(input_path))
    else:
        figures_dir = (output_path.parent / args.figures_dir).resolve()
        figures_dir.mkdir(parents=True, exist_ok=True)
        md_text = pymupdf4llm.to_markdown(
            str(input_path),
            write_images=True,
            image_path=str(figures_dir),
            image_format=args.image_format,
            dpi=args.dpi,
        )
        # Rewrite any image reference to use `<figures-dir>/<basename>` so
        # the md is portable regardless of how pymupdf4llm emits the path.
        figdir = args.figures_dir.rstrip("/")

        def _rewrite(match: re.Match) -> str:
            alt, path = match.group(1), match.group(2)
            basename = pathlib.PurePosixPath(path.replace("\\", "/")).name
            return f"![{alt}]({figdir}/{basename})"

        md_text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", _rewrite, md_text)

    if not args.no_toc:
        toc = extract_toc(md_text)
        tokens = estimate_tokens(md_text)
        frontmatter = build_frontmatter(
            sections=len(toc),
            estimated_tokens=tokens,
            toc=toc,
        )
        md_text = frontmatter + "\n" + md_text

    output_path.write_bytes(md_text.encode())
    print(f"Converted: {input_path} -> {output_path}")

if __name__ == "__main__":
    main()
