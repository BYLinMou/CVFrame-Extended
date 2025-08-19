
"""
slice_csv_ver2.py
-----------------
Re‑written version of **slice_csv.py**

Key changes
-----------
1. No hard‑coded ``sheet_csv_map`` / ``sheet_video_map``, rely on the
   *offset Excel* which must contain **video_name**, **csv_name**, **offset**.
2. Iterate over every row of that offset sheet; each row fully describes one
   video/CSV pair that needs slicing.
3. ``slice_csv_based_on_offsets`` now receives ``offset_value`` and
   ``video_name`` directly, so it doesn’t need to look them up again.
4. ``sheet_name`` is inferred from the *csv_name* with a tiny helper that maps
   keywords (museum, bowling, …) to the DataCollection sheet names.

Usage
-----
Adjust the CONFIGURATION block (folder paths / codes) and run:

    python slice_csv_ver2.py

All sliced CSVs are saved under:

    <output_path>/CSV_<video_name_without_ext>/csv_<video_name_without_ext>_row<row>_rep<rep>_<action>.csv
"""

import os
import pandas as pd
import argparse


# ---------------------------------------------------------------------------
# CONFIGURATION –––> CHANGE THESE TO SUIT YOUR DIRECTORY STRUCTURE
# ---------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(description='Slice CSV files based on video code')
    parser.add_argument('--video_code', type=str, required=True,
                      help='Video code (01-15) to process')
    return parser.parse_args()

args = parse_args()
video_code = args.video_code                                # e.g. '04'
excel_path = f"./data/DataCollection/DataCollection_{video_code}.xlsx"
offset_excel_path = "./new_csv_offset.xlsx"                 # the new offset file
csv_folder_path = f"./data/extracted_csv/{video_code}_17kp"      # where extracted CSVs live
output_path = f"./data/output/slice_csv{video_code}"        # where you want slices

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
video_folder_name = video_folder_map[video_code]            # sheet name inside offset_excel


# ---------------------------------------------------------------------------
# Helper: infer DataCollection sheet name from csv/video keywords
# ---------------------------------------------------------------------------
_KEYWORD_TO_SHEET = {
    "museum":  "Gaming Museum",
    "bowling": "BowlingVR",
    "gallery": "Gallery of H.K. History",
    "travel":  "Hong Kong Time Travel",
    "boss":    "Boss Fight",
    "candy":   "Candy Shooter",
}


def get_sheet_name_from_csv(csv_name: str) -> str:
    """Return the DataCollection sheet name that goes with *csv_name*.

    >>> get_sheet_name_from_csv('04_candy_3d_points.csv')
    'Candy Shooter'
    """
    lower = csv_name.lower()
    for kw, sheet in _KEYWORD_TO_SHEET.items():
        if kw in lower:
            return sheet
    raise ValueError(
        f"Unable to infer sheet name – add a mapping for “{csv_name}”.")


# ---------------------------------------------------------------------------
# Core worker
# ---------------------------------------------------------------------------
def slice_csv_based_on_offsets(
        csv_path: str,
        sheet_name: str,
        offset_value: float,
        data_collection_path: str,
        output_root: str,
        video_name: str,
) -> None:
    """Slice *csv_path* according to repetition frames & *offset_value*.

    One CSV is produced for every (row, repetition) pair found in the
    DataCollection sheet.  Files are written under::

        <output_root>/CSV_<video_name_without_ext>/
    """
    # ------------------------------------------------------------------
    # 1. Load DataCollection sheet (defines repetitions)
    # ------------------------------------------------------------------
    df_meta = pd.read_excel(data_collection_path, sheet_name=sheet_name)
    # df_meta.fillna(method='ffill', inplace=True)
    # df_meta.ffill(inplace=True)

    rep_start_cols = [c for c in df_meta.columns
                      if "Repetition" in c and "Start" in c]
    rep_end_cols = [c for c in df_meta.columns
                    if "Repetition" in c and "End" in c]

    # ------------------------------------------------------------------
    # 2. Load 3‑D points CSV for this video
    # ------------------------------------------------------------------
    df_points = pd.read_csv(csv_path)
    # df_points.fillna(method='ffill', inplace=True)
    # df_points.ffill(inplace=True)
    csv_length = len(df_points) - 1
    print(f"{csv_path}: {csv_length} frames")

    # ------------------------------------------------------------------
    # 3. Iterate through every (row, repetition) to cut slices
    # ------------------------------------------------------------------
    action = "unknown"
    action_safe = "unknown"

    for row_idx, row in df_meta.iterrows():
        for rep in range(1, len(rep_start_cols) + 1):
            start_col = f"Repetition {rep} Start"
            end_col = f"Repetition {rep} End"

            start_frame = row.get(start_col)
            end_frame = row.get(end_col)
            action_tmp = row.get("Action")
            if not pd.isna(action_tmp):
                action = str(action_tmp)
                action_safe = action.replace(' ', '-')

            if pd.notna(start_frame) and pd.notna(end_frame):

                # length = end_frame - start_frame
                # print(f"start at {start_frame}, end at {end_frame}, length is {length}")

                # Apply offset
                start_frame = int(float(start_frame) + offset_value)
                end_frame = int(float(end_frame) + offset_value)

                # if length <= 0: continue            

                # start_frame = max(start_frame, 0)  # guard against negatives
                if start_frame > csv_length: return # return if action start in another csv
                if start_frame < 0: break # next action if the start_frame is negative
                
                #sliced = df_points.iloc[start_frame:end_frame]
                sliced = df_points.iloc[start_frame:end_frame+1] # slice exclude end frame so +1

                # Build output path
                base_video_name = os.path.splitext(video_name)[0]
                out_dir = os.path.join(output_root, f"CSV_{base_video_name}")
                os.makedirs(out_dir, exist_ok=True)

                out_csv = os.path.join(
                    out_dir,
                    f"csv_{base_video_name}_row{row_idx + 1}_rep{rep}_{action_safe}.csv"
                )
                sliced.to_csv(out_csv, index=False)
                print(f"✓ Saved: {out_csv}")


# ---------------------------------------------------------------------------
# Main driver
# ---------------------------------------------------------------------------
def main() -> None:
    # Load offset sheet
    offset_df = pd.read_excel(offset_excel_path, sheet_name=video_folder_name)

    # Ensure output root exists
    os.makedirs(output_path, exist_ok=True)

    # Process every row (one row ⇔ one video / csv / offset triple)
    for _, rec in offset_df.iterrows():
        csv_name = str(rec["csv_name"][:-4]).strip() + "_17kp.csv"
        video_name = str(rec["video_name"]).strip()
        offset_val = float(rec["offset"])

        csv_path = os.path.join(csv_folder_path, csv_name)
        if pd.isna(offset_val):     # skip if offset value is empty
            print(f"⚠ Offset value is null → skip: {video_name}: {csv_path}")
            continue
        
        if not os.path.isfile(csv_path):
            print(f"⚠ CSV not found → skip: {csv_path}")
            continue

        try:
            sheet_name = get_sheet_name_from_csv(csv_name)
        except ValueError as e:
            print(f"⚠ {e} – skipping {csv_name}")
            continue

        slice_csv_based_on_offsets(
            csv_path=csv_path,
            sheet_name=sheet_name,
            offset_value=offset_val,
            data_collection_path=excel_path,
            output_root=output_path,
            video_name=video_name,
        )


if __name__ == "__main__":
    main()
