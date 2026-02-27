#!/bin/bash
cd /Users/user/Code/xam-images
export PYTHONUNBUFFERED=1
/Users/user/miniconda3/bin/python -u crawl_videos.py > crawl_log.txt 2>&1
