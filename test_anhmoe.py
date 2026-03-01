import re, requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://anh.moe/",
}
BASE = "https://anh.moe"
CDN_RE = re.compile(r'https?://[^\s"\'<>]+\.(?:jpg|jpeg|png|webp|gif)', re.I)


def scrape_page(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
    print(f"Status: {r.status_code} | URL: {r.url}")
    soup = BeautifulSoup(r.text, "html.parser")

    # === 1. direct CDN links in raw HTML ===
    cdn = list(dict.fromkeys(CDN_RE.findall(r.text)))
    # filter out icons/avatars/ui assets — keep pncloudfl or cdn-like paths
    img_cdn = [u for u in cdn if any(x in u for x in ["cdn", "pncloud", "anh.moe/"])]
    print(f"\n--- CDN image links in HTML: {len(img_cdn)}")
    for u in img_cdn[:20]:
        print(" ", u)

    # === 2. <img> tags ===
    imgs = soup.select("img[src]")
    print(f"\n--- <img> tags: {len(imgs)}")
    for i in imgs[:15]:
        print(" ", i.get("src"), "| data-src:", i.get("data-src", "-"))

    # === 3. /view/ links ===
    view_links = soup.select("a[href*='/view/']")
    print(f"\n--- /view/ links: {len(view_links)}")
    for a in view_links[:10]:
        print(" ", a["href"])

    # === 4. next page link ===
    for sel in [
        "a[href*='page=2']",
        "a.pagination__next",
        "a[aria-label='Next']",
        "a[rel='next']",
    ]:
        nxt = soup.select_one(sel)
        if nxt:
            print(f"\n--- Next page ({sel}):", nxt.get("href"))
            break
    else:
        # scan all <a> for next/page
        for a in soup.select("a[href]"):
            if "page=" in a.get("href", "") and "seek=" in a.get("href", ""):
                print(
                    f"\n--- Next-like link: {a['href']} | text: {a.get_text(strip=True)[:30]}"
                )

    print("\n--- HTML snippet (first 3000 chars):")
    print(r.text[:3000])

    return soup, r.text


print("=" * 60)
print("PAGE 1")
print("=" * 60)
scrape_page("https://anh.moe/album/G%C3%81I-XINH-4.Ww3iH")

print("\n\n" + "=" * 60)
print("PAGE 2")
print("=" * 60)
scrape_page(
    "https://anh.moe/album/G%C3%81I-XINH-4.Ww3iH/?page=2&seek=2025-11-07+15%3A07%3A17.Dx8873"
)
