#!/usr/bin/env python3
"""Create one unique, old-school Wiki2 article from Wikimedia's public APIs.

The script is safe to run repeatedly. It never overwrites an existing article,
records generated topics in .wiki-generated.json, and can run once or forever.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
ARTICLES = ROOT / "articles"
LEDGER = ROOT / ".wiki-generated.json"
USER_AGENT = "Wiki2-Automated-Encyclopedia/1.0 (https://github.com/recgoblingu-lgtm/Wiki2)"
API = "https://en.wikipedia.org/w/api.php"
REST = "https://en.wikipedia.org/api/rest_v1/page/summary/"

# Starter topics provide predictable first runs. Once they are used, the
# selector falls through to Wikimedia's large, changing main-namespace corpus.
TOPICS: list[tuple[str, str]] = [
    ("Geography", x) for x in ["United States", "Canada", "Brazil", "Japan", "India", "Australia", "Egypt", "Alps", "Amazon rainforest", "Pacific Ocean", "Sahara", "Nile", "New York City", "London", "Tokyo", "Machu Picchu"]
] + [
    ("Technology", x) for x in ["Computer", "Internet", "World Wide Web", "Artificial intelligence", "Operating system", "Programming language", "Database", "Microprocessor", "Electric battery", "Robotics", "Cryptography", "Open-source software", "Solar power", "Telecommunications"]
] + [
    ("Science", x) for x in ["Astronomy", "Physics", "Chemistry", "Biology", "Evolution", "Genetics", "Climate", "Earth", "Moon", "Mars", "Mammal", "Photosynthesis", "Mathematics", "Scientific method", "Plate tectonics"]
] + [
    ("History", x) for x in ["Ancient Egypt", "Roman Empire", "Silk Road", "Industrial Revolution", "Renaissance", "World War I", "World War II", "Printing press", "Democracy", "United Nations", "Apollo program", "History of China", "History of Japan"]
] + [
    ("Games and culture", x) for x in ["Chess", "Go (game)", "Video game", "Tabletop game", "Olympic Games", "Theatre", "Music", "Film", "Literature", "Photography", "Architecture", "Cooking"]
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(title: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_")
    return value or "Article"


def load_ledger() -> dict[str, Any]:
    if not LEDGER.exists():
        return {"version": 1, "articles": []}
    try:
        data = json.loads(LEDGER.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("articles"), list):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"version": 1, "articles": []}


def save_ledger(data: dict[str, Any]) -> None:
    LEDGER.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def get_json(url: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    response = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    return response.json()


def acceptable_title(title: str) -> bool:
    # Avoid namespace pages, list pages, and date-only pages that do not read
    # like ordinary encyclopedia entries.
    return ":" not in title and not title.casefold().startswith(("list of ", "outline of ")) and not re.fullmatch(r"[0-9 -]+", title)


def choose_topic(ledger: dict[str, Any]) -> tuple[str, str, dict[str, Any]] | None:
    used_titles = {str(item.get("title", "")).casefold() for item in ledger["articles"]}
    used_files = {str(item.get("filename", "")) for item in ledger["articles"]}

    # Use the curated seeds first, then keep discovering pages dynamically.
    candidates = list(TOPICS) if len(ledger["articles"]) < len(TOPICS) else []
    for category, requested in candidates:
        if requested.casefold() in used_titles:
            continue
        try:
            summary = get_json(REST + quote(requested, safe=""))
        except requests.RequestException:
            continue
        title = str(summary.get("title") or requested)
        filename = slugify(title) + ".html"
        if title.casefold() in used_titles or filename in used_files or (ARTICLES / filename).exists():
            continue
        if summary.get("type") == "disambiguation" or not summary.get("extract") or not acceptable_title(title):
            continue
        return category, title, summary

    category_order = ["Technology", "Science", "Geography", "History", "Games and culture"]
    start = len(ledger["articles"]) % len(category_order)
    for offset in range(len(category_order)):
        category = category_order[(start + offset) % len(category_order)]
        try:
            data = get_json(API, {"action": "query", "generator": "random", "grnnamespace": "0", "grnlimit": "25", "prop": "info", "inprop": "url", "format": "json", "formatversion": "2"})
        except requests.RequestException:
            continue
        pages = data.get("query", {}).get("pages", [])
        for page in pages:
            title = str(page.get("title", "")).strip()
            if not title or not acceptable_title(title) or title.casefold() in used_titles:
                continue
            filename = slugify(title) + ".html"
            if filename in used_files or (ARTICLES / filename).exists():
                continue
            try:
                summary = get_json(REST + quote(title, safe=""))
            except requests.RequestException:
                continue
            if summary.get("type") == "disambiguation" or len(str(summary.get("extract", ""))) < 180:
                continue
            return category, title, summary
    return None


def clean_text(fragment: str) -> str:
    soup = BeautifulSoup(fragment, "html.parser")
    for node in soup(["script", "style", "table", "sup"]):
        node.decompose()
    return " ".join(soup.get_text(" ").split())


def source_sections(title: str) -> list[tuple[str, str]]:
    """Extract a small number of factual sections from Wikimedia's article HTML."""
    try:
        data = get_json(API, {"action": "parse", "page": title, "prop": "text|sections", "format": "json", "formatversion": "2"})
        parsed = data.get("parse", {})
        rendered = parsed.get("text", {}).get("*", "") if isinstance(parsed.get("text"), dict) else parsed.get("text", "")
        soup = BeautifulSoup(rendered or "", "html.parser")
        for node in soup(["script", "style", "table", "sup", "figure", "math"]):
            node.decompose()
        sections: list[tuple[str, str]] = []
        current = "Background"
        paragraphs: list[str] = []
        excluded_headings = {"see also", "references", "external links", "notes", "further reading", "contents"}
        for node in soup.find_all(["h2", "h3", "p"]):
            if node.name in {"h2", "h3"}:
                if paragraphs and current.casefold() not in excluded_headings:
                    text = clean_text(" ".join(paragraphs))
                    if len(text) >= 80:
                        sections.append((current, text[:1400]))
                current = clean_text(str(node)) or "Background"
                paragraphs = []
            else:
                text = clean_text(str(node))
                if text:
                    paragraphs.append(text)
        if paragraphs and current.casefold() not in excluded_headings:
            text = clean_text(" ".join(paragraphs))
            if len(text) >= 80:
                sections.append((current, text[:1400]))
        return sections[:4]
    except (requests.RequestException, ValueError):
        return []


def related_links(ledger: dict[str, Any], current_title: str) -> list[tuple[str, str]]:
    candidates = [item for item in ledger["articles"] if str(item.get("title", "")).casefold() != current_title.casefold()]
    return [(str(item["title"]), str(item["filename"])) for item in candidates[-5:]][::-1]


def render_article(category: str, title: str, summary: dict[str, Any], ledger: dict[str, Any]) -> str:
    edited = datetime.now().strftime("%B %-d, %Y")
    overview = clean_text(str(summary["extract"]))
    sections = source_sections(title)
    if not sections:
        sections = [("Background", overview), ("Importance", f"{title} is catalogued in Wiki2 under the {category} category and is connected to broader subjects in that field.")]
    links = related_links(ledger, title)
    see_also = "\n".join(f'      <li><a href="{html.escape(filename)}">{html.escape(name)}</a></li>' for name, filename in links)
    if not see_also:
        see_also = '      <li><a href="../index.html">Wiki2 main page</a></li>'
    body_sections = []
    for heading, text in sections:
        body_sections.append(f"    <hr>\n    <h2>{html.escape(heading)}</h2>\n    <p>{html.escape(text)}</p>")
    source_url = str(summary.get("content_urls", {}).get("desktop", {}).get("page", ""))
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{html.escape(title)} - Wiki2</title>
  <link rel="stylesheet" href="../style.css">
</head>
<body>
<div class="container">
  <div class="sidebar">
    <h2>Wiki2</h2>
    <a href="../index.html">Main Page</a>
    <a href="../article.html">Random Page</a>
    <a href="../index.html#categories">Categories</a>
  </div>
  <div class="content">
    <h1>{html.escape(title)}</h1>
    <p><b>{html.escape(title)}</b> is an encyclopedia entry in the <b>{html.escape(category)}</b> collection.</p>
    <p>{html.escape(overview)}</p>
{chr(10).join(body_sections)}
    <hr>
    <h2>See also</h2>
    <ul>
{see_also}
    </ul>
    <hr>
    <p><small>Source reference: <a href="{html.escape(source_url)}">Wikimedia article</a></small></p>
    <p><i>Last edited: {edited}</i></p>
  </div>
</div>
</body>
</html>
'''


def update_index(ledger: dict[str, Any]) -> None:
    rows = []
    for category in sorted({str(item.get("category", "Other")) for item in ledger["articles"]}):
        entries = [item for item in ledger["articles"] if item.get("category") == category]
        links = "\n".join(f'      <li><a href="articles/{html.escape(str(item["filename"]))}">{html.escape(str(item["title"]))}</a></li>' for item in entries)
        rows.append(f"    <h3>{html.escape(category)}</h3>\n    <ul>\n{links}\n    </ul>")
    listing = "\n".join(rows) or "    <p>No articles have been generated yet.</p>"
    INDEX = ROOT / "index.html"
    INDEX.write_text(f'''<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Wiki2</title><link rel="stylesheet" href="style.css"></head>
<body><div class="container"><div class="sidebar"><h2>Wiki2</h2><a href="index.html">Main Page</a><a href="article.html">Random Page</a><a href="#categories">Categories</a></div>
<div class="content"><h1>Welcome to Wiki2</h1><p>This is an automatically growing, old-school encyclopedia of real-world topics.</p><p>Articles currently indexed: <b>{len(ledger["articles"])}</b></p><hr><h2 id="categories">Article index</h2>{listing}</div></div></body></html>
''', encoding="utf-8")


def generate_once() -> bool:
    ARTICLES.mkdir(exist_ok=True)
    ledger = load_ledger()
    selected = choose_topic(ledger)
    if not selected:
        print("No unused topic is currently available or Wikimedia is unavailable.")
        return False
    category, title, summary = selected
    filename = slugify(title) + ".html"
    destination = ARTICLES / filename
    if destination.exists():
        print(f"Refusing to overwrite existing file: {destination}")
        return False
    destination.write_text(render_article(category, title, summary, ledger), encoding="utf-8")
    ledger["articles"].append({"title": title, "filename": filename, "category": category, "source": summary.get("content_urls", {}).get("desktop", {}).get("page", ""), "generated_at": now_iso()})
    save_ledger(ledger)
    update_index(ledger)
    print(f"Created {destination.relative_to(ROOT)} for topic {title!r}.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Create one article and exit (default).")
    parser.add_argument("--forever", action="store_true", help="Keep creating articles at the configured interval.")
    parser.add_argument("--interval", type=int, default=1800, help="Seconds between articles in --forever mode (default: 1800).")
    args = parser.parse_args()
    if args.forever:
        while True:
            try:
                generate_once()
            except Exception as exc:  # keep an unattended process alive after transient failures
                print(f"Transient generation error: {exc}", file=sys.stderr)
            time.sleep(max(60, args.interval))
    return 0 if generate_once() or args.once else 1


if __name__ == "__main__":
    raise SystemExit(main())

