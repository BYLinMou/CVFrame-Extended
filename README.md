# CV Frame Labeler & 3D Mocap Visualization Tool

This Python application provides a graphical interface for **video frame annotation**, **3D motion capture (mocap) data review**, and **projection of 3D/2D points onto video**. It is designed for computer vision and motion analysis workflows, supporting multiple synchronized data types and flexible visualization.

---

## Features

- **Video Frame Player**
  - Play, pause, seek by frame/time, and list videos in a folder.
  - Keyboard shortcuts for fast navigation (`Space`, `A`, `D`, `Q`, `E`, etc.).
  - Displays frame/time info over video.

- **3D Data Management**
  - Load multiple 3D data files (`.npy` or `.csv`), each can be toggled for visibility.
  - Supports raw mocap data (`.csv`), with flexible joint selection (all, "Skeleton 001", or custom).
  - Overlay 3D points and skeletons on video or on a virtual black background.
  - Assigns colors to each 3D dataset for clarity.

- **2D Pixel Data Overlay**
  - Load multiple pixel 2D data files (center/left views, `.npy` or `.csv`).
  - Overlay 2D skeletons on video.

- **Camera Calibration**
  - Supports loading camera intrinsics/extrinsics (`.json`).
  - Easily switch between different camera perspectives.

- **Export and Interoperability**
  - Export annotated videos with overlays.
  - Export custom joint lists for further analysis.
  - Supports batch loading of folders with 3D data.

- **Visualization**
  - 3D mocap scatter plot using matplotlib (Raw Mocap dataset only).
  - Panels are dockable/closable for a flexible workspace.

---

## Folder Structure

```
.
├── data/ 
│ ├── intrinsic_middle.json # Example camera intrinsic parameters 
│ ├── extrinsics_middle.json # Example camera extrinsic parameters 
│ └── ... 
├── main.py # Entry point for the application 
├── main_window.py # Main video labeler window (video playback/labeling) 
├── projection_window3.py # Main 3D visualization & projection window 
├── video_player.py # Video file player backend 
├── video_player_black.py # Virtual black video generator (for 3D-only sessions) 
├── pixel_data.py # 2D pixel data loader and dialog 
└── mocap_data.py # Raw mocap data loader and handler 
```
---

## Installation

### Prerequisites

- Python 3.7+
- `pip install PyQt5 numpy pandas matplotlib opencv-python`

### Setup

1. Clone/download this repository.
2. Make sure `data/` folder contains your camera calibration files and relevant test data.

---

## Running the Application

### 1. 3D Points Projection/Overlay Tool

```bash
python main.py
```
(Opens the main window for 3D/2D data overlay, mocap review, and export tools.)

### 2. Main Video Labeler (standalone)

```bash
python main_window.py
```
(Opens the video frame labeler with menu options to open videos/folders, and access 3D projection window.) 

---

## Usage Guide

- **Load Video**: Use the "File" menu to open a video or folder of videos.
- **Load 3D Data**: Use "Projection" menu or right panel to load .npy or .csv 3D datasets.
- **Load Pixel2D**: Use "File" menu or right panel to load 2D pixel data.
- **Load Raw Mocap**: Use "File" menu to load raw mocap CSV and explore joints.
- **Switch Camera View**: Use "Camera" menu to switch between "middle" and "left" perspectives.
- **Play/Seek Video**: Use buttons or keyboard shortcuts.
- **Export Video**: Use "Export" menu to save annotated video.
- **Export Joint List**: Use "Export" menu in custom mode (left panel) to save selected joints.

---

## Shortcuts

| Key   | Action                  |
|-------|--------------------------|
| Space | Play/Pause              |
| A / D | Previous/Next Frame     |
| Q / E | Back/Forward 1 Second   |
| W / S | Offset +1 / -1 Frame    |
| R     | Locate Frame            |
| F     | Locate Time             |
| Z     | Copy Offset             |

---

## Data Format Notes

- **3D Data**: `.npy` or `.csv` files with shape [frames, joints, 3] or [frames, joints*3] (xyz order).
- **Raw Mocap**: CSV with multi-row headers and "Position" columns, as exported from Vicon/Nexus.
- **Pixel2D**: `.npy` or `.csv` with [frames, joints, 3] (xyz or xy1).

---

## Troubleshooting

- **Data shape error**: Make sure .csv/.npy files match required dimensions.
- **Camera calibration missing**: Place your `intrinsic_*.json` and `extrinsics_*.json` in the `data/` folder.