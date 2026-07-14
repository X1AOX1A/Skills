#!/usr/bin/env python3
"""Fetch candidate papers for daily recommendation.

Sources:
  - arXiv (default category cs.CL), including NEW submissions and CROSS-listed papers.
      * "latest" mode uses the arXiv RSS feed (has abstracts + announce_type new/cross).
      * a specific --date or --days range uses the arXiv API (submittedDate range query).
  - HuggingFace daily papers via the `hf` CLI (id + title + upvotes), used as a
    trending signal and to surface topically-relevant papers beyond the arXiv category.
    Abstracts for HF-only papers are back-filled in one batched arXiv API call so the
    downstream topic matching needs no other tool or script.

Output: a single JSON object written to stdout (or -o FILE) that the skill reads.
Only Python stdlib + optional `hf` CLI — no third-party deps, no external scripts.

Examples:
  python3 fetch_papers.py                          # latest cs.CL (new+cross) + HF today
  python3 fetch_papers.py --date 2026-07-13
  python3 fetch_papers.py --days 3                 # last 3 days via arXiv API
  python3 fetch_papers.py --category cs.LG --no-hf
  python3 fetch_papers.py --include-replaced -o /tmp/papers.json
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "http://arxiv.org/schemas/atom"
DC_NS = "http://purl.org/dc/elements/1.1/"
UA = "paper-suggestions/1.0 (+https://arxiv.org)"


def _get(url, timeout=40, retries=4):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = e
            # arXiv rate-limits (429) and asks for >=3s between requests — back off harder.
            time.sleep((10 if e.code == 429 else 4) * (attempt + 1))
        except Exception as e:  # transient timeouts / connection resets
            last = e
            time.sleep(3 * (attempt + 1))
    raise last


def _clean(s):
    return " ".join((s or "").split())


def _rss_date_to_iso(build_date):
    """'Mon, 13 Jul 2026 04:00:01 +0000' -> '2026-07-13' (None on failure)."""
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S"):
        try:
            return dt.datetime.strptime(build_date.strip(), fmt).date().isoformat()
        except (ValueError, AttributeError):
            continue
    return None


def _bare_id(raw):
    """Normalize an arxiv id/url to bare id without version, e.g. 2607.09600."""
    raw = (raw or "").strip()
    if "/abs/" in raw:
        raw = raw.split("/abs/")[-1]
    raw = raw.rstrip("/").split("/")[-1]
    if raw.startswith("arXiv:"):
        raw = raw[len("arXiv:"):]
    if "v" in raw and raw.rsplit("v", 1)[-1].isdigit():
        raw = raw.rsplit("v", 1)[0]
    return raw


# ---------------------------------------------------------------- arXiv RSS
def fetch_arxiv_rss(category, include_replaced):
    """Latest announcement batch for a category (has abstracts + announce_type)."""
    url = f"https://rss.arxiv.org/rss/{category}"
    root = ET.fromstring(_get(url))
    channel = root.find("channel")
    build_date = _clean(channel.findtext("lastBuildDate"))
    ns = {"arxiv": ARXIV_NS, "dc": DC_NS}
    keep = {"new", "cross"} | ({"replace", "replace-cross"} if include_replaced else set())
    papers = []
    for item in channel.findall("item"):
        atype = item.findtext("arxiv:announce_type", default="", namespaces=ns)
        if atype not in keep:
            continue
        desc = item.findtext("description") or ""
        # RSS description = "arXiv:ID Announce Type: X \n Abstract: ..."
        abstract = desc.split("Abstract:", 1)[-1] if "Abstract:" in desc else desc
        cats = [c.text for c in item.findall("category")]
        papers.append({
            "id": _bare_id(item.findtext("link")),
            "title": _clean(item.findtext("title")),
            "abstract": _clean(abstract),
            "authors": _clean(item.findtext("dc:creator", default="", namespaces=ns)),
            "categories": cats,
            "primary_category": cats[0] if cats else category,
            "announce_type": atype,
            "url": _clean(item.findtext("link")),
        })
    return build_date, papers


# ---------------------------------------------------------------- arXiv API
def fetch_arxiv_api(category, start, end, include_replaced, max_results=400):
    """Papers in [start, end] date range via the arXiv API (arbitrary dates)."""
    lo = start.strftime("%Y%m%d0000")
    hi = end.strftime("%Y%m%d2359")
    q = f"cat:{category} AND submittedDate:[{lo} TO {hi}]"
    params = urllib.parse.urlencode({
        "search_query": q,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    })
    url = f"http://export.arxiv.org/api/query?{params}"
    root = ET.fromstring(_get(url))
    papers = []
    for e in root.findall(f"{ATOM}entry"):
        cats = [c.get("term") for c in e.findall(f"{ATOM}category")]
        prim_el = e.find(f"{{{ARXIV_NS}}}primary_category")
        prim = prim_el.get("term") if prim_el is not None else (cats[0] if cats else category)
        authors = ", ".join(_clean(a.findtext(f"{ATOM}name")) for a in e.findall(f"{ATOM}author"))
        papers.append({
            "id": _bare_id(e.findtext(f"{ATOM}id")),
            "title": _clean(e.findtext(f"{ATOM}title")),
            "abstract": _clean(e.findtext(f"{ATOM}summary")),
            "authors": authors,
            "categories": cats,
            "primary_category": prim,
            # API can't distinguish new vs cross cheaply; label by primary category
            "announce_type": "new" if prim == category else "cross",
            "url": f"https://arxiv.org/abs/{_bare_id(e.findtext(f'{ATOM}id'))}",
            "published": _clean(e.findtext(f"{ATOM}published")),
        })
    if not include_replaced:
        return papers
    return papers


# ---------------------------------------------------------------- arXiv id_list
def fetch_arxiv_by_ids(ids):
    """Batch-fetch abstracts/authors/categories for specific ids in one API call.
    Returns {bare_id: {abstract, authors, categories, primary_category, title}}."""
    ids = [_bare_id(i) for i in ids if i]
    if not ids:
        return {}
    params = urllib.parse.urlencode({"id_list": ",".join(ids), "max_results": len(ids)})
    url = f"http://export.arxiv.org/api/query?{params}"
    out = {}
    try:
        root = ET.fromstring(_get(url))
    except Exception:
        return out
    for e in root.findall(f"{ATOM}entry"):
        bid = _bare_id(e.findtext(f"{ATOM}id"))
        cats = [c.get("term") for c in e.findall(f"{ATOM}category")]
        prim_el = e.find(f"{{{ARXIV_NS}}}primary_category")
        prim = prim_el.get("term") if prim_el is not None else (cats[0] if cats else None)
        out[bid] = {
            "title": _clean(e.findtext(f"{ATOM}title")),
            "abstract": _clean(e.findtext(f"{ATOM}summary")),
            "authors": ", ".join(_clean(a.findtext(f"{ATOM}name")) for a in e.findall(f"{ATOM}author")),
            "categories": cats,
            "primary_category": prim,
        }
    return out


# ---------------------------------------------------------------- HF papers
def fetch_hf(date_str):
    """HF daily papers for a date: list of {id, title, upvotes}. Empty if hf missing."""
    try:
        out = subprocess.run(
            ["hf", "papers", "list", "--date", date_str, "--format", "json", "--limit", "100"],
            capture_output=True, text=True, timeout=60,
        )
        if out.returncode != 0 or not out.stdout.strip():
            return None
        data = json.loads(out.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None
    rows = data if isinstance(data, list) else data.get("papers", data.get("data", []))
    papers = []
    for p in rows:
        pid = p.get("id") or p.get("paper", {}).get("id") or p.get("arxiv_id")
        if not pid:
            continue
        papers.append({
            "id": _bare_id(pid),
            "title": _clean(p.get("title") or p.get("paper", {}).get("title", "")),
            "upvotes": p.get("upvotes") or p.get("paper", {}).get("upvotes") or 0,
            "url": f"https://arxiv.org/abs/{_bare_id(pid)}",
        })
    return papers


def main():
    ap = argparse.ArgumentParser(description="Fetch candidate papers for daily recommendation.")
    ap.add_argument("--category", default="cs.CL", help="arXiv category (default cs.CL)")
    ap.add_argument("--date", help="Specific day YYYY-MM-DD (uses arXiv API). Omit = latest RSS batch.")
    ap.add_argument("--days", type=int, help="Last N days ending today (uses arXiv API).")
    ap.add_argument("--include-replaced", action="store_true", help="Also include replaced/updated papers.")
    ap.add_argument("--no-hf", action="store_true", help="Skip HuggingFace papers.")
    ap.add_argument("--no-hf-abstracts", action="store_true",
                    help="Don't fetch abstracts for HF-only papers (faster, but titles only).")
    ap.add_argument("-o", "--output", help="Write JSON to this exact FILE (default stdout).")
    ap.add_argument("--out-dir", help="Write JSON to <DIR>/candidates-<batch-date>.json "
                                      "(filename carries the resolved date). Overrides -o.")
    args = ap.parse_args()

    result = {"category": args.category, "arxiv": [], "hf_only": [], "notes": []}

    # ---- arXiv ----
    if args.date or args.days:
        today = dt.date.today()
        if args.days:
            start = today - dt.timedelta(days=args.days - 1)
            end = today
            result["range"] = {"mode": "api", "start": start.isoformat(), "end": end.isoformat()}
            date_token = f"{start.isoformat()}_{end.isoformat()}"
        else:
            d = dt.date.fromisoformat(args.date)
            start = end = d
            result["range"] = {"mode": "api", "date": d.isoformat()}
            date_token = d.isoformat()
        arxiv_papers = fetch_arxiv_api(args.category, start, end, args.include_replaced)
        hf_date = (args.date if args.date else today.isoformat())
    else:
        build_date, arxiv_papers = fetch_arxiv_rss(args.category, args.include_replaced)
        result["range"] = {"mode": "rss", "build_date": build_date}
        # Align the HF query with the RSS announcement date, not wall-clock today
        # (the latest RSS batch is usually the previous business day).
        hf_date = _rss_date_to_iso(build_date) or dt.date.today().isoformat()
        date_token = hf_date
    # The resolved batch/range date — used for the digest filename AND the candidates filename
    # so runs never get mixed up across days.
    result["date_token"] = date_token
    result["arxiv"] = arxiv_papers

    # ---- HF ----
    if not args.no_hf:
        hf = fetch_hf(hf_date)
        if hf is None:
            result["notes"].append("HF papers unavailable (hf CLI missing or failed).")
        else:
            arxiv_ids = {p["id"] for p in arxiv_papers}
            up = {p["id"]: p["upvotes"] for p in hf}
            for p in arxiv_papers:
                if p["id"] in up:
                    p["hf_upvotes"] = up[p["id"]]
            result["hf_only"] = [p for p in hf if p["id"] not in arxiv_ids]
            result["hf_date"] = hf_date
            # Enrich HF-only papers with abstracts (one batched arXiv API call) so
            # topic matching can run fully offline without any external script.
            if result["hf_only"] and not args.no_hf_abstracts:
                meta = fetch_arxiv_by_ids([p["id"] for p in result["hf_only"]])
                for p in result["hf_only"]:
                    m = meta.get(p["id"])
                    if m:
                        p["abstract"] = m["abstract"]
                        p["authors"] = m["authors"]
                        p["categories"] = m["categories"]
                        p["primary_category"] = m["primary_category"]
                miss = sum(1 for p in result["hf_only"] if not p.get("abstract"))
                if miss:
                    result["notes"].append(f"{miss} HF-only paper(s) had no arXiv abstract.")

    result["counts"] = {
        "arxiv": len(result["arxiv"]),
        "arxiv_new": sum(1 for p in result["arxiv"] if p.get("announce_type") == "new"),
        "arxiv_cross": sum(1 for p in result["arxiv"] if p.get("announce_type") == "cross"),
        "hf_only": len(result["hf_only"]),
    }

    payload = json.dumps(result, ensure_ascii=False, indent=2)
    dest = None
    if args.out_dir:
        os.makedirs(os.path.expanduser(args.out_dir), exist_ok=True)
        dest = os.path.join(os.path.expanduser(args.out_dir), f"candidates-{date_token}.json")
    elif args.output:
        dest = args.output
    if dest:
        with open(dest, "w", encoding="utf-8") as f:
            f.write(payload)
        # Print the final path on its own line so the caller can capture it reliably.
        print(dest)
        print(f"Wrote {result['counts']} (batch {date_token}) to {dest}")
    else:
        print(payload)


if __name__ == "__main__":
    main()
