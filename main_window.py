from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QSlider, QLabel, QFileDialog, 
                            QListWidget, QSplitter, QAbstractItemView, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, QDir
from PyQt5.QtGui import QImage, QPixmap
from video_player import VideoPlayer
import os
import cv2

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CV Frame Labeler")
        self.setGeometry(100, 100, 1000, 600)
        
        # 设置窗口焦点策略，确保窗口可以捕获键盘事件
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Video player
        self.video_player = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        
        # 全局变量，存储当前打开的文件夹路径
        self.folder_path = ""
        
        # UI components
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setMinimumSize(200, 150)
        
        # 创建用于显示时间和帧数的标签
        self.info_label = QLabel(self.video_label)
        self.info_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.info_label.setStyleSheet("background-color: rgba(0, 0, 0, 0.5); color: white; padding: 5px;")
        self.info_label.setText("00:00:00 / 00:00:00\nFrame: 0 / 0")
        
        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.toggle_play)
        
        self.prev_second_btn = QPushButton("<< 1s")
        self.prev_second_btn.clicked.connect(self.prev_second)
        
        self.prev_frame_btn = QPushButton("<<")
        self.prev_frame_btn.clicked.connect(self.prev_frame)
        
        self.next_frame_btn = QPushButton(">>")
        self.next_frame_btn.clicked.connect(self.next_frame)
        
        self.next_second_btn = QPushButton("1s >>")
        self.next_second_btn.clicked.connect(self.next_second)
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.sliderMoved.connect(self.set_position)
        
        # Video list
        self.video_list = QListWidget()
        self.video_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.video_list.itemClicked.connect(self.on_video_selected)
        self.video_list.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
        # Layout
        control_layout = QHBoxLayout()
        control_layout.addWidget(self.prev_second_btn)
        control_layout.addWidget(self.prev_frame_btn)
        control_layout.addWidget(self.play_btn)
        control_layout.addWidget(self.next_frame_btn)
        control_layout.addWidget(self.next_second_btn)
        
        video_layout = QVBoxLayout()
        video_layout.addWidget(self.video_label, 1)
        video_layout.addWidget(self.slider)
        video_layout.addLayout(control_layout)
        
        video_widget = QWidget()
        video_widget.setLayout(video_layout)
        video_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.video_list)
        splitter.addWidget(video_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.setCentralWidget(splitter)
        
        # 设置窗口尺寸策略
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Menu
        menubar = self.menuBar()
        file_menu = menubar.addMenu('File')
        open_action = file_menu.addAction('Open File')
        open_action.triggered.connect(self.open_file)
        open_folder_action = file_menu.addAction('Open Folder')
        open_folder_action.triggered.connect(self.open_folder)
        
        # 添加快捷键提示
        self.statusBar().showMessage("快捷键: 空格 - 播放/暂停, A - 上一帧, D - 下一帧")
        
    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Video File", "", 
                                                 "Video Files (*.mp4 *.avi *.mov)")
        if file_path:
            self.video_list.clear()
            self.folder_path = os.path.dirname(file_path)  # 更新全局文件夹路径
            self.load_video(file_path)
    
    def open_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Open Video Folder")
        if folder_path:
            self.folder_path = folder_path  # 更新全局文件夹路径
            self.load_folder(folder_path)
    
    def load_folder(self, folder_path):
        self.video_list.clear()
        dir = QDir(folder_path)
        video_files = dir.entryList(["*.mp4", "*.avi", "*.mov"], QDir.Files)
        
        for video_file in video_files:
            self.video_list.addItem(video_file)
        
        if video_files:
            first_video = os.path.join(folder_path, video_files[0])
            self.load_video(first_video)
            self.video_list.setCurrentRow(0)
    
    def on_video_selected(self, item):
        """当视频列表中的视频被选中时调用"""
        # 使用全局文件夹路径拼接视频路径
        video_path = os.path.join(self.folder_path, item.text())
        
        # 加载选中的视频
        self.load_video(video_path)
    
    def load_video(self, file_path):
        if self.video_player:
            self.video_player.release()
        try:
            self.video_player = VideoPlayer(file_path)
            self.slider.setMaximum(self.video_player.frame_count - 1)
            self.update_frame()
            self.update_info_label()
            self.play_btn.setEnabled(True)
            self.prev_frame_btn.setEnabled(True)
            self.next_frame_btn.setEnabled(True)
        except ValueError as e:
            print(str(e))
    
    def toggle_play(self):
        if self.video_player:
            self.video_player.is_playing = not self.video_player.is_playing
            if self.video_player.is_playing:
                self.play_btn.setText("Pause")
                self.timer.start(int(1000 / self.video_player.fps))
            else:
                self.play_btn.setText("Play")
                self.timer.stop()
    
    def update_frame(self):
        if self.video_player and self.video_player.is_playing:
            self.video_player.next_frame()
            if self.video_player.current_frame >= self.video_player.frame_count - 1:
                self.video_player.is_playing = False
                self.play_btn.setText("Play")
                self.timer.stop()
        
        if self.video_player:
            frame = self.video_player.get_frame()
            if frame is not None:
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                
                label_size = self.video_label.size()
                scaled_pixmap = QPixmap.fromImage(q_img).scaled(
                    label_size, 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                self.video_label.setPixmap(scaled_pixmap)
                self.slider.blockSignals(True)
                self.slider.setValue(self.video_player.current_frame)
                self.slider.blockSignals(False)
                self.update_info_label()  # 更新信息标签
    
    def update_info_label(self):
        """更新视频左上角的信息标签"""
        if self.video_player:
            current_time = self.video_player.get_current_time()
            total_time = self.video_player.frame_count / self.video_player.fps
            current_frame = self.video_player.current_frame
            total_frames = self.video_player.frame_count
            self.info_label.setText(
                f"{self.format_time(current_time)} / {self.format_time(total_time)}\n"
                f"Frame: {current_frame} / {total_frames}"
            )
            # 调整信息标签的位置和大小
            self.info_label.resize(self.info_label.sizeHint())
            self.info_label.move(10, 10)  # 放置在视频左上角
    
    def prev_frame(self):
        if self.video_player:
            # 暂停视频
            if self.video_player.is_playing:
                self.toggle_play()
            # 跳转到前一帧
            self.video_player.prev_frame()
            self.update_frame()
    
    def next_frame(self):
        if self.video_player:
            # 暂停视频
            if self.video_player.is_playing:
                self.toggle_play()
            # 跳转到下一帧
            self.video_player.next_frame()
            self.update_frame()
    
    def set_position(self, position):
        if self.video_player:
            # 保存当前的播放状态
            was_playing = self.video_player.is_playing
            
            # 如果正在播放，先暂停视频
            if was_playing:
                self.toggle_play()
            
            # 跳转到指定位置
            self.slider.blockSignals(True)
            self.video_player.current_frame = position
            self.update_frame()
            self.slider.blockSignals(False)
            
            # 如果之前是播放状态，恢复播放
            if was_playing:
                self.toggle_play()
            self.update_info_label()  # 更新信息标签
    
    def update_time_label(self):
        if self.video_player:
            current_time = self.video_player.get_current_time()
            total_time = self.video_player.frame_count / self.video_player.fps
            self.time_label.setText(f"{self.format_time(current_time)} / {self.format_time(total_time)}")
    
    def format_time(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    
    def closeEvent(self, event):
        if self.video_player:
            self.video_player.release()
        event.accept()

    def resizeEvent(self, event):
        if self.video_player:
            self.update_frame()
        super().resizeEvent(event)
        
    def keyPressEvent(self, event):
        """处理键盘事件"""
        # print(f"Key pressed: {event.key()}")  # 调试信息，打印按下的键
        if event.key() == Qt.Key_Space:  # 空格键控制播放/暂停
            # print("Space key pressed - Toggling play/pause")  # 调试信息
            self.toggle_play()
        elif event.key() == Qt.Key_A:  # A键控制上一帧
            # print("A key pressed - Previous frame")  # 调试信息
            self.prev_frame()
        elif event.key() == Qt.Key_D:  # D键控制下一帧
            # print("D key pressed - Next frame")  # 调试信息
            self.next_frame()
        else:
            super().keyPressEvent(event)  # 其他按键交给父类处理
    
    def prev_second(self):
        """后退1秒"""
        if self.video_player:
            # 暂停视频
            if self.video_player.is_playing:
                self.toggle_play()
            # 跳转1秒
            self.video_player.jump_seconds(-1)
            self.update_frame()
    
    def next_second(self):
        """前进1秒"""
        if self.video_player:
            # 暂停视频
            if self.video_player.is_playing:
                self.toggle_play()
            # 跳转1秒
            self.video_player.jump_seconds(1)
            self.update_frame()
        