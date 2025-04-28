import pandas as pd
from tqdm import tqdm
import numpy as np


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
    22: [('RHandOut','Bone Marker')],
    23: [('RHandOut','Bone Marker')],
}


def extract_3d_points_from_csv(input_path: str, output_path: str, skiprows: int = 1):
    df = pd.read_csv(input_path, skiprows=skiprows, low_memory=False)
    type_list = list(df.iloc[0].index)
    header_row = df.iloc[0]
    df = df.iloc[5:].reset_index(drop=True)
    
    selected_columns = []

    for joint_id in range(24):
        joint_defs = TARGET_JOINTS_ORDERED[joint_id]
        if len(joint_defs) == 2:
            cols_0 = [i for i, val in enumerate(header_row)
                      if str(val)[13:] == joint_defs[0][0] and type_list[i].startswith(joint_defs[0][1])][-3:]
            cols_1 = [i for i, val in enumerate(header_row)
                      if str(val)[13:] == joint_defs[1][0] and type_list[i].startswith(joint_defs[1][1])][-3:]
            selected_columns.append((cols_0, cols_1))
        else:
            cols = [i for i, val in enumerate(header_row)
                    if str(val)[13:] == joint_defs[0][0] and type_list[i].startswith(joint_defs[0][1])][-3:]
            selected_columns.append(cols)

    final_data = []
    for frame_idx, row in tqdm(df.iterrows(), total=len(df), desc="提取3D点"):
        frame_data = []
        try:
            for cols in selected_columns:
                if isinstance(cols, tuple):  # 平均两个 marker
                    vals_0 = pd.to_numeric(row.iloc[cols[0]], errors='coerce').values
                    vals_1 = pd.to_numeric(row.iloc[cols[1]], errors='coerce').values
                    avg = (vals_0 + vals_1) / 2
                    frame_data.extend(avg)
                else:
                    vals = pd.to_numeric(row.iloc[cols], errors='coerce').values
                    frame_data.extend(vals)
            final_data.append(frame_data)
        except Exception as e:
            print(f"\n❌ 第 {frame_idx} 帧出错：{e}")
            # 可选：跳过这一帧，或填入 NaN
            frame_data = [np.nan] * (24 * 3)
            final_data.append(frame_data)

    columns = [f"{i}_{axis}" for i in range(24) for axis in ['x', 'y', 'z']]
    df_out = pd.DataFrame(final_data, columns=columns)
    df_out.to_csv(output_path, index=False)
    print(f"\n 提取完成，结果已保存至 {output_path}")


if __name__ == "__main__":
    import os, glob

    input_dir  = "./data/csv"
    output_dir = "./data/extracted_csv"
    os.makedirs(output_dir, exist_ok=True)

    for input_csv in glob.glob(os.path.join(input_dir, "*.csv")):
        fname     = os.path.splitext(os.path.basename(input_csv))[0]
        output_csv = os.path.join(output_dir, f"{fname}_3d_points.csv")
        extract_3d_points_from_csv(input_csv, output_csv)