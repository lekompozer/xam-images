#!/usr/bin/env python3
"""
Crawl mp4 links from xamvn.bond/forums/3/
Test mode: first 10 threads only
Output: videos.json
"""

import re, json, time, sys
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

# ── CONFIG ────────────────────────────────────────────────
BASE = "https://xamvn.bond"
FORUM_URL = "https://xamvn.bond/forums/3/"
MAX_THREADS = 500  # set to None to crawl all
DELAY = 0.8  # seconds between requests
OUTPUT = "videos.json"
# CDN pattern – expand regex if other CDN domains appear
CDN_RE = re.compile(r'https?://[^\s"\'<>]+\.mp4', re.IGNORECASE)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": BASE,
}

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


def get_page(url):
    """Return (soup, raw_html) or (None, '') on failure."""
    r = get(url)
    if not r:
        return None, ""
    return BeautifulSoup(r.text, "html.parser"), r.text


def get_soup(url):
    soup, _ = get_page(url)
    return soup


# ── STEP 1: collect thread URLs from category pages ───────
def get_thread_urls(max_threads=None):
    threads = []
    page = 1
    while True:
        url = FORUM_URL if page == 1 else f"{FORUM_URL}page-{page}"
        print(f"[category] page {page}: {url}")
        soup = get_soup(url)
        if not soup:
            break

        # XenForo thread link pattern
        links = soup.select("a[href*='/threads/']")
        new = []
        seen = set(threads)
        for a in links:
            href = a.get("href", "")
            # keep root thread page only (skip /post- anchors etc)
            m = re.match(r"(/threads/\d+/)$", href)
            if not m:
                m = re.match(r".+(/threads/\d+/)$", href)
            if not m:
                # try full url
                m = re.match(r"https?://[^/]+(/threads/\d+/)(\?.*)?$", href)
                if m:
                    href = BASE + m.group(1)
                else:
                    continue
            else:
                href = urljoin(BASE, href)
            if href not in seen:
                seen.add(href)
                new.append(href)

        if not new:
            print("  → no more threads, stopping.")
            break

        threads.extend(new)
        print(f"  → found {len(new)} threads (total {len(threads)})")

        if max_threads and len(threads) >= max_threads:
            threads = threads[:max_threads]
            break

        # check if there's a next page
        next_btn = soup.select_one(
            "a.pageNav-jump--next, a[rel='next'], .pagination a.next"
        )
        if not next_btn:
            break
        page += 1
        time.sleep(DELAY)

    return threads


# ── STEP 2: extract mp4 links from a single thread (all pages) ──
def get_mp4s_from_thread(thread_url):
    mp4s = []
    seen_mp4 = set()
    page = 1
    title = ""

    while True:
        url = thread_url if page == 1 else f"{thread_url}page-{page}"
        soup, raw_html = get_page(url)
        if not soup:
            break

        # grab thread title once
        if page == 1:
            t = soup.select_one("h1.p-title-value, h1.thread-title")
            if not t:
                # fallback: og:title meta (more reliable on XenForo)
                og = soup.select_one("meta[property='og:title']")
                title = og["content"].strip() if og and og.get("content") else url
            else:
                title = t.get_text(strip=True)

        # 1) raw html scan – catches JS blobs, meta tags, everywhere
        for u in CDN_RE.findall(raw_html):
            if u not in seen_mp4:
                seen_mp4.add(u)
                mp4s.append(u)

        # 2) <video src>, <source src> (explicit tags)
        for tag in soup.select("video[src], source[src]"):
            src = tag.get("src", "")
            if ".mp4" in src.lower() and src not in seen_mp4:
                seen_mp4.add(src)
                mp4s.append(src)

        # 3) any attribute containing .mp4
        for tag in soup.find_all(True):
            for attr in ("href", "data-url", "data-src", "data-original", "content"):
                val = tag.get(attr, "")
                if val and ".mp4" in val.lower():
                    for u in CDN_RE.findall(val):
                        if u not in seen_mp4:
                            seen_mp4.add(u)
                            mp4s.append(u)

        # next thread page?
        next_btn = soup.select_one(
            "a.pageNav-jump--next, a[rel='next'], .pagination a.next"
        )
        print(
            f"    page {page}: {'✓ VIDEO ' + str(len(mp4s)) if mp4s else 'no mp4'}  next={'yes' if next_btn else 'END'}"
        )
        if not next_btn:
            break
        page += 1
        time.sleep(DELAY)

    return {"title": title, "url": thread_url, "videos": mp4s}


# ── MAIN ──────────────────────────────────────────────────
def main():
    print("=" * 60)
    print(f"Crawling forum: {FORUM_URL}")
    print(f"Max threads (test mode): {MAX_THREADS}")
    print("=" * 60)

    thread_urls = get_thread_urls(max_threads=MAX_THREADS)
    print(f"\nCollected {len(thread_urls)} threads to scan.\n")

    results = []
    total_videos = 0
    for i, url in enumerate(thread_urls, 1):
        print(f"\n[{i}/{len(thread_urls)}] {url}")
        data = get_mp4s_from_thread(url)
        results.append(data)
        total_videos += len(data["videos"])
        vid_count = len(data["videos"])
        flag = " ✓ VIDEO" if vid_count else ""
        print(f"  → {vid_count} mp4 link(s){flag}  |  {data['title'][:70]}")

        # incremental save every 10 threads
        if i % 10 == 0:
            with open(OUTPUT, "w", encoding="utf-8") as f:
                json.dump(
                    {"threads": results, "total": total_videos},
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            print(f"  [saved] {i} threads so far → {OUTPUT}")

        time.sleep(DELAY)

    # ── summary ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"DONE — {len(results)} threads, {total_videos} total mp4 links")
    threads_with_video = [r for r in results if r["videos"]]
    print(f"Threads WITH videos : {len(threads_with_video)}")
    print(f"Threads WITHOUT     : {len(results) - len(threads_with_video)}")
    if total_videos:
        print(f"\nEstimated IndexedDB size:")
        avg_url_bytes = 80  # ~average cdn url length
        est_bytes = total_videos * avg_url_bytes
        print(f"  ~{total_videos} URLs × {avg_url_bytes}B = {est_bytes/1024:.1f} KB")
        print(f"  (IndexedDB handles 50MB+ per origin easily)")

    # ── write output ──────────────────────────────────────
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(
            {"threads": results, "total": total_videos}, f, ensure_ascii=False, indent=2
        )
    print(f"\nSaved → {OUTPUT}")


if __name__ == "__main__":
    main()
