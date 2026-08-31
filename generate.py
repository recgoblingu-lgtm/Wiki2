import requests
import os
import re
import json

print("🔥 GENERATOR STARTED")

RANDOM_API = "https://en.wikipedia.org/api/rest_v1/page/random/summary"

OUTPUT_DIR = "page"
TEMPLATE_FILE = "templates/article.html"

PAGES_PER_RUN = 20


# -----------------------------
# Helpers
# -----------------------------

def clean_filename(name):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name)


def ensure_dirs():
    print("📁 Ensuring /page exists...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_random_page():
    print("🌐 Requesting Wikipedia page...")
    r = requests.get(RANDOM_API, timeout=10)

    print("Status:", r.status_code)

    if r.status_code != 200:
        return None, None

    data = r.json()
    return data.get("title"), data.get("extract")


def make_html(title, content):
    print("🧩 Building HTML:", title)

    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template = f.read()

    return (
        template.replace("{{title}}", title)
                 .replace("{{content}}", content)
    )


def save_page(title, html):
    filename = clean_filename(title) + ".html"
    path = os.path.join(OUTPUT_DIR, filename)

    print("💾 Saving:", path)

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


# -----------------------------
# Main
# -----------------------------

def main():
    ensure_dirs()

    created = 0
    attempts = 0
    max_attempts = PAGES_PER_RUN * 5

    while created < PAGES_PER_RUN and attempts < max_attempts:
        attempts += 1

        print(f"\n🔁 Attempt {attempts}")

        title, content = get_random_page()

        if not title or not content:
            print("❌ Invalid page, skipping")
            continue

        html = make_html(title, content)
        save_page(title, html)

        created += 1
        print(f"✅ Created {created}/{PAGES_PER_RUN}")

    print("\n🎉 DONE")
    print("Total pages created:", created)


# Run immediately
main()
