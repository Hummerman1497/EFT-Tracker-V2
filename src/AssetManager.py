import os
import sys


class AssetManager:
    def __init__(self):
        # Determine if we're running from executable or source
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            self.base_path = sys._MEIPASS
            self.running_from_exe = True
        except Exception:
            self.base_path = os.path.abspath(os.path.dirname(__file__))
            self.running_from_exe = False

        # Log the base path for debugging
        print(f"Asset base path: {self.base_path}")

        # Define asset directories
        self.asset_dirs = {
            "maps": os.path.join(self.base_path, "../Assets", "Maps"),
            "icons": os.path.join(self.base_path, "../Assets", "Icons"),
            "fonts": os.path.join(self.base_path, "../Assets"),
            "csharp": os.path.join(self.base_path, "../Assets", "C-Sharp"),
            "images": os.path.join(self.base_path, "../Assets"),
        }

        # Verify directories exist
        for dir_name, dir_path in self.asset_dirs.items():
            if not os.path.exists(dir_path):
                print(f"Warning: Asset directory '{dir_name}' not found at: {dir_path}")

    def get_path_to_asset(self, asset_type, filename):
        if asset_type not in self.asset_dirs:
            print(f"Warning: Unknown asset type '{asset_type}'")
            return os.path.join(self.base_path, "../Assets", filename)

        full_path = os.path.join(self.asset_dirs[asset_type], filename)

        # Verify file exists
        if not os.path.exists(full_path):
            print(f"Warning: Asset file not found: {full_path}")

        return full_path

    def get_map_path(self, map_name, suffix="_Banner.png"):
        return self.get_path_to_asset("maps", f"{map_name}{suffix}")

    def get_icon_path(self, icon_name):
        return self.get_path_to_asset("icons", icon_name)

    def get_font_path(self, font_name):
        return self.get_path_to_asset("fonts", font_name)

    def get_csharp_path(self, exe_name):
        return self.get_path_to_asset("csharp", exe_name)
