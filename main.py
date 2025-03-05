import cv2
import argparse

def format_time(seconds):
    """ 将秒转换为 HH:MM:SS 格式 """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def show_frame(cap, current_frame, frame_count, fps):
    """ 读取并显示当前帧 """
    cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
    ret, frame = cap.read()
    if not ret:
        return False

    # 计算当前时间戳
    current_time = (current_frame / fps)
    time_text = f"Frame: {current_frame}/{frame_count} | Time: {format_time(current_time)}"

    # 在左上角绘制文本
    cv2.putText(frame, time_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # 显示帧
    cv2.imshow("Video Player", frame)
    return True

def video_player(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Cannot open video file '{video_path}'.")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)  # 视频帧率
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    current_frame = 0
    is_playing = True  # 播放状态

    while True:
        if is_playing:
            if not show_frame(cap, current_frame, frame_count, fps):
                print("Error: Cannot read frame.")
                break
            current_frame += 1  # 自动播放下一帧
            key = cv2.waitKey(int(1000 / fps))  # 控制播放速度
        else:
            key = cv2.waitKey(0)  # 暂停状态下等待用户输入

        # 按键控制
        if key == 27:  # 按'ESC' 退出
            break
        elif key == ord(' '):  # 按 '空格' 暂停/播放
            is_playing = not is_playing
        elif key == ord('a'):  # 按 'A' 跳到上一帧
            is_playing = False
            current_frame = max(0, current_frame - 1)
            show_frame(cap, current_frame, frame_count, fps)  # **手动刷新帧**
        elif key == ord('d'):  # 按 'D' 跳到下一帧
            is_playing = False
            current_frame = min(frame_count - 1, current_frame + 1)
            show_frame(cap, current_frame, frame_count, fps)  # **手动刷新帧**
        elif key == ord('q'):  # 按 '←' (左方向键) 跳 1 秒
            is_playing = False
            current_frame = max(0, current_frame - int(fps))
            show_frame(cap, current_frame, frame_count, fps)  # **手动刷新帧**
        elif key == ord('e'):  # 按 '→' (右方向键) 跳 1 秒
            is_playing = False
            current_frame = min(frame_count - 1, current_frame + int(fps))
            show_frame(cap, current_frame, frame_count, fps)  # **手动刷新帧**

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple Video Player with Frame and Time Display")
    parser.add_argument("video_path", type=str, help="Path to the video file")
    args = parser.parse_args()

    video_player(args.video_path)
