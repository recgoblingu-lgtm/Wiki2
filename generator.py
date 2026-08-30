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

REVIVAL_SOURCE = "https://recroom-standalone.neocities.org/"
REVIVAL_TOPICS: list[str] = [
    "Radium", "Vanilla", "RecLora", "LunarNet", "NexaNet", "Nexiom", "N3XI0M",
    "MeowNet", "Emerald", "Krypton", "PrismNet", "Deluxe Rec", "BlueRoom", "RicoRec",
    "RecPlace", "RecUni", "Vortex Rec", "Stella", "Requiem", "RugRoom", "Crimson",
    "RestoRoom", "TavernTale", "AndGravity", "Yanvar", "Kekora", "Plutonium", "RecSample",
    "Act2.games", "DocNet", "10 Whole Years", "RebornRec",
]

REVIVAL_DESCRIPTIONS: dict[str, str] = {
    "RebornRec": "RebornRec is a publicly documented, locally hosted server project for preserving older Rec Room builds from approximately 2016 through 2020. Its public repository describes server emulation features and notes that it is an independent project rather than an official Rec Room product.",
    "Act2.games": "Act2.games is listed by a public Rec Room build directory as a web-based project for playing older Rec Room maps, games, CV2 content, and avatars. It is presented as a community preservation utility and is not affiliated with Rec Room.",
}

CATEGORY_SOURCES: list[tuple[str, str]] = [
    ("Game franchises", "Category:Video game franchises"),
    ("Indie games", "Category:Indie games"),
    ("Game engines", "Category:Video game engines"),
    ("Platforms", "Category:Video game platforms"),
    ("Streaming services", "Category:Streaming media systems"),
    ("Esports titles", "Category:Esports games"),
    ("Classic games", "Category:Arcade video games"),
    ("Mobile games", "Category:Mobile games"),
    ("Horror games", "Category:Horror video games"),
    ("Sandbox games", "Category:Sandbox games"),
]

# Starter topics provide predictable first runs. Once they are used, the
# selector falls through to Wikimedia's large, changing main-namespace corpus.
TOPICS: list[tuple[str, str]] = [
    ("Games", x) for x in [
        "Minecraft", "Roblox", "Fortnite", "Rec Room", "Rec Room Revivals", "Call of Duty",
        "Grand Theft Auto V", "Grand Theft Auto: San Andreas", "Terraria", "Stardew Valley", "Among Us",
        "Rocket League", "Valorant", "League of Legends", "Dota 2", "Counter-Strike 2", "Counter-Strike: Global Offensive",
        "Team Fortress 2", "Apex Legends", "Overwatch", "Overwatch 2", "The Legend of Zelda",
        "The Legend of Zelda: Breath of the Wild", "The Legend of Zelda: Tears of the Kingdom", "Super Mario Bros.",
        "Super Mario Odyssey", "Mario Kart", "Pokémon Red and Blue", "Pokémon Scarlet and Violet", "Pokémon Go",
        "Kirby (series)", "Elden Ring", "Dark Souls", "Bloodborne", "Sekiro: Shadows Die Twice", "The Elder Scrolls V: Skyrim",
        "Fallout 4", "Fallout: New Vegas", "The Witcher 3: Wild Hunt", "Cyberpunk 2077", "Red Dead Redemption 2",
        "Halo (franchise)", "Halo Infinite", "Destiny 2", "Warframe", "Battlefield 2042", "Rust", "DayZ",
        "ARK: Survival Evolved", "Dead by Daylight", "Phasmophobia", "The Sims 4", "SimCity", "Civilization VI",
        "Age of Empires II", "Cities: Skylines", "RollerCoaster Tycoon", "Factorio", "Minecraft Dungeons", "Hades",
        "Hollow Knight", "Hollow Knight: Silksong", "Cuphead", "Undertale", "Deltarune", "Celeste", "Dead Cells",
        "Ori and the Blind Forest", "Ori and the Will of the Wisps", "Limbo", "Inside"
    ]
] + [
    ("Media and platforms", x) for x in [
        "YouTube", "Twitch", "Netflix", "Disney+", "Hulu", "Amazon Prime Video", "HBO Max", "Spotify",
        "SoundCloud", "TikTok", "Discord", "Steam", "Epic Games Store", "PlayStation Network", "Xbox network",
        "Nintendo eShop", "Roblox Studio", "Unreal Engine", "Unity (game engine)", "Blender (software)"
    ]
] + [
    ("Movies, series, and culture", x) for x in [
        "Minecraft (film)", "The Super Mario Bros. Movie", "Avengers: Endgame", "Spider-Man: No Way Home",
        "Star Wars", "Star Wars: The Clone Wars", "The Mandalorian", "Stranger Things", "Breaking Bad", "The Office"
    ]
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


def revival_summary(title: str) -> dict[str, Any]:
    description = REVIVAL_DESCRIPTIONS.get(
        title,
        f"{title} is a community-listed Rec Room revival or preservation project. Public revival directories organize projects like this by the era of Rec Room builds they seek to preserve. Availability, features, and maintenance status may change over time, and the project should not be confused with an official Rec Room product.",
    )
    return {
        "title": title,
        "extract": description,
        "type": "standard",
        "content_urls": {"desktop": {"page": REVIVAL_SOURCE}},
    }


def choose_topic(ledger: dict[str, Any]) -> tuple[str, str, dict[str, Any]] | None:
    used_titles = {str(item.get("title", "")).casefold() for item in ledger["articles"]}
    used_files = {str(item.get("filename", "")) for item in ledger["articles"]}

    # Prioritize the researched Rec Room revival catalog so each community
    # project receives its own clearly labeled Wiki2 page.
    for requested in REVIVAL_TOPICS:
        if requested.casefold() in used_titles:
            continue
        filename = slugify(requested) + ".html"
        if filename in used_files or (ARTICLES / filename).exists():
            continue
        return "Rec Room revivals", requested, revival_summary(requested)

    # Use a short curated starter sample, then rotate through the requested
    # Wikimedia categories. The full curated list remains available as a
    # fallback source without delaying category discovery for many runs.
    candidates = list(TOPICS) if len(ledger["articles"]) < 10 else []
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

    # Walk the requested Wikimedia categories. The continuation token is
    # persisted in the ledger so successive runs move through each category
    # instead of repeatedly seeing the same first page of results.
    cursors = ledger.setdefault("category_cursors", {})
    start = len(ledger["articles"]) % len(CATEGORY_SOURCES)
    for offset in range(len(CATEGORY_SOURCES)):
        category, category_page = CATEGORY_SOURCES[(start + offset) % len(CATEGORY_SOURCES)]
        params = {"action": "query", "list": "categorymembers", "cmtitle": category_page, "cmnamespace": "0|14", "cmtype": "page|subcat", "cmlimit": "100", "format": "json", "formatversion": "2"}
        if cursors.get(category_page):
            params["cmcontinue"] = str(cursors[category_page])
        try:
            data = get_json(API, params)
        except requests.RequestException:
            continue
        if data.get("continue", {}).get("cmcontinue"):
            cursors[category_page] = data["continue"]["cmcontinue"]
        else:
            cursors.pop(category_page, None)
        pages = list(data.get("query", {}).get("categorymembers", []))
        # Include one level of subcategories so broad category pages with few
        # direct articles still provide a deep, varied topic stream.
        for subcat in [p for p in pages if str(p.get("title", "")).startswith("Category:")][:12]:
            try:
                nested = get_json(API, {"action": "query", "list": "categorymembers", "cmtitle": subcat["title"], "cmnamespace": "0", "cmtype": "page", "cmlimit": "50", "format": "json", "formatversion": "2"})
                pages.extend(nested.get("query", {}).get("categorymembers", []))
            except requests.RequestException:
                continue
        for page in pages:
            title = str(page.get("title", "")).strip()
            if not title or title.startswith("Category:") or not acceptable_title(title) or title.casefold() in used_titles:
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
            save_ledger(ledger)
            return category, title, summary
        save_ledger(ledger)

    # Wikimedia's random main-namespace generator keeps the system productive
    # after a category has been traversed and also supplies occasional topics
    # that belong to more than one category.
    for _ in range(5):
        try:
            data = get_json(API, {"action": "query", "generator": "random", "grnnamespace": "0", "grnlimit": "25", "prop": "info", "inprop": "url", "format": "json", "formatversion": "2"})
        except requests.RequestException:
            continue
        for page in data.get("query", {}).get("pages", []):
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
            return "Wikimedia discovery", title, summary
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


def related_images(title: str) -> list[dict[str, str]]:
    try:
        data = get_json(API, {"action": "query", "titles": title, "prop": "pageimages|images", "imlimit": "10", "piprop": "original", "format": "json", "formatversion": "2"})
    except requests.RequestException:
        return []
    images: list[dict[str, str]] = []
    for page in data.get("query", {}).get("pages", []):
        original = page.get("original", {})
        if original.get("source"):
            images.append({"url": str(original["source"]), "alt": title})
        for image in page.get("images", []):
            name = str(image.get("title", ""))
            if not name or name.casefold().endswith((".svg", ".ogv", ".webm")):
                continue
            try:
                info = get_json(API, {"action": "query", "titles": name, "prop": "imageinfo", "iiprop": "url", "iiurlwidth": "900", "format": "json", "formatversion": "2"})
            except requests.RequestException:
                continue
            for image_page in info.get("query", {}).get("pages", []):
                imageinfo = (image_page.get("imageinfo") or [{}])[0]
                source = imageinfo.get("thumburl") or imageinfo.get("url")
                if source:
                    images.append({"url": str(source), "alt": name.removeprefix("File:")})
                    break
            if len(images) >= 3:
                break
        if len(images) >= 3:
            break
    unique: list[dict[str, str]] = []
    seen: set[str] = set()
    for image in images:
        if image["url"] not in seen:
            unique.append(image)
            seen.add(image["url"])
    return unique[:3]


def render_article(category: str, title: str, summary: dict[str, Any], ledger: dict[str, Any]) -> str:
    edited = datetime.now().strftime("%B %-d, %Y")
    overview = clean_text(str(summary["extract"]))
    sections = source_sections(title)
    if not sections:
        sections = [("Background", overview), ("Importance", f"{title} is catalogued in Wiki2 under the {category} category and is connected to broader subjects in that field.")]
    links = related_links(ledger, title)
    images = related_images(title)
    image_markup = "\n".join(f'    <figure class="article-image"><img src="{html.escape(image["url"])}" alt="{html.escape(image["alt"])}"><figcaption>Related Wikimedia image</figcaption></figure>' for image in images)
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
{image_markup}
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
<div class="content"><h1>Welcome to Wiki2</h1><p>This is an automatically growing, old-school encyclopedia of real-world topics.</p><p>Total pages indexed: <b>{len(ledger["articles"])}</b></p><hr><h2 id="categories">Article index</h2>{listing}</div></div></body></html>
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


def generate_batch(target: int) -> int:
    created = 0
    for _ in range(max(1, target)):
        try:
            if not generate_once():
                break
            created += 1
        except Exception as exc:
            print(f"Skipping one topic after transient error: {exc}", file=sys.stderr)
    return created


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Create one article and exit (default).")
    parser.add_argument("--forever", action="store_true", help="Keep creating articles at the configured interval.")
    parser.add_argument("--interval", type=int, default=1800, help="Seconds between articles in --forever mode (default: 1800).")
    parser.add_argument("--batch", type=int, default=0, help="Create up to this many articles, then exit.")
    args = parser.parse_args()
    if args.batch:
        created = generate_batch(args.batch)
        return 0 if created > 0 else 1
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

