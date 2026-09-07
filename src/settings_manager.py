"""
Settings manager for Localhost Radar.
Handles persistence of settings and favorites.
"""

import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path


class SettingsManager:
    """Manages application settings persistence."""
    
    def __init__(self, app_data_dir: str = None):
        # Determine app data directory
        if app_data_dir is None:
            app_data_dir = os.environ.get(
                "APPDATA", os.path.expanduser("~")
            )
        self.settings_dir = Path(app_data_dir) / "LocalhostRadar"
        self.settings_dir.mkdir(parents=True, exist_ok=True)
        self.settings_file = self.settings_dir / "settings.json"
        self.log_file = self.settings_dir / "localhost-radar.log"
    
    def _load(self) -> Dict[str, Any]:
        """Load settings from file."""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return self._get_defaults()
        return self._get_defaults()
    
    def _get_defaults(self) -> Dict[str, Any]:
        """Get default settings."""
        return {
            "auto_refresh_interval": 10000,  # 10 seconds
            "auto_refresh_enabled": True,
            "collapse_duplicate_bindings": True,
            "show_system_processes": True,
            "confirm_termination": True,
            "favorite_ports": [5173, 3000, 3032, 5432, 8080],
            "theme": "dark",
        }
    
    def save(self, settings: Dict[str, Any]) -> None:
        """Save settings to file."""
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
        except IOError as e:
            # Log error but don't crash
            print(f"Error saving settings: {e}")
    
    def load(self) -> Dict[str, Any]:
        """Load settings, returning defaults if file doesn't exist."""
        return self._load()
    
    def get_favorite_ports(self) -> List[int]:
        """Get list of favorite port numbers."""
        defaults = self._get_defaults()
        data = self._load()
        ports = data.get("favorite_ports", defaults["favorite_ports"])
        return [int(p) for p in ports]
    
    def add_favorite_port(self, port: int) -> None:
        """Add a port to favorites."""
        data = self._load()
        favorites = data.get("favorite_ports", [])
        if port not in favorites:
            favorites.append(port)
            data["favorite_ports"] = favorites
            self.save(data)
    
    def remove_favorite_port(self, port: int) -> None:
        """Remove a port from favorites."""
        data = self._load()
        favorites = data.get("favorite_ports", [])
        if port in favorites:
            favorites.remove(port)
            data["favorite_ports"] = favorites
            self.save(data)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a specific setting value."""
        data = self._load()
        return data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a specific setting value."""
        data = self._load()
        data[key] = value
        self.save(data)
    
    @property
    def log_path(self) -> str:
        """Get the log file path."""
        return str(self.log_file)
