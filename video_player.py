import cv2
import threading
import time

class VideoPlayer:
    def __init__(self, video_path):
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise ValueError(f"Cannot open video file '{video_path}'")
        
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.current_frame = 0
        self.is_playing = False
        
        # Caching mechanism: store the last fetched frame and its index
        self.cached_frame = None
        self.cached_frame_index = -1
        
        # Multi-threaded decoding attributes
        self.lock = threading.Lock()
        self.async_frame = None
        self.async_frame_index = -1
        self.stop_async_thread = False
        self.async_thread = threading.Thread(target=self._async_decode, daemon=True)
        self.async_thread.start()

    def _async_decode(self):
        """Background thread to pre-decode the next frame when playing sequentially."""
        while not self.stop_async_thread:
            # Determine the next frame index we want to prefetch.
            with self.lock:
                next_index = self.cached_frame_index + 1
            if self.is_playing and self.current_frame == next_index and self.async_frame_index != next_index:
                # Wrap VideoCapture.read() inside the lock to avoid concurrent access.
                with self.lock:
                    ret, frame = self.cap.read()
                if ret:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    with self.lock:
                        self.async_frame = frame_rgb
                        self.async_frame_index = next_index
                else:
                    time.sleep(0.005)
            else:
                time.sleep(0.005)

    def get_frame(self):
        # Check if the asynchronous decoder has pre-fetched the required frame.
        with self.lock:
            if self.async_frame_index == self.current_frame:
                self.cached_frame = self.async_frame
                self.cached_frame_index = self.current_frame
                self.async_frame = None
                self.async_frame_index = -1
                return self.cached_frame

        # Use cached frame if it matches the current frame.
        if self.cached_frame_index == self.current_frame and self.cached_frame is not None:
            return self.cached_frame
        
        # For sequential play, if the next frame is requested, read directly.
        if self.is_playing and self.cached_frame_index != -1 and self.current_frame == self.cached_frame_index + 1:
            with self.lock:
                ret, frame = self.cap.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.cached_frame = frame_rgb
                self.cached_frame_index = self.current_frame
                return frame_rgb
            else:
                return None
        
        # For random access or non-sequential requests, use set() to seek.
        with self.lock:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            ret, frame = self.cap.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.cached_frame = frame_rgb
            self.cached_frame_index = self.current_frame
            return frame_rgb
        return None

    def get_current_time(self):
        return self.current_frame / self.fps

    def next_frame(self):
        self.current_frame = min(self.frame_count - 1, self.current_frame + 1)

    def prev_frame(self):
        self.current_frame = max(0, self.current_frame - 1)

    def jump_seconds(self, seconds):
        # Perform the seek operation while holding the lock to prevent concurrent access.
        with self.lock:
            new_frame = self.current_frame + int(seconds * self.fps)
            self.current_frame = max(0, min(self.frame_count - 1, new_frame))
            # Invalidate cached frames to avoid stale data.
            self.cached_frame = None
            self.cached_frame_index = -1
            self.async_frame = None
            self.async_frame_index = -1
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)

    def release(self):
        self.stop_async_thread = True
        if self.async_thread.is_alive():
            self.async_thread.join(timeout=1)
        self.cap.release()
