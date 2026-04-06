#!/usr/bin/env python3
"""
arxiv_figures.py — Extract figures from arXiv papers via HTML.

Lightweight approach: fetches the arXiv HTML rendering (LaTeXML),
parses <figure> elements, extracts captions and image URLs,
then lets you select which figures to download.

Usage:
    python arxiv_figures.py <arxiv_id>                  # interactive
    python arxiv_figures.py <arxiv_id> --all             # download all
    python arxiv_figures.py <arxiv_id> --list            # just list
    python arxiv_figures.py <arxiv_id> --json            # JSON to stdout
    python arxiv_figures.py <arxiv_id> -o path/to/dir    # custom output

Output structure:
    outputs/figures/<arxiv_id>/
    ├── fig1_overview_of_the_framework.png
    ├── fig2_performance_comparison.png
    └── captions.json
"""

import argparse
import json
import os
import re
import sys
import time
from copy import copy
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ARXIV_HTML_URL = "https://arxiv.org/html/{arxiv_id}"
HEADERS = {
    "User-Agent": "arxiv-figures/1.0 (academic research tool)",
}
MAX_RETRIES = 3
RETRY_DELAY = 3  # seconds


# ---------------------------------------------------------------------------
# Fetch HTML
# ---------------------------------------------------------------------------

def fetch_html(arxiv_id: str) -> tuple:
    """Fetch the HTML version of an arXiv paper.

    Returns:
        (html_text, final_url) — final_url is after redirects
    """
    url = ARXIV_HTML_URL.format(arxiv_id=arxiv_id)
    print(f"📥 Fetching {url} ...")

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code == 200:
                return resp.text, resp.url
            elif resp.status_code == 404:
                raise ValueError(
                    f"HTML not available for {arxiv_id}. "
                    "Not all papers have an HTML version on arXiv."
                )
            elif resp.status_code == 429:
                wait = RETRY_DELAY * (attempt + 1)
                print(f"⏳ Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.reason}")
        except requests.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise RuntimeError(f"Failed to fetch: {e}")

    raise RuntimeError("Max retries exceeded")


# ---------------------------------------------------------------------------
# Parse figures from HTML
# ---------------------------------------------------------------------------

def _get_caption_text(caption_el: Tag) -> str:
    """Extract caption text, removing the 'Figure N:' label prefix."""
    if caption_el is None:
        return ""
    # Work on a copy so we don't mutate the tree
    el = copy(caption_el)
    # Remove the label span (e.g. "Figure 1: ")
    for tag_span in el.find_all("span", class_="ltx_tag_figure"):
        tag_span.decompose()
    text = el.get_text(separator=" ", strip=True)
    # Clean up whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _get_figure_label(caption_el: Tag) -> str:
    """Extract figure label like 'Figure 1' from caption."""
    if caption_el is None:
        return ""
    tag_span = caption_el.find("span", class_="ltx_tag_figure")
    if tag_span:
        return tag_span.get_text(strip=True).rstrip(":")
    return ""


def _make_figure_name(label: str, caption: str) -> str:
    """Create a short, filesystem-safe name from label + caption summary."""
    # Start with label: "Figure 1" → "fig1"
    prefix = label.lower().replace("figure ", "fig").replace(" ", "")
    if not prefix:
        prefix = "fig"

    # Summarize caption: take first few meaningful words
    words = caption.split()[:6]
    summary = "_".join(words).lower()
    summary = re.sub(r"[^a-z0-9_]", "", summary)
    summary = re.sub(r"_+", "_", summary).strip("_")

    if summary:
        name = f"{prefix}_{summary}"
    else:
        name = prefix

    return name[:80]


def parse_figures(html: str, page_url: str) -> Dict[str, dict]:
    """
    Parse all figures from arXiv HTML.

    Returns:
        ({figure_name: {label, caption, image_urls, figure_id}}, title)
    """
    soup = BeautifulSoup(html, "html.parser")

    # Determine base URL for resolving relative image paths.
    # Some arXiv HTML pages have <base href="/html/2406.11434v1/">,
    # others don't and use paths like "2512.18832v2/x1.png".
    base_tag = soup.find("base")
    if base_tag and base_tag.get("href"):
        base_url = urljoin(page_url, base_tag["href"])
    else:
        # No <base> tag — use the page URL itself (without trailing /)
        # so urljoin replaces the last path segment correctly.
        base_url = page_url.rstrip("/")

    # Get paper title
    title_el = soup.find("h1", class_="ltx_title")
    title = title_el.get_text(strip=True).replace("Title:", "").strip() if title_el else ""

    figures = {}
    name_counts = {}  # for dedup

    for fig in soup.find_all("figure", class_="ltx_figure"):
        # Skip subfigures (nested inside any ancestor ltx_figure)
        is_subfigure = False
        for ancestor in fig.parents:
            if not isinstance(ancestor, Tag):
                break
            if ancestor.name == "figure" and "ltx_figure" in ancestor.get("class", []):
                is_subfigure = True
                break
        if is_subfigure:
            continue

        fig_id = fig.get("id", "")

        # Get the direct-child caption (not subfigure captions)
        caption_el = fig.find("figcaption", class_="ltx_caption", recursive=False)
        label = _get_figure_label(caption_el)
        caption = _get_caption_text(caption_el)

        # Collect all images (including from subfigures)
        imgs = fig.find_all("img", class_="ltx_graphics")
        image_urls = []
        for img in imgs:
            src = img.get("src", "")
            if src:
                full_url = urljoin(base_url, src)
                image_urls.append(full_url)

        if not image_urls:
            continue

        # Build name
        name = _make_figure_name(label, caption)
        if name in name_counts:
            name_counts[name] += 1
            name = f"{name}_{name_counts[name]}"
        else:
            name_counts[name] = 1

        figures[name] = {
            "label": label,
            "caption": caption,
            "image_urls": image_urls,
            "figure_id": fig_id,
        }

    return figures, title


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def display_figures(figures: dict, title: str = "") -> None:
    """Pretty-print the figure list."""
    if title:
        print(f"\n📄 {title}")

    if not figures:
        print("\n⚠️  No figures found.")
        return

    print(f"\n{'='*70}")
    print(f"  Found {len(figures)} figure(s)")
    print(f"{'='*70}\n")

    for i, (name, info) in enumerate(figures.items()):
        n_imgs = len(info["image_urls"])
        img_note = f" ({n_imgs} panels)" if n_imgs > 1 else ""
        print(f"  [{i}] {info['label']}{img_note}")
        caption = info["caption"]
        if len(caption) > 120:
            caption = caption[:120] + "..."
        print(f"      {caption}")
        print(f"      name: {name}")
        print()


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------

def select_figures(figures: dict) -> List[str]:
    """Interactive figure selection. Returns list of names."""
    names = list(figures.keys())
    display_figures(figures)

    while True:
        print("Select figures to download:")
        print("  • Indices separated by commas: 0,1,3")
        print("  • Range: 0-4")
        print("  • 'all' for everything")
        print("  • 'q' to quit")
        print()

        try:
            choice = input(">>> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return []

        if choice == "q":
            return []
        if choice == "all":
            return names

        # Parse selection
        try:
            indices = set()
            for part in choice.split(","):
                part = part.strip()
                if "-" in part:
                    a, b = part.split("-", 1)
                    indices.update(range(int(a), int(b) + 1))
                else:
                    indices.add(int(part))

            selected = []
            for idx in sorted(indices):
                if 0 <= idx < len(names):
                    selected.append(names[idx])
                else:
                    print(f"  ⚠️  Index {idx} out of range (0-{len(names)-1})")
            if selected:
                return selected
            print("  No valid indices selected. Try again.\n")
        except ValueError:
            print("  ❌ Invalid input.\n")


# ---------------------------------------------------------------------------
# Download & Save
# ---------------------------------------------------------------------------

def download_figures(
    figures: dict,
    selected: List[str],
    output_dir: str,
) -> dict:
    """Download selected figures and save captions.json."""
    os.makedirs(output_dir, exist_ok=True)

    captions = {}

    for name in selected:
        info = figures[name]
        urls = info["image_urls"]

        if len(urls) == 1:
            # Single image
            url = urls[0]
            ext = _guess_ext(url)
            filename = f"{name}{ext}"
            filepath = os.path.join(output_dir, filename)
            _download_file(url, filepath)
            captions[name] = {
                "file": filename,
                "label": info["label"],
                "caption": info["caption"],
            }
        else:
            # Multi-panel: save each with _a, _b, _c suffix
            files = []
            for j, url in enumerate(urls):
                suffix = chr(ord("a") + j) if j < 26 else str(j)
                ext = _guess_ext(url)
                filename = f"{name}_{suffix}{ext}"
                filepath = os.path.join(output_dir, filename)
                _download_file(url, filepath)
                files.append(filename)
            captions[name] = {
                "files": files,
                "label": info["label"],
                "caption": info["caption"],
            }

    # Save captions.json
    captions_path = os.path.join(output_dir, "captions.json")
    with open(captions_path, "w", encoding="utf-8") as f:
        json.dump(captions, f, indent=2, ensure_ascii=False)

    print(f"\n📝 Saved captions.json → {captions_path}")
    return captions


def _download_file(url: str, filepath: str) -> None:
    """Download a single file."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        with open(filepath, "wb") as f:
            f.write(resp.content)
        size_kb = len(resp.content) / 1024
        print(f"  ✅ {os.path.basename(filepath)} ({size_kb:.0f} KB)")
    except Exception as e:
        print(f"  ❌ Failed to download {url}: {e}")


def _guess_ext(url: str) -> str:
    """Guess file extension from URL."""
    path = url.split("?")[0]
    ext = os.path.splitext(path)[1].lower()
    if ext in (".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp", ".pdf"):
        return ext
    return ".png"  # default


# ---------------------------------------------------------------------------
# Public API (for importing as a module)
# ---------------------------------------------------------------------------

def get_figures(arxiv_id: str) -> dict:
    """
    Fetch and parse figures from an arXiv paper.

    Args:
        arxiv_id: e.g. "2406.11434" or "2406.11434v1"

    Returns:
        {
            "title": "...",
            "figures": {
                "fig1_overview": {
                    "label": "Figure 1",
                    "caption": "Overview of ...",
                    "image_urls": ["https://..."],
                },
                ...
            }
        }
    """
    arxiv_id = _normalize_id(arxiv_id)
    html, final_url = fetch_html(arxiv_id)
    figures, title = parse_figures(html, final_url)
    return {"title": title, "arxiv_id": arxiv_id, "figures": figures}


def download_paper_figures(
    arxiv_id: str,
    output_dir: Optional[str] = None,
    select: Optional[List[int]] = None,
    download_all: bool = False,
) -> dict:
    """
    Full pipeline: fetch → parse → download.

    Args:
        arxiv_id: arXiv paper ID
        output_dir: where to save (default: outputs/figures/<id>/figures)
        select: list of figure indices to download (0-based)
        download_all: if True, download everything

    Returns:
        captions dict
    """
    result = get_figures(arxiv_id)
    figures = result["figures"]
    title = result["title"]
    arxiv_id = result["arxiv_id"]

    if output_dir is None:
        safe_id = arxiv_id.replace("/", "_").replace(".", "_")
        output_dir = os.path.join("outputs", "figures", safe_id, "figures")

    names = list(figures.keys())

    if download_all:
        selected = names
    elif select is not None:
        selected = [names[i] for i in select if 0 <= i < len(names)]
    else:
        selected = names  # default to all

    print(f"\n📄 {title}")
    print(f"📁 Output: {output_dir}")
    print(f"📊 Downloading {len(selected)}/{len(figures)} figures\n")

    return download_figures(figures, selected, output_dir)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _normalize_id(arxiv_id: str) -> str:
    """Clean up arxiv ID from various input formats."""
    arxiv_id = arxiv_id.strip()
    for prefix in [
        "https://arxiv.org/abs/",
        "http://arxiv.org/abs/",
        "https://arxiv.org/html/",
        "http://arxiv.org/html/",
        "https://arxiv.org/pdf/",
        "http://arxiv.org/pdf/",
        "arxiv.org/abs/",
    ]:
        if arxiv_id.lower().startswith(prefix):
            arxiv_id = arxiv_id[len(prefix):]
            break
    # Remove trailing .pdf
    if arxiv_id.endswith(".pdf"):
        arxiv_id = arxiv_id[:-4]
    return arxiv_id


def main():
    parser = argparse.ArgumentParser(
        description="Extract figures from arXiv papers via HTML",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 2406.11434                    # interactive selection
  %(prog)s 2406.11434 --all              # download all figures
  %(prog)s 2406.11434 --list             # list figures only
  %(prog)s 2406.11434 --json             # output JSON
  %(prog)s 2406.11434 -o my_figs/        # custom output dir
  %(prog)s https://arxiv.org/abs/2406.11434   # URL input
        """,
    )
    parser.add_argument("arxiv_id", help="arXiv paper ID or URL")
    parser.add_argument("-o", "--output-dir", help="Output directory")
    parser.add_argument("--all", action="store_true", help="Download all figures")
    parser.add_argument("--list", action="store_true", help="List figures only")
    parser.add_argument("--json", action="store_true", help="Output JSON to stdout")

    args = parser.parse_args()

    arxiv_id = _normalize_id(args.arxiv_id)

    # Set output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        safe_id = arxiv_id.replace("/", "_").replace(".", "_")
        output_dir = os.path.join("outputs", "figures", safe_id, "figures")

    # Fetch & parse
    try:
        html, final_url = fetch_html(arxiv_id)
    except Exception as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    # Use actual response URL as base for resolving relative image paths
    figures, title = parse_figures(html, final_url)

    # --- JSON mode ---
    if args.json:
        output = {
            "title": title,
            "arxiv_id": arxiv_id,
            "figures": {
                name: {
                    "label": info["label"],
                    "caption": info["caption"],
                    "image_urls": info["image_urls"],
                }
                for name, info in figures.items()
            },
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return

    # --- List mode ---
    if args.list:
        display_figures(figures, title)
        return

    # --- Download mode ---
    if not figures:
        print(f"\n📄 {title}")
        print("\n⚠️  No figures found.")
        sys.exit(0)

    if args.all:
        selected = list(figures.keys())
        display_figures(figures, title)
        print(f"📁 Downloading all to: {output_dir}\n")
    else:
        selected = select_figures(figures)
        if not selected:
            print("Nothing selected. Bye!")
            return
        print(f"\n📁 Saving {len(selected)} figure(s) to: {output_dir}\n")

    download_figures(figures, selected, output_dir)
    print(f"\n🎉 Done! → {output_dir}")


if __name__ == "__main__":
    main()
