#!/usr/bin/env bash
# ─────────────────────────────────────────────
# FTP Upload Script — uploads index.html to hosting
# Usage: bash upload.sh
# ─────────────────────────────────────────────

FTP_HOST="ftpupload.net"
FTP_PORT=21
FTP_USER="if0_41261422"
FTP_PASS="vmB40e17EQ"
REMOTE_DIR="/htdocs"        # public_html root on InfinityFree
LOCAL_FILE="index.html"

echo "Uploading $LOCAL_FILE → ftp://$FTP_HOST$REMOTE_DIR/$LOCAL_FILE"

curl --ftp-create-dirs \
     --user "$FTP_USER:$FTP_PASS" \
     --upload-file "$LOCAL_FILE" \
     "ftp://$FTP_HOST:$FTP_PORT$REMOTE_DIR/$LOCAL_FILE" \
  && echo "✓ Upload complete!" \
  || echo "✗ Upload failed — check credentials / path"
