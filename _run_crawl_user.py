import subprocess, sys, os

url = "https://anh.moe/maihuyhoang"
tag = "Clip-Tiktok"
max_pages = "100"

log_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "crawl_cliptiktok.log"
)
with open(log_path, "w") as log:
    proc = subprocess.Popen(
        [sys.executable, "-u", "crawl_anhmoe_user.py", url, tag, max_pages],
        stdout=log,
        stderr=log,
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    print(f"Started PID {proc.pid} → {log_path}")
