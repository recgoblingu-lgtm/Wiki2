#!/usr/bin/env python3
from __future__ import annotations

import html
import json
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "wiki2ube"
VIDEOS = BASE / "videos"

VIDEO_CATALOG = [
    {
        "id": "wiki2-intro",
        "title": "Welcome to Wiki2",
        "description": "A short introduction to the automatically growing old-school encyclopedia.",
        "category": "Wiki2 original",
        "duration": "01:12",
        "date": "2026-08-31",
        "poster": "https://dummyimage.com/640x360/e8e8e8/222.png&text=Welcome+to+Wiki2",
        "src": "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
    },
    {
        "id": "history-writing-system",
        "title": "Writing Systems: An Encyclopedia Preview",
        "description": "A catalog preview for the history entries being added to Wiki2.",
        "category": "History",
        "duration": "00:45",
        "date": "2026-08-31",
        "poster": "https://dummyimage.com/640x360/e8e8e8/222.png&text=Writing+Systems",
        "src": "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
    },
    {
        "id": "wiki2-old-school-html",
        "title": "How Wiki2 Articles Are Built",
        "description": "A visual tour of the serif typography, borders, sidebars, and source-backed pages used by Wiki2.",
        "category": "Technology",
        "duration": "01:30",
        "date": "2026-08-31",
        "poster": "https://dummyimage.com/640x360/e8e8e8/222.png&text=Old-School+HTML",
        "src": "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
    },
]


def page(title: str, body: str, canonical: str) -> str:
    prefix = "../" if canonical.rstrip("/").endswith("wiki2ube") or canonical.endswith("about.html") else "../../../"
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} - WikiTube - Wiki2</title>
  <meta name="description" content="WikiTube, the video section of Wiki2.">
  <link rel="canonical" href="{html.escape(canonical)}">
  <link rel="stylesheet" href="{prefix}style.css">
  <link rel="stylesheet" href="{prefix}wiki2ube/wiki2ube.css">
</head>
<body>
<div class="container">
  <div class="sidebar">
    <h2>Wiki2</h2>
    <a href="{prefix}index.html">Main Page</a>
    <a href="{prefix}article.html">Random Page</a>
    <a href="{prefix}index.html#categories">Categories</a>
    <hr>
    <h3>WikiTube</h3>
    <a href="{prefix}wiki2ube/">Video Index</a>
    <a href="{prefix}wiki2ube/about.html">About WikiTube</a>
  </div>
  <div class="content wiki2ube-content">
    {body}
  </div>
</div>
</body>
</html>
'''


def video_card(video: dict[str, str]) -> str:
    url = f"videos/{quote(video['id'])}/"
    return f'''<article class="video-card">
  <a class="video-thumb" href="{url}">
    <img src="{html.escape(video['poster'])}" alt="{html.escape(video['title'])} thumbnail">
    <span class="duration">{html.escape(video['duration'])}</span>
  </a>
  <div class="video-card-text">
    <h3><a href="{url}">{html.escape(video['title'])}</a></h3>
    <p>{html.escape(video['description'])}</p>
    <small>{html.escape(video['category'])} &middot; {html.escape(video['date'])}</small>
  </div>
</article>'''


def build() -> None:
    VIDEOS.mkdir(parents=True, exist_ok=True)
    cards = "\n".join(video_card(v) for v in VIDEO_CATALOG)
    index_body = f'''<div class="wiki2ube-masthead">
  <div><h1>WikiTube</h1><p>Video articles and moving pictures from the Wiki2 encyclopedia.</p></div>
  <div class="tube-mark">WIKI<span>TUBE</span></div>
</div>
<hr>
<div class="wiki2ube-toolbar"><strong>Video Index</strong><span>{len(VIDEO_CATALOG)} videos indexed</span></div>
<section class="video-grid">{cards}</section>
<hr>
<p><small>WikiTube is an experimental static video catalog. Select a title to open its permanent video page.</small></p>'''
    (BASE / "index.html").write_text(page("Video Index", index_body, "https://recgoblingu-lgtm.github.io/Wiki2/wiki2ube/"), encoding="utf-8")
    about_body = '''<h1>About WikiTube</h1>
<p>WikiTube is the video reference section of Wiki2. It uses permanent, human-readable video identifiers instead of a single streaming feed.</p>
<h2>Address format</h2>
<p>Every video is available at <code>/wiki2ube/videos/{video-id}/</code>. The identifier is stable and can be linked from encyclopedia articles, social posts, or other WikiTube pages.</p>
<h2>Catalog notes</h2>
<p>This static edition stores the catalog as ordinary HTML pages so it works on GitHub Pages without a database or server-side runtime.</p>'''
    (BASE / "about.html").write_text(page("About WikiTube", about_body, "https://recgoblingu-lgtm.github.io/Wiki2/wiki2ube/about.html"), encoding="utf-8")
    for video in VIDEO_CATALOG:
        video_body = f'''<div class="watch-heading"><p class="breadcrumb"><a href="../../index.html">Wiki2</a> / <a href="../../index.html">WikiTube</a> / {html.escape(video['title'])}</p><h1>{html.escape(video['title'])}</h1></div>
<div class="watch-layout">
  <main>
    <div class="video-player"><video controls preload="metadata" poster="{html.escape(video['poster'])}"><source src="{html.escape(video['src'])}" type="video/mp4">Your browser does not support HTML5 video.</video></div>
    <div class="video-info"><strong>{html.escape(video['category'])}</strong><span>{html.escape(video['duration'])}</span><span>Published {html.escape(video['date'])}</span></div>
    <p>{html.escape(video['description'])}</p>
    <hr><h2>About this video</h2><p>This WikiTube entry is part of the Wiki2 video reference catalog. The page has a stable identifier and can be linked directly.</p>
  </main>
  <aside class="video-sidebar"><h2>Video record</h2><dl><dt>Video ID</dt><dd><code>{html.escape(video['id'])}</code></dd><dt>Section</dt><dd>{html.escape(video['category'])}</dd><dt>Format</dt><dd>HTML5 video</dd></dl><p><a href="../../index.html">Return to Video Index</a></p></aside>
</div>'''
        target = VIDEOS / quote(video["id"], safe="") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page(video["title"], video_body, f"https://recgoblingu-lgtm.github.io/Wiki2/wiki2ube/videos/{video['id']}/"), encoding="utf-8")
    (BASE / "wiki2ube.css").write_text('''
.wiki2ube-content { max-width: 1000px; width: 100%; }
.wiki2ube-masthead { display:flex; justify-content:space-between; align-items:end; gap:20px; }
.wiki2ube-masthead h1 { margin-bottom:4px; }
.tube-mark { border:2px solid #333; padding:4px 8px; background:#eee; font-weight:bold; letter-spacing:1px; white-space:nowrap; }
.tube-mark span { color:#b00000; }
.wiki2ube-toolbar { display:flex; justify-content:space-between; margin:12px 0; border:1px solid #aaa; padding:8px; background:#eee; }
.video-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:18px; }
.video-card { border:1px solid #999; background:#fff; padding:8px; }
.video-thumb { display:block; position:relative; background:#ddd; }
.video-thumb img { display:block; width:100%; aspect-ratio:16/9; object-fit:cover; }
.duration { position:absolute; right:5px; bottom:5px; background:#000; color:#fff; padding:2px 4px; font:12px Arial,sans-serif; }
.video-card h3 { margin:8px 0 4px; font-size:18px; }
.video-card p { margin:4px 0 8px; }
.video-card small, .video-info { color:#555; }
.breadcrumb { font-size:14px; }
.watch-layout { display:grid; grid-template-columns:minmax(0,1fr) 230px; gap:20px; }
.video-player { background:#111; border:1px solid #555; padding:8px; }
.video-player video { display:block; width:100%; max-height:560px; }
.video-info { display:flex; gap:14px; border:1px solid #aaa; border-top:0; background:#eee; padding:8px; font-size:14px; }
.video-sidebar { border:1px solid #aaa; background:#eee; padding:10px; }
.video-sidebar h2 { margin-top:0; font-size:19px; }
.video-sidebar dl { margin:0; }
.video-sidebar dt { font-weight:bold; margin-top:8px; }
.video-sidebar dd { margin-left:0; }
code { background:#eee; border:1px solid #ccc; padding:1px 3px; }
@media (max-width:700px) { .container { display:block; } .sidebar { width:auto; border-right:0; border-bottom:1px solid #aaa; } .watch-layout { grid-template-columns:1fr; } .wiki2ube-masthead { align-items:start; flex-direction:column; } }
''', encoding="utf-8")

if __name__ == "__main__":
    build()
    print(f"Built WikiTube with {len(VIDEO_CATALOG)} videos.")
