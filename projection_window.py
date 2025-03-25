import sys
import os
import json
import cv2
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, 
    QFileDialog, QSlider, QSpinBox, QApplication, QMessageBox, QLineEdit, QGridLayout
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QTimer

# --- Added import for VideoPlayer ---
from video_player import VideoPlayer  # use your video_player module

class ProjectionWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("3D Points Projection")
        self.player = None    # Changed: using VideoPlayer instance
        self.intrinsics = None
        self.extrinsics = None
        self.rvec = None
        self.tvec = None
        self.points3d = None  # Expected shape: (frame_count, num_points, 3)
        self.frame_offset = 0  # Adjustment for synchronization
        self.loaded_video_filename = ""
        self.loaded_intrinsics_filename = ""
        self.loaded_extrinsics_filename = ""
        self.loaded_points_filename = ""

        self.init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

    def init_ui(self):
        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout()

        # Video display label reserves empty space when no video is loaded.
        self.video_label = QLabel("")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(200, 150)  # Reserved space similar to main_window
        layout.addWidget(self.video_label)

        # File load controls: Change each load widget to use a horizontal layout.
        file_grid = QGridLayout()
        # Intrinsics
        self.btn_load_intr = QPushButton("Load Intrinsics")
        self.btn_load_intr.setFixedSize(150, 30)
        self.label_loaded_intr = QLabel("No File Loaded")
        intrinsics_widget = QWidget()
        intrinsics_layout = QHBoxLayout()  # changed from QVBoxLayout to QHBoxLayout
        intrinsics_layout.setContentsMargins(0, 0, 0, 0)
        intrinsics_layout.addWidget(self.btn_load_intr, alignment=Qt.AlignCenter)
        intrinsics_layout.addWidget(self.label_loaded_intr, alignment=Qt.AlignCenter)
        intrinsics_widget.setLayout(intrinsics_layout)
        # Extrinsics
        self.btn_load_extr = QPushButton("Load Extrinsics")
        self.btn_load_extr.setFixedSize(150, 30)
        self.label_loaded_extr = QLabel("No File Loaded")
        extrinsics_widget = QWidget()
        extrinsics_layout = QHBoxLayout()  # changed from QVBoxLayout to QHBoxLayout
        extrinsics_layout.setContentsMargins(0, 0, 0, 0)
        extrinsics_layout.addWidget(self.btn_load_extr, alignment=Qt.AlignCenter)
        extrinsics_layout.addWidget(self.label_loaded_extr, alignment=Qt.AlignCenter)
        extrinsics_widget.setLayout(extrinsics_layout)
        # Video
        self.btn_load_video = QPushButton("Load Video")
        self.btn_load_video.setFixedSize(150, 30)
        self.label_loaded_video = QLabel("No File Loaded")
        video_widget = QWidget()
        video_layout = QHBoxLayout()  # changed from QVBoxLayout to QHBoxLayout
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.addWidget(self.btn_load_video, alignment=Qt.AlignCenter)
        video_layout.addWidget(self.label_loaded_video, alignment=Qt.AlignCenter)
        video_widget.setLayout(video_layout)

        
        # Points
        self.btn_load_points = QPushButton("Load 3D Data (CSV)")
        self.btn_load_points.setFixedSize(150, 30)
        self.label_loaded_points = QLabel("No File Loaded")
        points_widget = QWidget()
        points_layout = QHBoxLayout()  # changed from QVBoxLayout to QHBoxLayout
        points_layout.setContentsMargins(0, 0, 0, 0)
        points_layout.addWidget(self.btn_load_points, alignment=Qt.AlignCenter)
        points_layout.addWidget(self.label_loaded_points, alignment=Qt.AlignCenter)
        points_widget.setLayout(points_layout)

        file_grid.addWidget(intrinsics_widget, 0, 0)
        file_grid.addWidget(extrinsics_widget, 0, 1)
        file_grid.addWidget(video_widget, 1, 0)
        file_grid.addWidget(points_widget, 1, 1)
        
        layout.addLayout(file_grid)

        # Connect file loading buttons
        self.btn_load_intr.clicked.connect(self.load_intrinsics)
        self.btn_load_extr.clicked.connect(self.load_extrinsics)
        self.btn_load_video.clicked.connect(self.load_video)
        self.btn_load_points.clicked.connect(self.load_points)

        # Synchronization offset controls
        sync_layout = QHBoxLayout()
        sync_layout.addWidget(QLabel("Frame Offset:"))
        self.offset_spin = QSpinBox()
        self.offset_spin.setRange(-1000, 1000)
        self.offset_spin.valueChanged.connect(self.change_offset)
        sync_layout.addWidget(self.offset_spin)
        layout.addLayout(sync_layout)

        # Video play controls (play/pause and jump/frame buttons)
        play_controls_layout = QHBoxLayout()
        self.btn_jump_bwd = QPushButton("<< -1 sec")
        self.btn_prev = QPushButton("<<")
        self.btn_toggle = QPushButton("Play")  # combined play/pause button
        # Removed self.btn_pause = QPushButton("Pause")
        self.btn_next = QPushButton(">>")
        self.btn_jump_fwd = QPushButton(">> +1 sec")
        play_controls_layout.addWidget(self.btn_jump_bwd)
        play_controls_layout.addWidget(self.btn_prev)
        play_controls_layout.addWidget(self.btn_toggle)
        play_controls_layout.addWidget(self.btn_next)
        play_controls_layout.addWidget(self.btn_jump_fwd)
        layout.addLayout(play_controls_layout)

        self.btn_toggle.clicked.connect(self.toggle_playback)
        # Removed: self.btn_pause.clicked.connect(self.pause_playback)
        self.btn_next.clicked.connect(self.next_frame)
        self.btn_prev.clicked.connect(self.prev_frame)
        self.btn_jump_fwd.clicked.connect(lambda: self.jump_seconds(1))
        self.btn_jump_bwd.clicked.connect(lambda: self.jump_seconds(-1))

        # Video info label (frame count and time)
        self.label_info = QLabel("Frame: N/A   Time: N/A")
        layout.addWidget(self.label_info)

        widget.setLayout(layout)
        
    def load_intrinsics(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select Intrinsics JSON", "", "JSON Files (*.json)")
        if filename:
            try:
                with open(filename, 'r') as fp:
                    data = json.load(fp)
                self.intrinsics = data
                self.loaded_intrinsics_filename = os.path.basename(filename)
                QMessageBox.information(self, "Success", f"Loaded Intrinsics from {self.loaded_intrinsics_filename}")
                self.update_loaded_files_label()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load intrinsics:\n{str(e)}")

    def load_extrinsics(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select Extrinsics JSON", "", "JSON Files (*.json)")
        if filename:
            try:
                with open(filename, 'r') as fp:
                    data = json.load(fp)
                self.extrinsics = data
                best_ext = np.array(data["best_extrinsic"])
                rotation_3x3 = best_ext[:, :3]
                translation_vec = best_ext[:, 3].reshape(3,1)
                self.rvec, _ = cv2.Rodrigues(rotation_3x3)
                self.tvec = translation_vec
                self.loaded_extrinsics_filename = os.path.basename(filename)
                QMessageBox.information(self, "Success", f"Loaded Extrinsics from {self.loaded_extrinsics_filename}")
                self.update_loaded_files_label()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load extrinsics:\n{str(e)}")

    def load_video(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select Video File", "", "Video Files (*.mp4 *.avi)")
        if filename:
            # Use VideoPlayer instead of directly using cv2.VideoCapture
            try:
                if self.player is not None:
                    self.player.release()
                self.player = VideoPlayer(filename)
                self.loaded_video_filename = os.path.basename(filename)
                QMessageBox.information(self, "Success", f"Loaded Video from {self.loaded_video_filename}")
                self.update_loaded_files_label()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Cannot open video file {filename}.\n{str(e)}")

    def load_points(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select 3D Data CSV", "", "CSV Files (*.csv)")
        if filename:
        # try:
            df = pd.read_csv(filename, skiprows=1)
            
            # Extract points using SPML dataset format mapping
            target_joints_ordered = {
                0:  [('Hip','Bone')],
                1:  [('LThigh','Bone')],
                2:  [('RThigh','Bone')],
                3:  [('Ab','Bone')],
                4:  [('LShin','Bone')],
                5:  [('RShin','Bone')],
                6:  [('BackLeft','Bone Marker'),('BackRight','Bone Marker')],
                7:  [('LFoot','Bone')],
                8:  [('RFoot','Bone')],
                9:  [('BackTop','Bone Marker')],
                10: [('LToe','Bone')],
                11: [('RToe','Bone')],
                12: [('Neck','Bone')], 
                13: [('LShoulder','Bone')],
                14: [('RShoulder','Bone')],
                15: [('Head','Bone')],
                16: [('LUArm','Bone')],
                17: [('RUArm','Bone')],
                18: [('LFArm','Bone')],
                19: [('RFArm','Bone')],
                20: [('LWristIn','Bone Marker'),('LWristOut','Bone Marker')],
                21: [('RWristIn','Bone Marker'),('RWristOut','Bone Marker')],
                22: [('RHandOut','Bone Marker')],
                23: [('RHandOut','Bone Marker')],
            }
            all_joints = [joint[0] for joints in target_joints_ordered.values() for joint in joints]
            header_row_values = df.iloc[0].values[2:]
            unique_values = np.unique(header_row_values)
            unique_values = [ v[13:] for v in unique_values]
            # print("Unique col identifiers:", unique_values)
            filtered_joints_ordered = [value for value in all_joints if value[13:] in unique_values]
            print("Number of filtered joints:", len(filtered_joints_ordered))
            print("Filtered Joints Ordered:", filtered_joints_ordered)
            print("Do we have enough data? ", len(filtered_joints_ordered) == len(all_joints))
            
            # Use 1000 frames beginning at row index start_f = 18
            p = 1000
            start_f = 15
            data_ = np.zeros((p, 24, 3))
            type_list = list(df.iloc[0].index)
            
            for frame in range(p):
                for joint in range(len(target_joints_ordered)):
                    if len(target_joints_ordered[joint]) > 1:
                        matching_columns_0 = [i for i, value in enumerate(df.iloc[0].values) 
                                                #[13:] is used to remove the 'Skeleton:00x' part of the string
                                                if str(value)[13:] == target_joints_ordered[joint][0][0] and 
                                                type_list[i].startswith(target_joints_ordered[joint][0][1])][-3:]
                        matching_columns_1 = [i for i, value in enumerate(df.iloc[0].values) 
                                                if str(value)[13:] == target_joints_ordered[joint][1][0] and 
                                                type_list[i].startswith(target_joints_ordered[joint][1][1])][-3:]
                        position_0 = df.iloc[start_f+frame][matching_columns_0].values.astype(float)
                        position_1 = df.iloc[start_f+frame][matching_columns_1].values.astype(float)
                        final_ = (position_0 + position_1) / 2
                        data_[frame, joint] = final_
                    else:
                        matching_columns = [i for i, value in enumerate(df.iloc[0].values) 
                                            if str(value)[13:] == target_joints_ordered[joint][0][0] and 
                                            type_list[i].startswith(target_joints_ordered[joint][0][1])][-3:]
                        # print(matching_columns)
                        data_[frame, joint] = np.array(df.iloc[start_f+frame][matching_columns].values, dtype=float)
            self.points3d = data_
            self.loaded_points_filename = os.path.basename(filename)
            QMessageBox.information(self, "Success", f"Loaded 3D data with {self.points3d.shape[0]} frames")
            self.update_loaded_files_label()
        # except Exception as e:
        #     QMessageBox.critical(self, "Error", f"Failed to load 3D data:\n{str(e)}")

    def update_loaded_files_label(self):
        self.label_loaded_video.setText(self.loaded_video_filename if self.loaded_video_filename else "No File Loaded")
        self.label_loaded_intr.setText(self.loaded_intrinsics_filename if self.loaded_intrinsics_filename else "No File Loaded")
        self.label_loaded_extr.setText(self.loaded_extrinsics_filename if self.loaded_extrinsics_filename else "No File Loaded")
        self.label_loaded_points.setText(self.loaded_points_filename if self.loaded_points_filename else "No File Loaded")

    def change_offset(self, value):
        self.frame_offset = value

    def start_playback(self):
        if self.player is None:
            QMessageBox.warning(self, "Warning", "Load a video first.")
            return
        self.timer.start(1000 // int(self.player.fps))

    def toggle_playback(self):
        if self.player is None:
            QMessageBox.warning(self, "Warning", "Load a video first.")
            return
        if self.timer.isActive():
            self.timer.stop()
            self.btn_toggle.setText("Play")
        else:
            self.timer.start(1000 // int(self.player.fps))
            self.btn_toggle.setText("Pause")

    def next_frame(self):
        if self.player:
            self.player.next_frame()
            self.update_frame()

    def prev_frame(self):
        if self.player:
            self.player.prev_frame()
            self.update_frame()

    def jump_seconds(self, seconds):
        if self.player:
            self.player.jump_seconds(seconds)
            self.update_frame()

    def update_frame(self):
        if self.player is None:
            return
        # Get frame from VideoPlayer
        frame = self.player.get_frame()
        if frame is None:
            return
        # Convert the frame (which is in RGB already) back to BGR for processing
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        # Optionally undistort the frame if intrinsic info is available
        if self.intrinsics is not None:
            cam_mtx = np.array(self.intrinsics["camera_matrix"])
            dcoeff = self.intrinsics["dist_coeffs"]
            if isinstance(dcoeff[0], list):
                dcoeff = np.array(dcoeff[0])
            else:
                dcoeff = np.array(dcoeff)
            frame_bgr = cv2.undistort(frame_bgr, cam_mtx, dcoeff)
        # Project points for frames in the range [current-30, current+30]
        if self.points3d is not None and self.extrinsics is not None:
            current_idx = self.player.current_frame + self.frame_offset
            start_idx = max(0, current_idx - 30)
            end_idx = min(self.points3d.shape[0] - 1, current_idx + 30)
            for idx in range(start_idx, end_idx + 1):
                pts3d = self.points3d[idx]
                if self.rvec is not None and self.tvec is not None:
                    if self.intrinsics is not None:
                        cam_mtx = np.array(self.intrinsics["camera_matrix"])
                    else:
                        cam_mtx = np.array(self.extrinsics["camera_matrix"])
                    dcoeff = np.array(self.extrinsics["dist_coeffs"])
                    pts3d_reshaped = pts3d.reshape(-1, 1, 3)
                    projected, _ = cv2.projectPoints(pts3d_reshaped, self.rvec, self.tvec, cam_mtx, dcoeff)
                    projected = projected.squeeze().astype(int)
                    for pt in projected:
                        x, y = pt
                        if 0 <= x < frame_bgr.shape[1] and 0 <= y < frame_bgr.shape[0]:
                            if idx == current_idx:
                                cv2.circle(frame_bgr, (x, y), 4, (0, 0, 255), -1)
                            else:
                                cv2.circle(frame_bgr, (x, y), 2, (255, 0, 0), -1)
        # Convert back to RGB for display
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        height, width, channel = frame_rgb.shape
        bytes_per_line = 3 * width
        q_img = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(q_img).scaled(
            self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        # Update info label with current frame and playback time
        info_text = f"Frame: {self.player.current_frame} / {self.player.frame_count}   Time: {self.player.get_current_time():.2f} sec"
        self.label_info.setText(info_text)

    def closeEvent(self, event):
        if self.player is not None:
            self.player.release()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProjectionWindow()
    window.resize(800, 600)  # matches main_window size
    window.show()
    sys.exit(app.exec_())