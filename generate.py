import requests
import os
import json
import re

print("🔥 SCRIPT STARTED")

RANDOM_API = "https://en.wikipedia.org/api/rest_v1/page/random/summary"

USED_FILE = "used.json"
OUTPUT_DIR = "page"
TEMPLATE_FILE = "templates/article.html"

PAGES_PER_RUN = 20


def clean_filename(name):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name)


def ensure_dirs():
    print("📁 Checking folders...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_random_article():
    print("🌐 Fetching Wikipedia page...")
    r = requests.get(RANDOM_API, timeout=10)
    print("Status:", r.status_code)

    data = r.json()
    return data.get("title"), data.get("extract")


def make_html(title, content):
    print("🧩 Building HTML:", title)
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template = f.read()

    return template.replace("{{title}}", title).replace("{{content}}", content)


def save_article(title, html):
    name = clean_filename(title)
    path = f"{OUTPUT_DIR}/{name}.html"

    print("💾 Writing:", path)

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    return True


def main():
    ensure_dirs()

    created = 0

    for i in range(PAGES_PER_RUN):
        print(f"\n🔁 Page {i+1}")

        try:
            title, content = get_random_article()

            if not title or not content:
                print("❌ Missing data")
                continue

            html = make_html(title, content)
            save_article(title, html)

            created += 1

        except Exception as e:
            print("❌ ERROR:", e)

    print("\n🎉 DONE. Created:", created)


main()
