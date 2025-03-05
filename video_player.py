import cv2

class VideoPlayer:
    def __init__(self, video_path):
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise ValueError(f"Cannot open video file '{video_path}'")
        
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.current_frame = 0
        self.is_playing = False

    def get_frame(self):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.cap.read()
        if ret:
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return None

    def get_current_time(self):
        return self.current_frame / self.fps

    def next_frame(self):
        self.current_frame = min(self.frame_count - 1, self.current_frame + 1)

    def prev_frame(self):
        self.current_frame = max(0, self.current_frame - 1)

    def jump_seconds(self, seconds):
        new_frame = self.current_frame + int(seconds * self.fps)
        self.current_frame = max(0, min(self.frame_count - 1, new_frame))

    def release(self):
        self.cap.release() 
