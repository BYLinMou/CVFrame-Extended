# Features

- **Keypoint Extraction**  
  Extract 17 or 24 keypoints (custom order) from CSVs. Supports robust header parsing and marker averaging.

- **CSV & Video Slicing**  
  Slice both CSV and video files into segments per action/repetition based on annotation Excel files. Outputs are organized for downstream analysis.

- **Preview Generation**  
  Overlay projected 3D keypoints onto video clips for quick quality checks.

- **Batch Processing & Synchronization**  
  Utilities for file presence checking, batch processing, and synchronization across modalities.

---

# Usage

## 1) Keypoint Extraction

```bash
python extract_17_keypoint_from_csv.py --video_code 04
```

**Input:** `./data/csv/04/*.csv`  
**Output:** `./data/extracted_csv/04_17kp/*.csv`

```bash
python extract_24_keypoint_from_csv_NotTest.py --video_code 04
```

**Input:** `./data/csv/04/*.csv`  
**Output:** `./data/extracted_csv/04/*.csv`

---

## 2) CSV Slicing

```bash
python slice_csv_ver2.py --video_code 04
```

Slices extracted CSVs into action/repetition clips based on the offset Excel.  
**Output:** `./data/output/slice_csv04/CSV_*/*.csv`

---

## 3) Video Slicing

Edit `slice_video.py` to set `video_code`, then run:

```bash
python slice_video.py
```

Slices videos according to repetition/action, matching the CSV slices.

---

## 4) Preview Slicing

```bash
python preview_slicing.py --video_code 04 --game museum --perspective C
```

Overlays 3D keypoints onto each video slice for visual verification.  
**Output:** `./data/output/previews/04_museum_C/*.mp4`

---

## 5) Batch Sync & Processing

```bash
python sync_all_video.py
```

Checks file presence and can batch-generate processed CSVs for all videos defined in an Excel sheet.

---

# Notes

## Environment

- Python 3.7+  
- Required packages: `pandas`, `numpy`, `opencv-python`, `matplotlib`, `tqdm`, etc.


## File Paths

Update file and folder paths in each script to match your local directory structure and data locations.

## Camera Parameters

Place JSON files with camera intrinsics/extrinsics under:
```
CVFrame-Extended/data/
```