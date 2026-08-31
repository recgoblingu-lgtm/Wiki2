import requests
import os
import re

print("🔥 SCRIPT STARTED")

RANDOM_API = "https://en.wikipedia.org/api/rest_v1/page/random/summary"

OUTPUT_DIR = "page"
TEMPLATE_FILE = "templates/article.html"

PAGES_PER_RUN = 20


def clean(name):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name)


def ensure():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("📁 page folder ready")


def fetch():
    r = requests.get(RANDOM_API, timeout=10)
    print("🌐 status:", r.status_code)

    if r.status_code != 200:
        return None, None

    j = r.json()
    return j.get("title"), j.get("extract")


def build(title, content):
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        t = f.read()

    return t.replace("{{title}}", title).replace("{{content}}", content)


def save(title, html):
    path = f"{OUTPUT_DIR}/{clean(title)}.html"

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    print("💾 saved:", path)


def main():
    ensure()

    made = 0

    for i in range(PAGES_PER_RUN):
        print(f"\n🔁 page {i+1}")

        title, content = fetch()

        if not title or not content:
            print("❌ skip")
            continue

        html = build(title, content)
        save(title, html)

        made += 1

    print("\n🎉 DONE:", made, "pages created")


main()
