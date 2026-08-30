from __future__ import annotations

import html
from pathlib import Path
from urllib.parse import quote

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
ARTICLES = ROOT / 'articles'
SITE_URL = 'https://recgoblingu-lgtm.github.io/Wiki2/'
FALLBACK_IMAGE = 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/80/Wikipedia-logo-v2.svg/512px-Wikipedia-logo-v2.svg.png'


def upsert(soup, head, key, value):
    attrs = {'property': key} if key.startswith('og:') else {'name': key}
    tag = head.find('meta', attrs=attrs)
    if tag is None:
        tag = soup.new_tag('meta')
        for name, attr_value in attrs.items():
            tag[name] = attr_value
        head.append(tag)
    tag['content'] = value


def process(path: Path) -> bool:
    soup = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
    if soup.head is None:
        soup.html.insert(0, soup.new_tag('head'))
    head = soup.head
    h1 = soup.find('h1')
    title = h1.get_text(' ', strip=True) if h1 else path.stem.replace('_', ' ')
    paragraph = soup.find('p')
    description = paragraph.get_text(' ', strip=True) if paragraph else f'{title} — an article in the Wiki2 automated encyclopedia.'
    description = description[:300]
    image = soup.find('img')
    image_url = image.get('src') if image and image.get('src', '').startswith(('http://', 'https://')) else FALLBACK_IMAGE
    url = SITE_URL + 'articles/' + quote(path.name)
    upsert(soup, head, 'og:type', 'article')
    upsert(soup, head, 'og:site_name', 'Wiki2')
    upsert(soup, head, 'og:title', title)
    upsert(soup, head, 'og:description', description)
    upsert(soup, head, 'og:url', url)
    upsert(soup, head, 'og:image', image_url)
    upsert(soup, head, 'twitter:card', 'summary_large_image')
    upsert(soup, head, 'twitter:title', title)
    upsert(soup, head, 'twitter:description', description)
    upsert(soup, head, 'twitter:image', image_url)
    canonical = head.find('link', rel='canonical')
    if canonical is None:
        canonical = soup.new_tag('link', rel='canonical')
        head.append(canonical)
    canonical['href'] = url
    rendered = str(soup)
    original = path.read_text(encoding='utf-8')
    if rendered == original:
        return False
    path.write_text(rendered, encoding='utf-8')
    return True


if __name__ == '__main__':
    changed = sum(process(path) for path in sorted(ARTICLES.glob('*.html')))
    print(f'Updated social metadata on {changed} article pages.')
