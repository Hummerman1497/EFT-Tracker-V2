import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPainter, QColor, QFont
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QWidget, QHBoxLayout, QLabel, QGridLayout, QGroupBox, QTableWidget, \
    QHeaderView, QTableWidgetItem, QFormLayout, QPushButton, QMessageBox


class ExpandableRaidTile(QFrame):
    def __init__(self, raid_data, parent=None, asset_manager=None):
        super().__init__(parent)
        self.raid_data = raid_data
        self.assets = asset_manager
        self.expanded = False

        # Basic setup
        self.setFrameShape(QFrame.StyledPanel)
        self.setLineWidth(3)

        # Set object name for the main frame so the style can target it specifically
        self.setObjectName("mainFrame")

        # Create layouts and widgets first
        self.main_layout = QVBoxLayout(self)
        self.collapsed_widget = QWidget()
        self.expanded_widget = QWidget()

        # Now we can set styles after the widgets are created
        self.update_style()

        # Setup collapsed and expanded views
        self.setup_collapsed_view()
        self.setup_expanded_view()

        # Add widgets to main layout
        self.main_layout.addWidget(self.collapsed_widget)
        self.main_layout.addWidget(self.expanded_widget)

        # Initial state is collapsed
        self.expanded_widget.setVisible(False)

        # Handle click event
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

    def update_style(self):
        # Set style based on survival status
        status = self.raid_data.get("status", "Unknown")
        border_color = "green" if status == "Survived" else "red"

        # Apply style only to the main frame, not to the inner widgets
        self.setStyleSheet(
            f"QFrame#mainFrame {{ background-color: rgb(80, 80, 80); border: 1px solid {border_color}; border-radius: 8px; }}")

        # Set object name for the main frame so the style can target it specifically
        self.setObjectName("mainFrame")

        # Make sure the collapsed widget has no border
        self.collapsed_widget.setStyleSheet("border: none; background-color: transparent;")

        # Make sure the expanded widget has no border
        self.expanded_widget.setStyleSheet("border: none; background-color: transparent;")

    def setup_collapsed_view(self):
        layout = QHBoxLayout(self.collapsed_widget)
        layout.setContentsMargins(0, 0, 0, 0)  # Remove outer margins
        layout.setSpacing(5)  # Reduce spacing between elements

        # Left side - Map info
        map_widget = QWidget()
        map_widget.setStyleSheet("border: none;")
        map_layout = QVBoxLayout(map_widget)
        map_layout.setContentsMargins(0, 0, 0, 0)  # Remove internal margins
        map_layout.setSpacing(0)  # Remove spacing between elements

        # Create a frame to contain the map image and overlaid text
        map_frame = QFrame()
        map_frame.setFixedSize(300, 150)  # Fixed size instead of minimum size
        map_frame.setStyleSheet("background-color: rgba(80, 80, 80, 0.5); border: none;")
        map_frame_layout = QVBoxLayout(map_frame)
        map_frame_layout.setContentsMargins(0, 0, 0, 0)  # Remove internal margins
        map_frame_layout.setSpacing(0)  # Remove spacing

        # Map image label
        map_label = QLabel()
        map_label.setFixedSize(300, 150)  # Fixed size instead of minimum
        map_label.setAlignment(Qt.AlignCenter)
        map_label.setStyleSheet("padding: 0; margin: 0;")

        # Create map image path
        map_name = self.raid_data.get("map", "Unknown")
        image_path = self.assets.get_map_path(map_name)

        # Check if image exists
        if os.path.isfile(image_path):
            map_image = QPixmap(image_path)
            # Scale to fill the entire space while keeping aspect ratio
            map_image = map_image.scaled(300, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            map_label.setPixmap(map_image)
        else:
            map_label.setText(f"[Map: {map_name}]")

        # Add the map image to the frame
        map_frame_layout.addWidget(map_label)

        # Create an overlay for map title and date - completely transparent
        overlay_widget = QWidget(map_frame)
        overlay_widget.setStyleSheet("background-color: transparent; border: none;")
        overlay_layout = QVBoxLayout(overlay_widget)
        overlay_layout.setContentsMargins(0, 0, 0, 0)

        # Position the overlay at the bottom of the map frame
        # Initial position, will be updated in resizeEvent
        overlay_widget.setGeometry(0, map_frame.height() - 40, map_frame.width(), 40)

        # Create a subclass of QLabel with custom paint event for enhanced readability
        class ShadowedLabel(QLabel):
            def __init__(self, text):
                super().__init__(text)

            def paintEvent(self, event):
                painter = QPainter(self)
                painter.setRenderHint(QPainter.Antialiasing)

                # Draw text shadow for better readability
                painter.setPen(QColor(0, 0, 0, 160))
                rect = self.rect()

                # Multiple shadow offsets for stronger effect
                for offset in [(1, 1), (1, 2), (2, 1), (2, 2)]:
                    painter.drawText(rect.adjusted(offset[0], offset[1], offset[0], offset[1]),
                                     self.alignment(), self.text())

                # Draw the actual text
                painter.setPen(QColor("#f6e7c5"))  # EFT yellowish color
                painter.drawText(rect, self.alignment(), self.text())

        # Map title with improved readability on any background
        map_title = ShadowedLabel(map_name)
        map_title.setAlignment(Qt.AlignHCenter | Qt.AlignBottom)
        map_title.setStyleSheet(
            "border: none; font-size: 18px; font-weight: bold; color: #f6e7c5; background-color: transparent;")

        # Date with updated style for overlay visibility
        date_str = self.raid_data.get("date", "Unknown")
        display_date = date_str

        # Convert date string to a more readable format
        if "_" in date_str:
            # Format: dd-mm-yyyy_hh-mm
            parts = date_str.split("_")
            if len(parts) == 2:
                date_part = parts[0]
                time_part = parts[1].replace("-", ":")
                display_date = f"{date_part} {time_part}"
        elif " " in date_str and "-" in date_str.split(" ")[1]:
            # Format: yyyy-mm-dd hh-mm
            date_part, time_part = date_str.split(" ", 1)
            time_part = time_part.replace("-", ":")
            display_date = f"{date_part} {time_part}"

        # Date label using the same shadow technique
        date_label = ShadowedLabel(display_date)
        date_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        date_label.setStyleSheet("border: none; font-size: 14px; color: #f6e7c5; background-color: transparent;")

        # Add title and date to overlay
        overlay_layout.addWidget(map_title)
        overlay_layout.addWidget(date_label)

        # Position the overlay at the bottom of the map frame
        overlay_widget.setGeometry(0, map_frame.height() - 40, map_frame.width(), 40)

        # Create custom resize event to ensure overlay stays at the bottom
        def update_overlay_position(event=None):
            # This ensures the overlay is always at the bottom of the map frame
            overlay_widget.setGeometry(0, map_frame.height() - 45, map_frame.width(), 45)

        # Attach the resize event handler
        map_frame.resizeEvent = update_overlay_position

        # Call it once to set initial position
        update_overlay_position()

        # Make sure you have the necessary imports at the top of your file
        # from PyQt5.QtWidgets import QGraphicsDropShadowEffect

        # Add the map frame (which now includes image and overlay) to the map layout
        map_layout.addWidget(map_frame)

        # Right side - Status, kills, exp
        info_widget = QWidget()
        info_widget.setStyleSheet("border: none;")
        info_layout = QGridLayout(info_widget)
        info_layout.setContentsMargins(5, 0, 5, 0)  # Reduce margins

        # Status
        status_label = QLabel(self.raid_data.get("status", "Unknown"))
        status_label.setStyleSheet("border: none; font-weight: bold; font-size: 14px; font-weight: bold;")

        # Level
        level_label = QLabel(f"Level: {self.raid_data.get('level', 'Unknown')}")
        level_label.setStyleSheet("border: none; font-weight: bold;")

        # Kills with icon
        kills_widget = QWidget()
        kills_widget.setStyleSheet("border: none;")
        kills_layout = QHBoxLayout(kills_widget)
        kills_layout.setContentsMargins(0, 0, 0, 0)

        kill_icon_label = QLabel()
        kill_icon_pixmap = QPixmap(self.assets.get_icon_path("Kills.png"))
        kill_icon_label.setFixedSize(30, 30)
        kill_icon_label.setPixmap(kill_icon_pixmap.scaled(30, 30, aspectRatioMode=Qt.KeepAspectRatio))

        kill_value_label = QLabel(str(self.raid_data.get("kills", 0)))
        kill_value_label.setStyleSheet("border: none; font-size: 16px; padding: 5px; font-weight: bold;")

        kills_layout.addWidget(kill_icon_label)
        kills_layout.addWidget(kill_value_label)

        # EXP
        exp_widget = QWidget()
        exp_widget.setStyleSheet("border: none;")
        exp_layout = QHBoxLayout(exp_widget)
        exp_layout.setContentsMargins(0, 0, 0, 0)

        exp_icon_label = QLabel()
        exp_icon_pixmap = QPixmap("../../Assets/Icons/exp_icon.png")
        exp_icon_label.setFixedSize(30, 30)
        exp_icon_label.setPixmap(exp_icon_pixmap.scaled(30, 30, aspectRatioMode=Qt.KeepAspectRatio))
        exp_value_label = QLabel(str(self.raid_data.get("exp", 0)))
        exp_value_label.setStyleSheet("border: none; font-size: 16px; padding: 5px; font-weight: bold;")

        exp_layout.addWidget(exp_icon_label)
        exp_layout.addWidget(exp_value_label)

        # Add to info layout
        info_layout.addWidget(status_label, 0, 0)
        info_layout.addWidget(level_label, 0, 1)
        info_layout.addWidget(kills_widget, 1, 0)
        info_layout.addWidget(exp_widget, 1, 1)

        # Add expand indicator
        expand_label = QLabel("▼")
        expand_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        expand_label.setStyleSheet("color: #f6e7c5; font-size: 16px;")

        # Add to layout
        layout.addWidget(map_widget, 1)
        layout.addWidget(info_widget, 2)
        layout.addWidget(expand_label)

        # Make sure the overall tile doesn't have excessive margins
        self.main_layout.setContentsMargins(5, 5, 5, 5)  # Reduce overall tile margins

    def setup_expanded_view(self):
        layout = QVBoxLayout(self.expanded_widget)

        # Set style for expanded widget to explicitly remove borders
        self.expanded_widget.setStyleSheet("border: none; background-color: transparent;")

        # Kill list
        kills_group = QGroupBox("Kills")
        font = QFont()
        font.setBold(True)
        kills_group.setStyleSheet("QGroupBox { border: 2px solid #444; border-radius: 4px; margin-top: 0.5em; } "
                                  "QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 3px; }")
        kills_group.setFont(font)
        kills_layout = QVBoxLayout()

        # Create a table for kills - styled like the map stats table
        kill_table = QTableWidget()

        # Set the table's stylesheet to match the requested colors
        kill_table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: rgb(60, 60, 60);
            }

            QTableWidget::item {
                padding: 4px;
            }

            QHeaderView::section {
                background-color: rgb(50, 50, 50);
                padding: 4px;
                border: 1px solid #444;
                color: #f6e7c5;
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

            /* Rest der horizontalen Scrollbar wie vorher */
        """)

        kill_table.setColumnCount(5)
        kill_table.setHorizontalHeaderLabels(["Time", "Player", "Level", "Faction", "Status"])

        # Individuelle Spaltenbreiten einstellen statt alle gleich zu machen
        header = kill_table.horizontalHeader()
        # Setze zuerst alle auf Interactive, damit sie einzeln angepasst werden können
        header.setSectionResizeMode(QHeaderView.Interactive)

        # Spalten mit fester Breite: Time und Level
        header.setSectionResizeMode(0, QHeaderView.Interactive)  # Time - kleine Spalte
        header.setSectionResizeMode(2, QHeaderView.Interactive)  # Level - kleine Spalte

        # Spalten mit variabler Breite: Player, Faction und Status
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Player - mehr Platz
        header.setSectionResizeMode(3, QHeaderView.Interactive)  # Faction - mittlere Spalte
        header.setSectionResizeMode(4, QHeaderView.Stretch)  # Status - mehr Platz

        # Setze Initialbreiten für die Spalten
        kill_table.setColumnWidth(0, 60)  # Time - schmaler
        kill_table.setColumnWidth(2, 50)  # Level - schmaler
        kill_table.setColumnWidth(3, 80)  # Faction - mittel

        # Match the styling from the stats tab map table
        kill_table.setSelectionBehavior(QTableWidget.SelectRows)
        kill_table.setSelectionMode(QTableWidget.SingleSelection)
        kill_table.setAlternatingRowColors(True)
        kill_table.verticalHeader().setVisible(False)  # Hide row numbers to match map table

        # Set a minimum height for the table to display multiple rows
        kill_table.setMinimumHeight(200)  # Mindesthöhe in Pixeln, zeigt ca. 5-6 Zeilen an

        # Add kill data if available
        kill_list = self.raid_data.get("kill_list", {})
        if kill_list:
            # Count valid rows first
            valid_rows = []
            for row_key, kill_data in kill_list.items():
                if kill_data.get("Player", "").strip():
                    valid_rows.append((row_key, kill_data))

            kill_table.setRowCount(len(valid_rows))

            for i, (row_key, kill_data) in enumerate(valid_rows):
                kill_table.setItem(i, 0, QTableWidgetItem(kill_data.get("Time", "")))
                kill_table.setItem(i, 1, QTableWidgetItem(kill_data.get("Player", "")))
                kill_table.setItem(i, 2, QTableWidgetItem(kill_data.get("LVL", "")))
                kill_table.setItem(i, 3, QTableWidgetItem(kill_data.get("Faction", "")))
                kill_table.setItem(i, 4, QTableWidgetItem(kill_data.get("Status", "")))
        else:
            # No kill data available
            kill_table.setRowCount(1)
            kill_table.setSpan(0, 0, 1, 5)
            no_data_item = QTableWidgetItem("NO KILLS")
            no_data_item.setTextAlignment(Qt.AlignCenter)
            kill_table.setItem(0, 0, no_data_item)

        kills_layout.addWidget(kill_table)
        kills_group.setLayout(kills_layout)

        # Additional details
        details_group = QGroupBox("Raid Details")
        details_group.setFont(font)
        details_group.setStyleSheet("QGroupBox { border: 2px solid #444; border-radius: 4px; margin-top: 0.5em; } "
                                    "QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 3px; }")
        details_layout = QFormLayout()

        # Font styling to match map stats
        font = QFont()
        font.setPointSize(12)

        # Add more details from the raid data with styled labels
        map_label = QLabel(self.raid_data.get("map", "Unknown"))
        map_label.setFont(font)
        map_label.setStyleSheet("border: none;")

        status_label = QLabel(self.raid_data.get("status", "Unknown"))
        status_label.setFont(font)
        status_label.setStyleSheet("border: none;")

        time_label = QLabel(self.raid_data.get("time", "Unknown"))
        time_label.setFont(font)
        time_label.setStyleSheet("border: none;")

        exp_label = QLabel(str(self.raid_data.get("exp", 0)))
        exp_label.setFont(font)
        exp_label.setStyleSheet("border: none;")

        # Create styled row labels
        map_row_label = QLabel("Map:")
        map_row_label.setFont(font)
        map_row_label.setStyleSheet("border: none;")

        status_row_label = QLabel("Status:")
        status_row_label.setFont(font)
        status_row_label.setStyleSheet("border: none;")

        time_row_label = QLabel("Raid Time:")
        time_row_label.setFont(font)
        time_row_label.setStyleSheet("border: none;")

        exp_row_label = QLabel("Experience:")
        exp_row_label.setFont(font)
        exp_row_label.setStyleSheet("border: none;")

        details_layout.addRow(map_row_label, map_label)
        details_layout.addRow(status_row_label, status_label)
        details_layout.addRow(time_row_label, time_label)
        details_layout.addRow(exp_row_label, exp_label)

        details_group.setLayout(details_layout)

        button_style = """
            QPushButton { 
                border: 1px solid #444; 
                border-radius: 4px; 
                padding: 5px; 
                background-color: rgb(60, 60, 60);
                color: #f6e7c5;
            }
            QPushButton:hover { 
                background-color: rgb(80, 80, 80);
                border: 1px solid #666; 
            }
            QPushButton:pressed { 
                background-color: rgb(40, 40, 40);
            }
        """

        # Collapse button
        screenshot_button = QPushButton("Screenshots öffnen")
        screenshot_button.setStyleSheet(button_style)
        screenshot_button.setCursor(Qt.PointingHandCursor)  # Ändert den Mauszeiger zu einer Hand
        screenshot_button.clicked.connect(self.open_screenshots)

        # Add to layout
        layout.addWidget(kills_group)
        layout.addWidget(details_group)
        button_layout = QHBoxLayout()
        collapse_button = QPushButton("Einklappen")
        collapse_button.setStyleSheet("QPushButton { border: 1px solid #444; border-radius: 4px; padding: 5px; }")
        collapse_button.clicked.connect(self.toggle_expansion)
        button_layout.addWidget(screenshot_button, alignment=Qt.AlignRight)
        layout.addLayout(button_layout)

    def mousePressEvent(self, event):
        self.toggle_expansion()
        super().mousePressEvent(event)

    def toggle_expansion(self):
        self.expanded = not self.expanded
        self.expanded_widget.setVisible(self.expanded)

    def open_screenshots(self):
        """Open the screenshots folder for this raid"""
        folder_name = self.raid_data.get("folder_name", "")
        if not folder_name:
            QMessageBox.warning(self, "Fehler", "Keine Ordnerinformation für diesen Raid gefunden.")
            return

        # Konstruiere den Pfad zum Screenshots-Ordner
        screenshot_path = os.path.join("Raids old", folder_name)

        # Überprüfe, ob der Ordner existiert
        if not os.path.exists(screenshot_path):
            QMessageBox.warning(
                self,
                "Ordner nicht gefunden",
                f"Der Screenshot-Ordner für diesen Raid wurde nicht gefunden:\n{screenshot_path}"
            )
            return

        # Ordner im Explorer öffnen (Windows-spezifisch)
        try:
            os.startfile(screenshot_path)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Fehler",
                f"Fehler beim Öffnen des Ordners:\n{str(e)}"
            )
