import os
import numpy as np
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QFileDialog, QHBoxLayout

class PixelFileDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Pixel2D NPYs")
        self.center_path = None
        self.left_path = None

        layout = QVBoxLayout()
        h1 = QHBoxLayout()
        self.center_btn = QPushButton("Choose Center (C)")
        self.center_label = QLabel("No file selected")
        self.center_btn.clicked.connect(self.choose_center)
        h1.addWidget(self.center_btn)
        h1.addWidget(self.center_label)
        layout.addLayout(h1)

        h2 = QHBoxLayout()
        self.left_btn = QPushButton("Choose Left (L)")
        self.left_label = QLabel("No file selected")
        self.left_btn.clicked.connect(self.choose_left)
        h2.addWidget(self.left_btn)
        h2.addWidget(self.left_label)
        layout.addLayout(h2)

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns = QHBoxLayout()
        btns.addWidget(ok_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)
        self.setLayout(layout)

    def choose_center(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Center Pixel2D NPY/CSV", "", "NPY/CSV Files (*.npy *.csv)")
        if path:
            self.center_path = path
            self.center_label.setText(os.path.basename(path))

    def choose_left(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Center Pixel2D NPY/CSV", "", "NPY/CSV Files (*.npy *.csv)")
        if path:
            self.left_path = path
            self.left_label.setText(os.path.basename(path))

class PixelData:
    def __init__(self, name, center_path=None, left_path=None):
        self.name = name
        self.center_path = center_path
        self.left_path = left_path
        self.center_data = self._load_pixel_file(center_path) if center_path else None
        self.left_data = self._load_pixel_file(left_path) if left_path else None

    @staticmethod
    def _load_pixel_file(path):
        if not path:
            return None
        ext = os.path.splitext(path)[1].lower()
        if ext == '.npy':
            arr = np.load(path)
        elif ext == '.csv':
            import pandas as pd
            df = pd.read_csv(path)
            arr = df.values
            num_cols = arr.shape[1]
            if num_cols % 3 != 0:
                raise ValueError(f"CSV file has {num_cols} columns, not a multiple of 3.")
            num_joints = num_cols // 3
            arr = arr.reshape(-1, num_joints, 3)
        else:
            raise ValueError(f"Unsupported file type: {ext}")
        # Clean NaN to 0
        arr = np.nan_to_num(arr, nan=0)
        return arr

    def has_center(self):
        return self.center_data is not None

    def has_left(self):
        return self.left_data is not None

    def get(self, view):
        if view == 'center':
            return self.center_data
        elif view == 'left':
            return self.left_data
        else:
            return None