---
name: arxiv-figures
description: >
  Extract, browse, and download figures from arXiv papers using their HTML rendering.
  Use this skill whenever the user wants to get figures/images/diagrams from an arXiv paper,
  extract paper illustrations, download paper visuals, grab charts or plots from a paper,
  or reference a specific figure from an arXiv paper for use in slides, blog posts, or documents.
  Also trigger when the user mentions an arXiv ID (like 2406.11434) in the context of needing
  images, visuals, or figures from that paper — even if they don't say "figure" explicitly
  (e.g., "get me the architecture diagram from 2406.11434", "I need the results chart from
  this paper"). This skill handles the full pipeline: fetching the paper's HTML, parsing all
  figure environments with their captions, letting the user choose which to download, and
  saving them with a structured captions.json metadata file.
---

# arXiv Figure Extractor

Extract figures and their captions from arXiv papers via the HTML rendering (LaTeXML). This is lightweight — no LaTeX compilation or source download needed.

## How it works

arXiv renders most papers as HTML using LaTeXML. The HTML contains `<figure class="ltx_figure">` elements with `<img>` tags and `<figcaption>` captions. This skill parses that structure to extract all figures with their captions, labels, and image URLs.

## Bundled script

The core logic lives in `scripts/arxiv_figures.py` (relative to this skill's directory). It has both a CLI and a Python API.

**Dependencies**: `requests`, `beautifulsoup4` (both common; install with `pip install requests beautifulsoup4` if needed).

## Workflow

### Step 1: Identify the paper

Accept any of these input formats and normalize to a bare arxiv ID:
- `2406.11434` or `2406.11434v2`
- `https://arxiv.org/abs/2406.11434`
- `https://arxiv.org/pdf/2406.11434`
- `https://arxiv.org/html/2406.11434`

### Step 2: List figures

Run the script with `--json` to get structured figure data:

```bash
python <skill-dir>/scripts/arxiv_figures.py <arxiv_id> --json
```

This outputs JSON to stdout:
```json
{
  "title": "Paper Title",
  "arxiv_id": "2406.11434",
  "figures": {
    "fig1_overview_of_the_framework": {
      "label": "Figure 1",
      "caption": "Overview of the framework...",
      "image_urls": ["https://arxiv.org/html/2406.11434v1/x1.png"]
    }
  }
}
```

Present the figures to the user in a readable format — show the figure number, a short caption summary, and how many panels (sub-images) each figure has.

**Tip — display without downloading**: If the user only needs to *display* figures (e.g., embedding in Markdown, a chat message, or a preview), you can reference the `image_urls` directly from the JSON output — no download needed. For example, use `![Figure 1](https://arxiv.org/html/2406.11434v1/x1.png)` in Markdown. Only proceed to Step 3 when the user needs local files (for slides, offline use, further editing, etc.).


### Step 3: Download selected figures

Based on what the user wants, run with appropriate flags:

```bash
# Download all figures
python <skill-dir>/scripts/arxiv_figures.py <arxiv_id> --all -o <output_dir>

# Download all, default output path
python <skill-dir>/scripts/arxiv_figures.py <arxiv_id> --all
```

Default output directory: `outputs/figures/<arxiv_id>/figures/`

The script saves:
- Image files named like `fig1_overview_of_framework.png`
- Multi-panel figures split as `fig3_results_a.png`, `fig3_results_b.png`, etc.
- `captions.json` with metadata for each downloaded figure

### Step 4: Present results

After downloading, show the user what was saved. If they want to use specific figures in other workflows (slides, blog posts, documents), tell them the file paths and read the relevant images to show them.

## Output structure

```
outputs/figures/<arxiv_id>/figures/
├── fig1_overview.png
├── fig2_architecture.png
├── fig3_results_a.png          # multi-panel figure, panel (a)
├── fig3_results_b.png          # multi-panel figure, panel (b)
└── captions.json
```

### captions.json format

```json
{
  "fig1_overview": {
    "file": "fig1_overview.png",
    "label": "Figure 1",
    "caption": "Full caption text from the paper"
  },
  "fig3_results": {
    "files": ["fig3_results_a.png", "fig3_results_b.png"],
    "label": "Figure 3",
    "caption": "Full caption text..."
  }
}
```

## Cross-workflow integration

When the user wants to use extracted figures in other tasks:

1. Check if figures were already downloaded by looking for `outputs/figures/<arxiv_id>/figures/captions.json`
2. If found, read `captions.json` to find the right figure by caption/label
3. Reference the file path directly — no need to re-download

**Example**: If the user says "use the architecture diagram from paper 2406.11434 in my slides", first check if `outputs/figures/2406_11434/figures/captions.json` exists. If so, find the figure whose caption mentions "architecture" and use that file path.

## Troubleshooting

- **"HTML not available"**: Not all arXiv papers have HTML versions. Older papers or those with complex LaTeX may not be rendered. There's no workaround in this skill — the paper simply needs to have an HTML version on arXiv.
- **Rate limiting (429)**: The script retries automatically with backoff. If it persists, wait a minute and try again.
- **Missing figures**: Some figures are generated purely from TikZ/PGF code in LaTeX and have no raster images — these won't appear in the HTML.
- **No figures found**: The paper may use non-standard figure environments, or may be a very short paper with no figures.
