import sys
from PyQt5.QtWidgets import QApplication
# from main_window import MainWindow
from projection_window3 import ProjectionWindow3

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # window = MainWindow()
    window = ProjectionWindow3()
    window.show()
    sys.exit(app.exec_())