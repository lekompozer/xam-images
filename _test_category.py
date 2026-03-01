import requests, re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

s = requests.Session()
s.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36",
        "Referer": "https://anh.moe/",
    }
)

r = s.get("https://anh.moe/category/sfw", timeout=15)
print("Status:", r.status_code)
soup = BeautifulSoup(r.text, "html.parser")

# Check images (same /b/ CDN?)
CDN_B = re.compile(
    r'https://cdn\.save\.moe/b/[^\s"\'<>]+\.(?:jpg|jpeg|png|webp|gif)', re.I
)
imgs = CDN_B.findall(r.text)
print("CDN /b/ images:", len(set(imgs)))
for u in list(set(imgs))[:5]:
    print(" ", u[:80])

# Check next page link pattern
for a in soup.select("a[href]"):
    href = a.get("href", "")
    if "page=2" in href and "seek=" in href:
        print("Next link:", urljoin("https://anh.moe", href)[:100])
        break
