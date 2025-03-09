import winreg
import os


def find_eft_installation_path():
    """
    Attempts to find the Escape from Tarkov installation path by searching
    the Windows registry.

    Returns:
        str: The path to the EFT logs directory if found, None otherwise
    """
    try:
        # Common registry paths where game launchers register their games
        registry_paths = [
            # BSG Launcher path (most likely)
            r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\EscapeFromTarkov",
            # Standard uninstall paths
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\EscapeFromTarkov",
            # Alternative BSG Launcher path
            r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\{B0FDA062-7581-4D67-B085-C4E7C358CADE}_is1",
        ]

        # Common installation paths to check if registry fails
        common_install_paths = [
            r"C:\Battlestate Games\EFT",
            r"C:\Games\Escape from Tarkov",
            r"C:\Program Files\Battlestate Games\EFT",
            r"C:\Program Files (x86)\Battlestate Games\EFT",
            r"D:\Battlestate Games\EFT",
            r"D:\Games\Escape from Tarkov",
            r"E:\Battlestate Games\EFT",
            r"E:\Games\Escape from Tarkov",
        ]

        # Try to find the installation path in the registry
        for registry_path in registry_paths:
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_path)
                install_location, _ = winreg.QueryValueEx(key, "InstallLocation")
                winreg.CloseKey(key)

                if install_location and os.path.exists(install_location):
                    # Check if the Logs directory exists
                    logs_path = os.path.join(install_location, "Logs")
                    if os.path.exists(logs_path):
                        return logs_path

                    # If no Logs directory, return the installation path
                    return install_location
            except (WindowsError, FileNotFoundError):
                continue

        # If registry search fails, check common installation paths
        for install_path in common_install_paths:
            logs_path = os.path.join(install_path, "Logs")
            if os.path.exists(logs_path):
                return logs_path

            # Check if the base path exists
            if os.path.exists(install_path):
                return install_path

        # If all attempts fail, return None
        return None

    except Exception as e:
        print(f"Error searching for EFT installation: {e}")
        return None


def get_eft_logs_path():
    """
    Get the path to the EFT logs directory.
    First tries to find the installation path, then appends 'Logs' if needed.

    Returns:
        str: Path to the logs directory, or None if not found
    """
    install_path = find_eft_installation_path()

    if not install_path:
        return None

    # Check if the found path already points to the Logs directory
    if os.path.basename(install_path) == "Logs":
        return install_path

    # Otherwise, append the Logs directory
    logs_path = os.path.join(install_path, "Logs")
    if os.path.exists(logs_path):
        return logs_path

    # If no Logs directory found, return the base path
    return install_path