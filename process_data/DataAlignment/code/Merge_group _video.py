import os
import pandas as pd
import subprocess
import cv2
import csv
import numpy as np # 新增導入
from itertools import zip_longest
from typing import List, Tuple # 新增導入

excel_path = 'paired_video_names.xlsx'
video_dir = 'cropped_videos'
csv_dir = 'sliced_csvs'
merged_video_dir = 'merged_videos'
merged_csv_dir = 'merged_csvs'

os.makedirs(merged_video_dir, exist_ok=True)
os.makedirs(merged_csv_dir, exist_ok=True)

# ---------- 全局參數 ----------
N_HEADER  = 7                          # 表頭行數
CHUNKSIZE = 5_000                    # 每批讀幾列資料（依機器調整）
ENCODING  = 'utf-8'

# ---------- 工具函數 ----------

def read_header(path:str, n_header:int) -> pd.MultiIndex:
    """
    將前 n_header 行讀成 DataFrame，再轉 MultiIndex。
    不做任何補值或 forward-fill；和原檔 100% 相同。
    """
    rows = []
    with open(path, 'r', encoding=ENCODING) as f:
        reader = csv.reader(f)
        for _ in range(n_header):
            rows.append(next(reader))
    max_len = max(len(r) for r in rows)
    for r in rows:
        r.extend([''] * (max_len - len(r)))
    tuples = list(zip_longest(*rows, fillvalue="")) # 使用 zip_longest 確保所有欄位都包含在內
    return pd.MultiIndex.from_tuples(tuples)

def write_header(path:str, columns:pd.MultiIndex, n_header:int, sep=','):
    """把 MultiIndex 還原為 n_header 行文字並寫檔"""
    with open(path, 'w', encoding=ENCODING, newline='') as f:
        for level in range(n_header):
            line = sep.join([col[level] if level < len(col) else ''
                             for col in columns])
            f.write(line + '\n')

def union_columns(col_a:pd.MultiIndex, col_b:pd.MultiIndex) -> pd.MultiIndex:
    """先保留 target 的欄位順序，再接上 source 中『不存在』的欄位"""
    merged: List[Tuple[str, ...]] = list(col_a)
    merged.extend([c for c in col_b if c not in col_a])
    return pd.MultiIndex.from_tuples(merged)


def get_video_frame_count(video_path):
    """用ffprobe獲取視訊幀數"""
    cmd = [
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=nb_read_frames', '-of', 'default=nokey=1:noprint_wrappers=1',
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return int(result.stdout.strip())

def get_csv_data_row_count(csv_path, n_header=7):
    """獲取CSV檔案的資料行數（排除表頭）"""
    with open(csv_path, 'r', encoding='utf-8') as f:
        for _ in range(n_header):
            next(f) # skip header
        return sum(1 for line in f)

def merge_video_ffmpeg(file1, file2, output):
    """用ffmpeg合併兩個mp4（直接串接）"""
    list_file = 'input_list.txt'
    with open(list_file, 'w', encoding='utf-8') as f:
        f.write(f"file '{os.path.abspath(file1)}'\n")
        f.write(f"file '{os.path.abspath(file2)}'\n")
    cmd = [
        'ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_file,
        '-c', 'copy', output, '-y'
    ]
    subprocess.run(cmd, check=True)
    os.remove(list_file)
    frame_count = get_video_frame_count(output)
    print(f"🎥 合併後的視訊 {os.path.basename(output)} 共有 {frame_count} 幀")

def csv_headers_match(file1, file2, n_header=7):
    """比對前n_header行是否一致"""
    with open(file1, 'r', encoding='utf-8') as f1, open(file2, 'r', encoding='utf-8') as f2:
        h1 = [next(f1) for _ in range(n_header)]
        h2 = [next(f2) for _ in range(n_header)]
        return h1 == h2

# ---------- 主流程函式 ----------
def merge_csv_chunked(target_path:str, source_path:str, output_path:str):
    # 1. 先取兩邊的 MultiIndex 欄位
    col_tgt = read_header(target_path, N_HEADER)
    col_src = read_header(source_path, N_HEADER)
    merged_cols = union_columns(col_tgt, col_src)

    # 2. 先輸出表頭
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    write_header(output_path, merged_cols, N_HEADER)

    # 3. 依塊寫入 target ⇢ source 資料
    for path, cols in [(target_path, col_tgt), (source_path, col_src)]:
        for chunk in pd.read_csv(
            path,
            skiprows=N_HEADER,
            header=None,
            names=cols,          # 把 7 行 MultiIndex 指定回欄名
            encoding=ENCODING,
            chunksize=CHUNKSIZE,
            low_memory=False
        ):
            # 3-1 依 merged_cols 對齊，缺的欄位補 NaN
            chunk = chunk.reindex(columns=merged_cols)
            # 3-2 寫入（追加），不再寫 header
            chunk.to_csv(output_path,
                         mode='a',
                         header=False,
                         index=False)

    print(f'✅ 合併完成 → {output_path}')

df = pd.read_excel(excel_path)

video_cols = [('video_C_name', 'video_C_name_2'), ('video_L_name', 'video_L_name_2')]
csv_cols = [('csv_name_1', 'csv_name_2')]

for idx, row in df.iterrows():
    # # 處理視頻
    # for col1, col2 in video_cols:
    #     name1, name2 = row[col1], row[col2]
    #     if pd.notna(name1) and pd.notna(name2):
    #         f1 = os.path.join(video_dir, name1)
    #         f2 = os.path.join(video_dir, name2)
    #         if os.path.isfile(f1) and os.path.isfile(f2):
    #             merged_name = name1.replace('.mp4', '_merged.mp4')
    #             merged_path = os.path.join(merged_video_dir, merged_name)
    #             merge_video_ffmpeg(f1, f2, merged_path)
    #             print(f"✅ 合併 {name1} + {name2} -> {merged_name}")

    # 處理csv
    for col1, col2 in csv_cols:
        name1, name2 = row[col1], row[col2]
        if pd.notna(name1) and pd.notna(name2):
            f1 = os.path.join(csv_dir, name1)
            f2 = os.path.join(csv_dir, name2)
            if os.path.isfile(f1) and os.path.isfile(f2):
                # merged_name = name1.replace('.csv', '_merged.csv')
                merged_name = name1
                merged_path = os.path.join(merged_csv_dir, merged_name)
                # 替換為新的分塊合併函數
                merge_csv_chunked(f1, f2, merged_path)
                # Removed header check as the new function handles it internally
                # if csv_headers_match(f1, f2, n_header=7):
                #     merged_name = name1.replace('.csv', '_merged.csv')
                #     merged_path = os.path.join(merged_csv_dir, merged_name)
                #     merge_csv(f1, f2, merged_path, n_header=7)
                #     print(f"✅ 合併 {name1} + {name2} -> {merged_name}")
                # else:
                #     print(f"⚠️ {name1} 和 {name2} 前7行表頭不同，不合併！")