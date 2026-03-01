#!/usr/bin/env python3
"""
Crawl image URLs from an anh.moe category page (paginated).
Each listing page → collect /view/ links → visit each view page
→ grab a[href*="?dl="] from cdn.anh.moe/f/ (images only, skip video CDNs)
→ strip ?dl=1 → full-res URL.
Appends to album_items[tag] in tags-data.js (deduplicates).

Usage:
  python3 crawl_anhmoe_category.py <start_url> [tag] [max_pages]

Example (SFW, start from page 3 which is first page with images):
  python3 crawl_anhmoe_category.py \
    "https://anh.moe/category/sfw/?page=3&seek=2025-07-30+05:08:28.frRGFq" \
    "girl-xinh" 300
"""

import re, sys, time, json, os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": "https://anh.moe/",
}
BASE = "https://anh.moe"
DELAY_PAGE = 1.0  # between listing pages
DELAY_VIEW = 0.5  # between view page visits

# Image CDN: cdn.anh.moe/f/  (e.g. https://cdn.anh.moe/f/mcF5pEO.jpeg)
IMG_CDN_RE = re.compile(r"^https://cdn\.anh\.moe/f/", re.I)
# Video CDNs to skip
VID_CDN_RE = re.compile(
    r"cdn\.save\.moe|anh-cdn\.cyou|amvideos\.cfd|cdn\.anh\.moe/s", re.I
)

session = requests.Session()
session.headers.update(HEADERS)


def get(url, retries=3):
    for i in range(retries):
        try:
            r = session.get(url, timeout=15)
            r.raise_for_status()
            return r
        except Exception as e:
            print(f"  [warn] {e} (attempt {i+1}/{retries})", file=sys.stderr)
            time.sleep(2)
    return None


def current_page_num(url: str) -> int:
    qs = parse_qs(urlparse(url).query)
    try:
        return int(qs.get("page", ["1"])[0])
    except ValueError:
        return 1


def scrape_view_page(view_url: str):
    """Visit a /view/ page, return image URL or None."""
    r = get(view_url)
    if not r:
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    for a in soup.select("a[href*='?dl=']"):
        href = a.get("href", "")
        if IMG_CDN_RE.match(href):
            return href.split("?")[0]  # strip ?dl=1
    return None


def scrape_listing_page(url):
    """Scrape one category listing page.
    Returns (image_urls, next_page_url_or_None).
    """
    r = get(url)
    if not r:
        return [], None
    soup = BeautifulSoup(r.text, "html.parser")

    # Unique /view/ links (each card appears twice in HTML)
    view_links = list(
        dict.fromkeys(a.get("href") for a in soup.select("a[href^='/view/']"))
    )

    images = []
    for i, vpath in enumerate(view_links):
        vurl = urljoin(BASE, vpath)
        img_url = scrape_view_page(vurl)
        status = f"✓  {img_url[-40:]}" if img_url else "✗  (video/skip)"
        print(f"  [{i+1:2d}/{len(view_links)}] {status}")
        if img_url:
            images.append(img_url)
        time.sleep(DELAY_VIEW)

    # Next page: page=N+1 with seek= token
    n = current_page_num(url)
    next_url = None
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if f"page={n + 1}" in href and "seek=" in href:
            next_url = urljoin(BASE, href)
            break

    return images, next_url


def crawl_category(start_url, max_pages=300):
    all_urls = []
    seen_pages = set()
    url = start_url
    page_num = current_page_num(start_url)
    pages_crawled = 0

    while url and pages_crawled < max_pages:
        if url in seen_pages:
            print("  [loop detected] stopping.")
            break
        seen_pages.add(url)
        print(f"\n[page {page_num}] {url}")
        imgs, nxt = scrape_listing_page(url)
        print(f"  → {len(imgs)} image(s) on this page")
        all_urls.extend(imgs)
        pages_crawled += 1
        url = nxt
        page_num += 1
        if nxt:
            time.sleep(DELAY_PAGE)

    print(f"\n[done] {pages_crawled} page(s) crawled, {len(all_urls)} raw image URLs")

    # Dedup maintaining order
    seen = set()
    deduped = []
    for u in all_urls:
        if u not in seen:
            seen.add(u)
            deduped.append(u)
    return deduped


# ── TAGS-DATA UPDATER ────────────────────────────────────────
def update_tags_data(tag: str, new_ids: list, tags_file="tags-data.js"):
    if not os.path.exists(tags_file):
        print(f"[warn] {tags_file} not found, skipping update.")
        return
    with open(tags_file, encoding="utf-8") as f:
        content = f.read()
    m = re.search(r"window\.TAGS_DATA\s*=\s*(\{.*\})\s*;", content, re.DOTALL)
    if not m:
        print("[error] Could not parse TAGS_DATA from tags-data.js")
        return
    data = json.loads(m.group(1))
    # Auto-add tag to tags list and items if not present
    if tag not in data.get("tags", []):
        data.setdefault("tags", []).append(tag)
        print(f"  Added '{tag}' to tags list")
    if tag not in data.get("items", {}):
        data.setdefault("items", {})[tag] = []
        print(f"  Added '{tag}' to items")
    if "album_items" not in data:
        data["album_items"] = {}
    existing = data["album_items"].get(tag, [])
    existing_set = set(existing)
    appended = [u for u in new_ids if u not in existing_set]
    data["album_items"][tag] = existing + appended
    total = len(data["album_items"][tag])
    print(f"  existing: {len(existing)}, new: {len(appended)}, total: {total}")
    new_json = json.dumps(data, ensure_ascii=False, indent=2)
    new_content = (
        f"// Auto-generated by indexlocal.html\nwindow.TAGS_DATA = {new_json};\n"
    )
    with open(tags_file, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"[tags-data.js] album_items['{tag}'] updated → {total} total URLs")


# ── MAIN ────────────────────────────────────────────────────
if __name__ == "__main__":
    start_url = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "https://anh.moe/category/sfw/?page=3&seek=2025-07-30+05:08:28.frRGFq"
    )
    tag = sys.argv[2] if len(sys.argv) > 2 else "girl-xinh"
    max_pages = int(sys.argv[3]) if len(sys.argv) > 3 else 300

    print("=" * 60)
    print(f"Start : {start_url}")
    print(f"Tag   : {tag}")
    print(f"Max   : {max_pages} pages")
    print("=" * 60)

    urls = crawl_category(start_url, max_pages=max_pages)

    print(f"\n{'='*60}")
    print(f"TOTAL unique images: {len(urls)}")
    print(f"{'='*60}")
    print("First 5:")
    for u in urls[:5]:
        print(" ", u)

    out = "anhmoe_category_urls.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(
            {"tag": tag, "start": start_url, "urls": urls},
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"\nSaved all URLs → {out}")

    update_tags_data(tag, urls)
