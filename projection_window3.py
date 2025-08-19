import sys
import os
import json
import cv2
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QProgressDialog,
    QFileDialog, QSlider, QSpinBox, QApplication, QMessageBox, QLineEdit, QGridLayout, QSizePolicy, QInputDialog, QMenuBar, QListWidget, QListWidgetItem, QCheckBox, QButtonGroup, QRadioButton
)
from PyQt5.QtGui import QImage, QPixmap, QGuiApplication
from PyQt5.QtCore import Qt, QTimer, QCoreApplication
from video_player import VideoPlayer  
from video_player_black import BlackVideoPlayer
from mocap_data import RawMocapData
from pixel_data import PixelData, PixelFileDialog

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt # Needed for initial Figure creation
import datetime # Import datetime for timestamp

# 定義關鍵點連接對，用於繪製骨架
# 17 keypoints
JOINT_PAIRS_17kp = [
    (0, 1), (1, 2), (2, 3),
    (0, 4), (4, 5), (5, 6),
    (0, 7), (7, 8), (8, 9), (9, 10),
    (8, 11), (11, 12), (12, 13),
    (8, 14), (14, 15), (15, 16)
]

# 24 keypoints
JOINT_PAIRS_24kp = [
    (0, 1), (0, 2), (0, 3),  # 骨盆到髋部
    (1, 4), (4, 7), (7, 10),  # 左腿
    (2, 5), (5, 8), (8, 11),  # 右腿
    (3, 6), (6, 9), (9, 12), (12, 15),  # 脊柱到头
    (9, 13), (13, 16), (16, 18), (18, 20), (20, 22),  # 左臂
    (9, 14), (14, 17), (17, 19), (19, 21), (21, 23)   # 右臂
]

# 骨架連接對的映射表
JOINT_PAIRS_MAP = {
    17: JOINT_PAIRS_17kp,
    24: JOINT_PAIRS_24kp,
}

class ProjectionWindow3(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("3D Points Projection ver3")
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
        self.points_frame_count = 0
        self.loaded_video_filename = ""
        self.loaded_video_path = ""
        self.recent_video_filename = ""
        self.recent_video_path = ""
        self.loaded_intrinsics_filename = ""
        self.loaded_extrinsics_filename = ""
        self.loaded_points_filename = ""
        self.is_playing = False
        self.max_frame_3d = 0
        
        # New: Attributes for Raw Mocap Data
        self.raw_mocap_data = None
        self.raw_mocap_filename = ""
        self.raw_mocap_frame_count = 0
        self.show_raw_mocap_points = True # Control visibility of raw mocap points (and skeleton)
        
        # 添加多個3D資料檔案的支援
        self.loaded_points_files = []  # 存儲已加載的3D資料檔案資訊
        self.current_points_index = -1  # 當前選中的3D資料檔案索引
        self.visible_points_files = set()  # 存儲勾選顯示的檔案索引
        self.show_skeleton = True  # 控制是否顯示骨架連接線

        # 添加 Pixel2D 数据相关
        self.loaded_pixel2d_files = []
        self.visible_pixel2d_files = set()
        self.active_pixel2d_view = 'center'  # 或 'left'

        # 新增：原始 Mocap 點顯示模式選擇
        self.raw_mocap_display_mode_group = QButtonGroup(self)
        self.radio_show_all_raw_mocap = QRadioButton("Show All Raw Mocap Joints")
        self.radio_show_skeleton001_raw_mocap = QRadioButton("Show Skeleton 001 Joints")
        self.radio_show_custom_raw_mocap = QRadioButton("Custom Select Joints") # 新增 Custom mode Radio Button
        
        self.raw_mocap_joint_list = QListWidget()
        self.raw_mocap_joint_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.selected_joints_count_label = QLabel("Selected 0 joints") # Initialize the label here

        # Matplotlib 3D visualization components
        self.figure_3d = Figure()
        self.ax_3d = self.figure_3d.add_subplot(111, projection='3d')
        self.canvas_3d = FigureCanvas(self.figure_3d)

        self.init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        
        # 初始化時自動加載內外參數
        self.update_camera_parameters()
        
        self.statusBar().showMessage(
            "Shortcut: Space - Play/Pause, A - Prev Frame, D - Next Frame, Q - Back 1s, E - Forward 1s, W - Increase Offset, S - Decrease Offset, R - Locate Frame, F - Locate Time, Z - Copy Offset"
        )
        # Connect scroll event for debugging
        self.canvas_3d.mpl_connect('scroll_event', self.on_scroll)

    ########## UI Components ##########
    def init_ui(self):
        widget = QWidget()
        self.setCentralWidget(widget)
        main_layout = QVBoxLayout()
        
        # 創建水平佈局來放置視頻和3D資料列表
        content_layout = QHBoxLayout()
        
        # 新增左側框架 (用於原始Mocap資料顯示)
        self.left_panel_container_widget = QWidget() # 使用 QWidget 來控制顯示/隱藏
        self.left_panel_container_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.left_panel_layout = QVBoxLayout(self.left_panel_container_widget)
        
        # 原始 Mocap 資料固定標籤
        fixed_raw_mocap_label = QLabel("Loaded 3D Raw Mocap Data:")
        fixed_raw_mocap_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.left_panel_layout.addWidget(fixed_raw_mocap_label)
        # 原始 Mocap 資料檔案詳細資訊標籤 (顯示檔名和幀數)
        self.raw_mocap_file_details_label = QLabel("Not Loaded")
        self.left_panel_layout.addWidget(self.raw_mocap_file_details_label)
        
        # 原始 Mocap 點顯示控制 (取代骨架顯示)
        self.raw_mocap_points_checkbox = QCheckBox("Show Raw Mocap Points")
        self.raw_mocap_points_checkbox.setChecked(self.show_raw_mocap_points) # Initial state
        self.raw_mocap_points_checkbox.stateChanged.connect(self.on_raw_mocap_points_checkbox_changed)
        self.left_panel_layout.addWidget(self.raw_mocap_points_checkbox)
        
        # 新增原始 Mocap 點顯示模式選擇 Radio Buttons
        self.left_panel_layout.addWidget(self.radio_show_all_raw_mocap)
        self.left_panel_layout.addWidget(self.radio_show_skeleton001_raw_mocap)
        self.left_panel_layout.addWidget(self.radio_show_custom_raw_mocap) # Add new radio button
        self.raw_mocap_display_mode_group.addButton(self.radio_show_all_raw_mocap)
        self.raw_mocap_display_mode_group.addButton(self.radio_show_skeleton001_raw_mocap)
        self.raw_mocap_display_mode_group.addButton(self.radio_show_custom_raw_mocap) # Add new radio button to group
        self.radio_show_all_raw_mocap.setChecked(True) # Default to 'Show All'
        self.raw_mocap_display_mode = 'all' # Initialize display mode
        self.raw_mocap_display_mode_group.buttonClicked.connect(self.on_raw_mocap_display_mode_changed)

        # 新增原始 Mocap 點列表
        self.raw_mocap_joint_list = QListWidget()
        self.raw_mocap_joint_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.raw_mocap_joint_list.itemChanged.connect(self.on_raw_mocap_joint_checkbox_changed) # Connect signal here
        self.raw_mocap_joint_list.itemClicked.connect(self.on_raw_mocap_joint_list_clicked) # Connect for toggling on click
        self.left_panel_layout.addWidget(self.selected_joints_count_label) # Add the new label here
        self.left_panel_layout.addWidget(self.raw_mocap_joint_list, 1) # 設定垂直伸展因子為1
        
        # Video layout: video display and overlaid info label
        self.video_panel_container_widget = QWidget() # 新增：影片面板的容器 Widget
        video_layout = QVBoxLayout(self.video_panel_container_widget) # 將 video_layout 設置為此容器的佈局
        self.video_label = QLabel("")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(400, 300)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # Ensure full horizontal fill
        video_layout.addWidget(self.video_label)
        self.info_label = QLabel(self.video_label) # 將 info_label 設置為 video_label 的子元件
        self.info_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.info_label.setStyleSheet("background-color: rgba(0, 0, 0, 0.5); color: white; padding: 5px;")
        self.info_label.setText("00:00:00 / 00:00:00\nFrame: 0 / 0")
        
        # 新增 3D 視覺化面板 (最右側)
        self.three_d_visualization_container_widget = QWidget()
        self.three_d_visualization_container_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.three_d_visualization_layout = QVBoxLayout(self.three_d_visualization_container_widget)
        
        #fixed_3d_viz_label = QLabel("3D Visualization:")
        #fixed_3d_viz_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        #self.three_d_visualization_layout.addWidget(fixed_3d_viz_label)
        self.three_d_visualization_layout.addWidget(self.canvas_3d) # Add Matplotlib canvas
        
        # 3D Data Files List (右側)
        self.right_panel_container_widget = QWidget() # 新增：用於控制右側面板顯示/隱藏的 QWidget
        self.right_panel_container_layout = QVBoxLayout(self.right_panel_container_widget) # 新增：右側面板的佈局
        
        points_list_label = QLabel("Loaded 3D Data Files:")
        points_list_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.right_panel_container_layout.addWidget(points_list_label) # 將元件添加到新的佈局中
        
        # 使用QListWidget with checkboxes
        self.points_list = QListWidget()
        self.points_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) # Allow both horizontal and vertical expansion
        self.points_list.itemChanged.connect(self.on_points_checkbox_changed)
        self.points_list.itemDoubleClicked.connect(self.on_points_file_double_clicked)
        self.right_panel_container_layout.addWidget(self.points_list) # 將元件添加到新的佈局中
        
        # 添加3D資料檔案的按鈕
        add_points_btn = QPushButton("Add 3D Data")
        add_points_btn.clicked.connect(lambda: self.load_points(is_visible_by_default=True))
        add_points_btn.setMaximumWidth(250)
        self.right_panel_container_layout.addWidget(add_points_btn) # 將元件添加到新的佈局中
        
        # 添加 Pixel2D 数据相关
        # 在 right_panel_container_layout 添加
        pixel2d_label = QLabel("Loaded Pixel 2D Data:")
        pixel2d_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.right_panel_container_layout.addWidget(pixel2d_label)

        self.pixel2d_listwidget = QListWidget()
        self.pixel2d_listwidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.pixel2d_listwidget.itemChanged.connect(self.on_pixel2d_checkbox_changed)
        # self.pixel2d_listwidget.itemDoubleClicked.connect(self.on_pixel2d_item_double_clicked)
        self.right_panel_container_layout.addWidget(self.pixel2d_listwidget)

        add_pixel2d_btn = QPushButton("Add Pixel 2D Data")
        add_pixel2d_btn.clicked.connect(self.load_pixel2d)
        self.right_panel_container_layout.addWidget(add_pixel2d_btn)

        # 添加骨架顯示控制 (這個是針對右側列表的 NPY/CSV 檔案)
        self.skeleton_checkbox = QCheckBox("Show Skeleton")
        self.skeleton_checkbox.setChecked(self.show_skeleton)
        self.skeleton_checkbox.stateChanged.connect(self.on_skeleton_checkbox_changed)
        self.skeleton_checkbox.setMaximumWidth(250)
        self.right_panel_container_layout.addWidget(self.skeleton_checkbox) # 將元件添加到新的佈局中
        
        # 將視頻和3D資料列表添加到水平佈局
        content_layout.insertWidget(0, self.left_panel_container_widget, 1) # 左側佔1份空間
        content_layout.addWidget(self.video_panel_container_widget, 4)  # 影片容器佔4份空間
        content_layout.addWidget(self.three_d_visualization_container_widget, 2) # 新的3D可視化佔2份空間
        content_layout.addWidget(self.right_panel_container_widget, 1)  # 右側 NPY/CSV 列表佔1份空間

        self.left_panel_container_widget.hide()
        self.right_panel_container_widget.hide()
        self.three_d_visualization_container_widget.hide()
        self.video_panel_container_widget.show() # 確保影片面板預設顯示
        # 影片面板在初始時應該是可見的，因此不需要隱藏它
        
        # Control layout: file load controls (wrapped in a fixed-height widget) on top and play buttons underneath
        control_layout = QVBoxLayout()
        file_grid = QGridLayout()
        self.create_file_widgets(file_grid)
        file_grid.setVerticalSpacing(5)
        file_grid.setHorizontalSpacing(5)
        file_grid_widget = QWidget()
        file_grid_widget.setLayout(file_grid)
        control_layout.addWidget(file_grid_widget)
        
        # --- Add synchronization offset controls ---
        sync_layout = QHBoxLayout()
        offset_label = QLabel("Frame Offset:")
        self.offset_spin = QSpinBox()
        self.offset_spin.setRange(-20000, 20000)
        self.offset_spin.setValue(self.frame_offset)
        self.offset_spin.valueChanged.connect(self.change_offset)
        sync_layout.addWidget(offset_label)
        sync_layout.addWidget(self.offset_spin)
        control_layout.addLayout(sync_layout)
        # --- End synchronization offset controls ---
        
        play_controls_layout = QHBoxLayout()
        self.create_play_buttons(play_controls_layout)
        control_layout.addLayout(play_controls_layout)
        
        # Adjust stretch factors: content layout gets more space than controls
        main_layout.addLayout(content_layout, 4)
        main_layout.addLayout(control_layout, 1)
        widget.setLayout(main_layout)
        
        menu_bar = self.menuBar() if self.menuBar() else self.menuBar()  # ensure it exists

        # 新增 File 選單
        file_menu = menu_bar.addMenu("File")
        act_load_folder = file_menu.addAction("Load Folder (npy/csv)")
        act_load_raw_mocap = file_menu.addAction("Load Raw Mocap (csv)")
        act_load_pixel = file_menu.addAction("Load Pixel (npy/csv)")
        act_load_folder.triggered.connect(self.load_folder)
        act_load_raw_mocap.triggered.connect(self.load_raw_mocap_data)
        act_load_pixel.triggered.connect(self.load_pixel2d)

        # --- Add Locate controls ---
        go_menu   = menu_bar.addMenu("Go")
        act_frame = go_menu.addAction("Locate Frame")
        act_time  = go_menu.addAction("Locate Time")
        act_frame.triggered.connect(self.locate_frame)
        act_time.triggered.connect(self.locate_time)
        
        # --- Add Camera Parameters menu ---
        camera_menu = menu_bar.addMenu("Camera")
        act_middle = camera_menu.addAction("Switch Perspective (middle)")
        act_left = camera_menu.addAction("Switch Perspective (left)")
        act_middle.triggered.connect(self.update_camera_parameters)
        act_left.triggered.connect(self.update_camera_parameters_left)

        # Add video menu
        video_menu = menu_bar.addMenu("Video")
        act_virtual = video_menu.addAction("Use Virtual Video")
        act_video_file = video_menu.addAction(f"Use Video file")
        act_virtual.triggered.connect(self.update_background_virtual)
        act_video_file.triggered.connect(self.update_background_real)

        # Add export menu
        export_menu = menu_bar.addMenu("Export")
        act_export = export_menu.addAction("Export Video")
        act_export.triggered.connect(self.export_video)
        act_export_custom_joints = export_menu.addAction("Export Custom Joint List")
        act_export_custom_joints.triggered.connect(self.export_custom_joint_list)

        # Add Visibility menu
        visibility_menu = menu_bar.addMenu("Visibility")
        self.action_toggle_joint_mocap = visibility_menu.addAction("Joint - Mocap")
        self.action_toggle_video = visibility_menu.addAction("Video")
        self.action_toggle_3d_mocap = visibility_menu.addAction("3D - Mocap")
        self.action_toggle_3d_data = visibility_menu.addAction("Data List")

        self.action_toggle_joint_mocap.setCheckable(True)
        self.action_toggle_video.setCheckable(True)
        self.action_toggle_3d_mocap.setCheckable(True)
        self.action_toggle_3d_data.setCheckable(True)

        # Initial state: only video is visible
        self.action_toggle_joint_mocap.setChecked(False)
        self.action_toggle_video.setChecked(True) # Video is visible by default
        self.action_toggle_3d_mocap.setChecked(False)
        self.action_toggle_3d_data.setChecked(False)

        self.action_toggle_joint_mocap.triggered.connect(lambda: self.toggle_panel_visibility(self.left_panel_container_widget, self.action_toggle_joint_mocap.isChecked()))
        self.action_toggle_video.triggered.connect(lambda: self.toggle_panel_visibility(self.video_panel_container_widget, self.action_toggle_video.isChecked())) # 更新為新的影片容器 Widget
        self.action_toggle_3d_mocap.triggered.connect(lambda: self.toggle_panel_visibility(self.three_d_visualization_container_widget, self.action_toggle_3d_mocap.isChecked()))
        self.action_toggle_3d_data.triggered.connect(lambda: self.toggle_panel_visibility(self.right_panel_container_widget, self.action_toggle_3d_data.isChecked()))

    def create_file_widgets(self, file_grid):
        # Simplified function to create all file loading buttons and labels
        self.btn_load_intr = self.create_button("Update Intrinsics", "No File Loaded", self.load_intrinsics)
        self.btn_load_extr = self.create_button("Update Extrinsics", "No File Loaded", self.load_extrinsics)
        self.btn_load_video = self.create_button("Load Video", "No File Loaded",self.load_video)
        #self.btn_load_points = self.create_button("Load 3D Data (CSV)", "No File Loaded",self.load_points)
        self.btn_load_points = self.create_button("Load 3D Data (NPY/CSV)", "No File Loaded", lambda: self.load_points(is_visible_by_default=True))
        
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
        """手動選擇並載入內參檔案"""
        filename, _ = QFileDialog.getOpenFileName(self, "Selfect Intrinsics JSON", "", "JSON Files (*.json)")
        if filename:
            try:
                with open(filename, 'r') as fp:
                    data = json.load(fp)
                self.intrinsics = data
                self.loaded_intrinsics_filename = os.path.basename(filename)
                print(f"Loaded Intrinsics from {filename}")
                self.update_loaded_files_label()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load intrinsics:\n{str(e)}")

    def load_extrinsics(self):
        """手動選擇並載入外參檔案"""
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
                print(f"Loaded Extrinsics from {filename}")
                self.update_loaded_files_label()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load extrinsics:\n{str(e)}")
    
    def update_background_virtual(self):
        # print(f"Creating virtual black video with {self.max_frame_3d} frame")
        if self.player is not None:
            self.player.release()
        self.player = BlackVideoPlayer(frame_count=self.max_frame_3d)
        self.recent_video_filename = "Virtual Black Video"
        self.recent_video_path = "Virtual Black Video"
        self.update_frame()
        self.update_loaded_files_label()
    
    def update_background_real(self):   
        try:
            if self.player is not None:
                self.player.release()
            self.player = VideoPlayer(self.loaded_video_path)
            self.recent_video_filename = self.loaded_video_filename
            self.recent_video_path = self.loaded_video_path
            self.frame_offset = 0
            if hasattr(self, 'offset_spin'):
                self.offset_spin.setValue(0)
            self.update_frame()
            self.update_loaded_files_label()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot open video file {self.loaded_video_path}.\n{str(e)}")     

    def load_video(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select Video File", "", "Video Files (*.mp4 *.avi)")
        if filename:
            try:
                if self.player is not None:
                    self.player.release()
                self.player = VideoPlayer(filename)
                self.loaded_video_path = filename
                self.loaded_video_filename = os.path.basename(filename)
                self.recent_video_filename = self.loaded_video_filename
                self.recent_video_path = self.loaded_video_path
                self.frame_offset = 0
                if hasattr(self, 'offset_spin'):
                    self.offset_spin.setValue(0)
                # Update max_frame_3d if the new video has more frames
                if self.player.frame_count > self.max_frame_3d:
                    self.max_frame_3d = self.player.frame_count
                    print(f"max_frame_3d updated to: {self.max_frame_3d}")
                self.update_loaded_files_label()
                self.update_frame()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Cannot open video file {filename}.\n{str(e)}")

    def load_points(self, filename=None, is_visible_by_default=True):
        """載入3D資料檔案 (NPY/CSV)，並添加到多檔案列表中"""
        # self.is_raw_mocap_active = False # Reverted: Switching to NPY/CSV mode
        # self.left_panel_container_widget.hide() # Reverted: Hide left panel

        # 如果沒有提供 filename，則開啟檔案選擇對話框
        if filename is None:
            filename, _ = QFileDialog.getOpenFileName(self, "Select 3D Data File", "", "3D Data Files (*.npy *.csv)")
            if not filename:
                return

        try:
            data = None
            file_extension = os.path.splitext(filename)[1].lower()
            
            if file_extension == ".npy":
                data = np.load(filename)
                print(f"Loaded NPY data shape: {data.shape}")
            elif file_extension == ".csv":
                # 根據之前查看的 extract_17_keypoint_from_csv.py 邏輯，
                # 假設 CSV 檔案的格式是每一行代表一幀，每三個列代表一個關鍵點的XYZ座標
                df = pd.read_csv(filename)
                # 確保所有列都是數值類型，非數值的轉換為NaN
                df = df.apply(pd.to_numeric, errors='coerce')
                
                # 從列名中解析出關鍵點數量，例如 '0_x', '0_y', '0_z', '1_x', ...
                # 假設列名格式為 "joint_idx_axis"
                num_cols = df.shape[1]
                if num_cols % 3 != 0:
                    QMessageBox.critical(self, "Error", f"CSV file has {num_cols} columns, which is not a multiple of 3. Expected (joints * 3).")
                    return
                num_joints = num_cols // 3
                
                # 將 DataFrame 重塑為 (frames, joints, 3)
                # 首先將所有XYZ座標合併成一個大的一維陣列，然後重塑
                # 注意：這裡需要確保df的順序是按照x,y,z順序排列
                data = df.values.reshape(-1, num_joints, 3)
                print(f"Loaded CSV data shape: {data.shape}")
            else:
                QMessageBox.critical(self, "Error", "Unsupported file type. Please select a .npy or .csv file.")
                return
            
            # 檢查載入的資料是否符合預期形狀 (frames, joints, 3)
            if data is not None and len(data.shape) == 3 and data.shape[2] == 3:
                frame_count = data.shape[0]
                print(f"Number of frames: {frame_count}")

                # 如果沒有載入視頻，或者新增file have larger total frame，則創建虛擬視頻播放器
                if self.player is None or frame_count > self.max_frame_3d:
                    self.max_frame_3d = frame_count
                    if self.player is not None:
                        self.player.release()
                    print(f"Creating virtual black video with {self.max_frame_3d} frame")
                    self.player = BlackVideoPlayer(frame_count=self.max_frame_3d)
                    self.recent_video_filename = "Virtual Black Video"
                    self.recent_video_path = "Virtual Black Video"
                    self.update_loaded_files_label()
                    
                # 創建檔案資訊字典
                file_info = {
                    'filename': os.path.basename(filename),
                    'full_path': filename,
                    'data': data,
                    'frame_count': frame_count,
                    'color': self.get_next_color(len(self.loaded_points_files))  # 為每個檔案分配不同顏色
                }
                print(f"Assigning color {file_info['color']} to {file_info['filename']}")
                
                # 添加到已加載檔案列表
                self.loaded_points_files.append(file_info)
                
                # 根據 is_visible_by_default 決定是否勾選新加載的檔案
                if is_visible_by_default:
                    self.visible_points_files.add(len(self.loaded_points_files) - 1)
                
                # 更新列表顯示
                self.update_points_list()
                
                # 如果是第一個檔案，自動選中
                if len(self.loaded_points_files) == 1:
                    self.current_points_index = 0
                    self.points3d = data
                    self.points_frame_count = frame_count
                    self.frame_offset = 0
                    if hasattr(self, 'offset_spin'):
                        self.offset_spin.setValue(0)

                # QMessageBox.information(self, "Success", f"3D data loaded: {os.path.basename(filename)} ({frame_count} frames)")
                self.update_loaded_files_label()
                self.update_frame()
                
                # 載入3D資料後顯示右側面板
                self.toggle_panel_visibility(self.right_panel_container_widget, True)
                self.action_toggle_3d_data.setChecked(True)
            else:
                QMessageBox.critical(self, "Error", f"Unexpected data shape: {data.shape}. Expected 3D array (frames, joints, 3) with 3 coordinates per joint.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load 3D data:\n{str(e)}")
    
    def load_pixel2d(self):
        dialog = PixelFileDialog(self)
        if dialog.exec_():
            if not dialog.center_path and not dialog.left_path:
                return
            name = "Pixel_" + (os.path.basename(dialog.center_path) if dialog.center_path else os.path.basename(dialog.left_path))
            data = PixelData(name, center_path=dialog.center_path, left_path=dialog.left_path)
            self.loaded_pixel2d_files.append(data)
            self.visible_pixel2d_files.add(len(self.loaded_pixel2d_files) - 1)
            self.update_pixel2d_list()
            self.update_frame()
            self.toggle_panel_visibility(self.right_panel_container_widget, True)
            self.action_toggle_3d_data.setChecked(True)

    def get_next_color(self, index):
        """為每個3D資料檔案分配不同的顏色"""
        colors = [
            (0, 0, 255),    # 紅色 (BGR)
            (0, 255, 0),    # 綠色 (BGR)
            (255, 0, 0),    # 藍色 (BGR)
            (0, 255, 255),  # 黃色 (BGR)
            (255, 0, 255),  # 洋紅色 (BGR)
            (255, 255, 0),  # 青色 (BGR)
            (128, 0, 128),  # 紫色 (BGR)
            (0, 165, 255),  # 橙色 (BGR)
            (0, 128, 0),    # 深綠色 (BGR)
            (0, 0, 128),    # 深紅色 (BGR)
        ]
        assigned_color = colors[index % len(colors)]
        print(f"Getting color for index {index}: {assigned_color} (BGR)")
        return assigned_color
    
    def update_points_list(self):
        """更新3D資料檔案列表顯示"""
        self.points_list.clear()
        for i, file_info in enumerate(self.loaded_points_files):
            item = QListWidgetItem()
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            
            # 設定勾選狀態
            if i in self.visible_points_files:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            
            # 設定顯示文字
            item_text = f"{file_info['filename']} ({file_info['frame_count']} frames)"
            '''
            if i == self.current_points_index:
                item_text += " [Active]"
            '''
            item.setText(item_text)
            
            self.points_list.addItem(item)

    def update_pixel2d_list(self):
        self.pixel2d_listwidget.clear()
        for i, data in enumerate(self.loaded_pixel2d_files):
            txt = f"{data.name} {'[C]' if data.has_center() else ''}{'[L]' if data.has_left() else ''}"
            item = QListWidgetItem(txt)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if i in self.visible_pixel2d_files else Qt.Unchecked)
            self.pixel2d_listwidget.addItem(item)
    
    def on_pixel2d_checkbox_changed(self, item):
        i = self.pixel2d_listwidget.row(item)
        if 0 <= i < len(self.loaded_pixel2d_files):
            if item.checkState() == Qt.Checked:
                self.visible_pixel2d_files.add(i)
            else:
                self.visible_pixel2d_files.discard(i)
            self.update_frame()
    
    def on_points_checkbox_changed(self, item):
        """當使用者勾選或取消勾選3D資料檔案時"""
        index = self.points_list.row(item)
        if 0 <= index < len(self.loaded_points_files):
            if item.checkState() == Qt.Checked:
                self.visible_points_files.add(index)
                print(f"Enabled 3D data: {self.loaded_points_files[index]['filename']}")
            else:
                self.visible_points_files.discard(index)
                print(f"Disabled 3D data: {self.loaded_points_files[index]['filename']}")
            
            # 立即更新幀顯示
            self.update_frame()

    def on_points_file_double_clicked(self, item):
        """當使用者雙擊3D資料檔案時，切換為當前激活檔案"""
        # self.is_raw_mocap_active = False # Reverted: Switching to NPY/CSV mode
        # self.left_panel_container_widget.hide() # Reverted: Hide left panel

        index = self.points_list.row(item)
        if 0 <= index < len(self.loaded_points_files):
            self.current_points_index = index
            file_info = self.loaded_points_files[index]
            self.points3d = file_info['data']
            self.points_frame_count = file_info['frame_count']
            self.loaded_points_filename = file_info['filename']
            self.frame_offset = 0
            if hasattr(self, 'offset_spin'):
                self.offset_spin.setValue(0)
            
            print(f"Switched to 3D data: {file_info['filename']}")
            self.update_points_list()  # 更新列表顯示
            self.update_loaded_files_label()

    ########## Video Control Functions ##########
    def update_loaded_files_label(self):
        # Update the info label with loaded file names  
        self.btn_load_video[1].setText(self.recent_video_filename if self.recent_video_filename else "No File Loaded")
        self.btn_load_intr[1].setText(self.loaded_intrinsics_filename if self.loaded_intrinsics_filename else "No File Loaded") 
        self.btn_load_extr[1].setText(self.loaded_extrinsics_filename if self.loaded_extrinsics_filename else "No File Loaded")
        
        # 顯示右側列表當前選中的3D資料檔案
        if self.current_points_index >= 0 and self.current_points_index < len(self.loaded_points_files):
            current_file = self.loaded_points_files[self.current_points_index]
            self.btn_load_points[1].setText(f"{current_file['filename']} ({current_file['frame_count']})")
        else:
            self.btn_load_points[1].setText(f"No File Loaded ({len(self.loaded_points_files)} files available)")

        # 更新原始 Mocap 資料的詳細資訊標籤
        if self.raw_mocap_data is not None:
            self.raw_mocap_file_details_label.setText(
                f"{os.path.basename(self.raw_mocap_filename)} ({self.raw_mocap_frame_count} frames)"
            )
        else:
            self.raw_mocap_file_details_label.setText("Not Loaded")

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
        # 如果是虛擬視頻，直接使用黑色背景，不用轉換
        if isinstance(self.player, BlackVideoPlayer):
            frame_bgr = frame 
        else:
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # Optionally undistort using intrinsics if available
        # if self.intrinsics is not None:
        #     cam_mtx = np.array(self.intrinsics["camera_matrix"])
        #     dcoeff = self.intrinsics["dist_coeffs"]
        #     if isinstance(dcoeff[0], list):
        #         dcoeff = np.array(dcoeff[0])
        #     else:
        #         dcoeff = np.array(dcoeff)
        #     frame_bgr = cv2.undistort(frame_bgr, cam_mtx, dcoeff)
        
        # Map 3D points onto the frame if available
        # Drawing primary 3D data (either raw mocap or currently selected from loaded_points_files)
        if self.extrinsics is not None and (
            self.points3d is not None
            or self.visible_points_files
            or (self.raw_mocap_data is not None and self.show_raw_mocap_points)
            or self.visible_pixel2d_files
        ):  # Only draw if there's *any* data to draw
            frame_bgr = self.draw_3d_points_and_skeleton(frame_bgr, self.player.current_frame, bgr=True)

        # Convert processed frame back to RGB (if it was BGR, for QImage)
        # 虛擬視頻的frame_bgr已經是BGR，直接使用
        # if isinstance(self.player, BlackVideoPlayer):
        #     frame_rgb = frame_bgr 
        # else:
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

        # Update 3D visualization panel
        self.update_3d_visualization_panel(self.player.current_frame)

    def change_offset(self, value):
        self.frame_offset = value
        self.update_frame() 
        
    def toggle_playback(self):
        if self.player is None:
            QMessageBox.warning(self, "Warning", "Load a video or 3D data first.")
            return
        if self.timer.isActive():
            self.timer.stop()
            self.btn_toggle.setText("Play")
            self.is_playing = False
            self.player.is_playing = False  # added: stop player playback
        else:
            if self.player.frame_count > 0: # 只有有幀數才允許播放
                self.timer.start(1000 // int(self.player.fps))
                self.btn_toggle.setText("Pause")
                self.is_playing = True
                self.player.is_playing = True  # added: start player playback
            else:
                QMessageBox.warning(self, "Warning", "No frames to play.")

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
    
        # --- new helper ---
    def locate_frame(self):
        """Jump to an exact frame number."""
        if self.player:
            current = self.player.current_frame
            frame, ok = QInputDialog.getInt(
                self, "Locate Frame", "Enter frame number:",
                min=0, max=self.player.frame_count - 1,
                value=current,
            )
            if ok:
                self.player.current_frame = frame
                self.update_frame()

    # --- new helper ---
    def locate_time(self):
        """Jump to an exact timestamp (HH:MM:SS)."""
        if self.player:
            cur_time = self.player.get_current_time()
            total_time = self.player.frame_count / self.player.fps
            time_str, ok = QInputDialog.getText(
                self, "Locate Time",
                f"Enter time (HH:MM:SS, max {self.format_time(total_time)}):",
                text=self.format_time(cur_time)
            )
            if ok:
                try:
                    h, m, s = map(int, time_str.split(':'))
                    target_sec   = h*3600 + m*60 + s
                    self.player.current_frame = int(
                        max(0, min(self.player.frame_count-1, target_sec * self.player.fps))
                    )
                    self.update_frame()
                except ValueError:
                    QMessageBox.warning(self, "Invalid Time",
                                        "Please enter time in HH:MM:SS format.")

    def copy_offset(self):
        """
        Copy current frame-offset value to clipboard.
        """
        QGuiApplication.clipboard().setText(str(self.frame_offset))
        
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
        elif event.key() == Qt.Key_R:
            self.locate_frame()
        elif event.key() == Qt.Key_F:
            self.locate_time()
        elif event.key() == Qt.Key_Z:
            self.copy_offset()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        if self.player is not None:
            self.player.release()
        event.accept()
        
    def _load_camera_parameters(self, intrinsics_path, extrinsics_path):
        """載入指定的相機內外參數檔案"""
        # 加載內參
        if os.path.exists(intrinsics_path):
            try:
                with open(intrinsics_path, 'r') as fp:
                    data = json.load(fp)
                self.intrinsics = data
                self.loaded_intrinsics_filename = os.path.basename(intrinsics_path)
                print(f"Loaded Intrinsics from {intrinsics_path}")
            except Exception as e:
                print(f"Failed to load intrinsics: {str(e)}")
                self.intrinsics = None
                self.loaded_intrinsics_filename = ""
        else:
            print(f"Intrinsics file not found: {intrinsics_path}")
            self.intrinsics = None
            self.loaded_intrinsics_filename = ""
        
        # 加載外參
        if os.path.exists(extrinsics_path):
            try:
                with open(extrinsics_path, 'r') as fp:
                    data = json.load(fp)
                self.extrinsics = data
                best_ext = np.array(data["best_extrinsic"])
                rotation_3x3 = best_ext[:, :3]
                translation_vec = best_ext[:, 3].reshape(3,1)
                self.rvec, _ = cv2.Rodrigues(rotation_3x3)
                self.tvec = translation_vec
                self.loaded_extrinsics_filename = os.path.basename(extrinsics_path)
                print(f"Loaded Extrinsics from {extrinsics_path}")
            except Exception as e:
                print(f"Failed to load extrinsics: {str(e)}")
                self.extrinsics = None
                self.rvec = None
                self.tvec = None
                self.loaded_extrinsics_filename = ""
        else:
            print(f"Extrinsics file not found: {extrinsics_path}")
            self.extrinsics = None
            self.rvec = None
            self.tvec = None
            self.loaded_extrinsics_filename = ""

        # 更新UI顯示
        self.update_loaded_files_label()
        self.update_frame()

    def update_camera_parameters(self):
        """更新相机内外参数 - 使用预设的绝对路径"""
        intrinsics_path = "data/intrinsic_middle.json"
        extrinsics_path = "data/extrinsics_middle.json"
        self.active_pixel2d_view = "center"
        self._load_camera_parameters(intrinsics_path, extrinsics_path)

    
    def update_camera_parameters_left(self):
        """切換到left視角的相機內外參數"""
        intrinsics_path = "data/intrinsic_left.json"
        extrinsics_path = "data/extrinsics_left.json"
        self.active_pixel2d_view = "left"
        self._load_camera_parameters(intrinsics_path, extrinsics_path)

    def on_skeleton_checkbox_changed(self, state):
        self.show_skeleton = state == Qt.Checked
        self.update_frame()

    def export_video(self):
        if not self.player or not self.recent_video_filename:
            QMessageBox.warning(self, "Warning", "Please load a video or 3D data first.")
            return
        
        # 如果是虚拟视频，直接创建新的黑视频
        if isinstance(self.player, BlackVideoPlayer):
            video_name = "virtual_black_video"
            fps = self.player.fps
            width = self.player.width
            height = self.player.height
            total_frames = self.player.frame_count
            is_virtual = True
        else:
            # 生成导出文件名
            video_name = self.recent_video_filename
            # 用cap读取原始帧，保证分辨率和像素排列不变
            cap = cv2.VideoCapture(self.loaded_video_path)
            if not cap.isOpened():
                QMessageBox.warning(self, "Error", "Cannot open video file for export.")
                return
            fps = self.player.fps
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            is_virtual = False

        # 获取所有勾选的3D点文件名
        showing_files = [self.loaded_points_files[i]['filename'] for i in sorted(self.visible_points_files) if 0 <= i < len(self.loaded_points_files)]
        showing_files_str = '+'.join(showing_files) if showing_files else 'none'
        skeleton_status = 'true' if self.show_skeleton else 'false'
        default_name = f"exported_{video_name}+{showing_files_str}+{skeleton_status}.mp4"

        save_path, _ = QFileDialog.getSaveFileName(self, "Export Video", default_name, "MP4 Files (*.mp4)")
        if not save_path:
            if not is_virtual: cap.release() # 如果是实际视频，退出前释放cap
            return

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(save_path, fourcc, fps, (width, height))

        # print(f"Exporting: {self.recent_video_filename}")
        print(f"Exporting: fps={fps}, width={width}, height={height}, total_frames={total_frames}")

        progress = QProgressDialog("Exporting video...", "Cancel", 0, total_frames, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        # 保存当前帧
        original_frame = self.player.current_frame
        was_playing = self.is_playing
        self.is_playing = False
        self.player.is_playing = False

        for frame_idx in range(total_frames):
            if is_virtual:
                frame = np.zeros((height, width, 3), dtype=np.uint8) # 黑色背景
            else:
                ret, frame = cap.read()
                if not ret:
                    break
            
            # frame 是 BGR 格式，直接在 frame 上绘制骨架
            self.player.current_frame = frame_idx
            frame_bgr = self.draw_3d_points_and_skeleton(frame, frame_idx, bgr=True)
            # 画timer和帧号
            current_time = frame_idx / fps
            total_time = total_frames / fps
            timer_text = f"{self.format_time(current_time)} / {self.format_time(total_time)}"
            frame_text = f"Frame: {frame_idx} / {total_frames}"
            cv2.putText(frame_bgr, timer_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
            cv2.putText(frame_bgr, frame_text, (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
            
            out.write(frame_bgr)
            progress.setValue(frame_idx)
            QCoreApplication.processEvents()
            if progress.wasCanceled():
                break
        
        if not is_virtual: cap.release()
        out.release()
        progress.close()
        # 恢复 current_frame
        self.player.current_frame = original_frame
        self.update_frame()
        self.is_playing = was_playing
        self.player.is_playing = was_playing
        QMessageBox.information(self, "Export Finished", f"Video exported to {save_path}")

    def draw_points_and_skeleton_on_frame(self, frame_bgr, pts3d, color, draw_skeleton=True, NeedProjection=True):
        """Helper function to draw points and skeleton for a given 3D points array and color"""
        if self.rvec is not None and self.tvec is not None:
            if self.intrinsics is not None:
                cam_mtx = np.array(self.intrinsics["camera_matrix"])
            else:
                cam_mtx = np.array(self.extrinsics["camera_matrix"])
            dcoeff_ex = np.array(self.extrinsics["dist_coeffs"])
            
            # Filter out NaN points before projection to avoid errors
            valid_pts_mask = ~np.isnan(pts3d).any(axis=1)
            valid_pts3d = pts3d[valid_pts_mask]

            if valid_pts3d.shape[0] == 0: # If no valid points, return early
                return frame_bgr

            if NeedProjection:
                projected, _ = cv2.projectPoints(valid_pts3d.reshape(-1, 1, 3), self.rvec, self.tvec, cam_mtx, dcoeff_ex)
                projected = projected.squeeze().astype(int)
            else:
                projected = pts3d[:, :2]
                projected = projected.astype(int)
            
            # 畫點
            for pt in projected:
                x, y = pt
                if 0 <= x < frame_bgr.shape[1] and 0 <= y < frame_bgr.shape[0]:
                    cv2.circle(frame_bgr, (x, y), 4, color, -1)
            
            # 畫骨架 (僅當 draw_skeleton 為 True 且 show_skeleton 勾選時)
            if draw_skeleton and self.show_skeleton:
                num_joints = pts3d.shape[0]
                joint_pairs = JOINT_PAIRS_MAP.get(num_joints) # 從映射表中獲取骨架連接對
                if joint_pairs:
                    for joint_pair in joint_pairs:
                        # Ensure both joints in the pair are valid (not NaN)
                        if valid_pts_mask[joint_pair[0]] and valid_pts_mask[joint_pair[1]]:
                            pt1 = projected[np.where(valid_pts_mask)[0] == joint_pair[0]][0] # Get projected index for original joint_pair[0]
                            pt2 = projected[np.where(valid_pts_mask)[0] == joint_pair[1]][0] # Get projected index for original joint_pair[1]
                            x1, y1 = pt1
                            x2, y2 = pt2
                            if (0 <= x1 < frame_bgr.shape[1] and 0 <= y1 < frame_bgr.shape[0] and
                                0 <= x2 < frame_bgr.shape[1] and 0 <= y2 < frame_bgr.shape[0]):
                                line_color = tuple(int(c * 0.7) for c in color) # Darker shade for lines
                                cv2.line(frame_bgr, (x1, y1), (x2, y2), line_color, 2)
        return frame_bgr

    def draw_3d_points_and_skeleton(self, frame_bgr, frame_idx, bgr=False):
        """在frame_bgr上繪製所有勾選的3D點和骨架，frame_idx為當前幀號。bgr=True表示frame_bgr已經是BGR格式。"""
        # 如果不是BGR格式，先轉BGR
        if not bgr:
            frame_bgr = cv2.cvtColor(frame_bgr, cv2.COLOR_RGB2BGR)
        
        # 在 draw_3d_points_and_skeleton 前面加上 pixel
        for i in self.visible_pixel2d_files:
            data = self.loaded_pixel2d_files[i]
            arr = data.get(self.active_pixel2d_view)
            if arr is not None and 0 <= frame_idx < arr.shape[0]:
                pts2d = arr[frame_idx]
                self.draw_points_and_skeleton_on_frame(frame_bgr, pts2d, (34, 139, 230), draw_skeleton=self.show_skeleton, NeedProjection=False)

        if self.extrinsics is not None:
            current_idx = frame_idx + self.frame_offset

            # 繪製所有勾選的 NPY/CSV 檔案
            for file_index in self.visible_points_files:
                if 0 <= file_index < len(self.loaded_points_files):
                    file_info = self.loaded_points_files[file_index]
                    points_data = file_info['data']
                    color = file_info['color']
                    if 0 <= current_idx < points_data.shape[0]:
                        pts3d = points_data[current_idx]
                        # 對於 NPY/CSV 檔案，根據 skeleton_checkbox 決定是否繪製骨架
                        self.draw_points_and_skeleton_on_frame(frame_bgr, pts3d, color, draw_skeleton=self.show_skeleton)
            
            # 繪製原始 Mocap 資料 (如果已載入並勾選顯示)
            if self.raw_mocap_data is not None and self.show_raw_mocap_points:
                if 0 <= current_idx < self.raw_mocap_frame_count:
                    joint_names = self.get_current_raw_mocap_joint_names()
                    pts3d_raw_mocap = self.raw_mocap_data.get_joints_by_names(current_idx, joint_names)
                    self.draw_points_and_skeleton_on_frame(frame_bgr, pts3d_raw_mocap, (255, 255, 255), draw_skeleton=False)

        return frame_bgr

    def load_folder(self):
        """載入資料夾中的所有 NPY/CSV 檔案"""
        folder_path = QFileDialog.getExistingDirectory(self, "Select 3D Data Folder")
        if not folder_path:
            return

        loaded_count = 0
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                if file.lower().endswith(('.npy', '.csv')):
                    # 透過 load_folder 載入的檔案預設為不可見
                    self.load_points(filename=file_path, is_visible_by_default=False)
                    loaded_count += 1
        
        QMessageBox.information(self, "Load Folder", f"Finished loading {loaded_count} 3D data files from {os.path.basename(folder_path)}.")
        self.update_points_list() # 確保列表是最新的
        self.update_frame()

    def load_raw_mocap_data(self):
        """
        載入原始 mocap CSV 檔案，遵循舊版 projection_window.py 的邏輯。
        將資料載入到 self.raw_mocap_data (RawMocapData 物件)。
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Select Raw Mocap CSV", "", "CSV Files (*.csv)")
        if filename:
            try:                
                # 讀取整個 CSV 檔案來處理多行標頭
                # 第三行 (索引2) 包含 Type (Bone, Time etc.)
                # 第四行 (索引3) 包含 Name (Skeleton 001:Hip, Time (Seconds) etc.)
                # 第五行 (索引4) 包含 ID (1, etc.)
                # 第六行 (索引5) 包含 Rotation, Position
                # 第七行（索引6）包含Axis(X/Y/Z)
                raw_df = pd.read_csv(filename, header=[1, 2, 3, 4, 5], low_memory=False)
                # === 2) 只保留 Position 的 X/Y/Z ===
                pos = raw_df.xs("Position", level=3, axis=1)   # 取出 Axis == 'Position'
                # === 3) 把欄位重新命名成   f"{ID}:{Name}({Type})_<axis>" ===
                new_cols = []
                for col in pos.columns:
                    Type, Name, ID, axis = col         # 依序對應多層索引
                    joint = f"{ID}:{Name}({Type})"
                    new_cols.append(f"{joint}_{axis}") # 例如  '1:Skeleton 001:Hip(Bone)_X'
                pos.columns = new_cols
                
                type_list = list(pos.iloc[0].index)
                self.raw_mocap_data = RawMocapData(pos, type_list)
                self.left_panel_container_widget.show() # Make the left panel visible
                
                joint_names = self.raw_mocap_data.get_joint_names()
                self.raw_mocap_joint_list.clear() # Clear existing items
                
                # Block signals temporarily to prevent on_raw_mocap_joint_checkbox_changed from firing
                self.raw_mocap_joint_list.blockSignals(True) 
                
                # Determine initial checked state based on the currently active radio button
                # If Custom mode is active, default to Skeleton 001 for initial load
                for name in joint_names:
                    item = QListWidgetItem(name)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    if "Skeleton 001" in name:
                        item.setCheckState(Qt.Checked)
                    else:
                        item.setCheckState(Qt.Unchecked)
                    self.raw_mocap_joint_list.addItem(item)
                
                self.raw_mocap_joint_list.blockSignals(False) # Re-enable signals

                self.raw_mocap_filename = filename
                self.raw_mocap_frame_count = self.raw_mocap_data.get_total_frame()
                
                if self.raw_mocap_frame_count > self.max_frame_3d:
                    self.max_frame_3d = self.raw_mocap_frame_count
                # 如果沒有載入視頻，或者正在使用虛擬視頻播放器，則創建新虛擬視頻播放器
                if self.player is None or isinstance(self.player, BlackVideoPlayer):
                    self.max_frame_3d = self.raw_mocap_frame_count
                    if self.player is not None:
                        self.player.release()
                    print(f"Creating virtual black video with {self.max_frame_3d} frame for raw mocap data")
                    self.player = BlackVideoPlayer(frame_count=self.max_frame_3d)
                    self.recent_video_filename = "Virtual Black Video (Raw Mocap)"
                    self.recent_video_path = "Virtual Black Video (Raw Mocap)"

                self.update_loaded_files_label()
                self.update_frame()
                # Toggle visibility of Joint - Mocap and 3D - Mocap panels when loaded
                self.toggle_panel_visibility(self.left_panel_container_widget, True)
                self.action_toggle_joint_mocap.setChecked(True)
                self.toggle_panel_visibility(self.three_d_visualization_container_widget, True)
                self.action_toggle_3d_mocap.setChecked(True)
                
                # Force select 'Select All Raw Mocap Joints' as default mode after loading
                self.radio_show_all_raw_mocap.setChecked(True)
                self.on_raw_mocap_display_mode_changed()
                self.update_selected_joints_count_label() # Call here after load
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load Raw Mocap data: {str(e)}")

    def on_raw_mocap_points_checkbox_changed(self, state):
        """當原始 Mocap 點顯示勾選框狀態改變時"""
        self.show_raw_mocap_points = state == Qt.Checked
        self._update_raw_mocap_display_state() # 呼叫輔助函數來更新UI和畫面
        self.update_3d_visualization_panel(self.player.current_frame) # Update the 3D visualization panel

    def on_raw_mocap_display_mode_changed(self):
        # 根據選中的 Radio Button 設定模式，並更新關節點列表的勾選狀態和啟用狀態
        if self.raw_mocap_data is None:
            return

        self.raw_mocap_joint_list.blockSignals(True) # Block signals during update

        # Reset all checkboxes first
        # for i in range(self.raw_mocap_joint_list.count()):
        #     item = self.raw_mocap_joint_list.item(i)
        #     item.setCheckState(Qt.Unchecked)

        if self.radio_show_all_raw_mocap.isChecked():
            self.raw_mocap_display_mode = 'all'
            # for i in range(self.raw_mocap_joint_list.count()):
            #     item = self.raw_mocap_joint_list.item(i)
            #     item.setCheckState(Qt.Checked)
            self.raw_mocap_joint_list.setEnabled(False) # Disable list in 'all' mode
        elif self.radio_show_skeleton001_raw_mocap.isChecked():
            self.raw_mocap_display_mode = 'skeleton001'
            # for i in range(self.raw_mocap_joint_list.count()):
            #     item = self.raw_mocap_joint_list.item(i)
            #     if "Skeleton 001" in item.text():
            #         item.setCheckState(Qt.Checked)
            #     else:
            #         item.setCheckState(Qt.Unchecked)
            self.raw_mocap_joint_list.setEnabled(False) # Disable list in 'skeleton001' mode
        elif self.radio_show_custom_raw_mocap.isChecked(): # Custom mode
            self.raw_mocap_display_mode = 'custom'
            self.raw_mocap_joint_list.setEnabled(True) # Enable list in 'custom' mode
        
        self.raw_mocap_joint_list.blockSignals(False) # Re-enable signals
        self._update_raw_mocap_display_state() # Update UI and redraw frame

    def on_raw_mocap_joint_checkbox_changed(self, item):
        # 如果不是 Custom mode，當列表中的項目被修改時，自動切換到 Custom mode
        if self.raw_mocap_display_mode != 'custom':
            self.radio_show_custom_raw_mocap.setChecked(True)
            self.on_raw_mocap_display_mode_changed() # Force update to custom mode
        self._update_raw_mocap_display_state()

    def on_raw_mocap_joint_list_clicked(self, item):
        """當使用者點擊原始 Mocap 關節列表中的項目時，切換其勾選狀態並切換到 Custom mode。"""
        self.raw_mocap_joint_list.blockSignals(True) # 暫時禁用信號
        if item.checkState() == Qt.Checked:
            item.setCheckState(Qt.Unchecked)
        else:
            item.setCheckState(Qt.Checked)
        self.raw_mocap_joint_list.blockSignals(False)
        
        # 即使點擊了，也自動切換到 Custom mode
        self.radio_show_custom_raw_mocap.setChecked(True)
        self.on_raw_mocap_display_mode_changed() # 呼叫模式改變函數來更新

    def _update_raw_mocap_display_state(self):
        """更新原始 Mocap 點的顯示狀態，並觸發畫面重繪。"""
        enable_modes = self.show_raw_mocap_points and (self.raw_mocap_data is not None)
        self.radio_show_all_raw_mocap.setEnabled(enable_modes)
        self.radio_show_skeleton001_raw_mocap.setEnabled(enable_modes)
        self.radio_show_custom_raw_mocap.setEnabled(enable_modes) # Enable/disable custom radio button
        
        # 根據當前模式決定列表是否啟用
        self.raw_mocap_joint_list.setEnabled(enable_modes and self.raw_mocap_display_mode == 'custom')
        
        self.update_frame() # 重新繪製以反映變化
        self.update_selected_joints_count_label() # 更新選中關節點數量的標籤

    def get_current_raw_mocap_joint_names(self):
        # 根據目前模式回傳 joint 名稱 list
        if self.raw_mocap_data is None:
            return []
        
        if self.raw_mocap_display_mode == 'all':
            return self.raw_mocap_data.get_joint_names()
        elif self.raw_mocap_display_mode == 'skeleton001':
            return [name for name in self.raw_mocap_data.get_joint_names() if "Skeleton 001" in name]
        elif self.raw_mocap_display_mode == 'custom': # 新增 Custom mode 邏輯
            names = []
            for i in range(self.raw_mocap_joint_list.count()):
                item = self.raw_mocap_joint_list.item(i)
                if item.checkState() == Qt.Checked:
                    names.append(item.text())
            return names
        return [] # Default empty list if no mode is selected

    def update_3d_visualization_panel(self, frame_idx):
        """Update the 3D visualization panel with current raw mocap data."""
        self.ax_3d.cla() # Clear current axes
        self.ax_3d.set_xlabel('X')
        self.ax_3d.set_ylabel('Y')
        self.ax_3d.set_zlabel('Z')
        self.ax_3d.set_title(f"Raw Mocap 3D - Frame {frame_idx}")

        # Set fixed axis limits similar to visualization.py
        self.ax_3d.set_xlim([-1, 1])
        self.ax_3d.set_ylim([0, 1.8])
        self.ax_3d.set_zlim([0, 1])

        if self.raw_mocap_data is not None and self.show_raw_mocap_points:
            current_idx = frame_idx + self.frame_offset
            if 0 <= current_idx < self.raw_mocap_frame_count:
                joint_names = self.get_current_raw_mocap_joint_names()
                pts3d_raw_mocap = self.raw_mocap_data.get_joints_by_names(current_idx, joint_names)
                
                # Filter out NaN points for plotting
                valid_pts_mask = ~np.isnan(pts3d_raw_mocap).any(axis=1)
                valid_pts3d = pts3d_raw_mocap[valid_pts_mask]

                if valid_pts3d.shape[0] > 0:
                    self.ax_3d.scatter(valid_pts3d[:, 0], valid_pts3d[:, 1], valid_pts3d[:, 2], color='blue', s=10)

        self.canvas_3d.draw()

    def on_scroll(self, event):
        # This method is called when the scroll wheel is used
        if event.inaxes == self.ax_3d: # Ensure scroll event is within our 3D axes
            cur_xlim = self.ax_3d.get_xlim3d()
            cur_ylim = self.ax_3d.get_ylim3d()
            cur_zlim = self.ax_3d.get_zlim3d()

            # Calculate zoom factor
            zoom_factor = 0.9 # For zooming in
            if event.button == 'up':
                scale_factor = zoom_factor
            elif event.button == 'down':
                scale_factor = 1 / zoom_factor
            else:
                return

            # Get center of the current view
            x_center = (cur_xlim[0] + cur_xlim[1]) / 2
            y_center = (cur_ylim[0] + cur_ylim[1]) / 2
            z_center = (cur_zlim[0] + cur_zlim[1]) / 2

            # Calculate new limits centered around the current view center
            new_xlim = [x_center - (x_center - cur_xlim[0]) * scale_factor, x_center + (cur_xlim[1] - x_center) * scale_factor]
            new_ylim = [y_center - (y_center - cur_ylim[0]) * scale_factor, y_center + (cur_ylim[1] - y_center) * scale_factor]
            new_zlim = [z_center - (z_center - cur_zlim[0]) * scale_factor, z_center + (cur_zlim[1] - z_center) * scale_factor]

            self.ax_3d.set_xlim3d(new_xlim)
            self.ax_3d.set_ylim3d(new_ylim)
            self.ax_3d.set_zlim3d(new_zlim)
            
            self.canvas_3d.draw_idle()

    def toggle_panel_visibility(self, panel_widget, is_visible):
        panel_widget.setVisible(is_visible)
        self.update_frame()

    def update_selected_joints_count_label(self):
        """更新顯示選中關節點數量的標籤。"""
        selected_count = 0
        for i in range(self.raw_mocap_joint_list.count()):
            item = self.raw_mocap_joint_list.item(i)
            if item.checkState() == Qt.Checked:
                selected_count += 1
        self.selected_joints_count_label.setText(f"Selected {selected_count} joints")

    def export_custom_joint_list(self):
        """將選中的自定義關節點名稱匯出為TXT檔案。"""
        if self.raw_mocap_data is None:
            QMessageBox.warning(self, "Warning", "No raw mocap data loaded.")
            return
        if self.raw_mocap_display_mode != 'custom':
            QMessageBox.warning(self, "Warning", "Please switch to 'Custom Select Joints' mode to export selected joints.")
            return
        
        selected_joints = self.get_current_raw_mocap_joint_names()
        if not selected_joints:
            QMessageBox.information(self, "Info", "No joints selected in Custom mode to export.")
            return
        
        selected_count = len(selected_joints) # Get the count of selected joints
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") # Generate timestamp
        default_filename = f"Selected_{selected_count}_joints_{timestamp}.txt" # Construct the new filename
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Custom Joint List", default_filename, "Text Files (*.txt)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    for joint_name in selected_joints:
                        f.write(joint_name + '\n')
                QMessageBox.information(self, "Success", f"Custom joint list exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export custom joint list:\n{str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProjectionWindow3()
    # window.resize(800, 600)  # matches main_window size
    window.show()
    sys.exit(app.exec_())
