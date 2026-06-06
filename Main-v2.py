# main_v2.py
import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                             QPushButton, QStackedWidget, QLabel, QFrame, QProgressBar,
                             QListWidget, QListWidgetItem, QGraphicsOpacityEffect)
from PyQt6.QtCore import (Qt, QSize, QPropertyAnimation, QEasingCurve, pyqtProperty, 
                        QThread, QObject, pyqtSignal, pyqtSlot)
from PyQt6.QtGui import QIcon, QPainter, QColor

# --- Professional Styling (QSS) ---
# Based on the Nord color palette for a clean, modern look.
PROFESSIONAL_STYLE_SHEET = """
    * {
        border: none;
        font-family: 'Segoe UI', 'Roboto', 'Arial';
    }
    QMainWindow, QFrame#main_frame {
        background-color: #2E3440; /* nord0 */
    }
    /* --- Sidebar --- */
    QFrame#sidebar {
        background-color: #3B4252; /* nord1 */
        border-right: 1px solid #4C566A; /* nord3 */
    }
    QPushButton#sidebar_button {
        background-color: transparent;
        text-align: left;
        padding: 10px;
        border-radius: 5px;
        font-size: 11pt;
        font-weight: bold;
        color: #D8DEE9; /* nord4 */
    }
    QPushButton#sidebar_button:hover {
        background-color: #434C5E; /* nord3 */
    }
    QPushButton#sidebar_button:checked {
        background-color: #5E81AC; /* nord9 */
        color: #ECEFF4; /* nord6 */
    }
    /* --- Content Area --- */
    QLabel#page_title {
        font-size: 18pt;
        font-weight: bold;
        color: #ECEFF4; /* nord6 */
        padding: 10px;
    }
    QListWidget {
        background-color: #2E3440; /* nord0 */
    }
    /* --- Custom Download Item Widget --- */
    QFrame#download_item_frame {
        background-color: #3B4252; /* nord1 */
        border-radius: 5px;
        border: 1px solid #434C5E;
    }
    QLabel#item_filename {
        font-weight: bold;
        font-size: 11pt;
        color: #ECEFF4; /* nord6 */
    }
    QLabel.info_label {
        font-size: 9pt;
        color: #D8DEE9; /* nord4 */
    }
    /* --- Progress Bar --- */
    QProgressBar {
        background-color: #434C5E;
        color: #ECEFF4;
        border-radius: 4px;
        text-align: center;
    }
    QProgressBar::chunk {
        background-color: #88C0D0; /* nord8 */
        border-radius: 4px;
    }
    /* --- Scrollbar --- */
    QScrollBar:vertical {
        border: none;
        background: #3B4252;
        width: 10px;
        margin: 0px 0px 0px 0px;
    }
    QScrollBar::handle:vertical {
        background: #5E81AC;
        min-height: 20px;
        border-radius: 5px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
"""

# --- Custom Widget for each Download Item ---
class DownloadItemWidget(QFrame):
    def __init__(self, filename="New Download"):
        super().__init__()
        self.setObjectName("download_item_frame")
        self.setContentsMargins(10, 10, 10, 10)

        # Layouts
        self.main_layout = QVBoxLayout(self)
        self.top_layout = QHBoxLayout()
        self.bottom_layout = QHBoxLayout()

        # Widgets
        self.filename_label = QLabel(filename)
        self.filename_label.setObjectName("item_filename")

        self.status_label = QLabel("Status: Queued")
        self.status_label.setObjectName("info_label")

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximumHeight(8)

        self.info_label = QLabel("0 MB / 0 MB  |  0 KB/s  |  ETA: --:--")
        self.info_label.setObjectName("info_label")
        
        # Action buttons
        self.pause_button = QPushButton(QIcon.fromTheme("media-playback-pause"), "")
        self.cancel_button = QPushButton(QIcon.fromTheme("edit-delete"), "")
        self.pause_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)

        # Assemble
        self.top_layout.addWidget(self.filename_label)
        self.top_layout.addStretch()
        self.top_layout.addWidget(self.status_label)
        
        self.bottom_layout.addWidget(self.info_label)
        self.bottom_layout.addStretch()
        self.bottom_layout.addWidget(self.pause_button)
        self.bottom_layout.addWidget(self.cancel_button)

        self.main_layout.addLayout(self.top_layout)
        self.main_layout.addWidget(self.progress_bar)
        self.main_layout.addLayout(self.bottom_layout)

    def update_progress(self, percent, size_str, speed_str, eta_str):
        self.progress_bar.setValue(int(percent))
        self.info_label.setText(f"{size_str}  |  {speed_str}  |  ETA: {eta_str}")

    def set_status(self, status):
        self.status_label.setText(f"Status: {status}")

# --- Animated QStackedWidget ---
class AnimatedStackedWidget(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.m_duration = 500  # Animation duration in ms
        self.m_fade_animation = QPropertyAnimation(self, b"opacity")

    def set_current_index(self, index):
        self.m_fade_animation.stop()
        
        # Fade out
        self.m_fade_animation.setDuration(self.m_duration // 2)
        self.m_fade_animation.setStartValue(1.0)
        self.m_fade_animation.setEndValue(0.0)
        self.m_fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.m_fade_animation.finished.connect(lambda: self._fade_in(index))
        self.m_fade_animation.start()

    def _fade_in(self, index):
        self.setCurrentIndex(index)
        
        # Fade in
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
        self.setGeometry(100, 100, 950, 700)
        self.setWindowIcon(QIcon.fromTheme("network-transmit-receive"))

        # Main frame
        self.main_frame = QFrame(self)
        self.main_frame.setObjectName("main_frame")
        self.setCentralWidget(self.main_frame)
        self.main_layout = QHBoxLayout(self.main_frame)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- Sidebar ---
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(200)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(5, 5, 5, 5)
        self.sidebar_layout.setSpacing(5)

        # Sidebar buttons
        self.downloads_button = QPushButton(QIcon.fromTheme("go-down"), " Active Downloads")
        self.completed_button = QPushButton(QIcon.fromTheme("emblem-ok"), " Completed")
        self.settings_button = QPushButton(QIcon.fromTheme("preferences-system"), " Settings")
        
        sidebar_buttons = [self.downloads_button, self.completed_button, self.settings_button]
        for btn in sidebar_buttons:
            btn.setObjectName("sidebar_button")
            btn.setIconSize(QSize(24, 24))
            btn.setCheckable(True)
            btn.clicked.connect(self.on_sidebar_button_clicked)
            self.sidebar_layout.addWidget(btn)

        self.sidebar_layout.addStretch()
        self.downloads_button.setChecked(True) # Default page

        # --- Content Area ---
        self.content_area = QFrame()
        self.content_layout = QVBoxLayout(self.content_area)
        
        # Stacked widget for pages
        self.pages_widget = AnimatedStackedWidget()
        self.content_layout.addWidget(self.pages_widget)

        # Create pages
        self.create_downloads_page()
        self.create_completed_page()
        self.create_settings_page()

        # Add pages to stack
        self.pages_widget.addWidget(self.downloads_page)
        self.pages_widget.addWidget(self.completed_page)
        self.pages_widget.addWidget(self.settings_page)
        
        # Assemble main layout
        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.content_area)

    def on_sidebar_button_clicked(self):
        sender = self.sender()
        buttons = self.sidebar.findChildren(QPushButton)
        for btn in buttons:
            if btn is not sender:
                btn.setChecked(False)
        
        if self.downloads_button.isChecked():
            self.pages_widget.set_current_index(0)
        elif self.completed_button.isChecked():
            self.pages_widget.set_current_index(1)
        elif self.settings_button.isChecked():
            self.pages_widget.set_current_index(2)

    def create_downloads_page(self):
        self.downloads_page = QFrame()
        layout = QVBoxLayout(self.downloads_page)
        
        top_bar = QHBoxLayout()
        title = QLabel("Active Downloads")
        title.setObjectName("page_title")
        add_button = QPushButton(QIcon.fromTheme("list-add"), " Add Download")
        add_button.setStyleSheet("background-color: #5E81AC; padding: 8px 16px; border-radius: 4px; font-weight: bold;")
        add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        add_button.clicked.connect(self.add_dummy_download)

        top_bar.addWidget(title)
        top_bar.addStretch()
        top_bar.addWidget(add_button)
        layout.addLayout(top_bar)
        
        self.download_list_widget = QListWidget()
        layout.addWidget(self.download_list_widget)

    def create_completed_page(self):
        self.completed_page = QFrame()
        layout = QVBoxLayout(self.completed_page)
        title = QLabel("Completed Downloads")
        title.setObjectName("page_title")
        layout.addWidget(title)
        layout.addStretch()

    def create_settings_page(self):
        self.settings_page = QFrame()
        layout = QVBoxLayout(self.settings_page)
        title = QLabel("Settings")
        title.setObjectName("page_title")
        layout.addWidget(title)
        layout.addStretch()

    def add_dummy_download(self):
        # In a real app, this would come from a dialog and start a real download worker
        item_widget = DownloadItemWidget("example_file_big_name_test.zip")
        item_widget.update_progress(45, "450.1 MB / 1000.2 MB", "4.5 MB/s", "01:32")
        item_widget.set_status("Downloading")
        
        list_item = QListWidgetItem(self.download_list_widget)
        list_item.setSizeHint(item_widget.sizeHint())
        self.download_list_widget.addItem(list_item)
        self.download_list_widget.setItemWidget(list_item, item_widget)


# --- Application Bootstrap ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(PROFESSIONAL_STYLE_SHEET)
    
    main_window = MainWindow()
    main_window.show()
    
    # Add a couple of dummy items to show the UI
    main_window.add_dummy_download()
    main_window.add_dummy_download()
    
    sys.exit(app.exec())
