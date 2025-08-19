import cv2
import pandas as pd
import os
import csv

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

def crop_video(input_video_path: str, output_video_path: str, start_frame: int, end_frame: int):
    """Use OpenCV to crop video."""
    cap = cv2.VideoCapture(input_video_path)
    if not cap.isOpened():
        print(f"Error: Cannot open video file for cropping: {input_video_path}")
        return

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Recommended: 'mp4v' or 'XVID'
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
    if not out.isOpened():
        print(f"Error: Cannot create output video file: {output_video_path}")
        cap.release()
        return

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"  (影片 {input_video_path} 的總幀數: {total_frames})")

    current_frame_idx = 0
    frames_written = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break  # End of video or read failure

        if current_frame_idx >= start_frame and current_frame_idx <= end_frame:
            out.write(frame)
            frames_written += 1
        elif current_frame_idx > end_frame:
            break

        current_frame_idx += 1

    cap.release()
    out.release()
    print(f"  Cropped and saved {frames_written} frames from {input_video_path} to {output_video_path} (frames {start_frame}-{end_frame})")

def slice_csv(input_csv_path: str, output_csv_path: str, start_row: int, end_row: int):
    """Slice CSV file by reading row by row."""
    try:
        rows_written = 0
        with open(input_csv_path, 'r', newline='', encoding='utf-8') as infile, \
             open(output_csv_path, 'w', newline='', encoding='utf-8') as outfile:
            reader = csv.reader(infile)
            writer = csv.writer(outfile)

            # Read and write the first 7 header rows
            for _ in range(7):
                try:
                    header_row = next(reader)
                    writer.writerow(header_row)
                except StopIteration:
                    print(f"Warning: CSV file {input_csv_path} has fewer than 7 rows. Not enough header rows to copy.")
                    break

            current_data_row_idx = 7
            for row in reader:
                if current_data_row_idx >= start_row and current_data_row_idx <= end_row:
                    writer.writerow(row)
                    rows_written += 1
                elif current_data_row_idx > end_row:
                    break
                current_data_row_idx += 1

        print(f"  Cropped and saved {rows_written} data rows (after 7 headers) from {input_csv_path} to {output_csv_path} (rows {start_row}-{end_row})")
    except Exception as e:
        print(f"Error: Failed to slice CSV file {input_csv_path}: {e}")

def get_non_conflicting_path(path):
    base, ext = os.path.splitext(path)
    counter = 2
    new_path = path
    while os.path.exists(new_path):
        new_path = f"{base}_{counter}{ext}"
        counter += 1
    return new_path

def main():
    print("Ver 0.1")

    excel_file_path = os.path.join(os.path.dirname(__file__), "summary.xlsx")  # 請將此路徑替換為您的 Excel 檔案路徑

    try:
        df = pd.read_excel(excel_file_path)
    except FileNotFoundError:
        print(f"錯誤：找不到 Excel 檔案：{excel_file_path}")
        return
    except Exception as e:
        print(f"錯誤：讀取 Excel 檔案時發生錯誤：{e}")
        return

    print("成功讀取 Excel 檔案。")
    print("Excel 檔案內容：")
    print(df)

    for index, row in df.iterrows():
        csv_name = row["csv_name"]
        video_C_name = row["video_C_name"]
        video_L_name = row["video_L_name"]
        start_C = int(row["start_C"])
        end_C = int(row["end_C"])
        start_L = int(row["start_L"])
        end_L = int(row["end_L"])
        start_CSV = int(row["start_CSV"])
        end_CSV = int(row["end_CSV"])
        L_min = int(row["L_min"])

        print(f"處理行 {index + 1}:")
        print(f"  csv_name: {csv_name}")
        print(f"  video_C_name: {video_C_name}")
        print(f"  video_L_name: {video_L_name}")
        print(f"  start_C: {start_C}, end_C: {end_C}")
        print(f"  start_L: {start_L}, end_L: {end_L}")
        print(f"  start_CSV: {start_CSV}, end_CSV: {end_CSV}")
        print(f"  L_min: {L_min}")

        # 根據 video_C_name 和 video_L_name 的前綴查找對應的影片資料夾
        video_C_prefix = video_C_name[:2]
        video_L_prefix = video_L_name[:2]

        video_C_folder = video_folder_map.get(video_C_prefix)
        video_L_folder = video_folder_map.get(video_L_prefix)

        if not video_C_folder:
            print(f"警告：找不到 video_C_name {video_C_name} 的對應影片資料夾 ({video_C_folder})。跳過此行影片處理。")
            continue
        if not video_L_folder:
            print(f"警告：找不到 video_L_name {video_L_name} 的對應影片資料夾 ({video_L_folder})。跳過此行影片處理。")
            continue

        # 建構輸入路徑
        current_dir = os.path.dirname(__file__)
        video_C_input_path = os.path.join(current_dir, video_C_folder, video_C_name)
        video_L_input_path = os.path.join(current_dir, video_L_folder, video_L_name)
        csv_input_path = os.path.join(current_dir, "smoothed", csv_name)

        # 建構輸出資料夾並確保它們存在
        output_videos_dir = os.path.join(current_dir, "cropped_videos")
        output_csvs_dir = os.path.join(current_dir, "sliced_csvs")

        os.makedirs(output_videos_dir, exist_ok=True)
        os.makedirs(output_csvs_dir, exist_ok=True)

        # 建構輸出路徑
        output_video_C_path = get_non_conflicting_path(os.path.join(output_videos_dir, f"{video_C_name}"))
        output_video_L_path = get_non_conflicting_path(os.path.join(output_videos_dir, f"{video_L_name}"))
        output_csv_path = os.path.join(output_csvs_dir, f"{csv_name}")

        print(f"  video_C 輸入路徑: {video_C_input_path}")
        print(f"  video_L 輸入路徑: {video_L_input_path}")
        print(f"  CSV 輸入路徑: {csv_input_path}")

        # 呼叫 crop_video 和 slice_csv 函數
        crop_video(video_C_input_path, output_video_C_path, start_C, end_C)
        crop_video(video_L_input_path, output_video_L_path, start_L, end_L)
        slice_csv(csv_input_path, output_csv_path, start_CSV, end_CSV)

if __name__ == "__main__":
    main()
