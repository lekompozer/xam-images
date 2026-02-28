#!/usr/bin/env bash
# ─────────────────────────────────────────────
# FTP Upload Script — uploads all production files
# Usage: bash upload.sh
# ─────────────────────────────────────────────

FTP_HOST="ftpupload.net"
FTP_PORT=21
FTP_USER="if0_41261422"
FTP_PASS="vmB40e17EQ"
REMOTE_DIR="/htdocs"

FILES=(
    "index.html"
    "videos.html"
    "videos.json"
    "videos-data.js"
    "tags-data.js"
)

# Auto-copy tags-data.js from Downloads if newer than local copy
TAGS_DOWNLOAD="$HOME/Downloads/tags-data.js"
if [ -f "$TAGS_DOWNLOAD" ]; then
    if [ ! -f "tags-data.js" ] || [ "$TAGS_DOWNLOAD" -nt "tags-data.js" ]; then
        cp "$TAGS_DOWNLOAD" tags-data.js
        echo "📋 Copied tags-data.js from Downloads"
    fi
fi

ok=0; fail=0
for f in "${FILES[@]}"; do
    if [ ! -f "$f" ]; then
        echo "⚠ Skipping $f (not found locally)"
        continue
    fi
    echo -n "Uploading $f … "
    curl -s --ftp-create-dirs \
         --user "$FTP_USER:$FTP_PASS" \
         --upload-file "$f" \
         "ftp://$FTP_HOST:$FTP_PORT$REMOTE_DIR/$f" \
      && { echo "✓"; ok=$((ok+1)); } \
      || { echo "✗ FAILED"; fail=$((fail+1)); }
done

echo ""
echo "Done: $ok uploaded, $fail failed"
