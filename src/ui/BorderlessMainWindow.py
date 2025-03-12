from PyQt5.QtWidgets import (QMainWindow, QWidget,
                             QVBoxLayout, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from src.ui.TitleBar import TitleBar


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


