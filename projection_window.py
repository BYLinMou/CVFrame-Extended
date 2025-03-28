import sys
import os
import json
import cv2
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QProgressDialog,
    QFileDialog, QSlider, QSpinBox, QApplication, QMessageBox, QLineEdit, QGridLayout, QSizePolicy
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QTimer, QCoreApplication
from video_player import VideoPlayer  

class ProjectionWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("3D Points Projection")
        self.setGeometry(100, 100, 1000, 600)
        self.setFocusPolicy(Qt.StrongFocus)  # Added to capture key events
        self.setFocus()                       # Ensure window has focus
        self.player = None 
        self.intrinsics = None
        self.extrinsics = None
        self.rvec = None
        self.tvec = None
        self.points3d = None
        self.frame_offset = 0
        self.loaded_video_filename = ""
        self.loaded_intrinsics_filename = ""
        self.loaded_extrinsics_filename = ""
        self.loaded_points_filename = ""
        self.is_playing = False

        self.init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.statusBar().showMessage(
            "Shortcut: Space - Play/Pause, A - Prev Frame, D - Next Frame, Q - Back 1s, E - Forward 1s, W - Increase Offset, S - Decrease Offset"
        )

    ########## UI Components ##########
    def init_ui(self):
        widget = QWidget()
        self.setCentralWidget(widget)
        main_layout = QVBoxLayout()
        
        # Video layout: video display and overlaid info label
        video_layout = QVBoxLayout()
        self.video_label = QLabel("")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(400, 300)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # Ensure full horizontal fill
        video_layout.addWidget(self.video_label)
        self.info_label = QLabel(self.video_label)
        self.info_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.info_label.setStyleSheet("background-color: rgba(0, 0, 0, 0.5); color: white; padding: 5px;")
        self.info_label.setText("00:00:00 / 00:00:00\nFrame: 0 / 0")
        
        # Control layout: file load controls (wrapped in a fixed-height widget) on top and play buttons underneath
        control_layout = QVBoxLayout()
        file_grid = QGridLayout()
        self.create_file_widgets(file_grid)
        file_grid.setVerticalSpacing(5)
        file_grid.setHorizontalSpacing(5)
        file_grid_widget = QWidget()
        file_grid_widget.setLayout(file_grid)
        file_grid_widget.setFixedHeight(120)
        control_layout.addWidget(file_grid_widget)
        
        # --- Add synchronization offset controls ---
        sync_layout = QHBoxLayout()
        offset_label = QLabel("Frame Offset:")
        self.offset_spin = QSpinBox()
        self.offset_spin.setRange(-1000, 1000)
        self.offset_spin.setValue(self.frame_offset)
        self.offset_spin.valueChanged.connect(self.change_offset)
        sync_layout.addWidget(offset_label)
        sync_layout.addWidget(self.offset_spin)
        control_layout.addLayout(sync_layout)
        # --- End synchronization offset controls ---
        
        play_controls_layout = QHBoxLayout()
        self.create_play_buttons(play_controls_layout)
        control_layout.addLayout(play_controls_layout)
        
        # Adjust stretch factors: video layout gets more space than controls
        main_layout.addLayout(video_layout, 3)
        main_layout.addLayout(control_layout, 2)
        widget.setLayout(main_layout)

    def create_file_widgets(self, file_grid):
        # Simplified function to create all file loading buttons and labels
        self.btn_load_intr = self.create_button("Load Intrinsics", "No File Loaded",self.load_intrinsics)
        self.btn_load_extr = self.create_button("Load Extrinsics", "No File Loaded",self.load_extrinsics)
        self.btn_load_video = self.create_button("Load Video", "No File Loaded",self.load_video)
        self.btn_load_points = self.create_button("Load 3D Data (CSV)", "No File Loaded",self.load_points)
        
        file_grid.addWidget(self.btn_load_intr[0], 0, 0)
        file_grid.addWidget(self.btn_load_extr[0], 0, 1)
        file_grid.addWidget(self.btn_load_video[0], 1, 0)
        file_grid.addWidget(self.btn_load_points[0], 1, 1)
        
    def create_button(self, text, label_text, click_event):
        btn = QPushButton(text)
        btn.setFixedSize(150, 30)
        btn.clicked.connect(click_event)
        label = QLabel(label_text)
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(btn, alignment=Qt.AlignCenter)
        layout.addWidget(label, alignment=Qt.AlignCenter)
        widget.setLayout(layout)
        return widget, label

    def create_play_buttons(self, play_controls_layout):
        self.btn_jump_bwd = QPushButton("<< -1 sec")
        self.btn_prev = QPushButton("<<")
        self.btn_toggle = QPushButton("Play")  # combined play/pause button
        self.btn_next = QPushButton(">>")
        self.btn_jump_fwd = QPushButton(">> +1 sec")

        play_controls_layout.addWidget(self.btn_jump_bwd)
        play_controls_layout.addWidget(self.btn_prev)
        play_controls_layout.addWidget(self.btn_toggle)
        play_controls_layout.addWidget(self.btn_next)
        play_controls_layout.addWidget(self.btn_jump_fwd)

        self.btn_toggle.clicked.connect(self.toggle_playback)
        self.btn_next.clicked.connect(self.next_frame)
        self.btn_prev.clicked.connect(self.prev_frame)
        self.btn_jump_fwd.clicked.connect(lambda: self.jump_seconds(1))
        self.btn_jump_bwd.clicked.connect(lambda: self.jump_seconds(-1))

    ########## Loading Utilities ##########
    def load_intrinsics(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select Intrinsics JSON", "", "JSON Files (*.json)")
        if filename:
            try:
                with open(filename, 'r') as fp:
                    data = json.load(fp)
                self.intrinsics = data
                self.loaded_intrinsics_filename = os.path.basename(filename)
                # QMessageBox.information(self, "Success", f"Loaded Intrinsics from {self.loaded_intrinsics_filename}")
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
                # QMessageBox.information(self, "Success", f"Loaded Extrinsics from {self.loaded_extrinsics_filename}")
                self.update_loaded_files_label()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load extrinsics:\n{str(e)}")

    def load_video(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select Video File", "", "Video Files (*.mp4 *.avi)")
        if filename:
            try:
                if self.player is not None:
                    self.player.release()
                self.player = VideoPlayer(filename)
                self.loaded_video_filename = os.path.basename(filename)
                # QMessageBox.information(self, "Success", f"Loaded Video from {self.loaded_video_filename}")
                self.update_loaded_files_label()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Cannot open video file {filename}.\n{str(e)}")

    def load_points(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select 3D Data CSV", "", "CSV Files (*.csv)")
        if filename:
            try:
                # no block size specified, so pandas will read the entire file
                df = pd.read_csv(filename, skiprows=1, low_memory=False)
                start_f = 5 ### skip the first 5 rows which are hearders (totally 6 rows, one row skipped in file reading)
                self.frame_offset = 0
                p = len(df) - 5
                print(p)
                progress = QProgressDialog("Loading 3D data...", "Cancel", 0, p, self)
                progress.setWindowModality(Qt.WindowModal)
                progress.setMinimumDuration(0)
                progress.setFixedSize(300, 100)
                
                ### Extract column names using SPML dataset format mapping

                all_joints = [joint[0] for joints in TARGET_JOINTS_ORDERED.values() for joint in joints]
                header_row_values = df.iloc[0].values[2:]
                unique_values = np.unique(header_row_values)
                unique_values = [ v[13:] for v in unique_values]
                filtered_joints_ordered = [value for value in all_joints if value[13:] in unique_values]

                
                ### Extract 3D points that fit the names
                data_ = np.zeros((p, 24, 3))
                type_list = list(df.iloc[0].index)                
                for frame in range(p):
                    if progress.wasCanceled():  # Check if the user canceled the operation
                        self.points3d = None
                        QMessageBox.information(self, "Canceled", "3D data loading was canceled.")
                        break
                    for joint in range(len(TARGET_JOINTS_ORDERED)):
                        if len(TARGET_JOINTS_ORDERED[joint]) > 1:
                            matching_columns_0 = [i for i, value in enumerate(df.iloc[0].values) 
                                                    #[13:] is used to remove the 'Skeleton:00x' part of the string
                                                    if str(value)[13:] == TARGET_JOINTS_ORDERED[joint][0][0] and 
                                                    type_list[i].startswith(TARGET_JOINTS_ORDERED[joint][0][1])][-3:]
                            matching_columns_1 = [i for i, value in enumerate(df.iloc[0].values) 
                                                    if str(value)[13:] == TARGET_JOINTS_ORDERED[joint][1][0] and 
                                                    type_list[i].startswith(TARGET_JOINTS_ORDERED[joint][1][1])][-3:]
                            position_0 = df.iloc[start_f+frame][matching_columns_0].values.astype(float)
                            position_1 = df.iloc[start_f+frame][matching_columns_1].values.astype(float)
                            final_ = (position_0 + position_1) / 2
                            data_[frame, joint] = final_
                        else:
                            matching_columns = [i for i, value in enumerate(df.iloc[0].values) 
                                                if str(value)[13:] == TARGET_JOINTS_ORDERED[joint][0][0] and 
                                                type_list[i].startswith(TARGET_JOINTS_ORDERED[joint][0][1])][-3:]
                            data_[frame, joint] = np.array(df.iloc[start_f+frame][matching_columns].values, dtype=float)
                    progress.setValue(frame)
                    QCoreApplication.processEvents()
                    
                progress.close()
                if not progress.wasCanceled():  # Only proceed if not canceled
                    self.points3d = data_
                    self.loaded_points_filename = os.path.basename(filename)
                    QMessageBox.information(self, "Success", f"Loaded 3D data with {self.points3d.shape[0]} frames")
                    self.update_loaded_files_label()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load 3D data:\n{str(e)}")

    ########## Video Control Functions ##########
    def update_loaded_files_label(self):
        # Update the info label with loaded file names  
        self.btn_load_video[1].setText(self.loaded_video_filename if self.loaded_video_filename else "No File Loaded")
        self.btn_load_intr[1].setText(self.loaded_intrinsics_filename if self.loaded_intrinsics_filename else "No File Loaded") 
        self.btn_load_extr[1].setText(self.loaded_extrinsics_filename if self.loaded_extrinsics_filename else "No File Loaded")
        self.btn_load_points[1].setText(self.loaded_points_filename if self.loaded_points_filename else "No File Loaded")


    def update_frame(self):
        # If playing, advance the frame
        if self.player and self.player.is_playing:
            self.player.next_frame()
            if self.player.current_frame >= self.player.frame_count - 1:
                self.player.is_playing = False
                self.btn_toggle.setText("Play")
                self.timer.stop()
        
        if not self.player:
            return

        frame = self.player.get_frame()
        if frame is None:
            return

        # Process the frame: convert to BGR for processing
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # Optionally undistort using intrinsics if available
        if self.intrinsics is not None:
            cam_mtx = np.array(self.intrinsics["camera_matrix"])
            dcoeff = self.intrinsics["dist_coeffs"]
            if isinstance(dcoeff[0], list):
                dcoeff = np.array(dcoeff[0])
            else:
                dcoeff = np.array(dcoeff)
            frame_bgr = cv2.undistort(frame_bgr, cam_mtx, dcoeff)
        
        # Map 3D points onto the frame if available
        if self.points3d is not None and self.extrinsics is not None:
            current_idx = self.player.current_frame + self.frame_offset
            if 0 <= current_idx < self.points3d.shape[0]:
                pts3d = self.points3d[current_idx]
                if self.rvec is not None and self.tvec is not None:
                    if self.intrinsics is not None:
                        cam_mtx = np.array(self.intrinsics["camera_matrix"])
                    else:
                        cam_mtx = np.array(self.extrinsics["camera_matrix"])
                    dcoeff_ex = np.array(self.extrinsics["dist_coeffs"])
                    pts3d_reshaped = pts3d.reshape(-1, 1, 3)
                    projected, _ = cv2.projectPoints(pts3d_reshaped, self.rvec, self.tvec, cam_mtx, dcoeff_ex)
                    projected = projected.squeeze().astype(int)
                    for pt in projected:
                        x, y = pt
                        if 0 <= x < frame_bgr.shape[1] and 0 <= y < frame_bgr.shape[0]:
                            cv2.circle(frame_bgr, (x, y), 4, (0, 0, 255), -1)
        
        # Convert processed frame back to RGB
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        q_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # Cache label size to avoid unnecessary re-scaling.
        label_size = self.video_label.size()
        if not hasattr(self, '_cached_label_size') or self._cached_label_size != label_size:
            self._cached_label_size = label_size
            self._cached_pixmap = None  # Invalidate the cache if label size changes
        
        # Always update the pixmap for the new frame.
        self._cached_pixmap = QPixmap.fromImage(q_img).scaled(
            label_size,
            Qt.KeepAspectRatio,
            Qt.FastTransformation  # Faster than SmoothTransformation
        )
        
        # Temporarily disable updates to avoid flicker.
        self.video_label.setUpdatesEnabled(False)
        self.video_label.setPixmap(self._cached_pixmap)
        self.video_label.setUpdatesEnabled(True)
        
        # Compute letterbox offsets (if needed later for click mapping, etc.)
        pixmap_width = self._cached_pixmap.width()
        pixmap_height = self._cached_pixmap.height()
        label_width = self.video_label.width()
        label_height = self.video_label.height()
        self._video_offset_x = max(0, (label_width - pixmap_width) // 2)
        self._video_offset_y = max(0, (label_height - pixmap_height) // 2)
        
        # Update info label text if video is loaded
        if self.player and self.player.frame_count:
            current_time = self.player.get_current_time()
            total_time = self.player.frame_count / self.player.fps
            self.info_label.setText(
                f"{self.format_time(current_time)} / {self.format_time(total_time)}\n"
                f"Frame: {self.player.current_frame} / {self.player.frame_count}"
            )
        
        # Restore offset line: position info_label relative to displayed video area with a 10-pixel margin.
        offset_x = self._video_offset_x + 10
        offset_y = self._video_offset_y + 10
        self.info_label.move(offset_x, offset_y)

    def change_offset(self, value):
        self.frame_offset = value
        self.update_frame() 
        
    def toggle_playback(self):
        if self.player is None:
            QMessageBox.warning(self, "Warning", "Load a video first.")
            return
        if self.timer.isActive():
            self.timer.stop()
            self.btn_toggle.setText("Play")
            self.is_playing = False
            self.player.is_playing = False  # added: stop player playback
        else:
            self.timer.start(1000 // int(self.player.fps))
            self.btn_toggle.setText("Pause")
            self.is_playing = True
            self.player.is_playing = True  # added: start player playback

    def next_frame(self):
        if self.player:
            if self.is_playing:
                self.toggle_playback()
                self.is_playing = False
            self.player.next_frame()
            self.update_frame()

    def prev_frame(self):
        if self.player:
            if self.is_playing:
                self.toggle_playback()
                self.is_playing = False
            self.player.prev_frame()
            self.update_frame()

    def jump_seconds(self, seconds):
        if self.player:
            if self.is_playing:
                self.toggle_playback()
                self.is_playing = False
            self.player.jump_seconds(seconds)
            self.update_frame()

    def format_time(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02}:{minutes:02}:{secs:02}"

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.toggle_playback()
        elif event.key() == Qt.Key_A:
            self.prev_frame()
        elif event.key() == Qt.Key_D:
            self.next_frame()
        elif event.key() == Qt.Key_Q:
            self.jump_seconds(-1)
        elif event.key() == Qt.Key_E:
            self.jump_seconds(1)
        elif event.key() == Qt.Key_W:
            # Increase sync offset count by 1
            self.offset_spin.setValue(self.offset_spin.value() + 1)
        elif event.key() == Qt.Key_S:
            # Decrease sync offset count by 1
            self.offset_spin.setValue(self.offset_spin.value() - 1)
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        if self.player is not None:
            self.player.release()
        event.accept()
        
TARGET_JOINTS_ORDERED = {
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProjectionWindow()
    # window.resize(800, 600)  # matches main_window size
    window.show()
    sys.exit(app.exec_())
