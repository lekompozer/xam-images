import subprocess, sys, os

# After kuzu restore finishes, run QMH search crawl
scripts = [
    {
        "url": "https://anh.moe/album/Kuzu.7jdQy",
        "title": "kuzu",
        "log": "crawl_kuzu_restore.log",
    },
    {
        "url": "https://anh.moe/search/images/?q=%22QMH%22",
        "title": "QMH",
        "log": "crawl_qmh.log",
    },
]

target = {
    "url": "https://anh.moe/album/Sex.Uqwx",
    "title": "Clip Viet",
    "log": "crawl_clipviet.log",
}

log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), target["log"])
with open(log_path, "w") as log:
    proc = subprocess.Popen(
        [
            sys.executable,
            "-u",
            "crawl_anhmoe_videos.py",
            target["url"],
            target["title"],
        ],
        stdout=log,
        stderr=log,
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    print(f"Started '{target['title']}' PID {proc.pid} → {log_path}")
