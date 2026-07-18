#!/bin/bash
# Mirror the vault essentials to the SD card so the box runs without the
# USB drive (config.py auto-falls-back to ~/vault when the drive is
# absent). Full index included — SD random reads beat the spinner.
# Rerun any time to refresh; ~1 min.
set -e
SRC=/media/caleb/Expansion/vault
DST=/home/caleb/vault
mkdir -p "$DST"
rsync -a --info=progress2 \
  "$SRC/index.db" "$SRC/scribe.db" "$SRC/pois.db" "$DST/" 2>/dev/null || \
  rsync -a "$SRC/index.db" "$SRC/scribe.db" "$SRC/pois.db" "$DST/"
rsync -a "$SRC/canned" "$SRC/storybooks" "$SRC/photos" "$DST/"
echo "travel vault ready at $DST:"
du -sh "$DST"
df -h / | tail -1
