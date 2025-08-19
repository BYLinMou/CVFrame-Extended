"""
Extract 17 keypoints (H36M order) from Perception‑Neuron CSV — *legacy header parser*

This version mimics the logic of the working 24‑kp extractor:
• Reads the marker names from the **first row of the file** (after one skip row)
• Uses the same 13‑char slice trick to isolate the joint name
• Distinguishes between “Bone”, “Bone Marker”, etc.

Example:
    python extract_17_keypoint_from_csv.py --video_code 04
"""

import pandas as pd
import numpy as np
from tqdm import tqdm
import argparse, glob, os

# ──────────────────────────────────────────────────────────────────────────────
# 17‑joint dictionary (Human3.6M style order)
# ──────────────────────────────────────────────────────────────────────────────
TARGET_JOINTS_ORDERED = {
    0:  [('Hip', 'Bone')],
    1:  [('WaistRBack', 'Bone Marker'), ('WaistRFront', 'Bone Marker')],
    2:  [('RKneeOut', 'Bone Marker')],
    3:  [('RFoot', 'Bone')],
    4:  [('WaistLBack', 'Bone Marker'), ('WaistLFront', 'Bone Marker')],
    5:  [('LKneeOut', 'Bone Marker')],
    6:  [('LFoot', 'Bone')],
    7:  [('BackLeft', 'Bone Marker'), ('BackRight', 'Bone Marker')],
    8:  [('Neck', 'Bone')],
    9:  [],                     # Pelvis top (dummy joint) — always NaN
    10: [('Head', 'Bone')],
    11: [('LShoulder', 'Bone')],
    12: [('LElbowOut', 'Bone Marker')],
    13: [('LWristIn', 'Bone Marker'), ('LWristOut', 'Bone Marker')],
    14: [('RShoulder', 'Bone')],
    15: [('RElbowOut', 'Bone Marker')],
    16: [('RWristIn', 'Bone Marker'), ('RWristOut', 'Bone Marker')],
}
NUM_JOINTS = 17 # len(TARGET_JOINTS_ORDERED)

# ──────────────────────────────────────────────────────────────────────────────
def parse_args():
    ap = argparse.ArgumentParser(description='Slice CSV files down to 17 keypoints')
    ap.add_argument('--video_code', required=True, help='e.g. 04; 01-15')
    ap.add_argument('--input_dir',  default='./data/csv')
    ap.add_argument('--output_dir', default='./data/extracted_csv')
    ap.add_argument('--skiprows', type=int, default=1,
                    help='Rows to skip before header row (default 1 for PN CSV)')
    return ap.parse_args()

# ──────────────────────────────────────────────────────────────────────────────
def extract_3d_points_from_csv(input_path: str, output_path: str, skiprows: int = 1):
    # Read the first few rows to get header and type information before chunking
    temp_df = pd.read_csv(input_path, skiprows=skiprows, nrows=6, low_memory=False)
    type_list = list(temp_df.iloc[0].index)
    header_row = temp_df.iloc[0]

    selected_columns = []
    for joint_id in range(NUM_JOINTS):
        joint_defs = TARGET_JOINTS_ORDERED[joint_id]

        # Joint intentionally blank (id 9)
        if not joint_defs:
            selected_columns.append(None)
            continue

        if len(joint_defs) == 2:  # need average of two markers
            cols_a = [i for i, val in enumerate(header_row)
                      if str(val)[13:] == joint_defs[0][0] and type_list[i].startswith(joint_defs[0][1])][-3:]
            cols_b = [i for i, val in enumerate(header_row)
                      if str(val)[13:] == joint_defs[1][0] and type_list[i].startswith(joint_defs[1][1])][-3:]
            selected_columns.append((cols_a, cols_b))
        else:                      # single marker
            cols = [i for i, val in enumerate(header_row)
                    if str(val)[13:] == joint_defs[0][0] and type_list[i].startswith(joint_defs[0][1])][-3:]
            selected_columns.append(cols)

    columns = [f"{i}_{axis}" for i in range(NUM_JOINTS) for axis in ['x','y','z']]
    first_chunk = True

    # Use chunksize for memory efficiency
    for chunk_idx, df_chunk in tqdm(
        enumerate(pd.read_csv(input_path, skiprows=skiprows + 5, chunksize=2000, low_memory=False)), # Adjusted skiprows
        desc=os.path.basename(input_path)
    ):
        frame_start_idx = chunk_idx * 2000 # Approximate starting index for current chunk

        chunk_data = []
        for row_idx, row in df_chunk.iterrows():
            frame_data = []
            try:
                for cols in selected_columns:
                    if cols is None:
                        frame_data.extend([np.nan]*3)
                    elif isinstance(cols, tuple):
                        vals_a = pd.to_numeric(row.iloc[cols[0]], errors='coerce').values
                        vals_b = pd.to_numeric(row.iloc[cols[1]], errors='coerce').values
                        avg = (vals_a + vals_b) / 2
                        frame_data.extend(avg)
                    else:
                        vals = pd.to_numeric(row.iloc[cols], errors='coerce').values
                        frame_data.extend(vals)
                chunk_data.append(frame_data)
            except Exception as e:
                print(f"❌ Frame {frame_start_idx + row_idx} failed: {e}\n")
                frame_data = [np.nan] * (NUM_JOINTS * 3)
                chunk_data.append(frame_data)

        # Convert chunk data to DataFrame and save
        processed_chunk_df = pd.DataFrame(chunk_data, columns=columns)
        if first_chunk:
            processed_chunk_df.to_csv(output_path, index=False, mode='w')
            first_chunk = False
        else:
            processed_chunk_df.to_csv(output_path, index=False, mode='a', header=False)

    print(f"✅ Saved → {output_path}\n")

# ──────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import os
    args = parse_args()

    in_dir  = os.path.join(args.input_dir,  args.video_code)
    out_dir = os.path.join(args.output_dir, f"{args.video_code}_17kp")
    os.makedirs(out_dir, exist_ok=True)

    for inp_csv in glob.glob(os.path.join(in_dir, '*.csv')):
        base = os.path.splitext(os.path.basename(inp_csv))[0]
        out_csv = os.path.join(out_dir, f"{base}_17kp.csv")
        extract_3d_points_from_csv(inp_csv, out_csv, args.skiprows)
