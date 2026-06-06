# main.py
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QLineEdit, QLabel, QDialogButtonBox
from PyQt6.QtCore import QThread, QObject, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QIcon
import requests
import time
# For a real torrent implementation, you would use a library like libtorrent
# import libtorrent as lt

# --- Constants and Styling ---
APP_NAME = "QuantumDownloader"
APP_VERSION = "0.1.0"
MODERN_STYLE_SHEET = """
    QWidget {
        background-color: #2E3440;
        color: #ECEFF4;
        font-family: 'Segoe UI';
        font-size: 10pt;
    }
    QMainWindow {
        border: 1px solid #4C566A;
    }
    QTableWidget {
        background-color: #3B4252;
        border: none;
        gridline-color: #4C566A;
    }
    QTableWidget::item {
        padding: 5px;
    }
    QHeaderView::section {
        background-color: #434C5E;
        color: #D8DEE9;
        padding: 4px;
        border: 1px solid #4C566A;
        font-weight: bold;
    }
    QPushButton {
        background-color: #5E81AC;
        color: #ECEFF4;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
    }
    QPushButton:hover {
        background-color: #81A1C1;
    }
    QPushButton:pressed {
        background-color: #88C0D0;
    }
    QLineEdit {
        background-color: #3B4252;
        border: 1px solid #4C566A;
        padding: 5px;
        border-radius: 3px;
    }
    QDialog {
        background-color: #2E3440;
    }
"""

# --- Backend Worker for HTTP/S Downloads ---
class DownloadWorker(QObject):
    """
    Manages a single file download in a separate thread.
    """
    progress = pyqtSignal(int, int, int)  # id, bytes_downloaded, total_size
    finished = pyqtSignal(int, str)  # id, final_filepath
    error = pyqtSignal(int, str)  # id, error_message

    def __init__(self, download_id, url, save_path):
        super().__init__()
        self.download_id = download_id
        self.url = url
        self.save_path = save_path
        self.is_running = True

    @pyqtSlot()
    def run(self):
        try:
            with requests.get(self.url, stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                bytes_downloaded = 0
                
                with open(self.save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if not self.is_running:
                            raise Exception("Download cancelled")
                        
                        bytes_downloaded += len(chunk)
                        f.write(chunk)
                        self.progress.emit(self.download_id, bytes_downloaded, total_size)
            
            if self.is_running:
                self.finished.emit(self.download_id, self.save_path)

        except Exception as e:
            self.error.emit(self.download_id, str(e))

    def stop(self):
        self.is_running = False

# --- Add Download Dialog ---
class AddDownloadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Download")
        self.setMinimumWidth(400)

        self.layout = QVBoxLayout(self)
        
        self.url_label = QLabel("Download URL or Magnet Link:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("http://, https://, magnet:?xt=")
        
        self.layout.addWidget(self.url_label)
        self.layout.addWidget(self.url_input)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.layout.addWidget(self.buttons)

    def get_url(self):
        return self.url_input.text()

# --- Main Application Window ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} - v{APP_VERSION}")
        self.setGeometry(100, 100, 800, 600)
        self.threads = {}
        self.download_id_counter = 0

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Toolbar
        self.add_button = QPushButton(QIcon.fromTheme("list-add"), " Add Download") # Placeholder icon
        self.add_button.clicked.connect(self.show_add_download_dialog)
        self.layout.addWidget(self.add_button)

        # Download Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "File Name", "Size", "Progress", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setColumnHidden(0, True) # Hide ID column
        self.layout.addWidget(self.table)
    
    def show_add_download_dialog(self):
        dialog = AddDownloadDialog(self)
        if dialog.exec():
            url = dialog.get_url()
            if url:
                self.start_new_download(url)

    def start_new_download(self, url):
        self.download_id_counter += 1
        download_id = self.download_id_counter
        
        file_name = url.split('/')[-1] or f"download_{download_id}"
        save_path = f"./{file_name}" # In a real app, you'd prompt for location

        # Add row to table
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)
        self.table.setItem(row_position, 0, QTableWidgetItem(str(download_id)))
        self.table.setItem(row_position, 1, QTableWidgetItem(file_name))
        self.table.setItem(row_position, 2, QTableWidgetItem("0 MB"))
        self.table.setItem(row_position, 3, QTableWidgetItem("0%"))
        self.table.setItem(row_position, 4, QTableWidgetItem("Starting..."))

        # Create worker and thread
        thread = QThread()
        worker = DownloadWorker(download_id, url, save_path)
        worker.moveToThread(thread)

        # Connect signals
        worker.progress.connect(self.update_progress)
        worker.finished.connect(self.on_download_finished)
        worker.error.connect(self.on_download_error)
        thread.started.connect(worker.run)

        # Store thread and worker to manage them
        self.threads[download_id] = (thread, worker)
        thread.start()

    def find_row_by_id(self, download_id):
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == str(download_id):
                return row
        return -1

    @pyqtSlot(int, int, int)
    def update_progress(self, download_id, bytes_downloaded, total_size):
        row = self.find_row_by_id(download_id)
        if row == -1: return

        if total_size > 0:
            percent = (bytes_downloaded / total_size) * 100
            self.table.setItem(row, 3, QTableWidgetItem(f"{percent:.2f}%"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{total_size / 1_048_576:.2f} MB"))
        else:
            self.table.setItem(row, 3, QTableWidgetItem("N/A"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{bytes_downloaded / 1_048_576:.2f} MB"))

        self.table.setItem(row, 4, QTableWidgetItem("Downloading..."))

    @pyqtSlot(int, str)
    def on_download_finished(self, download_id, final_filepath):
        row = self.find_row_by_id(download_id)
        if row != -1:
            self.table.setItem(row, 3, QTableWidgetItem("100%"))
            self.table.setItem(row, 4, QTableWidgetItem("Completed"))
        
        self.cleanup_thread(download_id)

    @pyqtSlot(int, str)
    def on_download_error(self, download_id, error_message):
        row = self.find_row_by_id(download_id)
        if row != -1:
            self.table.setItem(row, 4, QTableWidgetItem(f"Error: {error_message[:30]}..."))

        self.cleanup_thread(download_id)
        
    def cleanup_thread(self, download_id):
        if download_id in self.threads:
            thread, worker = self.threads[download_id]
            thread.quit()
            thread.wait()
            del self.threads[download_id]


# --- Application Bootstrap ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(MODERN_STYLE_SHEET)
    
    main_window = MainWindow()
    main_window.show()
    
    sys.exit(app.exec())
