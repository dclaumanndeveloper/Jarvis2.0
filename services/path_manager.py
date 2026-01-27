import sys
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class PathManager:
    APP_NAME = "Jarvis2.0"

    @staticmethod
    def get_app_data_dir() -> Path:
        """Get the application data directory."""
        if sys.platform == "win32":
            base_dir = os.environ.get("APPDATA")
            if not base_dir:
                 base_dir = os.path.expanduser("~\\AppData\\Roaming")
        elif sys.platform == "darwin":
            base_dir = os.path.expanduser("~/Library/Application Support")
        else:
            base_dir = os.path.expanduser("~/.local/share")

        app_dir = Path(base_dir) / PathManager.APP_NAME

        try:
            app_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            # Fallback to local directory if permission denied
            print(f"Failed to create app data dir at {app_dir}: {e}")
            app_dir = Path.cwd() / "data"
            app_dir.mkdir(parents=True, exist_ok=True)

        return app_dir

    @staticmethod
    def get_log_file() -> Path:
        return PathManager.get_app_data_dir() / "jarvis_unified.log"

    @staticmethod
    def get_database_path() -> Path:
        return PathManager.get_app_data_dir() / "jarvis_data.db"

    @staticmethod
    def get_voice_profile_db() -> Path:
        return PathManager.get_app_data_dir() / "jarvis_voice_profiles.db"

    @staticmethod
    def get_learning_dir() -> Path:
        learning_dir = PathManager.get_app_data_dir() / "learning_data"
        learning_dir.mkdir(exist_ok=True)
        return learning_dir

    @staticmethod
    def get_resource_path(relative_path: str) -> Path:
        """Get absolute path to resource, works for dev and for PyInstaller"""
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = Path(sys._MEIPASS)
        except AttributeError:
            base_path = Path.cwd()

        return base_path / relative_path
