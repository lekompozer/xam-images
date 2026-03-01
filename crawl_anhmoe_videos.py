#!/usr/bin/env python3
"""
Crawl video links from an anh.moe album.
Each card links to a /view/ page which has a download anchor (?dl=1).
Strip ?dl=1 to get the raw streamable CDN URL.

Usage:
  python3 crawl_anhmoe_videos.py <album_url> <thread_title>

Example:
  python3 crawl_anhmoe_videos.py "https://anh.moe/album/C%C3%81C-VIDEO-HAY.s6C6" "Phim Âu Mỹ"
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
DELAY_PAGE = 1.0  # between album listing pages
DELAY_VIEW = 0.6  # between individual view-page requests
OUTPUT_JSON = "videos.json"
OUTPUT_JS = "videos-data.js"

session = requests.Session()
session.headers.update(HEADERS)


# ── helpers ───────────────────────────────────────────────


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


def current_page_num(url):
    qs = parse_qs(urlparse(url).query)
    try:
        return int(qs.get("page", ["1"])[0])
    except ValueError:
        return 1


def title_from_view_url(view_url):
    """Extract human-readable title from the view URL slug."""
    path = urlparse(view_url).path  # /view/Some.Title.XXXX
    slug = path.rstrip("/").rsplit("/", 1)[-1]
    # Remove trailing short ID (last segment after last dot if looks like ID)
    parts = slug.split(".")
    # Drop last part if it looks like a random ID (mixed case, short)
    if (
        parts
        and re.match(r"^[A-Za-z0-9]{5,12}$", parts[-1])
        and not parts[-1].isdigit()
    ):
        parts = parts[:-1]
    return " ".join(parts).strip()


# ── album listing ─────────────────────────────────────────


def get_view_links_from_page(url):
    """Return (view_urls_list, next_page_url_or_None) for one album page."""
    r = get(url)
    if not r:
        return [], None
    soup = BeautifulSoup(r.text, "html.parser")

    seen, links = set(), []
    for a in soup.select("a[href^='/view/']"):
        href = a.get("href", "")
        full = urljoin(BASE, href)
        if full not in seen:
            seen.add(full)
            links.append(full)

    n = current_page_num(url)
    next_url = None
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if f"page={n + 1}" in href and "seek=" in href:
            next_url = urljoin(BASE, href)
            break

    return links, next_url


def crawl_album_view_links(start_url):
    """Walk all album pages and collect unique /view/ URLs."""
    all_links, seen, page_url = [], set(), start_url
    while page_url:
        n = current_page_num(page_url)
        print(f"[album page {n}] {page_url}")
        links, next_url = get_view_links_from_page(page_url)
        new = [u for u in links if u not in seen]
        seen.update(new)
        all_links.extend(new)
        print(f"  → {len(links)} view links ({len(new)} new)")
        page_url = next_url
        if next_url:
            time.sleep(DELAY_PAGE)
    return all_links


# ── view page ─────────────────────────────────────────────

CDN_VIDEO_RE = re.compile(
    r'https://cdn\.(?:save|anh)\.moe/[^\s"\'<>]+\.(?:mp4|webm|mov)',
    re.I,
)


def scrape_view_page(view_url):
    """Return (video_url, title) or (None, title) if not found."""
    r = get(view_url)
    if not r:
        return None, title_from_view_url(view_url)

    soup = BeautifulSoup(r.text, "html.parser")

    # 1. Prefer explicit download anchor (?dl=1)
    dl_a = soup.select_one('a[href*="?dl="]')
    if dl_a:
        raw = dl_a.get("href", "").split("?")[0].strip()
        if raw:
            return raw, title_from_view_url(view_url)

    # 2. Fallback: CDN video URL anywhere in raw HTML
    matches = CDN_VIDEO_RE.findall(r.text)
    if matches:
        return matches[0], title_from_view_url(view_url)

    return None, title_from_view_url(view_url)


# ── output ────────────────────────────────────────────────


def update_videos_json(thread_title, videos):
    """Append (or replace) a thread with the given title in videos.json."""
    if not os.path.exists(OUTPUT_JSON):
        data = {"threads": [], "total": 0}
    else:
        with open(OUTPUT_JSON, encoding="utf-8") as f:
            data = json.load(f)

    # Helper: get URL from a video entry (supports both str and {url,title} dict)
    def vid_url(v):
        return v if isinstance(v, str) else v.get("url", "")

    # Merge into existing thread (append+deduplicate by URL), otherwise insert at top
    existing_idx = next(
        (i for i, t in enumerate(data["threads"]) if t.get("title") == thread_title),
        None,
    )
    if existing_idx is not None:
        existing_videos = data["threads"][existing_idx].get("videos", [])
        existing_urls = {vid_url(v) for v in existing_videos}
        new_unique = [v for v in videos if vid_url(v) not in existing_urls]
        merged = existing_videos + new_unique
        data["threads"][existing_idx]["videos"] = merged
        print(
            f"  Merged into existing thread '{thread_title}': "
            f"{len(existing_videos)} + {len(new_unique)} new = {len(merged)} videos"
        )
    else:
        data["threads"].insert(0, {"title": thread_title, "url": "", "videos": videos})
        print(
            f"  Inserted new thread '{thread_title}' at top with {len(videos)} videos"
        )

    data["total"] = sum(len(t.get("videos", [])) for t in data["threads"])

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_JS, "w", encoding="utf-8") as f:
        f.write("// Auto-generated by crawl_videos.py — do not edit manually\n")
        f.write("window.VIDEOS_DATA = ")
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")

    print(f"  Total videos across all threads: {data['total']}")


# ── main ──────────────────────────────────────────────────

if __name__ == "__main__":
    album_url = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "https://anh.moe/album/C%C3%81C-VIDEO-HAY.s6C6"
    )
    thread_title = sys.argv[2] if len(sys.argv) > 2 else "Phim Âu Mỹ"

    print("=" * 60)
    print(f"Album : {album_url}")
    print(f"Thread: {thread_title}")
    print("=" * 60)

    # Step 1: collect all /view/ URLs
    view_links = crawl_album_view_links(album_url)
    print(f"\nTotal view pages to scrape: {len(view_links)}\n")

    # Step 2: visit each view page to get video URL
    videos, failed = [], 0
    for i, vurl in enumerate(view_links, 1):
        video_url, title = scrape_view_page(vurl)
        status = "✓" if video_url else "✗"
        print(f"  [{i:3d}/{len(view_links)}] {status}  {title[:55]}")
        if video_url:
            videos.append({"url": video_url, "title": title})
        else:
            failed += 1
        time.sleep(DELAY_VIEW)

    print(f"\n{'='*60}")
    print(f"Videos found : {len(videos)}")
    print(f"Failed/skipped: {failed}")
    if videos:
        print("First 5:")
        for v in videos[:5]:
            print(" ", v["url"], "|", v["title"])

    # Step 3: write to videos.json + videos-data.js
    if videos:
        update_videos_json(thread_title, videos)
        print(f"\nSaved → {OUTPUT_JSON}  +  {OUTPUT_JS}")
    else:
        print("\nNo videos found — nothing written.")
