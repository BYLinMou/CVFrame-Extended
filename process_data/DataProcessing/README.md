Features：

Keypoint Extraction\
Extract 17 or 24 keypoints (custom order) from Perception-Neuron CSVs.\
Support for both robust header parsing and marker averaging.

CSV & Video Slicing\
Slice both CSV and video files into segments per action/repetition, based on annotation Excel files.\
Outputs are organized for downstream analysis.

Preview Generation\
Overlay projected 3D keypoints onto video clips for quick quality checks.

Batch Processing & Synchronization\
Utilities for file presence checking, batch processing, and synchronization across modalities.

Usage

1. Keypoint Extraction
```bash
python extract_17_keypoint_from_csv.py --video_code 04
Input: ./data/csv/04/*.csv
Output: ./data/extracted_csv/04_17kp/*.csv
Extract 24 keypoints (untested version):
```
```bash
python extract_24_keypoint_from_csv_NotTest.py --video_code 04
Input: ./data/csv/04/*.csv
Output: ./data/extracted_csv/04/*.csv
```

2. CSV Slicing
```bash
python slice_csv_ver2.py --video_code 04
Slices extracted CSVs into action/repetition clips based on offset Excel.
Output: ./data/output/slice_csv04/CSV_*/*.csv
```

3. Video Slicing
Edit slice_video.py for video_code and run:
```bash
python slice_video.py
Slices videos according to repetition/action, matching the CSVs.
```

4. Preview Slicing
```bash
python preview_slicing.py --video_code 04 --game museum --perspective C
Overlays 3D keypoints onto each video slice for visual verification.
Output: ./data/output/previews/04_museum_C/*.mp4
```

5. Batch Sync & Processing
```bash
python sync_all_video.py
Checks file presence and can batch-generate processed CSVs for all videos defined in an Excel sheet.
```

Notes\
Environment:\
Scripts require Python 3.7+ and packages: pandas, numpy, opencv-python, matplotlib, tqdm, etc.

File Paths:\
Please update file and folder paths in each script as needed to match your local directory structure and data locations.

Camera Parameters:\
Place JSON files with camera intrinsics/extrinsics under Projection/CVFrame-main/data/.

Authors & Contact\
Maintained by the CVRA research team.

For issues or questions, please open an issue or contact the repo maintainer.

License\
This project is intended for academic/research use.\
Please contact the authors for commercial licensing.
