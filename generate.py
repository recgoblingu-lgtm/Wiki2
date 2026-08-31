import requests
import os
import re
import json

RANDOM_API = "https://en.wikipedia.org/api/rest_v1/page/random/summary"

USED_FILE = "used.json"

def clean_filename(name):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name)

def load_used():
    if os.path.exists(USED_FILE):
        with open(USED_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_used(used):
    with open(USED_FILE, "w") as f:
        json.dump(list(used), f)

def get_random_article():
    res = requests.get(RANDOM_API)
    if res.status_code == 200:
        data = res.json()
        return data.get("title"), data.get("extract")
    return None, None

def make_html(title, content):
    with open("templates/article.html", "r", encoding="utf-8") as f:
        template = f.read()

    return template.replace("{{title}}", title).replace("{{content}}", content)

def save_article(title, html):
    safe_name = clean_filename(title)
    filename = safe_name + ".html"
    path = os.path.join("page", filename)

    if os.path.exists(path):
        return False

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    return True

def main():
    used = load_used()

    for _ in range(5):  # try multiple times to avoid duplicates
        title, content = get_random_article()

        if not title or not content:
            continue

        if title in used:
            continue

        html = make_html(title, content)
        success = save_article(title, html)

        if success:
            used.add(title)
            save_used(used)
            break

if __name__ == "__main__":
    main()
