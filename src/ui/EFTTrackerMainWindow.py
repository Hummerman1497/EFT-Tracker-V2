import ctypes
import json
import os
import subprocess
import time
from datetime import datetime

import mss
from PyQt5.QtChart import QChart, QChartView, QPieSeries
from PyQt5.QtCore import QSettings, QTimer, QProcess, Qt
from PyQt5.QtGui import QFontDatabase, QFont, QPalette, QColor, QPixmap, QBrush, QPen, QPainter
from PyQt5.QtWidgets import QApplication, QTextEdit, QTabWidget, QMessageBox, QWidget, QVBoxLayout, QPushButton, \
    QGroupBox, QHBoxLayout, QFormLayout, QLabel, QTableWidget, QHeaderView, QTableWidgetItem, QScrollArea, QLineEdit, \
    QFileDialog

from src.App_Main import asset_manager, CSharpOutputReader
from src.eft_registry_finder import get_eft_logs_path
from src.ui.ExpandableRaidTile import ExpandableRaidTile
from src.ui.custom_window import BorderlessMainWindow


class EFTTracker(BorderlessMainWindow):
    def __init__(self):
        super().__init__()
        self.assets = asset_manager

        # Icon import
        app_icon_path = self.assets.get_icon_path("Ushanka_icon.ico")  # Icon-Pfad anpassen
        if os.path.exists(app_icon_path):
            from PyQt5.QtGui import QIcon
            app_icon = QIcon(app_icon_path)
            self.setWindowIcon(app_icon)
            # Setze auch das Icon für die gesamte Anwendung
            QApplication.setWindowIcon(app_icon)
        else:
            self.log_message(f"Warnung: Icon-Datei nicht gefunden: {app_icon_path}", "warning")

        # Important: Initialize your data BEFORE setting up UI content
        self.raids = []
        self.ocr_data_dir = "data"
        self.settings = QSettings("EFTTracker", "AppSettings")

        # Set window title (displayed in the custom title bar)
        self.title_bar.title_label.setText("EFT Tracker")

        # Apply dark theme
        self.setup_dark_theme()

        # Create log text edit before it's referenced in any log methods
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)

        # Try to auto-detect EFT path with a slight delay to ensure the UI is ready
        QTimer.singleShot(500, self.initialize_eft_path)

        saved_log_path = self.settings.value("eft_log_path", "", str)
        if saved_log_path:
            QTimer.singleShot(600, lambda: self.write_log_path_to_config(saved_log_path))

        # Create your UI in the content area
        self.setup_eft_content()

        # Load raids and update stats
        self.load_raids()
        self.update_stats()
        self.update_raid_tiles()

        # Size the window
        self.resize(1200, 900)

    def setup_eft_content(self):
        """Set up the main EFT Tracker content in the custom window's content area"""
        # Create tabs widget
        self.tabs = QTabWidget()

        # Create your tabs
        self.stats_tab = self.create_stats_tab()
        self.history_tab = self.create_history_tab()
        self.settings_tab = self.create_settings_tab()
        self.log_tab = self.create_log_tab()

        # Add tabs to the tab widget
        self.tabs.addTab(self.stats_tab, "Statistik")
        self.tabs.addTab(self.history_tab, "History")
        self.tabs.addTab(self.settings_tab, "Einstellungen")
        self.tabs.addTab(self.log_tab, "Log")

        # Add styling to the tabs
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
            }
            QTabBar::tab:selected {
                background-color: #2D2D2D;
                border-bottom: 1px solid #2D2D2D;
            }
            QTabBar::tab:!selected {
                margin-top: 2px;
            }
        """)

        # Add the tabs to the content layout
        self.content_layout.addWidget(self.tabs)

    def reset_statistics_flag(self):
        """Reset the statisticsFound flag in the LogWatcher"""
        if hasattr(self, 'process') and self.process is not None and isinstance(self.process, QProcess):
            self.process.write(b"RESET_FLAG\n")
            self.log_message("Sent statistics flag reset to LogWatcher", "python")

    def show_log_path_help(self):
        """Show help information about setting the log path"""
        QMessageBox.information(
            self,
            "Log path information"
            "The EFT log path is necessary for the application to capture your raid data.\n\n"
            "Typical storage locations for EFT logs:\n"
            "• C:\\Battlestate Games\\EFT\\Logs\n"
            "• D:\\Battlestate Games\\EFT\\Logs\n"
            "• E:\\Battlestate Games\\EFT\\Logs\n\n"
            "The correct setting of this path is important for the automatic screenshot function."
        )

    def handle_stdout(self):
        """Processes the standard output of the QProcess"""
        if not hasattr(self, 'process') or self.process is None:
            return

        data = self.process.readAllStandardOutput()
        try:
            stdout = bytes(data).decode('utf-8', errors='replace')
            if stdout:
                for line in stdout.splitlines():
                    if line.strip():
                        self.log_message(line.strip(), "csharp")
        except Exception as e:
            self.log_message(f"Error processing standard output: {str(e)}", "error")

    def handle_stderr(self):
        """Processes the error output of the QProcess"""
        if not hasattr(self, 'process') or self.process is None:
            return

        data = self.process.readAllStandardError()
        try:
            stderr = bytes(data).decode('utf-8', errors='replace')
            if stderr:
                for line in stderr.splitlines():
                    if line.strip():
                        self.log_message(f"{line.strip()}", "error")
        except Exception as e:
            self.log_message(f"Error processing error output: {str(e)}", "error")

    def handle_process_finished(self, exit_code, exit_status):
        """Called when the QProcess terminates"""
        status_text = "normal" if exit_status == QProcess.NormalExit else "with crash"
        self.log_message(f"C# LogWatcher terminated ({status_text}, Exit code: {exit_code})", "warning")

        # Reset process reference
        self.process = None

    def set_mouse_pos(self, x, y):
        ctypes.windll.user32.SetCursorPos(x, y)

    def mouse_click(self):
        mouseLeft_down = 0x0002
        mouseLeft_up = 0x0004
        ctypes.windll.user32.mouse_event(mouseLeft_down, 0, 0, 0, 0)
        ctypes.windll.user32.mouse_event(mouseLeft_up, 0, 0, 0, 0)

    def take_screenshot(self, n, dir_raid=datetime.now().strftime("%d.%m.%Y %H-%M"), dateiname=None):
        dir_screenshots = "Raids new"

        raid_path = os.path.join(dir_screenshots, dir_raid)

        if not os.path.exists(raid_path):
            os.makedirs(raid_path)

        if dateiname is None:
            dateiname = f"screenshot {dir_raid} ({n}).png"

        filepath = os.path.join(dir_screenshots, dir_raid, dateiname)

        with mss.mss() as sct:
            screenshot = sct.shot(output=filepath)
            print(f"Screenshot gespeichert: {screenshot}")

    def screenshot_script(self, folder_name=None):
        """Nimmt eine Reihe von Screenshots für einen Raid auf"""
        if folder_name is None:
            folder_name = datetime.now().strftime("%d.%m.%Y. %H-%M")

        self.log_message(f"Screenshot-Sequenz gestartet für Ordner: {folder_name}", "python")

        # Get the current screen resolution from settings
        screen_width = self.settings.value("monitor_width", 2560, int)  # Default to 1440p width
        screen_height = self.settings.value("monitor_height", 1440, int)  # Default to 1440p height

        # Original button coordinates for 1440p (2560x1440)
        base_next_x = 1280
        base_next_y = 1280
        base_back_x = 1280
        base_back_y = 1380

        # Reference resolution (1440p)
        ref_width = 2560
        ref_height = 1440

        # Calculate percentages based on 1440p resolution
        next_button_x_percent = base_next_x / ref_width
        next_button_y_percent = base_next_y / ref_height

        back_button_x_percent = base_back_x / ref_width
        back_button_y_percent = base_back_y / ref_height

        # Calculate actual coordinates for current resolution
        buttonNextX = int(screen_width * next_button_x_percent)
        buttonNextY = int(screen_height * next_button_y_percent)

        buttonBackX = int(screen_width * back_button_x_percent)
        buttonBackY = int(screen_height * back_button_y_percent)

        # Log the calculated coordinates for debugging
        self.log_message(f"Using resolution: {screen_width}x{screen_height}", "python")
        self.log_message(f"Next button coordinates: ({buttonNextX}, {buttonNextY})", "python")
        self.log_message(f"Back button coordinates: ({buttonBackX}, {buttonBackY})", "python")

        try:
            # Positioniere die Maus auf den "Next"-Button
            self.set_mouse_pos(buttonNextX, buttonNextY)

            # Screenshot 1
            self.take_screenshot(1, folder_name)
            self.mouse_click()
            time.sleep(0.3)  # Warte, bis die neue Seite geladen ist

            # Screenshot 2
            self.take_screenshot(2, folder_name)
            self.mouse_click()
            time.sleep(0.3)

            # Screenshot 3
            self.take_screenshot(3, folder_name)
            self.mouse_click()
            time.sleep(0.3)

            # Screenshot 4
            self.take_screenshot(4, folder_name)

            # Zurück zu vorherigen Bildschirmen
            self.set_mouse_pos(buttonBackX, buttonBackY)
            time.sleep(0.05)
            self.mouse_click()
            time.sleep(0.05)
            self.mouse_click()
            time.sleep(0.05)
            self.mouse_click()

            self.log_message(f"Screenshot-Sequenz abgeschlossen für: {folder_name}", "python")

            # Try to reset the statistics flag, but catch errors
            try:
                self.reset_statistics_flag()
            except Exception as reset_error:
                self.log_message(f"Fehler beim Zurücksetzen des Statistik-Flags: {str(reset_error)}", "error")
                # Log that manual intervention might be needed
                self.log_message("Benutzereingriff könnte erforderlich sein - bitte LogWatcher neu starten.", "warning")

        except Exception as e:
            self.log_message(f"Fehler während der Screenshot-Sequenz: {str(e)}", "error")
            import traceback
            self.log_message(traceback.format_exc(), "error")

    def reset_statistics_flag(self):
        """Resets the statisticsFound flag in the LogWatcher"""
        if hasattr(self, 'process') and self.process is not None:
            try:
                # Handle different process types
                if isinstance(self.process, QProcess):
                    # For QProcess
                    self.process.write(b"RESET_FLAG\n")
                else:
                    # For subprocess.Popen
                    if hasattr(self.process, 'stdin') and self.process.stdin:
                        # Make sure stdin is not closed
                        try:
                            # Write the command and flush
                            self.process.stdin.write(b"RESET_FLAG\n")
                            self.process.stdin.flush()
                            self.log_message("Statistik-Flag-Reset an LogWatcher gesendet", "python")
                        except (BrokenPipeError, IOError) as e:
                            # Handle pipe errors
                            self.log_message(f"Error sending reset flag: {str(e)}", "error")
                            # The process might have died, restart it
                            self.log_message("Attempting to restart LogWatcher process", "warning")
                            self.start_csharp_process()
                    else:
                        self.log_message("Cannot reset statistics flag - process stdin not available", "error")
            except Exception as e:
                self.log_message(f"Error resetting statistics flag: {str(e)}", "error")
                import traceback
                self.log_message(traceback.format_exc(), "error")

    def setup_dark_theme(self):
        # Schriftart laden
        font_path = self.assets.get_font_path("bender.regular.otf")
        font_id = QFontDatabase.addApplicationFont(font_path)

        if font_id != -1:  # Falls das Laden erfolgreich war
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            app_font = QFont(font_family)
            app_font.setPointSize(10)  # Hier kannst du die Größe anpassen
            QApplication.setFont(app_font)
        else:
            print("⚠ Schriftart konnte nicht geladen werden!")

        # Dunkles Farbschema
        dark_palette = QPalette()

        # Hintergrund (dunkelgrau)
        dark_color = QColor(45, 45, 45)
        light_color = QColor(246, 231, 197)  # #f6e7c5

        dark_palette.setColor(QPalette.Window, dark_color)
        dark_palette.setColor(QPalette.WindowText, light_color)
        dark_palette.setColor(QPalette.Base, QColor(30, 30, 30))
        dark_palette.setColor(QPalette.AlternateBase, dark_color)
        dark_palette.setColor(QPalette.ToolTipBase, light_color)
        dark_palette.setColor(QPalette.ToolTipText, light_color)
        dark_palette.setColor(QPalette.Text, light_color)
        dark_palette.setColor(QPalette.Button, dark_color)
        dark_palette.setColor(QPalette.ButtonText, light_color)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)

        QApplication.setPalette(dark_palette)
        QApplication.setStyle("Fusion")

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

    def create_log_tab(self):
        """Creates the log tab with color-coded output for Python and C# logs"""
        tab = QWidget()
        layout = QVBoxLayout()

        # Create a custom QTextEdit with HTML formatting support
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)

        # Set a monospace font for better log readability
        font = QFont("Courier New", 10)
        self.log_text_edit.setFont(font)

        # Set dark background for the log text edit
        self.log_text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #f6e7c5;
                border: 1px solid #444444;
            }
        """)

        # Add clear button
        clear_button = QPushButton("Clear Log")
        clear_button.clicked.connect(self.clear_log)
        clear_button.setStyleSheet("""
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
        """)

        # Add the widgets to the layout
        layout.addWidget(self.log_text_edit)
        layout.addWidget(clear_button, alignment=Qt.AlignRight)

        tab.setLayout(layout)
        return tab

    def clear_log(self):
        """Clears the log text edit"""
        self.log_text_edit.clear()

    def log_message(self, message, source="python"):
        """
        Logs a message with color coding based on the source

        Parameters:
        message (str): The message to log
        source (str): The source of the message ('python' or 'csharp')
        """
        if not hasattr(self, 'log_text_edit') or self.log_text_edit is None:
            return

        timestamp = datetime.now().strftime("%H:%M:%S")

        if source == "python":
            # Python logs are green
            color = "#98C379"  # Light green
            source_label = "[Python]"
        elif source == "csharp":
            # C# logs are blue
            color = "#61AFEF"  # Light blue
            source_label = "[C#]"
        elif source == "error":
            # Error logs are red
            color = "#E06C75"  # Light red
            source_label = "[ERROR]"
        elif source == "warning":
            # Warning logs are yellow
            color = "#E5C07B"  # Light yellow
            source_label = "[WARNING]"
        elif source == "data":
            color = "#C678DD"
            source_label = "[Data correction]"
        else:
            # Other logs are default color
            color = "#f6e7c5"  # EFT yellowish color
            source_label = "[INFO]"

        # Format the log message with HTML
        formatted_message = f'<br><span style="color: #7F848E;">{timestamp}</span> <span style="color: {color};">{source_label}</span> {message}'

        # Append the message to the log
        self.log_text_edit.moveCursor(self.log_text_edit.textCursor().End)
        self.log_text_edit.insertHtml(formatted_message)
        self.log_text_edit.ensureCursorVisible()

    def reload_ocr_data(self):
        """Reload OCR data and update UI"""
        self.log_message("Reloading OCR data...", "python")
        self.load_raids()
        self.update_raid_tiles()
        self.update_stats()
        self.log_message("OCR data reloaded and UI updated.", "python")

    def update_stats(self):
        """Update all statistics displays"""
        # Aktualisiere die Statistiken
        total_raids = len(self.raids)
        survived_raids = sum(1 for raid in self.raids if raid["status"] == "Survived")
        survival_rate = (survived_raids / total_raids * 100) if total_raids > 0 else 0
        total_kills = sum(raid["kills"] for raid in self.raids)

        # Calculate K/D as kills divided by deaths
        deaths = total_raids - survived_raids  # TODO: nichts deaths sondern deaths+runthroughs
        kd_ratio = (total_kills / deaths) if deaths > 0 else total_kills

        self.total_raids_label.setText(f"{total_raids}")
        self.survived_raids_label.setText(f"{survived_raids}")
        self.survival_rate_label.setText(f"{survival_rate:.1f}%")
        self.total_kills_label.setText(f"{total_kills}")
        self.kd_ratio_label.setText(f"{kd_ratio:.2f}")

        # Tortendiagramm aktualisieren
        self.update_pie_chart()

        # Map-Statistiken aktualisieren
        self.update_map_stats()

    def start_csharp_process(self):
        """Start the C# LogWatcher process and set up communication"""
        try:
            # Track if we're already running a process to avoid looping
            if hasattr(self, 'process') and self.process is not None:
                if isinstance(self.process, QProcess):
                    if self.process.state() != QProcess.NotRunning:
                        self.log_message("LogWatcher process already running, not starting a new one", "python")
                        return
                elif hasattr(self.process, 'poll') and self.process.poll() is None:
                    self.log_message("LogWatcher process already running, not starting a new one", "python")
                    return

            # Only kill existing processes when we don't have one already tracked
            self.kill_existing_logwatcher()

            # Path to C# application
            exe_path = self.assets.get_csharp_path("LogWatcherv1.exe")

            # Log debugging information
            self.log_message(f"Starting C# LogWatcher: {exe_path}", "python")
            self.log_message(f"File exists: {os.path.exists(exe_path)}", "python")

            # Use subprocess.Popen instead of QProcess for better stdout capture
            self.process = subprocess.Popen(
                [exe_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                bufsize=0,  # Unbuffered mode
                text=False,  # Binary mode
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
                # Hide console window completely
            )

            # Create and start the output reader thread
            self.output_reader = CSharpOutputReader(self.process)
            self.output_reader.set_application(self)  # Set reference to self for triggering functions
            self.output_reader.output_received.connect(self.on_process_output)
            self.output_reader.start()

            self.log_message("C# LogWatcher successfully started", "python")

            # Send the log path to the process if we have one
            log_path = self.settings.value("eft_log_path", "", str)
            if log_path and os.path.exists(log_path):
                self.log_message(f"Using log path: {log_path}", "python")
                # Make sure to update the config file without restarting the process
                self.write_log_path_to_config_without_restart(log_path)
            else:
                self.log_message("Warning: No valid log path configured!", "warning")

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.log_message(f"Error starting C# process: {str(e)}", "error")
            self.log_message(f"Details:\n{error_details}", "error")

    def write_log_path_to_config_without_restart(self, log_path):
        """Write the EFT logs path to the configuration file for LogWatcher without restarting the process"""
        try:
            # Get the path to the LogWatcherv1.exe
            exe_path = self.assets.get_csharp_path("LogWatcherv1.exe")

            # Extract the directory where the executable is located
            exe_directory = os.path.dirname(exe_path)

            # Ensure the directory exists
            if not os.path.exists(exe_directory):
                os.makedirs(exe_directory, exist_ok=True)
                self.log_message(f"Created directory: {exe_directory}", "python")

            # Ensure the path is valid
            if not log_path or not os.path.exists(log_path):
                self.log_message(f"Warning: Log path doesn't exist: {log_path}", "warning")

            # Create the path for the configuration file in the same directory as the exe
            config_file = os.path.join(exe_directory, "eft_logs_path.txt")

            # Write the log path to the configuration file
            with open(config_file, 'w') as f:
                f.write(log_path)

            self.log_message(f"Log path saved to configuration file: {log_path}", "python")
            self.log_message(f"Configuration file path: {config_file}", "python")

            return True
        except Exception as e:
            self.log_message(f"Error saving log path to configuration file: {str(e)}", "error")
            import traceback
            self.log_message(traceback.format_exc(), "error")
            return False

    def on_process_output(self, output):
        """Process output from the LogWatcher"""
        self.log_message(output, "csharp")

    def show_log_path_help(self):
        """Show help information about setting the log path"""
        QMessageBox.information(
            self,
            "Log-Pfad Information",
            "Der EFT Log-Pfad ist notwendig, damit die Anwendung Ihre Raid-Daten erfassen kann.\n\n"
            "Typische Speicherorte für EFT-Logs:\n"
            "• C:\\Battlestate Games\\EFT\\Logs\n"
            "• D:\\Battlestate Games\\EFT\\Logs\n"
            "• E:\\Battlestate Games\\EFT\\Logs\n\n"
            "Die korrekte Einstellung dieses Pfades ist wichtig für die automatische Screenshot-Funktion."
        )

    def kill_existing_logwatcher(self):
        """Kill any existing LogWatcherv1.exe processes"""
        try:
            # Use tasklist to find LogWatcherv1.exe processes
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq LogWatcherv1.exe', '/FO', 'CSV'],
                                    capture_output=True, text=True)

            # Log the tasklist result
            self.log_message(f"Tasklist after searching for LogWatcherv1.exe: {result.stdout}", "warning")

            # Check if any processes were found - if stdout is empty or doesn't contain the process name
            if not result.stdout or 'LogWatcherv1.exe' not in result.stdout:
                self.log_message("No LogWatcherv1.exe processes found to terminate.", "warning")
                return

            # If we get here, processes were found
            self.log_message("Found existing LogWatcher processes. Terminating...", "warning")

            # Kill the processes
            subprocess.run(['taskkill', '/F', '/IM', 'LogWatcherv1.exe'],
                           capture_output=True)

            # Wait a moment for processes to terminate
            time.sleep(1)
            self.log_message("Existing LogWatcher processes terminated.", "warning")

        except Exception as e:
            # Just log as a warning since this isn't critical
            self.log_message(f"Exception when checking for LogWatcher processes: {str(e)}", "warning")

    def create_stats_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        font_Header = QFont()
        font_Header.setPointSize(16)
        font_Header.setBold(True)

        # Statistiken anzeigen
        stats_group = QGroupBox("Gesamt Statistik")
        stats_group.setFont(font_Header)
        stats_layout = QHBoxLayout()  # Horizontal für Charts und Text

        # Text-Statistiken (links)
        text_stats_layout = QFormLayout()

        # Berechne und zeige Statistiken an
        total_raids = len(self.raids)
        survived_raids = sum(1 for raid in self.raids if raid["status"] == "Survived")
        survival_rate = (survived_raids / total_raids * 100) if total_raids > 0 else 0
        total_kills = sum(raid["kills"] for raid in self.raids)
        kd_ratio = (total_kills / (total_raids - survived_raids)) if (total_raids - survived_raids) > 0 else 0

        self.total_raids_label = QLabel(f"{total_raids}")
        self.survived_raids_label = QLabel(f"{survived_raids}")
        self.survival_rate_label = QLabel(f"{survival_rate:.1f}%")
        self.total_kills_label = QLabel(f"{total_kills}")
        self.kd_ratio_label = QLabel(f"{kd_ratio:.2f}")

        # Schriftart für Statistiken
        font = QFont()
        font.setPointSize(12)
        self.total_raids_label.setFont(font)
        self.survived_raids_label.setFont(font)
        self.survival_rate_label.setFont(font)
        self.total_kills_label.setFont(font)
        self.kd_ratio_label.setFont(font)

        # Manuelle Erstellung der Labels für die Beschriftung
        label_raids = QLabel("Anzahl Raids :")
        label_raids.setFont(font)

        label_survived = QLabel("Überlebt :")
        label_survived.setFont(font)

        label_survival_rate = QLabel("Überlebensrate :")
        label_survival_rate.setFont(font)

        label_kills = QLabel("Kills gesamt :")
        label_kills.setFont(font)

        label_kd = QLabel("K/D :")
        label_kd.setFont(font)

        # Dann die Zeilen mit den eigenen Labels hinzufügen
        text_stats_layout.addRow(label_raids, self.total_raids_label)
        text_stats_layout.addRow(label_survived, self.survived_raids_label)
        text_stats_layout.addRow(label_survival_rate, self.survival_rate_label)
        text_stats_layout.addRow(label_kills, self.total_kills_label)
        text_stats_layout.addRow(label_kd, self.kd_ratio_label)

        # Tortendiagramm (rechts)
        chart_widget = QWidget()
        chart_layout = QVBoxLayout()

        # Erstelle das Tortendiagramm
        self.pie_chart = QChart()
        # Hintergrundbild setzen

        background_image = QPixmap("../../Assets/Images/Norvinskzone.png")  # Pfad zum Bild anpassen
        self.pie_chart.setBackgroundBrush(QBrush(background_image))

        legend_pen = QPen(QColor(246, 231, 197))  # Hier die gewünschte Farbe anpassen
        self.pie_chart.legend().setLabelColor(legend_pen.color())

        font_legend = QFont()
        font_legend.setPointSize(12)
        font_legend.setBold(True)
        self.pie_chart.legend().setFont(font_legend)

        self.pie_chart.setTitle("")
        self.pie_chart.setAnimationOptions(QChart.SeriesAnimations)
        self.pie_chart.legend().setVisible(False)
        self.pie_chart.legend().setAlignment(Qt.AlignRight)

        # Aktualisiere das Tortendiagramm
        self.update_pie_chart()

        # Chart-View erstellen
        chart_view = QChartView(self.pie_chart)
        chart_view.setRenderHint(QPainter.Antialiasing)
        chart_view.setMinimumSize(300, 300)

        chart_layout.addWidget(chart_view)
        chart_widget.setLayout(chart_layout)

        # Alles zum Layout hinzufügen
        stats_layout.addLayout(text_stats_layout, 1)
        stats_layout.addWidget(chart_widget, 2)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # Map-Statistiken
        map_stats_group = QGroupBox("Map Statistik")
        map_stats_layout = QVBoxLayout()

        self.map_table = QTableWidget()
        self.map_table.setColumnCount(5)
        self.map_table.setHorizontalHeaderLabels(["Map", "Raids", "Überlebt", "Überlebensrate", "Kills"])
        self.map_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.update_map_stats()

        map_stats_layout.addWidget(self.map_table)
        map_stats_group.setLayout(map_stats_layout)
        layout.addWidget(map_stats_group)

        tab.setLayout(layout)
        return tab

    def update_pie_chart(self):
        # Lösche vorhandene Serien
        self.pie_chart.removeAllSeries()

        # Zähle Raids pro Map
        map_counts = {}
        for raid in self.raids:
            map_name = raid["map"]
            if map_name not in map_counts:
                map_counts[map_name] = 0
            map_counts[map_name] += 1

        sorted_maps = sorted(map_counts.items(), key=lambda x: x[1], reverse=True)

        # Erstelle neue Pie-Serie
        pie_series = QPieSeries()

        for index, (map_name, count) in enumerate(sorted_maps):
            slice = pie_series.append(f"{map_name} [{count}]", count)
            slice.setLabelVisible(True)
            slice.setLabelColor(QColor(246, 231, 197))

            # Berechne Grauton basierend auf dem Index und der Gesamtzahl der Raids
            # Startwert (Mittelgrau): 128, Endwert (Dunkelgrau): 64
            if len(sorted_maps) > 1:
                gray_value = int(128 - (64 * (index / (len(sorted_maps) - 1))))
            else:
                gray_value = 128

            slice.setColor(QColor(gray_value, gray_value, gray_value))
            slice.setBorderColor(QColor(246, 231, 197))
            slice.setBorderWidth(1)

            slice_font = QFont()
            slice_font.setPointSize(12)
            slice_font.setBold(True)
            slice.setLabelFont(slice_font)

        # Füge Serie zum Chart hinzu
        self.pie_chart.addSeries(pie_series)

    def update_map_stats(self):
        # Map-Statistiken berechnen
        map_stats = {}

        for raid in self.raids:
            map_name = raid["map"]
            if map_name not in map_stats:
                map_stats[map_name] = {
                    "total": 0,
                    "survived": 0,
                    "kills": 0
                }

            map_stats[map_name]["total"] += 1
            if raid["status"] == "Survived":
                map_stats[map_name]["survived"] += 1
            map_stats[map_name]["kills"] += raid["kills"]

        # Tabelle aktualisieren
        self.map_table.setRowCount(len(map_stats))

        for i, (map_name, stats) in enumerate(map_stats.items()):
            survival_rate = (stats["survived"] / stats["total"] * 100) if stats["total"] > 0 else 0

            self.map_table.setItem(i, 0, QTableWidgetItem(map_name))
            self.map_table.setItem(i, 1, QTableWidgetItem(str(stats["total"])))
            self.map_table.setItem(i, 2, QTableWidgetItem(str(stats["survived"])))
            self.map_table.setItem(i, 3, QTableWidgetItem(f"{survival_rate:.1f}%"))
            self.map_table.setItem(i, 4, QTableWidgetItem(str(stats["kills"])))

    def create_history_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        # ScrollArea für die Raid-Kacheln
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setSpacing(10)

        # Aktualisiere Raid-Kacheln
        self.update_raid_tiles()

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

        tab.setLayout(layout)
        return tab

    def create_settings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        # OCR-Einstellungen (inkl. Monitor-Auflösung)
        ocr_group = QGroupBox("OCR Settings")
        ocr_layout = QVBoxLayout()

        ocr_info = QLabel("Starting the OCR will take a few seconds please be patient")
        ocr_info.setWordWrap(True)

        ocr_button = QPushButton("Start OCR")
        ocr_button.clicked.connect(self.start_ocr)
        refresh_button = QPushButton("Reload OCR Data")
        refresh_button.clicked.connect(self.reload_ocr_data)

        # OCR-Layout zusammensetzen
        ocr_layout.addWidget(ocr_info)
        ocr_layout.addWidget(ocr_button)
        ocr_layout.addWidget(refresh_button)

        # Add a refresh button to reload raid data

        ocr_group.setLayout(ocr_layout)
        layout.addWidget(ocr_group)

        # Datenverwaltung
        data_group = QGroupBox("Datenverwaltung")
        data_layout = QVBoxLayout()

        export_button = QPushButton("Daten exportieren")
        export_button.clicked.connect(self.export_data)

        import_button = QPushButton("Daten importieren")
        import_button.clicked.connect(self.import_data)

        reset_button = QPushButton("Alle Daten zurücksetzen")
        reset_button.clicked.connect(self.reset_data)

        data_layout.addWidget(export_button)
        data_layout.addWidget(import_button)
        data_layout.addWidget(reset_button)

        data_group.setLayout(data_layout)
        layout.addWidget(data_group)

        # Log-Dateipfad Einstellungen
        log_group = QGroupBox("EFT Logs file path")
        log_layout = QVBoxLayout()  # Changed to VBoxLayout to add status label

        # Add a status label for path configuration
        self.log_path_status = QLabel()
        log_path_status_font = QFont()
        log_path_status_font.setBold(True)
        self.log_path_status.setFont(log_path_status_font)

        # Input layout
        input_layout = QHBoxLayout()

        self.log_path_edit = QLineEdit()
        self.log_path_edit.setPlaceholderText("Enter the path to the log folder...")

        saved_log_path = self.settings.value("eft_log_path", "", str)
        if saved_log_path:
            self.log_path_edit.setText(saved_log_path)
            self.log_path_status.setText("Log path configured ✓")
            self.log_path_status.setStyleSheet("color: green;")
        else:
            self.log_path_status.setText("⚠️ Log path not configured! Please set manually.")
            self.log_path_status.setStyleSheet("color: red;")

        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.select_log_path)

        # Add a Help button with path information
        help_button = QPushButton("?")
        help_button.setMaximumWidth(30)
        help_button.clicked.connect(self.show_log_path_help)

        input_layout.addWidget(self.log_path_edit)
        input_layout.addWidget(browse_button)
        input_layout.addWidget(help_button)

        # Add info about common paths

        log_layout.addWidget(self.log_path_status)
        log_layout.addLayout(input_layout)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        tab.setLayout(layout)
        return tab

    def export_data(self):
        # Ask for export file location
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Daten exportieren",
            "eft_tracker_data.json",
            "JSON Files (*.json)",
            options=options
        )

        if file_path:
            try:
                with open(file_path, "w") as f:
                    json.dump({"raids": self.raids}, f, indent=4)
                QMessageBox.information(
                    self,
                    "Daten exportiert",
                    f"Die Daten wurden als '{os.path.basename(file_path)}' exportiert."
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Fehler beim Exportieren",
                    f"Fehler beim Exportieren der Daten: {str(e)}"
                )

    def import_data(self):
        # Ask for import file location
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Daten importieren",
            "",
            "JSON Files (*.json)",
            options=options
        )

        if file_path:
            try:
                with open(file_path, "r") as f:
                    import_data = json.load(f)

                if isinstance(import_data, dict) and "raids" in import_data:
                    imported_raids = import_data["raids"]

                    # Confirm with the user
                    reply = QMessageBox.question(
                        self,
                        "Daten importieren",
                        f"{len(imported_raids)} Raids gefunden. Möchten Sie diese importieren?\n"
                        "Bestehende Daten werden ergänzt.",
                        QMessageBox.Yes | QMessageBox.No
                    )

                    if reply == QMessageBox.Yes:
                        # Merge imported raids with existing raids
                        self.raids.extend(imported_raids)

                        # Remove duplicates based on date and folder_name
                        unique_raids = {}
                        for raid in self.raids:
                            key = f"{raid.get('date', '')}_{raid.get('folder_name', '')}"
                            unique_raids[key] = raid

                        self.raids = list(unique_raids.values())

                        # Sort raids by date
                        self.raids.sort(key=lambda x: x.get("date", ""), reverse=True)

                        # Update UI
                        self.update_raid_tiles()
                        self.update_stats()

                        # Save the combined data
                        self.save_raids()

                        QMessageBox.information(
                            self,
                            "Daten importiert",
                            f"{len(imported_raids)} Raids wurden importiert."
                        )
                else:
                    QMessageBox.warning(
                        self,
                        "Ungültiges Format",
                        "Die importierte Datei hat ein ungültiges Format."
                    )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Fehler beim Importieren",
                    f"Fehler beim Importieren der Daten: {str(e)}"
                )

    def reset_data(self):
        reply = QMessageBox.question(
            self,
            "Daten zurücksetzen",
            "Bist du sicher, dass du alle Daten zurücksetzen möchtest? ")

    def save_raids(self):
        """Save raids data for backup purposes"""
        data_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raids_backup.json")
        try:
            with open(data_file, "w") as f:
                json.dump(self.raids, f, indent=4)
            self.log_message(f"Raids data saved to {data_file}", "python")
        except Exception as e:
            self.log_message(f"Error saving raids data: {e}", "error")

    def write_log_path_to_config(self, log_path):
        """Write the EFT logs path to the configuration file for LogWatcher"""
        try:
            # Get the path to the LogWatcherv1.exe
            exe_path = self.assets.get_csharp_path("LogWatcherv1.exe")

            # Extract the directory where the executable is located
            exe_directory = os.path.dirname(exe_path)

            # Ensure the directory exists
            if not os.path.exists(exe_directory):
                os.makedirs(exe_directory, exist_ok=True)
                self.log_message(f"Created directory: {exe_directory}", "python")

            # Ensure the path is valid
            if not log_path or not os.path.exists(log_path):
                self.log_message(f"Warning: Log path doesn't exist: {log_path}", "warning")

            # Create the path for the configuration file in the same directory as the exe
            config_file = os.path.join(exe_directory, "eft_logs_path.txt")

            # Write the log path to the configuration file
            with open(config_file, 'w') as f:
                f.write(log_path)

            self.log_message(f"Log path saved to configuration file: {log_path}", "python")
            self.log_message(f"Configuration file path: {config_file}", "python")

            # Check if the process is already running
            process_running = False
            if hasattr(self, 'process') and self.process is not None:
                if isinstance(self.process, QProcess):
                    process_running = self.process.state() != QProcess.NotRunning
                elif hasattr(self.process, 'poll'):
                    process_running = self.process.poll() is None

            # Only start the C# process if it's not already running
            if not process_running:
                QTimer.singleShot(1000, self.start_csharp_process)
                self.log_message("Starting LogWatcher process with new configuration", "python")
            else:
                self.log_message("LogWatcher process already running with existing configuration", "python")

            return True
        except Exception as e:
            self.log_message(f"Error saving log path to configuration file: {str(e)}", "error")
            import traceback
            self.log_message(traceback.format_exc(), "error")
            return False

    def select_log_path(self):
        options = QFileDialog.Options()
        folder_path = QFileDialog.getExistingDirectory(self, "Log-Ordner auswählen", "", options=options)

        if folder_path:
            self.log_path_edit.setText(folder_path)
            self.settings.setValue("eft_log_path", folder_path)

            # Update the status indicator
            self.log_path_status.setText("Log-Pfad konfiguriert ✓")
            self.log_path_status.setStyleSheet("color: green;")

            # Check if the LogWatcher process is already running
            process_running = False
            if hasattr(self, 'process') and self.process is not None:
                if isinstance(self.process, QProcess):
                    process_running = self.process.state() != QProcess.NotRunning
                elif hasattr(self.process, 'poll'):
                    process_running = self.process.poll() is None

            # Stop the existing process if it's running
            if process_running:
                self.log_message("Stopping existing LogWatcher process to apply new path", "python")
                try:
                    if isinstance(self.process, QProcess):
                        self.process.kill()
                        self.process.waitForFinished(1000)
                    else:
                        self.process.terminate()
                        try:
                            self.process.wait(timeout=1)
                        except:
                            pass
                    # Reset the process reference
                    self.process = None
                except Exception as e:
                    self.log_message(f"Error stopping LogWatcher process: {str(e)}", "error")

            # Write the path to the configuration file
            self.write_log_path_to_config_without_restart(folder_path)

            # Start a new process with the updated path
            QTimer.singleShot(1000, self.start_csharp_process)

            QMessageBox.information(self, "Pfad gespeichert", f"Log-Ordner wurde auf {folder_path} gesetzt.")

    def update_raid_tiles(self):
        # Lösche alle vorherigen Kacheln
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Erstelle neue Kacheln für jeden Raid (neueste zuerst)
        for raid in self.raids:
            # Make sure this matches the parameter name in __init__
            tile = ExpandableRaidTile(raid, asset_manager=self.assets)
            self.scroll_layout.addWidget(tile)

    def load_raids(self):
        """Load raids from OCR data directory with improved error handling"""
        self.raids = []

        try:
            # Check if OCR data directory exists
            if not os.path.exists(self.ocr_data_dir):
                print(f"OCR data directory not found: {self.ocr_data_dir}")
                if hasattr(self, 'log_text_edit'):
                    self.log_message(f"OCR data directory not found: {self.ocr_data_dir}", "warning")
                return

            # Find all raid_data.json files in the OCR data directory
            raid_data_files = []
            for root, dirs, files in os.walk(self.ocr_data_dir):
                if "raid_data.json" in files:
                    raid_data_files.append(os.path.join(root, "raid_data.json"))

            if not raid_data_files:
                print("No raid data files found")
                if hasattr(self, 'log_text_edit'):
                    self.log_message("No raid data files found", "warning")
                return

            print(f"Found {len(raid_data_files)} raid data files")
            if hasattr(self, 'log_text_edit'):
                self.log_message(f"Found {len(raid_data_files)} raid data files", "python")

            # Process each raid data file
            for file_path in raid_data_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        try:
                            ocr_data = json.load(f)

                            # Extract folder name (date & time) from path
                            folder_name = os.path.basename(os.path.dirname(file_path))

                            # Process OCR data into raid info
                            raid = self.process_ocr_data(ocr_data, folder_name)
                            if raid:
                                self.raids.append(raid)
                                if hasattr(self, 'log_text_edit'):
                                    self.log_message(f"Successfully loaded raid from {folder_name}", "python")
                        except json.JSONDecodeError as json_err:
                            print(f"Error parsing JSON file: {file_path} - {str(json_err)}")
                            if hasattr(self, 'log_text_edit'):
                                self.log_message(f"Error parsing JSON file: {file_path} - {str(json_err)}", "python")
                            continue
                except Exception as file_err:
                    print(f"Error reading file {file_path}: {str(file_err)}")
                    if hasattr(self, 'log_text_edit'):
                        self.log_message(f"Error reading file {file_path}: {str(file_err)}", "error")
                    continue

            # Sort raids by date (newest first)
            self.raids.sort(key=lambda x: x.get("date", ""), reverse=True)

            print(f"Loaded {len(self.raids)} raids")
            if hasattr(self, 'log_text_edit'):
                self.log_message(f"Loaded {len(self.raids)} raids", "python")

            # Save the loaded raids as backup
            self.save_raids()


        except Exception as e:

            import traceback

            error_details = traceback.format_exc()

            print(f"Error loading raids: {str(e)}\n{error_details}")

            if hasattr(self, 'log_text_edit'):
                self.log_message(f"Error loading raids: {str(e)}", "error")

                self.log_message(error_details, "error")

    def start_ocr(self):
        try:
            # Use the asset manager to get the correct path
            exe_path = os.path.join(self.assets.base_path, "../../Assets", "OCR.exe")

            # Log the path for debugging
            print(f"OCR executable path: {exe_path}")
            if hasattr(self, 'log_text_edit'):
                self.log_message(f"OCR executable path: {exe_path}", "python")

            # Check if the file exists
            if not os.path.exists(exe_path):
                # Try an alternative path if the first one fails
                exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../Assets", "OCR.exe")
                print(f"Trying alternative OCR path: {exe_path}")
                if hasattr(self, 'log_text_edit'):
                    self.log_message(f"Trying alternative OCR path: {exe_path}", "python")

                # Check if the alternative path exists
                if not os.path.exists(exe_path):
                    raise FileNotFoundError(f"OCR executable not found at: {exe_path}")

            # Start the OCR process
            subprocess.Popen(exe_path)
            print("OCR process started successfully")
            if hasattr(self, 'log_text_edit'):
                self.log_message("OCR process started successfully", "python")

        except Exception as e:
            error_msg = f"Error starting OCR executable: {e}"
            print(error_msg)
            if hasattr(self, 'log_text_edit'):
                self.log_text_edit.append(error_msg)

    def process_ocr_data(self, ocr_data, folder_name):
        """Process OCR data into raid info with corrections"""
        try:
            # Create OCR corrector
            from ocr_corrector import OCRDataCorrector
            corrector = OCRDataCorrector()

            # Extract information from OCR data
            status_info = ocr_data.get("Status", {})
            kill_list = ocr_data.get("KillList", {})
            raid_stats = ocr_data.get("RaidStatistics", {})
            exp_info = ocr_data.get("ExperienceGained", {})

            # Create a log entry for debugging
            self.log_message(f"Processing OCR data for folder: {folder_name}", "python")

            # Process and correct status
            # Handle both list and string cases for all extracted data
            status_text = ""
            if isinstance(status_info.get("Status"), list):
                status_text = " ".join(status_info.get("Status", []))
            elif isinstance(status_info.get("Status"), str):
                status_text = status_info.get("Status", "")
            status = corrector.correct_status(status_text) if status_text else "Unknown"

            # Extract and correct time
            time_text = ""
            if isinstance(status_info.get("Timer"), list):
                time_text = " ".join(status_info.get("Timer", []))
            elif isinstance(status_info.get("Timer"), str):
                time_text = status_info.get("Timer", "")
            time = corrector.correct_time_format(time_text) if time_text else "Unknown"

            # Extract and correct map
            map_text = ""
            if isinstance(raid_stats.get("map"), list):
                map_text = " ".join(raid_stats.get("map", []))
            elif isinstance(raid_stats.get("map"), str):
                map_text = raid_stats.get("map", "")
            map_name = corrector.correct_map_name(map_text) if map_text else "Unknown"

            # Extract and correct experience
            exp_text = ""
            if isinstance(status_info.get("Experience"), list):
                exp_text = " ".join(status_info.get("Experience", []))
            elif isinstance(status_info.get("Experience"), str):
                exp_text = status_info.get("Experience", "")
            exp = corrector.correct_number(exp_text) if exp_text else 0

            # Extract and correct level
            level_text = ""
            if isinstance(status_info.get("Level"), list):
                level_text = " ".join(status_info.get("Level", []))
            elif isinstance(status_info.get("Level"), str):
                level_text = status_info.get("Level", "")
            level = corrector.correct_number(level_text) if level_text else 0

            self.log_message(f"Status: {status_text} → {status}", "data")
            self.log_message(f"Time: {time_text} → {time}", "data")
            self.log_message(f"Map: {map_text} → {map_name}", "data")
            self.log_message(f"EXP: {exp_text} → {exp}", "data")
            self.log_message(f"Level: {level_text} → {level}", "data")

            # Process kill list with corrections
            try:
                corrected_kill_list = corrector.correct_kill_data(kill_list)
                kills = len(corrected_kill_list) if corrected_kill_list else 0
            except Exception as kill_error:
                self.log_message(f"Error processing kill list: {str(kill_error)}", "error")
                corrected_kill_list = {}
                kills = 0

            # Format date from folder name
            date_formatted = corrector.correct_date_format("", folder_name)

            # Create raid object with corrected data
            raid = {
                "date": date_formatted,
                "status": status,
                "map": map_name,
                "kills": kills,
                "exp": exp,
                "level": level,
                "time": time,
                "kill_list": corrected_kill_list,
                "folder_name": folder_name
            }

            self.log_message(f"Processed raid data with {kills} kills", "python")
            return raid

        except Exception as e:
            import traceback
            error_msg = f"Error processing OCR data: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            if hasattr(self, 'log_text_edit'):
                self.log_text_edit.append(error_msg)
            return None

    def initialize_eft_path(self):
        """Try to automatically detect and set the EFT logs path if not already set"""
        # Check if a log path is already configured
        saved_log_path = self.settings.value("eft_log_path", "", str)

        # Only attempt auto-detection if no path is configured
        if not saved_log_path:
            try:
                self.log_message("Looking for EFT installation in registry...", "python")
                detected_path = get_eft_logs_path()

                if detected_path and os.path.exists(detected_path):
                    self.settings.setValue("eft_log_path", detected_path)
                    self.log_message(f"EFT logs path automatically set to: {detected_path}", "python")

                    # Save the detected path to the configuration file without restarting
                    # We'll start the process only once later
                    self.write_log_path_to_config_without_restart(detected_path)

                    # If the settings tab is already created, update the text field
                    if hasattr(self, 'log_path_edit'):
                        self.log_path_edit.setText(detected_path)
                        # Update the status indicator too
                        if hasattr(self, 'log_path_status'):
                            self.log_path_status.setText("Log-Pfad konfiguriert ✓")
                            self.log_path_status.setStyleSheet("color: green;")

                    # Start the process only if it's not already running
                    QTimer.singleShot(1500, self.start_csharp_process)
                    return True
                else:
                    # Auto-detection failed, notify the user they need to set the path manually
                    self.log_message("Could not automatically detect EFT logs path.", "warning")
                    self.log_message("Please set the path manually in the Settings tab.", "warning")

                    # Show a message box to inform the user - delayed slightly to ensure UI is ready
                    QTimer.singleShot(1000, lambda: QMessageBox.information(
                        self,
                        "Log Path Configuration Required",
                        "Could not automatically detect the EFT logs path.\n\n"
                        "Please go to the Settings tab and manually set the path to your EFT Logs folder.\n"
                        "Typically this is located at: \n"
                        "C:\\Battlestate Games\\EFT\\Logs\n"
                        "D:\\Battlestate Games\\EFT\\Logs\n"
                        "or similar locations depending on your installation."
                    ))

                    return False
            except Exception as e:
                self.log_message(f"Error during auto-detection: {str(e)}", "error")
                self.log_message("Please set the path manually in the Settings tab.", "warning")
                return False
        else:
            self.log_message(f"Using saved EFT logs path: {saved_log_path}", "python")
            # Start the process only if it's not already running
            QTimer.singleShot(1500, self.start_csharp_process)
            return True

    def closeEvent(self, event):
        # Copy your cleanup code from __del__ here
        if hasattr(self, 'pipe_thread') and self.pipe_thread is not None:
            self.pipe_thread.send_message("STOP")
            self.pipe_thread.stop()
            self.pipe_thread.wait()

        if hasattr(self, 'process') and self.process is not None:
            try:
                self.process.terminate()
            except:
                pass

        # Always call the parent class method
        super().closeEvent(event)
