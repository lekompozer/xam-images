import sys

sys.path.insert(0, ".")
from crawl_videos import get_mp4s_from_thread

for url in [
    "https://xamvn.bond/threads/253233/",
    "https://xamvn.bond/threads/95835/",
]:
    data = get_mp4s_from_thread(url)
    print(f"\n{url}")
    print(f"  title : {data['title']}")
    print(f"  videos: {len(data['videos'])}")
