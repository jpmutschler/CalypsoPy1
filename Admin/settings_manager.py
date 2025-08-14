#!/usr/bin/env python3
"""
settings_manager.py

Environment settings management for CalypsoPy application.
Handles loading, saving, and validating application settings.
"""

import json
import os
import threading
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict, field
from datetime import datetime
import tempfile


@dataclass
class CacheSettings:
    """Cache-related settings"""
    enabled: bool = True
    default_ttl_seconds: int = 300  # 5 minutes
    max_entries: int = 1000
    cleanup_interval_minutes: int = 5
    cache_directory: str = ""  # Empty means use temp directory


@dataclass
class RefreshSettings:
    """Auto-refresh settings for dashboards"""
    enabled: bool = False
    interval_seconds: int = 30
    dashboards: Dict[str, bool] = field(default_factory=lambda: {
        'host': True,
        'link': True,
        'port': False,
        'compliance': False,
        'registers': False,
        'advanced': False,
        'resets': False,
        'firmware': False
    })


@dataclass
class UISettings:
    """User interface settings"""
    theme: str = "dark"  # dark, light
    font_family: str = "Arial"
    font_size: int = 10
    window_width: int = 1200
    window_height: int = 800
    remember_window_position: bool = True
    last_window_x: int = -1
    last_window_y: int = -1
    show_tooltips: bool = True
    show_status_bar: bool = True


@dataclass
class CommunicationSettings:
    """Serial communication settings"""
    default_baudrate: int = 115200
    timeout_seconds: float = 5.0
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0
    command_history_size: int = 100
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR


@dataclass
class DemoSettings:
    """Demo mode settings"""
    enabled_by_default: bool = False
    simulate_delays: bool = True
    random_data_variation: bool = True
    fake_errors: bool = False
    demo_device_name: str = "DEMO-DEVICE-001"


@dataclass
class AppSettings:
    """Main application settings container"""
    version: str = "1.0.0"
    last_modified: str = ""
    cache: CacheSettings = field(default_factory=CacheSettings)
    refresh: RefreshSettings = field(default_factory=RefreshSettings)
    ui: UISettings = field(default_factory=UISettings)
    communication: CommunicationSettings = field(default_factory=CommunicationSettings)
    demo: DemoSettings = field(default_factory=DemoSettings)

    def __post_init__(self):
        """Set last_modified timestamp"""
        self.last_modified = datetime.now().isoformat()


class SettingsManager:
    """
    Thread-safe settings manager with JSON persistence
    """

    def __init__(self, settings_file: Optional[str] = None):
        """
        Initialize settings manager

        Args:
            settings_file: Path to settings file (uses default if None)
        """
        self._lock = threading.RLock()

        # Determine settings file location
        if settings_file is None:
            # Try to use user's application data directory
            if os.name == 'nt':  # Windows
                app_data = os.environ.get('APPDATA', tempfile.gettempdir())
                settings_dir = os.path.join(app_data, 'CalypsoPy')
            else:  # Unix/Linux/Mac
                home_dir = os.path.expanduser('~')
                settings_dir = os.path.join(home_dir, '.calypsopy')

            os.makedirs(settings_dir, exist_ok=True)
            self.settings_file = os.path.join(settings_dir, 'settings.json')
        else:
            self.settings_file = settings_file

        # Initialize settings
        self.settings = AppSettings()
        self._defaults = AppSettings()  # Keep a copy of defaults

        # Load existing settings
        self.load()

    def load(self) -> bool:
        """
        Load settings from file

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            with self._lock:
                if os.path.exists(self.settings_file):
                    with open(self.settings_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # Reconstruct settings object
                    self.settings = self._dict_to_settings(data)
                    return True
                else:
                    # File doesn't exist, use defaults and save
                    self.save()
                    return False

        except Exception as e:
            print(f"Warning: Could not load settings file: {e}")
            # Use defaults on error
            self.settings = AppSettings()
            return False

    def save(self) -> bool:
        """
        Save settings to file

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            with self._lock:
                # Update last modified timestamp
                self.settings.last_modified = datetime.now().isoformat()

                # Convert to dictionary
                data = asdict(self.settings)

                # Write to file atomically
                temp_file = self.settings_file + '.tmp'
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, default=str)

                # Atomic move
                if os.name == 'nt':  # Windows
                    if os.path.exists(self.settings_file):
                        os.remove(self.settings_file)
                    os.rename(temp_file, self.settings_file)
                else:  # Unix/Linux
                    os.rename(temp_file, self.settings_file)

                return True

        except Exception as e:
            print(f"Error: Could not save settings file: {e}")
            return False

    def _dict_to_settings(self, data: Dict[str, Any]) -> AppSettings:
        """Convert dictionary to AppSettings object"""
        # Create settings with defaults first
        settings = AppSettings()

        # Update with loaded data
        if 'version' in data:
            settings.version = data['version']
        if 'last_modified' in data:
            settings.last_modified = data['last_modified']

        # Update cache settings
        if 'cache' in data:
            cache_data = data['cache']
            settings.cache = CacheSettings(
                enabled=cache_data.get('enabled', settings.cache.enabled),
                default_ttl_seconds=cache_data.get('default_ttl_seconds', settings.cache.default_ttl_seconds),
                max_entries=cache_data.get('max_entries', settings.cache.max_entries),
                cleanup_interval_minutes=cache_data.get('cleanup_interval_minutes',
                                                        settings.cache.cleanup_interval_minutes),
                cache_directory=cache_data.get('cache_directory', settings.cache.cache_directory)
            )

        # Update refresh settings
        if 'refresh' in data:
            refresh_data = data['refresh']
            settings.refresh = RefreshSettings(
                enabled=refresh_data.get('enabled', settings.refresh.enabled),
                interval_seconds=refresh_data.get('interval_seconds', settings.refresh.interval_seconds),
                dashboards=refresh_data.get('dashboards', settings.refresh.dashboards)
            )

        # Update UI settings
        if 'ui' in data:
            ui_data = data['ui']
            settings.ui = UISettings(
                theme=ui_data.get('theme', settings.ui.theme),
                font_family=ui_data.get('font_family', settings.ui.font_family),
                font_size=ui_data.get('font_size', settings.ui.font_size),
                window_width=ui_data.get('window_width', settings.ui.window_width),
                window_height=ui_data.get('window_height', settings.ui.window_height),
                remember_window_position=ui_data.get('remember_window_position', settings.ui.remember_window_position),
                last_window_x=ui_data.get('last_window_x', settings.ui.last_window_x),
                last_window_y=ui_data.get('last_window_y', settings.ui.last_window_y),
                show_tooltips=ui_data.get('show_tooltips', settings.ui.show_tooltips),
                show_status_bar=ui_data.get('show_status_bar', settings.ui.show_status_bar)
            )

        # Update communication settings
        if 'communication' in data:
            comm_data = data['communication']
            settings.communication = CommunicationSettings(
                default_baudrate=comm_data.get('default_baudrate', settings.communication.default_baudrate),
                timeout_seconds=comm_data.get('timeout_seconds', settings.communication.timeout_seconds),
                retry_attempts=comm_data.get('retry_attempts', settings.communication.retry_attempts),
                retry_delay_seconds=comm_data.get('retry_delay_seconds', settings.communication.retry_delay_seconds),
                command_history_size=comm_data.get('command_history_size', settings.communication.command_history_size),
                log_level=comm_data.get('log_level', settings.communication.log_level)
            )

        # Update demo settings
        if 'demo' in data:
            demo_data = data['demo']
            settings.demo = DemoSettings(
                enabled_by_default=demo_data.get('enabled_by_default', settings.demo.enabled_by_default),
                simulate_delays=demo_data.get('simulate_delays', settings.demo.simulate_delays),
                random_data_variation=demo_data.get('random_data_variation', settings.demo.random_data_variation),
                fake_errors=demo_data.get('fake_errors', settings.demo.fake_errors),
                demo_device_name=demo_data.get('demo_device_name', settings.demo.demo_device_name)
            )

        return settings

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get a specific setting value

        Args:
            section: Settings section (cache, refresh, ui, communication, demo)
            key: Setting key
            default: Default value if not found

        Returns:
            Setting value or default
        """
        with self._lock:
            section_obj = getattr(self.settings, section, None)
            if section_obj is None:
                return default
            return getattr(section_obj, key, default)

    def set(self, section: str, key: str, value: Any) -> bool:
        """
        Set a specific setting value

        Args:
            section: Settings section
            key: Setting key
            value: New value

        Returns:
            True if set successfully, False otherwise
        """
        try:
            with self._lock:
                section_obj = getattr(self.settings, section, None)
                if section_obj is None:
                    return False

                setattr(section_obj, key, value)
                return True

        except Exception as e:
            print(f"Error setting {section}.{key}: {e}")
            return False

    def reset_to_defaults(self) -> None:
        """Reset all settings to defaults"""
        with self._lock:
            self.settings = AppSettings()

    def reset_section_to_defaults(self, section: str) -> bool:
        """
        Reset a specific section to defaults

        Args:
            section: Section to reset

        Returns:
            True if reset successfully, False otherwise
        """
        try:
            with self._lock:
                if section == 'cache':
                    self.settings.cache = CacheSettings()
                elif section == 'refresh':
                    self.settings.refresh = RefreshSettings()
                elif section == 'ui':
                    self.settings.ui = UISettings()
                elif section == 'communication':
                    self.settings.communication = CommunicationSettings()
                elif section == 'demo':
                    self.settings.demo = DemoSettings()
                else:
                    return False

                return True

        except Exception as e:
            print(f"Error resetting section {section}: {e}")
            return False

    def validate_settings(self) -> Dict[str, list]:
        """
        Validate current settings and return any issues

        Returns:
            Dictionary of validation issues by section
        """
        issues = {}

        # Validate cache settings
        cache_issues = []
        if self.settings.cache.default_ttl_seconds < 1:
            cache_issues.append("TTL must be at least 1 second")
        if self.settings.cache.max_entries < 1:
            cache_issues.append("Max entries must be at least 1")
        if cache_issues:
            issues['cache'] = cache_issues

        # Validate refresh settings
        refresh_issues = []
        if self.settings.refresh.interval_seconds < 5:
            refresh_issues.append("Refresh interval must be at least 5 seconds")
        if refresh_issues:
            issues['refresh'] = refresh_issues

        # Validate UI settings
        ui_issues = []
        if self.settings.ui.font_size < 6 or self.settings.ui.font_size > 72:
            ui_issues.append("Font size must be between 6 and 72")
        if self.settings.ui.window_width < 640:
            ui_issues.append("Window width must be at least 640 pixels")
        if self.settings.ui.window_height < 480:
            ui_issues.append("Window height must be at least 480 pixels")
        if ui_issues:
            issues['ui'] = ui_issues

        # Validate communication settings
        comm_issues = []
        if self.settings.communication.timeout_seconds < 0.1:
            comm_issues.append("Timeout must be at least 0.1 seconds")
        if self.settings.communication.retry_attempts < 0:
            comm_issues.append("Retry attempts cannot be negative")
        if comm_issues:
            issues['communication'] = comm_issues

        return issues

    def get_settings_summary(self) -> Dict[str, Any]:
        """Get summary of current settings for display"""
        return {
            'settings_file': self.settings_file,
            'last_modified': self.settings.last_modified,
            'version': self.settings.version,
            'sections': {
                'cache': {
                    'enabled': self.settings.cache.enabled,
                    'ttl_seconds': self.settings.cache.default_ttl_seconds,
                    'max_entries': self.settings.cache.max_entries
                },
                'refresh': {
                    'enabled': self.settings.refresh.enabled,
                    'interval_seconds': self.settings.refresh.interval_seconds,
                    'active_dashboards': sum(1 for enabled in self.settings.refresh.dashboards.values() if enabled)
                },
                'ui': {
                    'theme': self.settings.ui.theme,
                    'font': f"{self.settings.ui.font_family} {self.settings.ui.font_size}pt",
                    'window_size': f"{self.settings.ui.window_width}x{self.settings.ui.window_height}"
                },
                'communication': {
                    'baudrate': self.settings.communication.default_baudrate,
                    'timeout': self.settings.communication.timeout_seconds,
                    'log_level': self.settings.communication.log_level
                }
            }
        }


# Usage example and testing
if __name__ == "__main__":
    print("Testing SettingsManager...")

    # Test settings manager
    settings_mgr = SettingsManager()

    print(f"Settings file: {settings_mgr.settings_file}")

    # Test getting values
    cache_enabled = settings_mgr.get('cache', 'enabled')
    refresh_interval = settings_mgr.get('refresh', 'interval_seconds')
    print(f"Cache enabled: {cache_enabled}")
    print(f"Refresh interval: {refresh_interval}")

    # Test setting values
    settings_mgr.set('cache', 'default_ttl_seconds', 600)
    settings_mgr.set('refresh', 'enabled', True)

    # Test validation
    issues = settings_mgr.validate_settings()
    print(f"Validation issues: {issues}")

    # Test summary
    summary = settings_mgr.get_settings_summary()
    print(f"Settings summary: {summary}")

    # Test save
    saved = settings_mgr.save()
    print(f"Settings saved: {saved}")

    print("Settings manager test completed!")