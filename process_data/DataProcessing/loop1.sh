#!/bin/bash

for i in $(seq -w 1 15)
do
    #if [ "$i" = "04" ] || [ "$i" = "02" ]; then
    #    echo "Skipping $i"
    #    continue
    #fi
    echo "Processing video_code $i"
    python3 slice_csv_ver2.py --video_code $i
done
