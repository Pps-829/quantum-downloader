# main_v3.py
import sys
import base64
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                             QPushButton, QStackedWidget, QLabel, QFrame, QProgressBar,
                             QListWidget, QListWidgetItem, QGraphicsOpacityEffect)
from PyQt6.QtCore import (Qt, QSize, QPropertyAnimation, QEasingCurve, pyqtProperty, 
                        QStandardPaths, QDir)
from PyQt6.QtGui import QIcon, QPixmap, QPainter

# --- Icon Resource Management (Cross-Platform) ---
# Icons are embedded as Base64 strings to make the application self-contained.
# This avoids dependencies on external files or system themes.
# Icons sourced from Feather Icons (MIT License).
ICON_DATA = {
    "download": "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiNFRkZBRjQiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIiBjbGFzcz0iZmVhdGhlciBmZWF0aGVyLWRvd25sb2FkIj48cGF0aCBkPSJNMjEgMTV2NGMwIDFIM2MtMSAwLTEtMS0xLTFWMTUiLz48cG9seWxpbmUgcG9pbnRzPSIxNyA4IDEyIDEzIDcgOCIvPjxsaW5lIHgxPSIxMiIgeTE9IjEzIiB4Mj0iMTIiIHkyPSIzIi8+PC9zdmc+",
    "check": "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiNFRkZBRjQiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIiBjbGFzcz0iZmVhdGhlciBmZWF0aGVyLWNoZWNrLWNpcmNsZSI+PHBhdGggZD0iTTIyIDExLjA4VjEyYTggOCAwIDEgMS0xMi4wNC02LjQ3Ii8+PHBvbHlsaW5lIHBvaW50cz0iMjIgNCAxMiAxNCA5IDEyIi8+PC9zdmc+",
    "settings": "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiNFRkZBRjQiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIiBjbGFzcz0iZmVhdGhlciBmZWF0aGVyLXNldHRpbmdzIj48Y2lyY2xlIGN4PSIxMiIgY3k9IjEyIiByPSIyIi8+PGNpcmNsZSBjeD0iMTkiIGN5PSIxMiIgcj0iMiIvPjxjaXJjbGUgY3g9IjUiIGN5PSIxMiIgcj0iMiIvPjwvc3ZnPg==",
    "plus": "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiNFRkZBRjQiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIiBjbGFzcz0iZmVhdGhlciBmZWF0aGVyLXBsdXMiPjxsaW5lIHgxPSIxMiIgeTE9IjUiIHgyPSIxMiIgeTI9IjE5Ii8+PGxpbmUgeDE9IjUiIHkxPSIxMiIgeDI9IjE5IiB5Mj0iMTIiLz48L3N2Zz4=",
    "pause": "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiNFRkZBRjQiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIiBjbGFzcz0iZmVhdGhlciBmZWF0aGVyLXBhdXNlIj48cmVjdCB4PSI2IiB5PSI0IiB3aWR0aD0iNCIgaGVpZ2h0PSIxNiIvPjxyZWN0IHg9IjE0IiB5PSI0IiB3aWR0aD0iNCIgaGVpZ2h0PSIxNiIvPjwvc3ZnPg==",
    "trash": "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiNFRkZBRjQiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIiBjbGFzcz0iZmVhdGhlciBmZWF0aGVyLXRyYXNoLTIiPjxwb2x5bGluZSBwb2ludHM9IjMgNiA1IDYgMjEgNiIvPjxwYXRoIGQ9Ik0xOSA2djE0YzAgMS0xIDItMiAyaC05Yy0xIDAtMi0xLTItMlY2bTQtM1Y0YTAgMCAwIDEgMiAwaDJhMCAwIDAgMSAyIDB2MiIvPjxsaW5lIHgxPSIxMCIgeTE9IjExIiB4Mj0iMTAiIHkyPSIxNyIvPjxsaW5lIHgxPSIxNCIgeTE9IjExIiB4Mj0iMTQiIHkyPSIxNyIvPjwvc3ZnPg=="
}

def get_icon(name):
    pixmap = QPixmap()
    pixmap.loadFromData(base64.b64decode(ICON_DATA[name]))
    return QIcon(pixmap)

# --- Professional Styling (QSS) - Unchanged from v0.2 ---
PROFESSIONAL_STYLE_SHEET = """
    * { border: none; font-family: 'Segoe UI', 'Roboto', 'Arial'; }
    QMainWindow, QFrame#main_frame { background-color: #2E3440; }
    QFrame#sidebar { background-color: #3B4252; border-right: 1px solid #4C566A; }
    QPushButton#sidebar_button { background-color: transparent; text-align: left; padding: 10px; border-radius: 5px; font-size: 11pt; font-weight: bold; color: #D8DEE9; }
    QPushButton#sidebar_button:hover { background-color: #434C5E; }
    QPushButton#sidebar_button:checked { background-color: #5E81AC; color: #ECEFF4; }
    QLabel#page_title { font-size: 18pt; font-weight: bold; color: #ECEFF4; padding: 10px; }
    QListWidget { background-color: #2E3440; }
    QFrame#download_item_frame { background-color: #3B4252; border-radius: 5px; border: 1px solid #434C5E; }
    QLabel#item_filename { font-weight: bold; font-size: 11pt; color: #ECEFF4; }
    QLabel.info_label { font-size: 9pt; color: #D8DEE9; }
    QProgressBar { background-color: #434C5E; color: #ECEFF4; border-radius: 4px; text-align: center; }
    QProgressBar::chunk { background-color: #88C0D0; border-radius: 4px; }
    QScrollBar:vertical { border: none; background: #3B4252; width: 10px; margin: 0px 0px 0px 0px; }
    QScrollBar::handle:vertical { background: #5E81AC; min-height: 20px; border-radius: 5px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
    QPushButton.action_button { background-color: transparent; }
"""

# --- Custom Widget for each Download Item (Responsive Update) ---
class DownloadItemWidget(QFrame):
    def __init__(self, filename="New Download"):
        super().__init__()
        self.setObjectName("download_item_frame")
        self.setContentsMargins(10, 10, 10, 10)

        # Main Layout
        self.main_layout = QVBoxLayout(self)

        # Top section with filename and status
        top_layout = QHBoxLayout()
        self.filename_label = QLabel(filename)
        self.filename_label.setObjectName("item_filename")
        self.filename_label.setWordWrap(True)  # *** RESPONSIVE: Allow filename to wrap

        self.status_label = QLabel("Status: Queued")
        self.status_label.setObjectName("info_label")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        top_layout.addWidget(self.filename_label)
        top_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximumHeight(8)

        # Bottom section with stats and actions
        bottom_layout = QHBoxLayout()
        self.info_label = QLabel("0 MB / 0 MB  |  0 KB/s  |  ETA: --:--")
        self.info_label.setObjectName("info_label")
        
        self.pause_button = QPushButton(get_icon("pause"), "")
        self.cancel_button = QPushButton(get_icon("trash"), "")
        for btn in [self.pause_button, self.cancel_button]:
            btn.setObjectName("action_button")
            btn.setIconSize(QSize(18, 18))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        bottom_layout.addWidget(self.info_label)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.pause_button)
        bottom_layout.addWidget(self.cancel_button)

        # Assemble
        self.main_layout.addLayout(top_layout)
        self.main_layout.addWidget(self.progress_bar)
        self.main_layout.addLayout(bottom_layout)

    def update_progress(self, percent, size_str, speed_str, eta_str):
        self.progress_bar.setValue(int(percent))
        self.info_label.setText(f"{size_str}  |  {speed_str}  |  ETA: {eta_str}")

    def set_status(self, status):
        self.status_label.setText(f"Status: {status}")

# --- Animated QStackedWidget (Unchanged from v0.2) ---
class AnimatedStackedWidget(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.m_duration = 300
        self.m_fade_animation = QPropertyAnimation(self, b"opacity")
    def set_current_index(self, index):
        self.m_fade_animation.stop()
        self.m_fade_animation.setDuration(self.m_duration // 2)
        self.m_fade_animation.setStartValue(1.0)
        self.m_fade_animation.setEndValue(0.0)
        self.m_fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.m_fade_animation.finished.connect(lambda: self._fade_in(index))
        self.m_fade_animation.start()
    def _fade_in(self, index):
        self.setCurrentIndex(index)
        self.m_fade_animation.setDuration(self.m_duration // 2)
        self.m_fade_animation.setStartValue(0.0)
        self.m_fade_animation.setEndValue(1.0)
        self.m_fade_animation.finished.disconnect()
        self.m_fade_animation.start()
    def set_opacity(self, opacity):
        effect = self.graphicsEffect()
        if not effect:
            effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(effect)
        effect.setOpacity(opacity)
    opacity = pyqtProperty(float, fset=set_opacity)


# --- Main Application Window ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QuantumDownloader")
        self.setMinimumSize(800, 600)  # *** RESPONSIVE: Set a sensible minimum size
        self.setGeometry(100, 100, 950, 700)
        self.setWindowIcon(get_icon("download"))

        # Main frame
        self.main_frame = QFrame(self); self.main_frame.setObjectName("main_frame")
        self.setCentralWidget(self.main_frame)
        self.main_layout = QHBoxLayout(self.main_frame)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- Sidebar ---
        self.sidebar = QFrame(); self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(200) # Fixed width is a common, acceptable design choice for sidebars
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(5, 5, 5, 5)
        self.sidebar_layout.setSpacing(5)

        self.downloads_button = QPushButton(get_icon("download"), " Active")
        self.completed_button = QPushButton(get_icon("check"), " Completed")
        self.settings_button = QPushButton(get_icon("settings"), " Settings")
        
        sidebar_buttons = [self.downloads_button, self.completed_button, self.settings_button]
        for btn in sidebar_buttons:
            btn.setObjectName("sidebar_button")
            btn.setIconSize(QSize(22, 22))
            btn.setCheckable(True)
            btn.clicked.connect(self.on_sidebar_button_clicked)
            self.sidebar_layout.addWidget(btn)

        self.sidebar_layout.addStretch()
        self.downloads_button.setChecked(True)

        # --- Content Area ---
        self.content_area = QFrame()
        self.content_layout = QVBoxLayout(self.content_area)
        self.pages_widget = AnimatedStackedWidget()
        self.content_layout.addWidget(self.pages_widget)

        self.create_downloads_page()
        self.create_completed_page()
        self.create_settings_page()

        self.pages_widget.addWidget(self.downloads_page)
        self.pages_widget.addWidget(self.completed_page)
        self.pages_widget.addWidget(self.settings_page)
        
        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.content_area)

    def on_sidebar_button_clicked(self):
        # ... (logic remains the same)
        sender = self.sender()
        buttons = self.sidebar.findChildren(QPushButton)
        for btn in buttons:
            if btn is not sender: btn.setChecked(False)
        
        if self.downloads_button.isChecked(): self.pages_widget.set_current_index(0)
        elif self.completed_button.isChecked(): self.pages_widget.set_current_index(1)
        elif self.settings_button.isChecked(): self.pages_widget.set_current_index(2)

    def create_downloads_page(self):
        self.downloads_page = QFrame()
        layout = QVBoxLayout(self.downloads_page)
        
        top_bar = QHBoxLayout()
        title = QLabel("Active Downloads"); title.setObjectName("page_title")
        
        add_button = QPushButton(get_icon("plus"), " Add Download")
        add_button.setStyleSheet("background-color: #5E81AC; padding: 8px 16px; border-radius: 4px; font-weight: bold;")
        add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        add_button.clicked.connect(self.add_dummy_download)

        top_bar.addWidget(title); top_bar.addStretch(); top_bar.addWidget(add_button)
        layout.addLayout(top_bar)
        
        self.download_list_widget = QListWidget()
        layout.addWidget(self.download_list_widget)

    def create_completed_page(self):
        # ... (logic remains the same)
        self.completed_page = QFrame()
        layout = QVBoxLayout(self.completed_page)
        title = QLabel("Completed Downloads"); title.setObjectName("page_title")
        layout.addWidget(title); layout.addStretch()

    def create_settings_page(self):
        self.settings_page = QFrame()
        layout = QVBoxLayout(self.settings_page)
        title = QLabel("Settings"); title.setObjectName("page_title")

        # *** CROSS-PLATFORM: Get default downloads path
        downloads_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        
        path_label = QLabel(f"Default download location: {downloads_path}")
        path_label.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(path_label)
        layout.addStretch()

    def add_dummy_download(self):
        # ... (logic remains the same)
        item_widget = DownloadItemWidget("A_very_long_file_name_that_should_wrap_on_smaller_window_sizes.zip")
        item_widget.update_progress(45, "450.1 MB / 1000.2 MB", "4.5 MB/s", "01:32")
        item_widget.set_status("Downloading")
        
        list_item = QListWidgetItem(self.download_list_widget)
        list_item.setSizeHint(item_widget.sizeHint())
        self.download_list_widget.addItem(list_item)
        self.download_list_widget.setItemWidget(list_item, item_widget)


# --- Application Bootstrap ---
if __name__ == "__main__":
    # *** RESPONSIVE: Enable high-DPI scaling
    #QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)

    app = QApplication(sys.argv)
    app.setStyleSheet(PROFESSIONAL_STYLE_SHEET)
    
    main_window = MainWindow()
    main_window.show()
    
    main_window.add_dummy_download()
    
    sys.exit(app.exec())

