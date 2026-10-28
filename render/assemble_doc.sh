#!/bin/bash
set -e
OUT="/opt/data/videos/render/evezart_documentary.mp4"
TITLE="/opt/data/videos/render/title_card.mp4"
END="/opt/data/videos/render/end_card.mp4"
TEMP_LIST="/opt/data/videos/render/doc_concat.txt"

# Title card - 5s
ffmpeg -y -f lavfi -i color=c=0x0A0E14:s=1920x1080:r=24 -vf "
drawtext=text='EVEZ-OS':fontcolor=0x00FF9F:fontsize=80:x=(w-text_w)/2:y=(h-text_h)/2-40,
drawtext=text='A DOCUMENTARY IN ASCII':fontcolor=0xC5C8C6:fontsize=40:x=(w-text_w)/2:y=(h-text_h)/2+60,
drawtext=text='Generative Surveillance State':fontcolor=0xFFB700:fontsize=30:x=(w-text_w)/2:y=(h-text_h)/2+120
" -frames:v 120 -pix_fmt yuv420p "$TITLE" 2>/dev/null || true

# End card - 5s
ffmpeg -y -f lavfi -i color=c=0x0A0E14:s=1920x1080:r=24 -vf "
drawtext=text='ETYMON':fontcolor=0x00FF9F:fontsize=100:x=(w-text_w)/2:y=(h-text_h)/2-50,
drawtext=text='The root outlives the crown':fontcolor=0xC5C8C6:fontsize=36:x=(w-text_w)/2:y=(h-text_h)/2+50
" -frames:v 120 -pix_fmt yuv420p "$END" 2>/dev/null || true

# Build concat list
cat > "$TEMP_LIST" << 'INNER'
file '/opt/data/videos/render/title_card.mp4'
file '/opt/data/videos/render/strange_attractor_garden.mp4'
file '/opt/data/videos/render/clip_00.mp4'
file '/opt/data/videos/render/clip_01.mp4'
file '/opt/data/videos/render/clip_02.mp4'
file '/opt/data/videos/render/clip_03.mp4'
file '/opt/data/videos/render/evez_ascii_video.mp4'
file '/opt/data/videos/render/end_card.mp4'
INNER

# Concatenate and normalize to 1920x1080
ffmpeg -y -f concat -safe 0 -i "$TEMP_LIST" \
  -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:-1:-1:color=0x0A0E14" \
  -c:v libx264 -preset medium -crf 23 -pix_fmt yuv420p \
  -movflags +faststart \
  "$OUT" 2>&1 | tail -20

echo "DOCUMENTARY: $OUT"
ls -lh "$OUT"
