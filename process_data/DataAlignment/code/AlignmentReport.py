import pandas as pd
import cv2
import os

def get_csv_line_count(csv_path: str, skiprows: int) -> int:
    """高效地計算 CSV 檔案中跳過指定標頭行後的資料行數。"""
    if not os.path.exists(csv_path):
        return 0
    try:
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            for _ in range(skiprows):
                next(f, None) # 跳過標頭行
            return sum(1 for line in f)
    except Exception as e:
        print(f"Error counting lines in CSV file {csv_path}: {e}")
        return 0

def get_video_frame_count(video_path):
    """獲取影片的總幀數。"""
    if not os.path.exists(video_path):
        print(f"警告：影片檔案未找到： {video_path}")
        return 0
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"錯誤：無法打開影片檔案： {video_path}")
        return 0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return frame_count

def align_media_data(
    offset_filepath: str,
    root_base_path: str,
    csv_base_path: str,
    CSV_HEADER_ROWS: int = 1,
    output_summary_path: str = "summary.xlsx", # 新增的參數
):
    """
    根據 new_csv_offset.xlsx（多 sheet）對齊影片和 CSV 數據。
    每個 sheet 名稱對應 root 目錄下的一個資料夾，該資料夾下存放影片。
    Args:
        offset_filepath (str): offset.xlsx 檔案的路徑。
        root_base_path (str): root 目錄路徑（各資料夾存放影片）。
        csv_base_path (str): CSV 檔案的基礎路徑。
        CSV_HEADER_ROWS (int): CSV 標題行數。
        output_summary_path (str): summary.xlsx 報告的輸出路徑。
    Returns:
        list: 包含每組對齊資訊的字典列表。
    """
    try:
        xls = pd.ExcelFile(offset_filepath)
    except FileNotFoundError:
        print(f"Error: Offset file not found: {offset_filepath}")
        return []
    except Exception as e:
        print(f"Error: Failed to read offset file: {e}")
        return []

    aligned_results = []
    summary_rows = [] # 在這裡初始化 summary_rows

    for sheet_name in xls.sheet_names:
        print(f"Processing sheet (directory): {sheet_name}")
        try:
            df_offset = pd.read_excel(xls, sheet_name=sheet_name)
        except Exception as e:
            print(f"  Error: Failed to read sheet {sheet_name}: {e}")
            continue
        # 根據 sheet_name 組合影片資料夾路徑
        video_base_path = os.path.join(root_base_path, sheet_name)
        for csv_name, group in df_offset.groupby("csv_name"):
            print(f"  Processing group: {csv_name}")
            try:
                c_row = group[group["video_name"].str.contains("_C.mp4")].iloc[0]
                l_row = group[group["video_name"].str.contains("_L.mp4")].iloc[0]
            except Exception as e:
                print(f"    Error: Cannot find C or L video row for {csv_name}: {e}")
                continue
            video_c_name = c_row["video_name"]
            video_l_name = l_row["video_name"]
            offset_c = c_row["offset"]
            offset_l = l_row["offset"]
            print(f"    Original Offset C: {offset_c}, Original Offset L: {offset_l}")
            video_c_path = os.path.join(video_base_path, video_c_name)
            video_l_path = os.path.join(video_base_path, video_l_name)
            csv_path = os.path.join(csv_base_path, csv_name)

            # 讀取 CSV，支援多標題行
            # 使用 get_csv_line_count 避免將整個檔案載入記憶體
            total_lines_csv = get_csv_line_count(csv_path, CSV_HEADER_ROWS)
            if total_lines_csv == 0:
                if not os.path.exists(csv_path):
                    print(f"    Warning: CSV file not found: {csv_path}")
                else:
                    print(f"    Error: Failed to read CSV file or it's empty after skipping headers: {csv_path}")

            total_frames_c = get_video_frame_count(video_c_path)
            total_frames_l = get_video_frame_count(video_l_path)

            
            print(f"    Total frames of C video: {total_frames_c}, Total frames of L video: {total_frames_l}, Total lines of CSV: {total_lines_csv}")

            # 計算 start_C, start_L, start_CSV
            start_c, start_l, start_csv = 0, 0, 0
            if offset_c >= 0 or offset_l >= 0:
                m = max(offset_c, offset_l)
                start_c = (m - offset_c) if offset_c < m else 0
                start_l = (m - offset_l) if offset_l < m else 0
                start_csv = m
            else:
                start_c = abs(offset_c)
                start_l = abs(offset_l)
                start_csv = 0
            # 處理多標題行
            start_csv += CSV_HEADER_ROWS
            # 確保起始幀/行不超出總長度
            start_c = min(start_c, total_frames_c)
            start_l = min(start_l, total_frames_l)
            start_csv = min(start_csv, total_lines_csv + CSV_HEADER_ROWS)
            # 計算各自可用長度
            length_c = total_frames_c - start_c
            length_l = total_frames_l - start_l
            length_csv = total_lines_csv - start_csv
            l_min = min(length_c, length_l, length_csv)
            l_min = max(0, l_min)
            print(f"    Result: start_C={start_c}, start_L={start_l}, start_CSV={start_csv}, L_min={l_min}")
            aligned_results.append({
                "sheet": sheet_name,
                "csv_name": csv_name,
                "video_C_path": video_c_path,
                "video_L_path": video_l_path,
                "csv_path": csv_path,
                "start_C": start_c,
                "start_L": start_l,
                "start_CSV": start_csv,
                "L_min": l_min,
            })

            # NEW: 即時生成 summary.xlsx 報告
            current_summary_item = {
                "csv_name": csv_name,
                "video_C_name": video_c_name, # 結合資料夾名稱和影片名稱
                "video_L_name": video_l_name, # 結合資料夾名稱和影片名稱
                "start_C": start_c,
                "end_C": start_c + l_min - 1,
                "start_L": start_l,
                "end_L": start_l + l_min - 1,
                "start_CSV": start_csv,
                "end_CSV": start_csv + l_min - 1,
                "L_min": l_min,
            }
            summary_rows.append(current_summary_item)

            df_summary = pd.DataFrame(summary_rows)
            df_summary = df_summary.sort_values("csv_name")
            df_summary.to_excel(output_summary_path, index=False)
            print(f"  summary.xlsx report updated for group: {csv_name}.\n")

    return aligned_results

# def crop_video(input_video_path: str, output_video_path: str, start_frame: int, num_frames_to_crop: int):
#     """Use OpenCV to crop video."""
#     cap = cv2.VideoCapture(input_video_path)
#     if not cap.isOpened():
#         print(f"Error: Cannot open video file for cropping: {input_video_path}")
#         return
#
#     fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Recommended: 'mp4v' or 'XVID'
#     fps = cap.get(cv2.CAP_PROP_FPS)
#     width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
#     height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
#
#     out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
#     if not out.isOpened():
#         print(f"Error: Cannot create output video file: {output_video_path}")
#         cap.release()
#         return
#
#     current_frame_idx = 0
#     frames_written = 0
#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             break  # End of video or read failure
#
#         if current_frame_idx >= start_frame and frames_written < num_frames_to_crop:
#             out.write(frame)
#             frames_written += 1
#         elif frames_written >= num_frames_to_crop:
#             break
#
#         current_frame_idx += 1
#
#     cap.release()
#     out.release()
#     print(f"  Cropped and saved {frames_written} frames from {input_video_path} to {output_video_path}")

# def slice_csv(input_csv_path: str, output_csv_path: str, start_row: int, num_rows_to_slice: int):
#     """Use pandas to crop CSV file."""
#     try:
#         df = pd.read_csv(input_csv_path)
#         sliced_df = df.iloc[start_row : start_row + num_rows_to_slice]
#         sliced_df.to_csv(output_csv_path, index=False)
#         print(f"  Cropped and saved {len(sliced_df)} rows from {input_csv_path} to {output_csv_path}")
#     except Exception as e:
#         print(f"Error: Failed to crop CSV file {input_csv_path}: {e}")

# def perform_alignment_and_save(alignment_results: list, output_video_dir: str, output_csv_dir: str):
#     """
#     Crop videos and CSV files according to alignment results and save to specified directories.
#     """
#     os.makedirs(output_video_dir, exist_ok=True)
#     os.makedirs(output_csv_dir, exist_ok=True)
#
#     print(f"\nSaving aligned files to:\nVideos: {output_video_dir}\nCSV: {output_csv_dir}")
#
#     for item in alignment_results:
#         csv_name = item["csv_name"]
#         video_c_path = item["video_C_path"]
#         video_l_path = item["video_L_path"]
#         csv_path = item["csv_path"]
#         start_c = item["start_C"]
#         start_l = item["start_L"]
#         start_csv = item["start_CSV"]
#         l_min = item["L_min"]
#
#         print(f"\nProcessing group: {csv_name}")
#
#         # Process C video
#         if os.path.exists(video_c_path) and l_min > 0:
#             output_c_video_name = f"aligned_{os.path.basename(video_c_path)}"
#             output_c_video_path = os.path.join(output_video_dir, output_c_video_name)
#             crop_video(video_c_path, output_c_video_path, start_c, l_min)
#         else:
#             print(f"  Skipping C video cropping: file does not exist or crop length is 0 ({video_c_path}).")
#
#         # Process L video
#         if os.path.exists(video_l_path) and l_min > 0:
#             output_l_video_name = f"aligned_{os.path.basename(video_l_path)}"
#             output_l_video_path = os.path.join(output_video_dir, output_l_video_name)
#             crop_video(video_l_path, output_l_video_path, start_l, l_min)
#         else:
#             print(f"  Skipping L video cropping: file does not exist or crop length is 0 ({video_l_path}).")
#
#         # Process CSV
#         if os.path.exists(csv_path) and l_min > 0:
#             output_csv_name = f"aligned_{os.path.basename(csv_path)}"
#             output_csv_path = os.path.join(output_csv_dir, output_csv_name)
#             slice_csv(csv_path, output_csv_path, start_csv, l_min)
#         else:
#             print(f"  Skipping CSV cropping: file does not exist or crop length is 0 ({csv_path}).")

if __name__ == "__main__":
    # ====== Please fill in your actual paths below ======
    offset_file = os.path.join(os.path.dirname(__file__), "new_csv_offset.xlsx")
    video_base_input_directory = os.path.dirname(__file__)
    csv_base_input_directory = os.path.join(os.path.dirname(__file__), "smoothed")
    # Adjustable CSV header row count
    CSV_HEADER_ROWS = 7  # Default is 2, please adjust according to your CSV
    # =====================================

    summary_output_file_path = os.path.join(os.path.dirname(__file__), "summary.xlsx") # 定義 summary.xlsx 的輸出路徑

    # Calculate alignment parameters
    alignment_info = align_media_data(
        offset_filepath=offset_file,
        root_base_path=video_base_input_directory,
        csv_base_path=csv_base_input_directory,
        CSV_HEADER_ROWS=CSV_HEADER_ROWS,
        output_summary_path=summary_output_file_path, # 傳遞輸出路徑
    )

    if alignment_info:
        print("\n--- Alignment Parameters Calculated ---")
        '''
        for item in alignment_info:
            print(f"  CSV Name: {item['csv_name']}")
            print(f"    C video start frame: {item['start_C']}")
            print(f"    C video end frame: {item['start_C'] + item['L_min']}")
            print(f"    L video start frame: {item['start_L']}")
            print(f"    L video end frame: {item['start_L'] + item['L_min']}")
            print(f"    CSV start row: {item['start_CSV']}")
            print(f"    CSV end row: {item['start_CSV'] + item['L_min']}")
            print(f"    Common crop length (L_min): {item['L_min']}")
            print("-" * 20)
        '''
    else:
        print("\nNo alignment information generated. Skipping save operation.")

    # 不再需要此處的 summary.xlsx 生成程式碼，因為它已移至 align_media_data 內部。
    # No actual cropping will be performed, crop_video/slice_csv are kept as comments
