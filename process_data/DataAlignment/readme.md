AlignmentReport.py → generate summary.xlsx which calculates the start/end frame of each document (mp4/csv)
Alignment.py → perform slicing on documents according to summary.xlsx
Pairing.py → Identify and pair video segments that originally belonged to the same video but were split due to interruptions.
Merge_group_video.py / Merge_group_csv.py → Merge the paired video or csv segments (as identified by Pairing.py) back into a single continuous file.
Rename.py → Check the naming format of all files and standardize file names according to predefined rules or requirements.