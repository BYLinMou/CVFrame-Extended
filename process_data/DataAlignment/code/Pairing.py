import pandas as pd

# 讀取csv文件
df = pd.read_excel('summary.xlsx')

# 依據 video_C_name 和 video_L_name 分組
grouped = df.groupby(['video_C_name', 'video_L_name'])

results = []

for (c_name, l_name), group in grouped:
    csv_names = group['csv_name'].tolist()
    if len(csv_names) >= 2:
        # 只配對第一個和第二個
        results.append([
            c_name,
            l_name,
            c_name.replace('.mp4', '_2.mp4'),
            l_name.replace('.mp4', '_2.mp4'),
            csv_names[0],
            csv_names[1]
        ])

# 轉成 DataFrame
out_df = pd.DataFrame(results, columns=[
    'video_C_name', 'video_L_name',
    'video_C_name_2', 'video_L_name_2',
    'csv_name_1', 'csv_name_2'
])

# 輸出結果到csv
out_df.to_excel('paired_video_names.xlsx', index=False)
print(out_df)