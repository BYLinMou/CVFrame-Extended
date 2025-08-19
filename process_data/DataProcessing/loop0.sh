#!/bin/bash

for i in $(seq -w 1 15)
do
    #if [ "$i" = "04" ] || [ "$i" = "02" ]; then
    #    echo "Skipping $i"
    #    continue
    #fi
    echo "Extracting video_code $i"
    python3 extract_17_keypoint_from_csv.py --video_code $i
done
