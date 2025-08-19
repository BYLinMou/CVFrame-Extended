import os
import pandas as pd
from utils.extract_24_keypoint_from_csv import extract_3d_points_from_csv

# offset_excel_path = r"C:\Users\16850\Desktop\csv_offset.xlsx"
# base_video_path = "D:/cv_data/raw_video"
# base_csv_path = "D:/cv_data/smoothed"

def check_files_exist(excel_path, video_base_path, csv_base_path):
    # 检查 Excel 是否为空
    try:
        xl = pd.ExcelFile(excel_path)
    except Exception as e:
        print(f"无法打开 Excel 文件: {e}")
        return

    if not xl.sheet_names:
        print("Excel 文件为空，不进行检查。")
        return
    err = False

    for sheet in xl.sheet_names:
        # print(f"\n 正在处理 sheet: {sheet}")
        df = xl.parse(sheet)
        if df.empty:
            print(f"⚠️ sheet {sheet} 内容为空，跳过。")
            continue

        video_root = os.path.join(video_base_path, sheet)

        for _, row in df.iterrows():
            video_name = str(row['video_name']).strip()
            csv_name = str(row['csv_name']).strip()

            video_path = os.path.join(video_root, video_name)
            csv_path = os.path.join(csv_base_path, csv_name)

            video_exists = os.path.exists(video_path)
            csv_exists = os.path.exists(csv_path)
            
            if not video_exists or not csv_exists:
                err = True
                print(f"⚠️ 文件缺失:")
                if not video_exists:
                    print(f"  - 视频文件缺失: {video_path}")
                if not csv_exists:
                    print(f"  - CSV 文件缺失: {csv_path}")
            
            # print(f"📹 {video_name}: {'✅ 存在' if video_exists else '❌ 不存在'}")
            # print(f"📄 {csv_name}: {'✅ 存在' if csv_exists else '❌ 不存在'}")
    return err



# if not check_files_exist(offset_excel_path, base_video_path, base_csv_path):
#     print("✅ 所有文件存在，继续执行。")

import cv2  # 用于获取视频帧数

def get_video_frame_count(video_path):
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return -1
        frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        return frames
    except Exception as e:
        print(f"⚠️ 无法读取视频帧数: {video_path}, 错误: {e}")
        return -1

def generate_3d_csvs(excel_path, video_base_path, csv_base_path, output_dir, skiprows=1):
    try:
        xl = pd.ExcelFile(excel_path)
    except Exception as e:
        print(f"❌ 无法打开 Excel 文件: {e}")
        return

    if not xl.sheet_names:
        print("⚠️ Excel 文件为空，不生成。")
        return

    os.makedirs(output_dir, exist_ok=True)

    for sheet in xl.sheet_names:
        df = xl.parse(sheet)
        if df.empty:
            print(f"⚠️ sheet {sheet} 内容为空，跳过。")
            continue

        video_root = os.path.join(video_base_path, sheet)
        sheet_output_dir = os.path.join(output_dir, sheet)
        os.makedirs(sheet_output_dir, exist_ok=True)

        for _, row in df.iterrows():
            video_name = str(row['video_name']).strip()
            csv_name = str(row['csv_name']).strip()
            offset = int(row['offset']) if 'offset' in row and pd.notna(row['offset']) else 0

            video_path = os.path.join(video_root, video_name)
            input_csv_path = os.path.join(csv_base_path, csv_name)
            output_csv_path = os.path.join(sheet_output_dir, f"{os.path.splitext(video_name)[0]}_3d.csv")

            if not os.path.exists(video_path):
                print(f"❌ 找不到视频文件: {video_path}，跳过。")
                continue
            if not os.path.exists(input_csv_path):
                print(f"❌ 找不到原始 CSV 文件: {input_csv_path}，跳过。")
                continue

            total_frames = get_video_frame_count(video_path)
            if total_frames <= 0:
                print(f"⚠️ 无法读取视频帧数: {video_path}，跳过。")
                continue
            if os.path.exists(output_csv_path):
                print(f"✅ 已存在输出文件: {output_csv_path}，跳过。")
                continue
            print(f"🔄 正在处理: {csv_name} -> {output_csv_path} | offset={offset}, total_frames={total_frames}")
            try:
                extract_3d_points_from_csv(input_csv_path, output_csv_path, total_frames=total_frames, skiprows=skiprows, offset=offset)
            except Exception as e:
                print(f"❌ 处理失败: {csv_name}, 错误: {e}")


if __name__ == "__main__":
    offset_excel_path = "./input/new_csv_offset.xlsx"
    base_video_path = "/data/sda1/mocap_data/raw_video"
    base_csv_path = "/data/sda1/mocap_data/smoothed"
    output_dir = "./output"

    # 先检查是否缺文件
    if not check_files_exist(offset_excel_path, base_video_path, base_csv_path):
        print("所有文件存在，开始生成3D CSV文件。")
        generate_3d_csvs(offset_excel_path, base_video_path, base_csv_path, output_dir)
