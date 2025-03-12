from PyQt5.QtWidgets import QTabWidget, QWidget, QVBoxLayout, QLabel

from src.ui.BorderlessMainWindow import BorderlessMainWindow


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
