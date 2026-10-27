#!/bin/sh
# One-time (idempotent) environment setup for local-meeting-transcript.
# Creates a uv-managed venv with faster-whisper + sherpa-onnx, and downloads
# the diarization models. Safe to re-run — skips anything already present.
#
# Usage: setup.sh [workdir]
#   workdir defaults to $MEETING_TOOLS_DIR, else .meeting-tools/ in the
#   current directory (run it from the project root). The skill itself may be
#   installed anywhere (a plugin cache, a container image), so its own
#   location says nothing about the project.
set -e
D="${1:-${MEETING_TOOLS_DIR:-$PWD/.meeting-tools}}"
mkdir -p "$D/models"
cd "$D"

# ffmpeg/yt-dlp/uv come from the machine's toolchain manager
# (e.g. `mise use ffmpeg yt-dlp uv`).
for bin in ffmpeg ffprobe yt-dlp uv; do
  command -v "$bin" >/dev/null 2>&1 || { echo "MISSING: $bin (install via mise)"; exit 1; }
done

if [ ! -x ".venv/bin/python" ]; then
  echo "creating venv..."
  uv venv --python 3.12 .venv
fi

echo "installing python deps (faster-whisper, sherpa-onnx)..."
uv pip install --python .venv/bin/python faster-whisper sherpa-onnx

if [ ! -f "models/sherpa-onnx-pyannote-segmentation-3-0/model.onnx" ]; then
  echo "downloading pyannote segmentation model..."
  ( cd models && \
    curl -sSL -O "https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2" && \
    tar xjf sherpa-onnx-pyannote-segmentation-3-0.tar.bz2 )
fi

if [ ! -f "models/wespeaker_en_voxceleb_CAM++.onnx" ]; then
  echo "downloading WeSpeaker CAM++ embedding model..."
  ( cd models && \
    curl -sSL -o "wespeaker_en_voxceleb_CAM++.onnx" \
      "https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/wespeaker_en_voxceleb_CAM%2B%2B.onnx" )
fi

echo "SETUP_DONE: $D ready"
