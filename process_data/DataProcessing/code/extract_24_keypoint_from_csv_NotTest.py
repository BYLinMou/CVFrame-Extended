'''
This version was created by simply modifying extract_24_keypoint_from_csv.py
after determining the improved solution for extract_17_keypoint_from_csv.py.
However, it has not been tested.
'''

import pandas as pd
from tqdm import tqdm
import numpy as np
import argparse
import os
import glob

def parse_args():
    parser = argparse.ArgumentParser(description='Slice CSV files based on video code')
    parser.add_argument('--video_code', type=str, required=True,
                      help='Video code (01-15) to process')
    return parser.parse_args()
args = parse_args()
video_code = args.video_code    # e.g."01", change video_code here, change input/output path at line85-86

TARGET_JOINTS_ORDERED = {
    0:  [('Hip','Bone')],
    1:  [('LThigh','Bone')],
    2:  [('RThigh','Bone')],
    3:  [('Ab','Bone')],
    4:  [('LShin','Bone')],
    5:  [('RShin','Bone')],
    6:  [('BackLeft','Bone Marker'),('BackRight','Bone Marker')],
    7:  [('LFoot','Bone')],
    8:  [('RFoot','Bone')],
    9:  [('BackTop','Bone Marker')],
    10: [('LToe','Bone')],
    11: [('RToe','Bone')],
    12: [('Neck','Bone')],
    13: [('LShoulder','Bone')],
    14: [('RShoulder','Bone')],
    15: [('Head','Bone')],
    16: [('LUArm','Bone')],
    17: [('RUArm','Bone')],
    18: [('LFArm','Bone')],
    19: [('RFArm','Bone')],
    20: [('LWristIn','Bone Marker'),('LWristOut','Bone Marker')],
    21: [('RWristIn','Bone Marker'),('RWristOut','Bone Marker')],
    22: [('LHandOut','Bone Marker')],
    23: [('RHandOut','Bone Marker')],
}


def extract_3d_points_from_csv(input_path: str, output_path: str, skiprows: int = 1):
    # Read the first few rows to get header and type information before chunking
    # If skiprows=1, this temp_df reads original lines 2 and 3.
    # temp_header_df.columns will be original CSV line 2 values (Type, Bone, ...).
    # temp_header_df.iloc[0] will be original CSV line 3 values (Name, Skeleton 001:Hip, ...).
    temp_header_df = pd.read_csv(input_path, skiprows=skiprows, nrows=2, low_memory=False)

    # type_list should be the values from original CSV line 2, which are the column names of temp_header_df.
    type_list = list(temp_header_df.columns)

    # header_row for joint names (e.g., 'Skeleton 001:Hip') should be original CSV line 3.
    header_row_for_joint_names = temp_header_df.iloc[0]
    
    selected_columns = []

    for joint_id in range(24): # NUM_JOINTS = 24
        joint_defs = TARGET_JOINTS_ORDERED[joint_id]

        if len(joint_defs) == 2:
            cols_0 = [i for i, val in enumerate(header_row_for_joint_names)
                      if str(val)[13:] == joint_defs[0][0] and type_list[i].startswith(joint_defs[0][1])][-3:]
            cols_1 = [i for i, val in enumerate(header_row_for_joint_names)
                      if str(val)[13:] == joint_defs[1][0] and type_list[i].startswith(joint_defs[1][1])][-3:]
            selected_columns.append((cols_0, cols_1))
        else:
            cols = [i for i, val in enumerate(header_row_for_joint_names)
                    if str(val)[13:] == joint_defs[0][0] and type_list[i].startswith(joint_defs[0][1])][-3:]
            selected_columns.append(cols)

    columns = [f"{i}_{axis}" for i in range(24) for axis in ['x', 'y', 'z']] # NUM_JOINTS = 24
    first_chunk = True

    # Use chunksize for memory efficiency, starting from the actual data rows (original CSV line 8)
    # skiprows = original_skiprows (1) + (lines 2-7, which is 6 lines) = 7.
    # This means the header for the main data will be line 7. Pandas will use it as header.
    for chunk_idx, df_chunk in tqdm(
        enumerate(pd.read_csv(input_path, skiprows=skiprows + 6, chunksize=2000, low_memory=False)),
        desc=os.path.basename(input_path)
    ):
        frame_start_idx = chunk_idx * 2000 # Approximate starting index for current chunk

        chunk_data = []
        for row_idx, row in df_chunk.iterrows():
            frame_data = []
            try:
                for cols_indices in selected_columns:
                    if isinstance(cols_indices, tuple):  # 平均两个 marker
                        vals_a = pd.to_numeric(row.iloc[cols_indices[0]], errors='coerce').values
                        vals_b = pd.to_numeric(row.iloc[cols_indices[1]], errors='coerce').values
                        avg = (vals_a + vals_b) / 2
                        frame_data.extend(avg)
                    else:
                        vals = pd.to_numeric(row.iloc[cols_indices], errors='coerce').values
                        frame_data.extend(vals)
                chunk_data.append(frame_data)
            except Exception as e:
                print(f"❌ 第 {frame_start_idx + row_idx} 帧出错：{e}")
                frame_data = [np.nan] * (24 * 3) # NUM_JOINTS * 3
                chunk_data.append(frame_data)

        processed_chunk_df = pd.DataFrame(chunk_data, columns=columns)
        if first_chunk:
            processed_chunk_df.to_csv(output_path, index=False, mode='w')
            first_chunk = False
        else:
            processed_chunk_df.to_csv(output_path, index=False, mode='a', header=False)

    print(f"✅ 提取完成，結果已保存至 {output_path}")


if __name__ == "__main__":
    args = parse_args()
    video_code = args.video_code

    input_dir  = os.path.join("./data/csv", video_code)
    output_dir = os.path.join("./data/extracted_csv", video_code)
    os.makedirs(output_dir, exist_ok=True)

    for input_csv in glob.glob(os.path.join(input_dir, "*.csv")):
        fname     = os.path.splitext(os.path.basename(input_csv))[0]
        output_csv = os.path.join(output_dir, f"{fname}_3d_points.csv")
        extract_3d_points_from_csv(input_csv, output_csv)