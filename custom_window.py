import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                             QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QSizePolicy, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, QPoint, QSize, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette, QPainter, QPixmap


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
            pixmap = QPixmap("Assets/Icons/Ushanka_icon.ico")  # Replace with your actual logo path
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


class BorderlessMainWindow(QMainWindow):
    """Base class for a borderless window with custom frame"""

    def __init__(self):
        super().__init__()

        # Setting Qt.AA_EnableHighDpiScaling is important for proper DPI scaling
        # but it should be done in the application initialization
        # QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

        # Remove system frame
        self.setWindowFlags(Qt.FramelessWindowHint)

        # Enable transparency and rounded corners
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Setup UI
        self.setup_ui()

        # For window resizing
        self._resize_active = False
        self._resize_edge = None
        self.resize_margin = 5

    def setup_ui(self):
        # Create central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Main vertical layout
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Create custom title bar
        self.title_bar = TitleBar(self)
        self.main_layout.addWidget(self.title_bar)

        # Create content area with border styling
        self.content_widget = QWidget()
        self.content_widget.setObjectName("contentWidget")
        self.content_widget.setStyleSheet("""
            QWidget#contentWidget {
                background-color: #2D2D2D;
                border-bottom-left-radius: 5px;
                border-bottom-right-radius: 5px;
                border-left: 1px solid #444444;
                border-right: 1px solid #444444;
                border-bottom: 1px solid #444444;
            }
        """)

        # Content layout with margins
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(10, 10, 10, 10)

        # Add content widget to main layout
        self.main_layout.addWidget(self.content_widget, 1)

        # Add drop shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 0)
        self.central_widget.setGraphicsEffect(shadow)

    def mousePressEvent(self, event):
        # Check if cursor is near the edge for resizing
        if self.is_near_edge(event.pos()):
            self._resize_active = True
            self._resize_edge = self.get_edge(event.pos())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # Handle resizing
        if self._resize_active:
            self.resize_window(event.globalPos())
        else:
            # Update cursor if near edge
            if self.is_near_edge(event.pos()):
                edge = self.get_edge(event.pos())
                if edge in ['left', 'right']:
                    self.setCursor(Qt.SizeHorCursor)
                elif edge in ['top', 'bottom']:
                    self.setCursor(Qt.SizeVerCursor)
                elif edge in ['top-left', 'bottom-right']:
                    self.setCursor(Qt.SizeFDiagCursor)
                elif edge in ['top-right', 'bottom-left']:
                    self.setCursor(Qt.SizeBDiagCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._resize_active = False
        self._resize_edge = None
        super().mouseReleaseEvent(event)

    def is_near_edge(self, pos):
        """Check if position is near any window edge"""
        margin = self.resize_margin
        width = self.width()
        height = self.height()

        near_left = pos.x() <= margin
        near_right = pos.x() >= width - margin
        near_top = pos.y() <= margin
        near_bottom = pos.y() >= height - margin

        return near_left or near_right or near_top or near_bottom

    def get_edge(self, pos):
        """Determine which edge the position is near"""
        margin = self.resize_margin
        width = self.width()
        height = self.height()

        near_left = pos.x() <= margin
        near_right = pos.x() >= width - margin
        near_top = pos.y() <= margin
        near_bottom = pos.y() >= height - margin

        # Corners
        if near_top and near_left:
            return 'top-left'
        if near_top and near_right:
            return 'top-right'
        if near_bottom and near_left:
            return 'bottom-left'
        if near_bottom and near_right:
            return 'bottom-right'

        # Edges
        if near_left:
            return 'left'
        if near_right:
            return 'right'
        if near_top:
            return 'top'
        if near_bottom:
            return 'bottom'

        return None

    def resize_window(self, global_pos):
        """Resize window based on mouse position and active edge"""
        if not self._resize_edge:
            return

        local_pos = self.mapFromGlobal(global_pos)

        # Current geometry
        x = self.x()
        y = self.y()
        width = self.width()
        height = self.height()

        # Minimum size
        min_width = 400
        min_height = 300

        # Adjust dimensions based on edge
        if 'left' in self._resize_edge:
            delta_x = local_pos.x()
            new_width = max(min_width, width - delta_x)
            if new_width != width:
                x = x + (width - new_width)
                width = new_width

        if 'right' in self._resize_edge:
            width = max(min_width, local_pos.x())

        if 'top' in self._resize_edge:
            delta_y = local_pos.y()
            new_height = max(min_height, height - delta_y)
            if new_height != height:
                y = y + (height - new_height)
                height = new_height

        if 'bottom' in self._resize_edge:
            height = max(min_height, local_pos.y())

        # Apply the new geometry
        self.setGeometry(x, y, width, height)


class EFTCustomWindow(BorderlessMainWindow):
    """EFT Tracker with custom window frame"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("EFT Tracker")
        self.setup_content()
        self.resize(900, 650)

    def setup_content(self):
        # Create tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #444444;
                background-color: #2D2D2D;
            }
            QTabBar::tab {
                background-color: #1A1A1A;
                color: #f6e7c5;
                padding: 8px 16px;
                border: 1px solid #444444;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: medium;
            }
            QTabBar::tab:selected {
                background-color: #2D2D2D;
                border-bottom: 1px solid #2D2D2D;
            }
            QTabBar::tab:!selected {
                margin-top: 2px;
            }
        """)

        # Add placeholder tabs
        tab1 = QWidget()
        tab2 = QWidget()
        tab3 = QWidget()

        # Create simple layouts for each tab
        layout1 = QVBoxLayout(tab1)
        layout2 = QVBoxLayout(tab2)
        layout3 = QVBoxLayout(tab3)

        # Add placeholder content
        layout1.addWidget(QLabel("Statistics Content"))
        layout2.addWidget(QLabel("History Content"))
        layout3.addWidget(QLabel("Settings Content"))

        # Add tabs
        self.tabs.addTab(tab1, "Statistik")
        self.tabs.addTab(tab2, "History")
        self.tabs.addTab(tab3, "Einstellungen")

        # Add to content layout
        self.content_layout.addWidget(self.tabs)