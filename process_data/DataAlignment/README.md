# Video/CSV Alignment and Merging Toolkit

This repository provides a suite of Python scripts for efficiently processing, aligning, segmenting, pairing, and merging video (`.mp4`) and CSV files. The toolkit is designed to handle workflows where video recordings and their corresponding data logs are interrupted, split, or need to be standardized for further analysis.

---

## Workflow Overview

### AlignmentReport.py
Generates a `summary.xlsx` file that contains calculated start and end frames for each document (both `.mp4` and `.csv` files).

### Alignment.py
Slices the documents according to the frame information provided in `summary.xlsx`.

### Pairing.py
Identifies and pairs video or CSV segments that originally belonged to the same video but were split due to interruptions.

### Merge_group_video.py / Merge_group_csv.py
Merges the paired video or CSV segments (as identified by `Pairing.py`) back into single, continuous files.

### Rename.py
Checks and standardizes the naming format of all files according to predefined rules or requirements.

---

## Getting Started

### Prerequisites

- Python 3.7+
- `pandas`
- `openpyxl`
- `moviepy` (for video processing)
- Other dependencies as required (see individual scripts)

---

## Usage

### Generate Summary

```bash
python AlignmentReport.py
```
Produces `summary.xlsx` with calculated frame information.

### Slice Documents

```bash
python Alignment.py
```
Slices `.mp4` and `.csv` files based on `summary.xlsx`.

### Pair Segments

```bash
python Pairing.py
```
Pairs segments from the same original video/data.

### Merge Segments

For videos:
```bash
python Merge_group_video.py
```

For CSVs:
```bash
python Merge_group_csv.py
```

### Rename Files

```bash
python Rename.py
```
Standardizes file naming formats.

---

## File/Folder Structure

```plaintext
project_root/
│
├── AlignmentReport.py
├── Alignment.py
├── Pairing.py
├── Merge_group_video.py
├── Merge_group_csv.py
├── Rename.py
├── requirements.txt
└── summary.xlsx
```

---

## Notes

- Ensure all source video and CSV files are placed in the correct input directory before starting.
- Adjust configuration or rules in the scripts as needed to fit your specific data or naming conventions.
