import requests
import os
import re
import json

RANDOM_API = "https://en.wikipedia.org/api/rest_v1/page/random/summary"
USED_FILE = "used.json"
OUTPUT_DIR = "page"
TEMPLATE_FILE = "templates/article.html"

PAGES_PER_RUN = 20


def clean_filename(name):
    # keep it safe for URLs/files
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name)


def load_used():
    if os.path.exists(USED_FILE):
        with open(USED_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_used(used):
    with open(USED_FILE, "w") as f:
        json.dump(list(used), f, indent=2)


def get_random_article():
    try:
        res = requests.get(RANDOM_API, timeout=10)
        if res.status_code == 200:
            data = res.json()
            title = data.get("title")
            content = data.get("extract")
            return title, content
    except:
        pass
    return None, None


def make_html(title, content):
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template = f.read()

    html = template.replace("{{title}}", title)
    html = html.replace("{{content}}", content)

    return html


def save_article(title, html):
    safe_name = clean_filename(title)
    filename = f"{safe_name}.html"
    path = os.path.join(OUTPUT_DIR, filename)

    # skip if already exists
    if os.path.exists(path):
        return False

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    return True


def ensure_dirs():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)


def main():
    ensure_dirs()
    used = load_used()

    created = 0
    attempts = 0
    max_attempts = PAGES_PER_RUN * 10

    while created < PAGES_PER_RUN and attempts < max_attempts:
        attempts += 1

        title, content = get_random_article()

        if not title or not content:
            continue

        if title in used:
            continue

        html = make_html(title, content)
        success = save_article(title, html)

        if success:
            used.add(title)
            created += 1
            print(f"✅ Created: {title}")
        else:
            print(f"⚠️ Skipped (exists): {title}")

    save_used(used)
    print(f"\n🎉 Total pages created this run: {created}")


if __name__ == "__main__":
    main()
