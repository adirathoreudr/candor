#!/bin/zsh
# Render the demo video: terminal segments (vhs) + narration (macOS say) + an optional live voice clip.
#   docs/video/build.sh [voice_clip.mov] [out_dir]
# Every command in the tapes replays from the committed LLM cache, so rendering needs no API calls.
# Output: <out_dir>/candor-demo.mp4 (default ~/Movies). Not committed: the video goes to YouTube/Drive.
set -euo pipefail

ROOT=${0:A:h:h:h}
CLIP=${1:-}
OUT=${2:-$HOME/Movies}
BUILD=$OUT/candor-demo-build
VOICE=${CANDOR_NARRATOR:-Samantha}
mkdir -p $BUILD
cd $ROOT

seconds() { ffprobe -v error -show_entries format=duration -of csv=p=0 "$1"; }

# One normalized segment: video held on its last frame or audio padded with silence, whichever is shorter.
finish() {   # finish <video> <audio> <out>
  local v=$(seconds $1) a=$(seconds $2)
  local len=$(python3 -c "print(round(max($v, $a + 0.9), 2))")
  local hold=$(python3 -c "print(round(max(0.0, $len - $v), 2))")
  ffmpeg -nostdin -loglevel error -y -i $1 -i $2 -filter_complex \
    "[0:v]fps=30,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,tpad=stop_mode=clone:stop_duration=${hold}[v];[1:a]aresample=48000,aformat=channel_layouts=stereo,adelay=400|400,apad[a]" \
    -map "[v]" -map "[a]" -t $len -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 160k $3
}

list=$BUILD/list.txt
: > $list
while IFS='|' read -r seg text; do
  [[ -z $seg ]] && continue
  echo "segment $seg"
  say -v $VOICE -r 178 -o $BUILD/$seg.aiff "$text"
  { echo "Output \"$BUILD/$seg.raw.mp4\""; cat docs/video/tapes/_setup.tape docs/video/tapes/$seg.tape; } > $BUILD/$seg.tape
  vhs $BUILD/$seg.tape >/dev/null </dev/null
  finish $BUILD/$seg.raw.mp4 $BUILD/$seg.aiff $BUILD/$seg.mp4
  echo "file '$BUILD/$seg.mp4'" >> $list
  if [[ $seg == 06-assistant && -n $CLIP ]]; then   # the live voice clip goes right after the text assistant
    echo "segment 07-voice (live clip)"
    ffmpeg -nostdin -loglevel error -y -i $CLIP -filter_complex \
      "[0:v]fps=30,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1[v];[0:a]aresample=48000,aformat=channel_layouts=stereo,loudnorm=I=-16:TP=-1.5:LRA=11[a]" \
      -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 160k $BUILD/07-voice.mp4
    echo "file '$BUILD/07-voice.mp4'" >> $list
  fi
done < docs/video/narration.txt

ffmpeg -nostdin -loglevel error -y -f concat -safe 0 -i $list -c copy $OUT/candor-demo.mp4
rm -rf outbox
echo "wrote $OUT/candor-demo.mp4 ($(printf '%.0f' $(seconds $OUT/candor-demo.mp4)) s)"
