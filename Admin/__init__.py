#!/usr/bin/env python3
"""
Admin/__init__.py

Admin module for CalypsoPy - Contains administrative and system management components

This module provides:
- Advanced response handling for fragmented device responses
- Data caching and persistence management
- Enhanced system information parsing
- Settings management and configuration
- Settings UI components

Author: Serial Cables Development Team
"""

# Version info
__version__ = "1.5.1"
__author__ = "Serial Cables Development Team"

# Import main classes for easy access
try:
    from .advanced_response_handler import (
        AdvancedResponseHandler,
        ResponseState,
        ResponsePattern,
        ResponseBuffer
    )

    print("DEBUG: Advanced Response Handler imported successfully")
except ImportError as e:
    print(f"WARNING: Could not import Advanced Response Handler: {e}")
    AdvancedResponseHandler = None

try:
    from .cache_manager import (
        DeviceDataCache,
        CacheEntry
    )

    print("DEBUG: Cache Manager imported successfully")
except ImportError as e:
    print(f"WARNING: Could not import Cache Manager: {e}")
    DeviceDataCache = None

try:
    from .enhanced_sysinfo_parser import EnhancedSystemInfoParser

    print("DEBUG: Enhanced Sysinfo Parser imported successfully")
except ImportError as e:
    print(f"WARNING: Could not import Enhanced Sysinfo Parser: {e}")
    EnhancedSystemInfoParser = None

try:
    from .settings_manager import (
        SettingsManager,
        CacheSettings,
        RefreshSettings,
        UISettings,
        CommunicationSettings,
        DemoSettings,
        AppSettings
    )

    print("DEBUG: Settings Manager imported successfully")
except ImportError as e:
    print(f"WARNING: Could not import Settings Manager: {e}")
    SettingsManager = None

try:
    from .settings_ui import SettingsDialog

    print("DEBUG: Settings UI imported successfully")
except ImportError as e:
    print(f"WARNING: Could not import Settings UI: {e}")
    SettingsDialog = None

try:
    from .debug_config import (
        debug_print,
        debug_error,
        debug_warning,
        debug_info,
        is_debug_enabled,
        get_debug_status,
        toggle_debug,
        enable_debug,
        disable_debug
    )

    print("DEBUG: Debug Config imported successfully")
except ImportError as e:
    print(f"WARNING: Could not import Debug Config: {e}")
    debug_print = None

# Module metadata
__all__ = [
    # Response Handler
    'AdvancedResponseHandler',
    'ResponseState',
    'ResponsePattern',
    'ResponseBuffer',

    # Cache Management
    'DeviceDataCache',
    'CacheEntry',

    # System Info Parsing
    'EnhancedSystemInfoParser',

    # Settings Management
    'SettingsManager',
    'CacheSettings',
    'RefreshSettings',
    'UISettings',
    'CommunicationSettings',
    'DemoSettings',
    'AppSettings',

    # Settings UI
    'SettingsDialog',
    # Note: CacheViewerDialog is a nested class inside SettingsDialog

    # Debug System
    'debug_print',
    'debug_error',
    'debug_warning',
    'debug_info',
    'is_debug_enabled',
    'get_debug_status',
    'toggle_debug',
    'enable_debug',
    'disable_debug'
]


def get_admin_info():
    """Get information about the Admin module"""
    return {
        'version': __version__,
        'author': __author__,
        'components': [
            'Advanced Response Handler',
            'Cache Manager',
            'Enhanced Sysinfo Parser',
            'Settings Manager',
            'Settings UI'
        ],
        'available_classes': [cls for cls in __all__ if globals().get(cls) is not None]
    }


def check_admin_dependencies():
    """Check if all admin components are available"""
    missing = []
    for component in __all__:
        if globals().get(component) is None:
            missing.append(component)

    if missing:
        print(f"WARNING: Missing admin components: {missing}")
        return False
    else:
        print("DEBUG: All admin components loaded successfully")
        return True


# Initialize admin module
print(f"DEBUG: Admin module initialized (version {__version__})")