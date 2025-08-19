#!/bin/bash

for video_code in $(seq -w 1 15); do
  for game in museum bowling gallery travel boss candy; do
    for perspective in C L; do
      echo "Processing: video_code=$video_code, game=$game, perspective=$perspective"
      python3 preview_slicing.py --video_code "$video_code" --game "$game" --perspective "$perspective"
    done
  done
done
