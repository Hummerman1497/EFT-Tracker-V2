import sys
import os
from PyQt5.QtWidgets import (QApplication)
from PyQt5.QtCore import QThread, pyqtSignal
import time
from datetime import datetime

from src.ui.EFTTrackerMainWindow import EFTTracker
from src.AssetManager import AssetManager


class CSharpOutputReader(QThread):
    """
    Thread to read output from the C# LogWatcher process
    """
    output_received = pyqtSignal(str)

    def __init__(self, process):
        super().__init__()
        self.process = process
        self.running = True
        self.buffer = bytearray()
        self.app = None  # Reference to main application for screenshot triggering

    def run(self):
        """
        Reads data from the process output pipe in a safe way
        """
        while self.running:
            try:
                # Read single bytes from the pipe instead of lines
                if not hasattr(self.process.stdout, 'read'):
                    self.output_received.emit("Process doesn't have a readable stdout property")
                    break

                # Try to read a single byte
                byte = self.process.stdout.read(1)

                # If nothing was read, check if the process is still running
                if not byte:
                    if self.process.poll() is not None:
                        # Process was terminated
                        self.output_received.emit("Process was terminated")
                        break
                    # Wait briefly and try again
                    time.sleep(0.01)
                    continue

                # Add the byte to the buffer
                self.buffer.append(byte[0])  # byte is a single byte in a byte array

                # Check if a complete line (with line break) is in the buffer
                if byte == b'\n' or len(self.buffer) > 4096:
                    # Try to decode the buffer - try different encodings
                    line = None
                    for encoding in ['utf-8', 'cp1252', 'latin1', 'ascii']:
                        try:
                            if encoding == 'ascii':
                                # For ASCII, ignore faulty characters
                                line = self.buffer.decode(encoding, errors='ignore').strip()
                            else:
                                line = self.buffer.decode(encoding).strip()
                            break  # If decoding was successful, break the loop
                        except UnicodeDecodeError:
                            continue  # Try the next encoding

                    # If decoding failed with all encodings, use Latin-1
                    if line is None:
                        line = self.buffer.decode('latin1', errors='replace').strip()

                    # Send the line if it's not empty
                    if line:
                        self.output_received.emit(line)

                        # Process specific commands from the LogWatcher
                        if "TRIGGER_SCREENSHOT" in line:
                            self.output_received.emit("[PYTHON] CSharpOutputReader: Trigger detected in backend.log")
                            if self.app is not None:
                                folder_name = datetime.now().strftime("%d-%m-%Y_%H-%M")
                                self.app.screenshot_script(folder_name)

                    # Reset buffer
                    self.buffer.clear()

            except Exception as e:
                # Output a message in case of error and reset the buffer
                error_msg = str(e)
                self.output_received.emit(f"Error reading process output: {error_msg}")
                self.buffer.clear()
                time.sleep(0.1)  # Short pause to reduce CPU load

    def set_application(self, app):
        """Sets a reference to the main application for communication"""
        self.app = app

    def stop(self):
        self.running = False
        # Wait until the thread is finished
        if self.isRunning():
            self.wait(1000)  # Wait max. 1 second


"""
Entry point for the EFT Tracker application.

This script initializes and starts the PyQt-based GUI application. It sets up 
the main event loop, loads the application icon (if available), and displays 
the main window.

Workflow:
1. Creates a QApplication instance.
2. Initializes the AssetManager to manage file paths.
3. Retrieves and sets the application icon if it exists.
4. Instantiates and displays the main window (EFTTracker).
5. Starts the PyQt event loop to handle user interactions.

Usage:
    Run this script directly to launch the EFT Tracker application.

Notes:
- Ensure that all required dependencies (PyQt5, AssetManager, EFTTracker) are installed.
- The application icon should be located in the appropriate assets directory.

Author: Janis Groeger
Date: 11.03.2025
"""
if __name__ == "__main__":
    app = QApplication(sys.argv)
    asset_manager = AssetManager()
    app_icon_path = asset_manager.get_icon_path("Ushanka_icon.ico")  # Icon-Pfad anpassen
    if os.path.exists(app_icon_path):
        from PyQt5.QtGui import QIcon

        app_icon = QIcon(app_icon_path)
        app.setWindowIcon(app_icon)

    window = EFTTracker()
    window.show()
    sys.exit(app.exec_())
