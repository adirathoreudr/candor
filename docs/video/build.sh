#!/bin/zsh
# Build the demo video: the 75-second brag cut, then (optionally) a live voice clip.
#   docs/video/build.sh [voice_clip.mov] [out_dir]          -> <out_dir>/candor-demo.mp4 (default ~/Movies)
#
# index.html draws every frame as a pure function of time; render.py captures 2,250 frames with headless
# Chromium (Playwright) and pipes them to ffmpeg; music.py synthesizes the soundtrack (music and effects in
# one key). Every string on screen is real Candor data or output. Requirements: ffmpeg, uv, and a Python
# with Playwright + Chromium (set CANDOR_PLAYWRIGHT_PYTHON; `pip install playwright && playwright install chromium`).
set -euo pipefail

HERE=${0:A:h}
ROOT=${HERE:h:h}
CLIP=${1:-}
OUT=${2:-$HOME/Movies}
PW=${CANDOR_PLAYWRIGHT_PYTHON:-python3}
W=$(mktemp -d)
trap 'rm -rf $W' EXIT
cd $ROOT

echo "frames…"
$PW $HERE/render.py video 75 $W/silent.mp4
echo "soundtrack…"
uv run --frozen python $HERE/music.py $W/music.wav

echo "poster as frame 0, music mixed to -16 LUFS…"
ffmpeg -nostdin -loglevel error -y -ss 30.0 -i $W/silent.mp4 -frames:v 1 -q:v 2 $W/poster.jpg
ffmpeg -nostdin -loglevel error -y -i $W/silent.mp4 -i $W/poster.jpg -i $W/music.wav -filter_complex \
  "[0:v][1:v]overlay=enable='eq(n\,0)'[v];[2:a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,aformat=channel_layouts=stereo[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest $W/brag.mp4

if [[ -n $CLIP ]]; then
  echo "appending the live voice clip…"
  ffmpeg -nostdin -loglevel error -y -i $W/brag.mp4 -i $CLIP -filter_complex \
    "[1:v]fps=30,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x0b0c10,setsar=1[cv];\
     [1:a]aresample=48000,aformat=channel_layouts=stereo,loudnorm=I=-16:TP=-1.5:LRA=11[ca];\
     [0:v][0:a][cv][ca]concat=n=2:v=1:a=1[v][a]" \
    -map "[v]" -map "[a]" -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart $OUT/candor-demo.mp4
else
  ffmpeg -nostdin -loglevel error -y -i $W/brag.mp4 -c copy -movflags +faststart $OUT/candor-demo.mp4
fi
echo "wrote $OUT/candor-demo.mp4 ($(ffprobe -v error -show_entries format=duration -of csv=p=0 $OUT/candor-demo.mp4 | cut -d. -f1) s)"
