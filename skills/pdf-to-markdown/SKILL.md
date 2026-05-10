---
name: pdf-to-markdown
description: |
  Convert PDF files to Markdown using pymupdf4llm.
  TRIGGER when: user asks to convert a PDF to markdown, extract text from PDF,
  or read/parse a PDF into markdown format.
  DO NOT TRIGGER when: user just wants to read an existing paper.md or work with already-converted files.
---

# PDF to Markdown Converter

Converts PDF files to clean Markdown using [pymupdf4llm](https://github.com/pymupdf/pymupdf4llm).

## Prerequisites

- Python environment with pymupdf4llm installed:

  ```bash
  pip3 install -U pymupdf4llm
  ```

## Usage

```bash
python3 scripts/pdf2md.py -i input.pdf -o output.md
```

## Figure Extraction

By default, embedded images are extracted into a `figures/` folder next to the
output markdown, and references in the md use the portable `figures/xxx.png`
form regardless of how pymupdf4llm internally names them.

Options:

- `--no-figures` — disable image extraction
- `--figures-dir DIR` — folder name relative to the md (default: `figures`)
- `--image-format {png,jpg}` — output image format (default: `png`)
- `--dpi N` — image rendering DPI (default: `200`)

Example:

```bash
python3 scripts/pdf2md.py -i paper.pdf --figures-dir assets --image-format jpg --dpi 300
```

## When to Use This Skill

Use when the user says things like:
- "Convert this PDF to markdown"
- "Extract text from this PDF"
- "Turn this PDF into markdown"
- "Parse this PDF"