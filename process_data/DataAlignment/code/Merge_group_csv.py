#!/usr/bin/env python3
# Merge_group.py — 直向 append 版

import csv
import os
import sys
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile

# ───────── 固定參數 ─────────
EXCEL_PATH       = 'paired_video_names.xlsx'
VIDEO_DIR        = 'cropped_videos'
CSV_DIR          = 'sliced_csvs'
MERGED_VIDEO_DIR = 'merged_videos'
MERGED_CSV_DIR   = 'merged_csvs'

N_HEADER  = 7          # CSV 表頭行數
ENCODING  = 'utf-8'
SEP       = ','        # 欄位分隔符

# ───────── 影片 ─────────
def merge_video_ffmpeg(f1: Path, f2: Path, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile('w', delete=False) as tmp:
        tmp.write(f"file '{f1.as_posix()}'\n")
        tmp.write(f"file '{f2.as_posix()}'\n")
        concat_list = tmp.name
    cmd = [
        'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
        '-f', 'concat', '-safe', '0', '-i', concat_list,
        '-c', 'copy', str(out_path)
    ]
    print(f'⏯  concat {f1.name} + {f2.name} → {out_path.name}')
    try:
        subprocess.check_call(cmd)
        print(f'✅  saved {out_path}')
    except subprocess.CalledProcessError as e:
        print(f'❌  ffmpeg error: {e}')
    finally:
        os.remove(concat_list)

# ───────── CSV ─────────
def read_header_rows(path: Path, n_header: int, sep: str, encoding: str) -> list[list[str]]:
    """讀前 n_header 行，保留原樣分割後的 list；行長度不一致沒關係。"""
    rows = []
    with open(path, encoding=encoding, newline='') as fp:
        reader = csv.reader(fp, delimiter=sep)
        for _ in range(n_header):
            try:
                rows.append(next(reader))
            except StopIteration:
                break
    return rows

def union_header_rows(rows_a: list[list[str]], rows_b: list[list[str]]) -> tuple[list[list[str]], list[tuple]]:
    """
    合併header並產生欄位key順序（tuple），key只看name(第4行)、第6行、第7行，不看id(第5行)
    """
    # 第一行：只保留A
    merged = [rows_a[0] if len(rows_a) > 0 else []]
    # 第二行：空行
    merged.append([])

    # 多層header
    start, end = 2, 6  # 3~7行（index 2~6）
    group_a = rows_a[start:end+1]
    group_b = rows_b[start:end+1]

    # key: (name, 第6行, 第7行)
    def keys_from_cols(cols):
        # cols: list of tuple(header3, header4, header5, header6, header7)
        return [(col[1], col[3], col[4]) for col in cols]  # index 3=第4行, 5=第6行, 6=第7行

    cols_a = list(zip(*group_a)) if group_a else []
    cols_b = list(zip(*group_b)) if group_b else []
    keys_a = keys_from_cols(cols_a)
    keys_b = keys_from_cols(cols_b)

    # union順序：A先，B新key append
    merged_keys = keys_a.copy()
    merged_cols = cols_a.copy()
    for k, cb in zip(keys_b, cols_b):
        if k not in merged_keys:
            merged_keys.append(k)
            merged_cols.append(cb)

    # 合併後header（轉回行格式）
    merged_multi = [list(level) for level in zip(*merged_cols)]
    col_counts = [len(row) for row in merged_multi]
    if len(set(col_counts)) != 1:
        raise ValueError(f"合併後第3~7行欄位數不一致：{col_counts}")

    merged.extend(merged_multi)
    return merged, merged_keys, merged_cols  # merged_keys順序對應merged_cols

def merge_csv_append(a_path: Path, b_path: Path, out_path: Path):
    print(f'📑  append {a_path.name} + {b_path.name} → {out_path.name}')
    rows_a = read_header_rows(a_path, N_HEADER, SEP, ENCODING)
    rows_b = read_header_rows(b_path, N_HEADER, SEP, ENCODING)
    merged_hdr, merged_keys, merged_cols = union_header_rows(rows_a, rows_b)
    n_cols = len(merged_keys)

    # 取得A/B的key對應欄位index
    def get_col_keys(rows):
        group = rows[2:7]
        cols = list(zip(*group)) if group else []
        return [(col[1], col[3], col[4]) for col in cols]  # (name, 第6行, 第7行)

    keys_a = get_col_keys(rows_a)
    keys_b = get_col_keys(rows_b)
    key_to_idx_a = {k: i for i, k in enumerate(keys_a)}
    key_to_idx_b = {k: i for i, k in enumerate(keys_b)}

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding=ENCODING, newline='') as fout:
        writer = csv.writer(fout, delimiter=SEP)
        writer.writerows(merged_hdr)

        def _copy_data(src: Path, tag: str, key_to_idx):
            with open(src, encoding=ENCODING, newline='') as fp:
                reader = csv.reader(fp, delimiter=SEP)
                # skip header lines
                for _ in range(N_HEADER):
                    next(reader, None)
                rows = 0
                for row in reader:
                    row_out = []
                    for k in merged_keys:
                        idx = key_to_idx.get(k)
                        if idx is not None and idx < len(row):
                            row_out.append(row[idx])
                        else:
                            row_out.append('')
                    writer.writerow(row_out)
                    rows += 1
            print(f'    {tag}: {rows:,} rows copied')

        _copy_data(a_path, 'A', key_to_idx_a)
        _copy_data(b_path, 'B', key_to_idx_b)
    print('✅  CSV done\n')

# ───────── 主流程 ─────────
def main():
    try:
        import pandas as pd
    except ImportError:
        sys.exit('請先安裝 pandas 以讀取 Excel： pip install pandas openpyxl')

    if not Path(EXCEL_PATH).is_file():
        sys.exit(f'找不到 {EXCEL_PATH}')

    import pandas as pd
    df = pd.read_excel(EXCEL_PATH, engine='openpyxl')

    video_cols = [('video_C_name', 'video_C_name_2'),
                  ('video_L_name', 'video_L_name_2')]
    csv_cols   = [('csv_name_1', 'csv_name_2')]

    for idx, row in df.iterrows():
        print('─' * 60)
        print(f'▶ Row {idx+1}')

        # csv
        for c1, c2 in csv_cols:
            n1, n2 = row.get(c1), row.get(c2)
            if pd.isna(n1) or pd.isna(n2):
                continue
            f1, f2 = Path(CSV_DIR, n1), Path(CSV_DIR, n2)
            if not f1.is_file() or not f2.is_file():
                print('⚠️  CSV missing')
                continue
            out_csv = Path(MERGED_CSV_DIR, f'{f1.stem}.csv')
            merge_csv_append(f1, f2, out_csv)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n中斷。')