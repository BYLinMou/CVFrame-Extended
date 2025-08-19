import os, json
import cv2
import numpy as np
import pandas as pd
import re
import argparse

# --- CONFIGURATION: point these to your folders + camera JSON ---
def parse_args():
    parser = argparse.ArgumentParser(description='Slice CSV files based on video code')
    parser.add_argument('--video_code', type=str, required=True,
                      help='Video code (01-15) to process')
    parser.add_argument('--game', type=str, required=True,
                      help='museum/bowling/gallery/travel/boss/candy')
    parser.add_argument('--perspective', type=str, required=False,
                      help='C/L, default C')
    return parser.parse_args()

args = parse_args()
video_code = args.video_code    # e.g. '04'
print(f"Set video code to: {video_code}")

perspective = "C"  # default value
if args.perspective and args.perspective.lower() in ["l", "left"]:
    perspective = "L"
print(f"Set perspective to: {perspective}")

game = "museum"
if args.game.lower() in ["museum", "bowling", "gallery", "travel", "boss", "candy"]:
    game = args.game.lower()
print(f"Process game: {game}")

video_folder_map = {
    '01': '25.1.20_01',
    '02': '25.1.9_02',
    '03': '25.1.10_03',
    '04': '25.1.10_04',
    '05': '25.1.13_05',
    '06': '25.1.13_06',
    '07': '25.1.14_07',
    '08': '25.1.15_08',
    '09': '25.1.15_09',
    '10': '25.1.16_10',
    '11': '25.1.16_11',
    '12': '25.1.17_12',
    '13': '25.1.17_13',
    '14': '25.1.20_14',
    '15': '25.1.21_15'
}
video_folder = video_folder_map[video_code]

name = f"{video_code}_{game}_{perspective}"                             # e.g. "04_museum_C"
csv_folder    = f"./data/output/slice_csv{video_code}/CSV_{name}"
video_folder  = f"./Projection/raw video/{video_folder}/Clips_{name}.mp4"   # now a folder of clip_*.mp4 files
output_folder = f"./data/output/previews/{name}"

# 检查video_folder是否存在
if not os.path.exists(video_folder):
    print(f"[ERROR] Video folder not found: {video_folder}")
    exit(1)

# 检查csv_folder是否存在
if not os.path.exists(csv_folder):
    print(f"[ERROR] CSV folder not found: {csv_folder}")
    exit(1)

# 检查video_folder是否为空
if not any(f.lower().endswith('.mp4') for f in os.listdir(video_folder)):
    print(f"[ERROR] No MP4 files found in video folder: {video_folder}")
    exit(1)

# 检查csv_folder是否为空
if not any(f.lower().endswith('.csv') for f in os.listdir(csv_folder)):
    print(f"[ERROR] No CSV files found in CSV folder: {csv_folder}")
    exit(1)

    
camera_json   = f"Projection/CVFrame-main/data/extrinsics_middle.json"      # default perspective is C
if perspective == "L":
    camera_json   = f"Projection/CVFrame-main/data/extrinsics_left.json"    # change to left if perspective is L

# 检查相机参数文件是否存在
if not os.path.exists(camera_json):
    print(f"[ERROR] Camera parameters file not found: {camera_json}")
    exit(1)

# load camera intrinsics+extrinsics
with open(camera_json, 'r') as f:
    cam = json.load(f)
K   = np.array(cam['camera_matrix'])       # 3×3
P4  = np.array(cam['best_extrinsic'])      # 3×4
proj = K.dot(P4)                           # full 3×4 projection
print(f"[INFO] Loaded camera, proj matrix shape = {proj.shape}")

# create output folder
os.makedirs(output_folder, exist_ok=True)

# build a map of (row,rep) → video file using new clip_ naming
video_map = {}
for vid in sorted(os.listdir(video_folder)):
    if not vid.lower().endswith(".mp4"):
        continue
    # match any filename ending in _row{row}_rep{rep}.mp4
    # m = re.match(r".*_row([0-9]+)_rep([0-9]+)\.mp4$", vid)
    m = re.match(r"row([0-9]+)_rep([0-9]+).*\.mp4$", vid)
    if m:
        key = (m.group(1), m.group(2))
        video_map[key] = os.path.join(video_folder, vid)
    else:
        print(f"[WARN] skipping unrecognized video name: {vid}")

for csv_name in sorted(os.listdir(csv_folder)):
    if not csv_name.lower().endswith(".csv"):
        continue

    # parse slice CSV name: slice_{code}_{name}_{suffix}_row{row}_rep{rep}_{action}.csv
    m = re.match(
        r"csv_([^_]+)_([^_]+)_([^_]+)_row([0-9]+)_rep([0-9]+)_(.+?)\.csv$",
        csv_name
    )

    if not m:
        print(f"[WARN] skipping unrecognized csv name: {csv_name}")
        continue
    code, vid_name, suffix, row_i, rep, action = m.groups()
    csv_path = os.path.join(csv_folder, csv_name)

    # lookup matching video by (row,rep)
    video_path = video_map.get((row_i, rep))
    if not video_path:
        print(f"[WARN] no clip for row{row_i}_rep{rep}, skipping")
        continue

    # build preview filename with code, video name, suffix, row & rep, action
    action_safe = action.replace(' ', '-')
    preview_name = (
        f"preview_{code}_{vid_name}_{suffix}_"
        f"row{row_i}_rep{rep}_{action_safe}.mp4"
    )
    out_path = os.path.join(output_folder, preview_name)

    print(f"[INFO] Processing pair: {csv_name} ⟷ {os.path.basename(video_path)}")

    # load CSV slice
    df3d = pd.read_csv(csv_path)
    print(f"       CSV rows = {len(df3d)}, columns = {len(df3d.columns)}")

    # open video clip
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    W   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(out_path, fourcc, fps, (W, H))
    print(f"       Video opened: {W}×{H}@{fps:.1f}fps → writing {out_path}")

    # project & write each frame
    for i, row in df3d.iterrows():
        ret, img = cap.read()
        if not ret:
            print("       [WARN] video ended prematurely")
            break

        # detect joint columns like '0_x','0_y','0_z',…
        joint_cols = [c for c in df3d.columns if "_" in c]
        if joint_cols:
            jids = sorted({c.split("_")[0] for c in joint_cols},
                          key=lambda s: int(s))
            for jid in jids:
                X3d = np.array([
                    row[f"{jid}_x"],
                    row[f"{jid}_y"],
                    row[f"{jid}_z"],
                    1.0
                ])
                x2d = proj.dot(X3d)
                if not np.isfinite(x2d).all() or x2d[2] == 0:
                    continue
                u, v = int(x2d[0]/x2d[2]), int(x2d[1]/x2d[2])
                cv2.circle(img, (u, v), 5, (0,0,255), -1)
        else:
            # fallback single‐point case
            row = row.rename(lambda s: s.strip().lower())
            X3d = np.array([row['x'], row['y'], row['z'], 1.0])
            x2d = proj.dot(X3d)
            if np.isfinite(x2d).all() and x2d[2] != 0:
                u, v = int(x2d[0]/x2d[2]), int(x2d[1]/x2d[2])
                cv2.circle(img, (u, v), 5, (0,0,255), -1)

        # frame counter
        cv2.putText(img, f"frame {i+1}/{len(df3d)}",
                    (10, H-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

        out.write(img)

    cap.release()
    out.release()
    print(f"[OK] Saved preview: {out_path}\n")