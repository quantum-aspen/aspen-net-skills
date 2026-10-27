#!/bin/sh
# Fetch a Zoom (or any yt-dlp-supported) recording and check for a real
# captions track before committing to local transcription.
#
# Usage: fetch.sh <url> <workdir>
set -e
URL="${1:?usage: fetch.sh <url> <workdir>}"
D="${2:?usage: fetch.sh <url> <workdir>}"
mkdir -p "$D"
cd "$D"

echo "$URL" > url.txt

echo "=== checking for existing captions/subs ==="
timeout 90 yt-dlp --list-subs --no-warnings "$URL" || true
echo "(if a real language track appears above — not just 'chapter' — prefer"
echo " 'yt-dlp --write-subs --sub-langs <lang>' over transcribing from audio)"

echo "=== pulling metadata (title, duration) ==="
timeout 120 yt-dlp -J --no-warnings "$URL" > info.json
jq '{title, duration, ext}' info.json

# Zoom's own recording timestamp is usually NOT in yt-dlp metadata
# (upload_date/timestamp are null for Zoom shares). It IS embedded in the
# CDN filename yt-dlp resolves internally, e.g.:
#   .../GMT20260827-171318_Recording_....mp4  ->  2026-08-27 17:13:18 GMT
# Extract it so the output folder/transcript can be dated correctly.
REC_URL=$(jq -r '.url // .requested_downloads[0].url // empty' info.json)
DATE_STAMP=$(echo "$REC_URL" | grep -oE 'GMT[0-9]{8}-[0-9]{6}' | head -1 | sed -E 's/GMT([0-9]{4})([0-9]{2})([0-9]{2})-([0-9]{2})([0-9]{2})([0-9]{2})/\1-\2-\3 \4:\5:\6 GMT/')
if [ -n "$DATE_STAMP" ]; then
  echo "$DATE_STAMP" > recording_datetime.txt
  echo "recording datetime (from CDN filename): $DATE_STAMP"
else
  echo "WARNING: could not extract recording datetime from CDN URL — check info.json manually"
fi

echo "=== downloading recording ==="
timeout 900 yt-dlp -o "meeting.mp4" --no-warnings --no-progress "$URL"
ls -la meeting.mp4

echo "=== extracting 16kHz mono WAV for Whisper ==="
ffmpeg -y -loglevel error -i meeting.mp4 -vn -ac 1 -ar 16000 -c:a pcm_s16le meeting.wav
ffprobe -v error -show_entries format=duration -of csv=p=0 meeting.wav

echo "FETCH_DONE"
