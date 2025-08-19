import os
import pandas as pd

# 讀取 Excel 檔案
df = pd.read_excel('paired_video_names.xlsx')

# 定義資料夾
video_dir = 'videos'
csv_dir = 'csvs'

# 把所有要刪除的檔案名稱集中
video_files = []
csv_files = []

# 根據你的欄位名提取檔名
video_cols = ['video_C_name', 'video_L_name', 'video_C_name_2', 'video_L_name_2']
csv_cols = ['csv_name_1', 'csv_name_2']

for col in video_cols:
    video_files += df[col].dropna().tolist()

for col in csv_cols:
    csv_files += df[col].dropna().tolist()

# 刪除 video 檔案
for filename in video_files:
    file_path = os.path.join(video_dir, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f'Deleted: {file_path}')
    else:
        print(f'Not found: {file_path}')

# 刪除 csv 檔案
for filename in csv_files:
    file_path = os.path.join(csv_dir, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f'Deleted: {file_path}')
    else:
        print(f'Not found: {file_path}')