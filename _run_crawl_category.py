import subprocess, sys, os

url = "https://anh.moe/search/images/?q=%22QMH%22"
tag = "QMH"
max_pages = "300"

log_file = os.path.join(os.path.dirname(__file__), "crawl_qmh.log")

with open(log_file, "w") as log:
    proc = subprocess.Popen(
        [sys.executable, "-u", "crawl_anhmoe_category.py", url, tag, max_pages],
        stdout=log,
        stderr=log,
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    print(f"Started PID {proc.pid} → {log_file}")
