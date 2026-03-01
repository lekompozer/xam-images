import requests, re
from bs4 import BeautifulSoup

s = requests.Session()
s.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36",
        "Referer": "https://anh.moe/",
    }
)

r = s.get(
    "https://anh.moe/view/WowGirls.19.04.14.Stacy.Bloom.Pink.Mirror.XXX.1080p.HEVC.x265.PRT.7RWxQ3mH",
    timeout=15,
)
print("Status:", r.status_code)
soup = BeautifulSoup(r.text, "html.parser")

title_el = soup.select_one("h1, .title, [class*=title]")
print("Title:", title_el.get_text(strip=True)[:80] if title_el else "none")

dl_links = soup.select(
    'a[href*="?dl="], a[download], a[href*="cdn.save.moe"], a[href*="cdn.anh.moe"]'
)
print("DL links:", len(dl_links))
for a in dl_links[:5]:
    print(" ", a.get("href", "")[:100])

vids = soup.select("video source, video[src]")
print("Video tags:", len(vids))
for v in vids[:3]:
    print(" src:", v.get("src", "")[:80])

cdn_vids = re.findall(
    r'https://cdn\.(?:save|anh)\.moe/[^\s"\'<>]+\.(?:mp4|webm|mov)', r.text, re.I
)
print("CDN video URLs in raw HTML:", len(cdn_vids))
for u in set(cdn_vids):
    print(" ", u[:100])
