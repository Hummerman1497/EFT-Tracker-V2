from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QColor, QPixmap, QPalette
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton


class TitleBar(QWidget):
    """Custom titlebar with EFT-themed styling"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        # Configuration - using logical pixels instead of physical pixels
        # This will respect the system's DPI settings
        self.height = 40
        self.button_width = 45
        self.button_height = 30
        self.bg_color = QColor(30, 30, 30)
        self.text_color = QColor(246, 231, 197)  # EFT yellowish color

        # Setup UI
        self.setup_ui()

        # Track mouse position for dragging
        self.start_pos = None

    def setup_ui(self):
        # We're still setting a fixed height, but now it will be interpreted
        # in logical pixels, which will scale with the system DPI
        self.setFixedHeight(self.height)

        # Horizontal layout for the title bar
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 0, 0)
        layout.setSpacing(0)

        # App logo
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(30, 30)

        # Try to load the logo file
        try:
            pixmap = QPixmap("../../Assets/Icons/Ushanka_icon.ico")  # Replace with your actual logo path
            self.logo_label.setPixmap(pixmap.scaled(
                24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except:
            # Fallback if no logo is available
            self.logo_label.setText("🎯")
            # Use relative font size which will scale with DPI
            self.logo_label.setStyleSheet(f"color: {self.text_color.name()}; font-size: large;")

        # App title - using relative font size
        self.title_label = QLabel("EFT Tracker")
        self.title_label.setStyleSheet(
            f"color: {self.text_color.name()}; font-size: large; font-weight: bold;")

        # Window control buttons
        self.btn_minimize = QPushButton("—")
        self.btn_maximize = QPushButton("□")
        self.btn_close = QPushButton("✕")

        # Style window buttons - using relative font sizes
        for btn in [self.btn_minimize, self.btn_maximize, self.btn_close]:
            btn.setFixedSize(self.button_width, self.button_height)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {self.text_color.name()};
                    border: none;
                    font-size: medium;
                }}
                QPushButton:hover {{
                    background-color: #444444;
                }}
            """)

        # Extra style for close button
        self.btn_close.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.text_color.name()};
                border: none;
                font-size: medium;
            }}
            QPushButton:hover {{
                background-color: #9B2915;  /* EFT reddish color */
            }}
        """)

        # Connect buttons to actions
        self.btn_minimize.clicked.connect(self.parent.showMinimized)
        self.btn_maximize.clicked.connect(self.toggle_maximize)
        self.btn_close.clicked.connect(self.parent.close)

        # Add all elements to layout
        layout.addWidget(self.logo_label)
        layout.addSpacing(10)
        layout.addWidget(self.title_label)
        layout.addStretch(1)
        layout.addWidget(self.btn_minimize)
        layout.addWidget(self.btn_maximize)
        layout.addWidget(self.btn_close)

        # Set background color
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, self.bg_color)
        self.setPalette(palette)

    def toggle_maximize(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
            self.btn_maximize.setText("□")
        else:
            self.parent.showMaximized()
            self.btn_maximize.setText("❐")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.globalPos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.start_pos is not None:
            # Don't drag if maximized
            if not self.parent.isMaximized():
                delta = QPoint(event.globalPos() - self.start_pos)
                self.parent.move(self.parent.x() + delta.x(), self.parent.y() + delta.y())
                self.start_pos = event.globalPos()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.start_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.toggle_maximize()
        super().mouseDoubleClickEvent(event)
