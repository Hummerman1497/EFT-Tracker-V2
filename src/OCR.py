import sys
import os
import cv2 as cv
import easyocr
from datetime import datetime
import json
import shutil
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QTextEdit, QProgressBar, QFrame)
from PyQt5.QtCore import pyqtSignal, QThread
from custom_window import BorderlessMainWindow


class OCRWorker(QThread):
    """Thread for running OCR processing in background"""
    progress_update = pyqtSignal(str)
    progress_value = pyqtSignal(int)
    processing_finished = pyqtSignal()
    processing_error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.reader = None
        self.data_dir = 'data'
        self.root_folder = 'Raids new'
        self.archive_folder = 'Raids old'

    def run(self):
        try:
            start_time = datetime.now()
            self.progress_update.emit(f"Starting OCR processing at {start_time}")

            # Initialize OCR reader
            if self.reader is None:
                self.progress_update.emit("Initializing EasyOCR reader (this might take a moment)...")
                self.reader = easyocr.Reader(['en'], gpu=True)
                self.progress_update.emit("EasyOCR reader initialized")

            # Ensure directories exist
            for directory in [self.data_dir, self.root_folder, self.archive_folder]:
                if not os.path.exists(directory):
                    os.makedirs(directory)
                    self.progress_update.emit(f"Created directory: {directory}")

            # Get subfolders sorted by creation time
            subfolders = sorted(
                [f.path for f in os.scandir(self.root_folder) if f.is_dir()],
                key=lambda x: os.path.getctime(x)
            )

            if not subfolders:
                self.progress_update.emit(f"No folders found in '{self.root_folder}'")
                self.processing_finished.emit()
                return

            self.progress_update.emit(f"Found {len(subfolders)} folders to process")

            # Process each subfolder
            processed_count = 0
            total_folders = len(subfolders)

            for i, subfolder in enumerate(subfolders):
                # Update progress
                progress_percent = int((i / total_folders) * 100)
                self.progress_value.emit(progress_percent)

                if self.process_subfolder(subfolder):
                    processed_count += 1

            # Final progress update
            self.progress_value.emit(100)

            end_time = datetime.now()
            time_delta = end_time - start_time
            self.progress_update.emit(f"Total processing time: {time_delta}")
            self.progress_update.emit(f"Processed {processed_count} of {total_folders} folders")

            self.processing_finished.emit()

        except Exception as e:
            self.processing_error.emit(str(e))

    def process_subfolder(self, subfolder):
        """Process a single subfolder containing PNG files"""
        png_files = [f for f in os.listdir(subfolder) if f.endswith('.png')]

        if len(png_files) == 4:
            folder_name = os.path.basename(subfolder)
            data_path = os.path.join(self.data_dir, folder_name)

            if not os.path.exists(data_path):
                os.makedirs(data_path)

            self.progress_update.emit(f"Processing folder: {subfolder}")

            # Load PNG files
            png_paths = [os.path.join(subfolder, png) for png in sorted(png_files)]
            images = [cv.imread(png) for png in png_paths]

            # Process each image
            all_data = {
                "Status": self.process_image0(images[0]),
                "KillList": self.process_image1(images[1]),
                "RaidStatistics": self.process_image2(images[2]),
                "ExperienceGained": self.process_image3(images[3])
            }

            # Save data to JSON
            json_file = os.path.join(data_path, "raid_data.json")
            self.save_to_json(all_data, json_file)
            self.progress_update.emit(f"All data saved to: {json_file}")

            # Move processed folder to archive
            try:
                target_folder = os.path.join(self.archive_folder, folder_name)
                shutil.move(subfolder, target_folder)
                self.progress_update.emit(f"Folder moved to: {target_folder}")
            except Exception as e:
                self.progress_update.emit(f"Error moving folder {subfolder}: {e}")

            return True
        else:
            self.progress_update.emit(f"Skipping folder {subfolder}: Expected 4 PNG files, found {len(png_files)}")
            return False

    def save_to_json(self, data_dict, filename):
        """Save dictionary to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, ensure_ascii=False, indent=4)

    def process_image0(self, img0):
        """Process Status Image OCR"""
        # Crop regions of interest (ROI)
        regions = {
            "Next": (1257, 1309, 1221, 1348),
            "Status": (865, 900, 1080, 1313),
            "Timer": (880, 910, 1387, 1537),
            "Experience": (975, 1017, 1100, 1420),
            "Names": (785, 823, 840, 1700),
            "Level": (190, 270, 1026, 1145)
        }

        results = {}
        for name, (y1, y2, x1, x2) in regions.items():
            roi = img0[y1:y2, x1:x2]
            text = self.reader.readtext(roi, detail=0)
            results[name] = text
            self.progress_update.emit(f"{name}: {text}")

        return results

    def process_image1(self, img1):
        """Process Kill List OCR with detailed sub-regions"""
        rows = {}

        for i in range(1, 10):
            y_start = 334 + (i - 1) * 80
            y_end = y_start + 65

            # Definieren der einzelnen Spalten innerhalb jeder Zeile
            regions = {
                "No": (y_start, y_end, 648, 723),
                "Time": (y_start, y_end, 723, 880),
                "Player": (y_start, y_end, 880, 1260),
                "LVL": (y_start, y_end, 1260, 1334),
                "Faction": (y_start, y_end, 1334, 1487),
                "Status": (y_start, y_end, 1487, 1930)
            }

            row_data = {}
            for name, (y1, y2, x1, x2) in regions.items():
                roi = img1[y1:y2, x1:x2]
                text_list = self.reader.readtext(roi, detail=0)

                # Zusammenführen aller erkannten Strings zu einem einzigen String
                if text_list:
                    combined_text = " ".join(text_list)
                    row_data[name] = combined_text
                else:
                    row_data[name] = ""

            row_name = f"row{i}"
            rows[row_name] = row_data

            # Nur ausgeben, wenn tatsächlich ein Spieler erkannt wurde
            if row_data["Player"]:
                self.progress_update.emit(f"Kill {i}: {row_data['Player']} ({row_data['Faction']})")

        return rows

    def process_image2(self, img2):
        """Process Raid Statistics OCR"""
        map_roi = img2[142:173, 1120:1400]
        map_text = self.reader.readtext(map_roi, detail=0)
        self.progress_update.emit(f"Map: {map_text}")

        return {"map": map_text}

    def process_image3(self, img3):
        """Process Experience Gained OCR"""
        elimination_roi = img3[484:513, 882:1062]
        elimination_text = self.reader.readtext(elimination_roi, detail=0)
        self.progress_update.emit(f"Eliminations: {elimination_text}")

        return {"Eliminations": elimination_text}


class OCRCustomWindow(BorderlessMainWindow):
    def __init__(self):
        # Initialisiere die Basisklasse
        super().__init__()

        # Setze den Fenstertitel in der Titelleiste
        self.title_bar.title_label.setText("EFT OCR Processor")

        # OCR Worker-Thread erstellen
        self.ocr_worker = OCRWorker()
        self.ocr_worker.progress_update.connect(self.update_log)
        self.ocr_worker.progress_value.connect(self.update_progress)
        self.ocr_worker.processing_finished.connect(self.processing_finished)
        self.ocr_worker.processing_error.connect(self.processing_error)

        # Eigene UI-Elemente einrichten
        self.setup_ocr_ui()

        # Fenstergröße setzen
        self.resize(800, 600)

    def setup_ocr_ui(self):
        """Setup the OCR specific UI elements"""
        # Create content widget
        content_widget = QWidget()
        main_layout = QVBoxLayout(content_widget)

        # Control area
        control_frame = QFrame()
        control_frame.setFrameShape(QFrame.StyledPanel)
        control_frame.setStyleSheet("background-color: #2D2D2D; border: none;")
        control_layout = QHBoxLayout(control_frame)

        # Start button with EFT style
        self.start_button = QPushButton("Start OCR Processing")
        self.start_button.setMinimumHeight(40)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #1A1A1A;
                color: #f6e7c5;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2D2D2D;
                border: 1px solid #666666;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #777777;
                border: 1px solid #444444;
            }
        """)
        self.start_button.clicked.connect(self.start_processing)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #f6e7c5; font-weight: bold;")

        # Progress bar with EFT style
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1A1A1A;
                color: #f6e7c5;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 1px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #6b4c2a;
                width: 5px;
                margin: 1px;
            }
        """)

        # Add controls to layout
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.status_label)
        control_layout.addWidget(self.progress_bar, 1)

        # Log area with EFT style
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1A1A1A;
                color: #f6e7c5;
                border: 1px solid #444444;
                border-radius: 4px;
                font-family: Consolas, monospace;
                font-size: 11pt;
            }
            QScrollBar:vertical {
                border: none;
                background: #2d2d2d;
                width: 14px;
                margin: 15px 0 15px 0;
            }

            QScrollBar::handle:vertical {
                background: #555555;
                min-height: 30px;
                border-radius: 3px;
            }

            QScrollBar::handle:vertical:hover {
                background: #666666;
            }

            QScrollBar::handle:vertical:pressed {
                background: #777777;
            }

            QScrollBar::add-line:vertical {
                border: none;
                background: #3a3a3a;
                height: 15px;
                border-bottom-left-radius: 3px;
                border-bottom-right-radius: 3px;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
            }

            QScrollBar::sub-line:vertical {
                border: none;
                background: #3a3a3a;
                height: 15px;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
                subcontrol-position: top;
                subcontrol-origin: margin;
            }

            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                background: none;
                border: none;
                color: #f6e7c5;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }

            /* Horizontale Scrollbar */
            QScrollBar:horizontal {
                border: none;
                background: #2d2d2d;
                height: 14px;
                margin: 0 15px 0 15px;
            }

            QScrollBar::handle:horizontal {
                background: #555555;
                min-width: 30px;
                border-radius: 3px;
            }

            QScrollBar::handle:horizontal:hover {
                background: #666666;
            }

            QScrollBar::handle:horizontal:pressed {
                background: #777777;
            }

            QScrollBar::add-line:horizontal {
                border: none;
                background: #3a3a3a;
                width: 15px;
                border-bottom-right-radius: 3px;
                border-top-right-radius: 3px;
                subcontrol-position: right;
                subcontrol-origin: margin;
            }

            QScrollBar::sub-line:horizontal {
                border: none;
                background: #3a3a3a;
                width: 15px;
                border-bottom-left-radius: 3px;
                border-top-left-radius: 3px;
                subcontrol-position: left;
                subcontrol-origin: margin;
            }

            QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {
                background: none;
                border: none;
                color: #f6e7c5;
            }

            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """)

        # Add everything to main layout
        main_layout.addWidget(control_frame)
        main_layout.addWidget(self.log_text, 1)

        # Füge das Content-Widget zum content_widget der Basisklasse hinzu
        self.content_layout.addWidget(content_widget)

    def start_processing(self):
        """Start OCR processing"""
        # Clear log
        self.log_text.clear()

        # Update UI
        self.start_button.setEnabled(False)
        self.status_label.setText("Processing...")
        self.progress_bar.setValue(0)

        # Start worker thread
        self.ocr_worker.start()

    def update_log(self, message):
        """Update log with new message"""
        self.log_text.append(message)

    def update_progress(self, value):
        """Update progress bar"""
        self.progress_bar.setValue(value)

    def processing_finished(self):
        """Called when processing is complete"""
        self.start_button.setEnabled(True)
        self.status_label.setText("Processing complete")
        self.update_log("=== OCR Processing Complete ===")

    def processing_error(self, error_msg):
        """Called when processing encounters an error"""
        self.start_button.setEnabled(True)
        self.status_label.setText("Error")
        self.update_log(f"ERROR: {error_msg}")

    def closeEvent(self, event):
        """Handle window close event"""
        # Stop worker thread if running
        if self.ocr_worker.isRunning():
            self.ocr_worker.terminate()
            self.ocr_worker.wait()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OCRCustomWindow()
    window.show()
    sys.exit(app.exec_())