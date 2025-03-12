from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFrame, QHBoxLayout, QPushButton, QLabel, QProgressBar, QTextEdit

from src.OCRManager import OCRWorker
from src.ui.custom_window import BorderlessMainWindow


class OCRCustomWindow(BorderlessMainWindow):
    def __init__(self):
        super().__init__()

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
