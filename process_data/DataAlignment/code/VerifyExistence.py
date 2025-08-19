import os
import pandas as pd
import subprocess

# 讀取 Excel 檔案
excel_path = 'paired_video_names.xlsx'  # 請改成你的檔名
df = pd.read_excel(excel_path)

# 各子檔案夾路徑
video_dir = 'videos'
csv_dir = 'csvs'

# 檢查檔案是否存在的函數
def check_file_exists(folder, filename):
    return os.path.isfile(os.path.join(folder, filename))

# 取得影片編碼資訊
def get_video_codec(filepath):
    if not os.path.isfile(filepath):
        return "檔案不存在"
    try:
        # 取得第一條影片stream的codec name
        result = subprocess.run(
            [
                'ffprobe', '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=codec_name',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                filepath
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        codec = result.stdout.strip()
        if codec:
            return codec
        else:
            return "無法取得編碼"
    except Exception as e:
        return f"錯誤：{e}"

video_cols = ['video_C_name', 'video_L_name', 'video_C_name_2', 'video_L_name_2']
csv_cols = ['csv_name_1', 'csv_name_2']

for idx, row in df.iterrows():
    print(f"Row {idx+2}:")
    for col in video_cols:
        fname = str(row[col])
        if pd.notna(fname) and fname != 'nan':
            path = os.path.join(video_dir, fname)
            exists = check_file_exists(video_dir, fname)
            if exists:
                codec = get_video_codec(path)
                print(f"  {col} ({fname}): 存在, 編碼: {codec}")
            else:
                print(f"  {col} ({fname}): 不存在")
    for col in csv_cols:
        fname = str(row[col])
        if pd.notna(fname) and fname != 'nan':
            exists = check_file_exists(csv_dir, fname)
            print(f"  {col} ({fname}): {'存在' if exists else '不存在'}")
    print("-" * 40)