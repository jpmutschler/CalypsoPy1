#!/usr/bin/env python3
"""
Admin/debug_config.py

Centralized Debug Configuration for CalypsoPy
Control all debug output from this single file

FIXED VERSION: Added missing standalone convenience functions
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum


class DebugLevel(Enum):
    """Debug levels for CalypsoPy"""
    NONE = 0  # No debug output
    ERROR = 1  # Errors only
    WARNING = 2  # Warnings and errors
    INFO = 3  # Info, warnings, and errors
    DEBUG = 4  # Debug, info, warnings, and errors
    VERBOSE = 5  # All output including verbose tracing


class DebugConfig:
    """
    Centralized debug configuration for CalypsoPy
    """

    def __init__(self):
        """Initialize debug configuration"""
        # Default settings
        self.enabled = True
        self.level = DebugLevel.INFO
        self.log_to_file = True
        self.log_to_console = True
        self.timestamp_format = '%Y-%m-%d %H:%M:%S.%f'

        # Component-specific debug flags
        self.components = {
            'main': True,
            'port_config': True,
            'host_card': True,
            'cache_manager': True,
            'sysinfo_parser': True,
            'demo_mode': True,
            'cli_interface': True,
            'settings': True,
            'ui_components': True
        }

        # File logging setup
        self.log_directory = 'logs'
        self.log_filename = f'calypsopy_debug_{datetime.now().strftime("%Y%m%d")}.log'

        # Initialize logging
        self._setup_logging()

        # Load configuration from environment variables
        self._load_from_environment()

    def _setup_logging(self):
        """Setup logging configuration"""
        # Create logs directory if it doesn't exist
        if self.log_to_file:
            os.makedirs(self.log_directory, exist_ok=True)
            log_path = os.path.join(self.log_directory, self.log_filename)

        # Configure logging
        log_level = logging.DEBUG if self.level.value >= DebugLevel.DEBUG.value else logging.INFO

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%H:%M:%S'
        )

        # Setup file logging
        if self.log_to_file:
            file_handler = logging.FileHandler(log_path)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logging.getLogger().addHandler(file_handler)

        # Setup console logging
        if self.log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)
            console_handler.setFormatter(formatter)
            logging.getLogger().addHandler(console_handler)

        logging.getLogger().setLevel(log_level)

    def _load_from_environment(self):
        """Load debug settings from environment variables"""
        # Enable/disable debug
        if 'CALYPSOPY_DEBUG' in os.environ:
            self.enabled = os.environ['CALYPSOPY_DEBUG'].lower() in ('true', '1', 'yes', 'on')

        # Set debug level
        if 'CALYPSOPY_DEBUG_LEVEL' in os.environ:
            level_str = os.environ['CALYPSOPY_DEBUG_LEVEL'].upper()
            try:
                self.level = DebugLevel[level_str]
            except KeyError:
                print(f"Warning: Invalid debug level '{level_str}', using INFO")
                self.level = DebugLevel.INFO

        # File logging
        if 'CALYPSOPY_LOG_FILE' in os.environ:
            self.log_to_file = os.environ['CALYPSOPY_LOG_FILE'].lower() in ('true', '1', 'yes', 'on')

        # Console logging
        if 'CALYPSOPY_LOG_CONSOLE' in os.environ:
            self.log_to_console = os.environ['CALYPSOPY_LOG_CONSOLE'].lower() in ('true', '1', 'yes', 'on')

    def is_enabled(self, component: str = 'main') -> bool:
        """Check if debug is enabled for a component"""
        if not self.enabled:
            return False
        return self.components.get(component, True)

    def should_log(self, level: DebugLevel, component: str = 'main') -> bool:
        """Check if message should be logged based on level and component"""
        return (self.enabled and
                self.is_enabled(component) and
                level.value <= self.level.value)

    def log(self, message: str, level: DebugLevel = DebugLevel.INFO,
            component: str = 'main', prefix: str = '') -> None:
        """Log a debug message"""
        if not self.should_log(level, component):
            return

        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]  # Include milliseconds

        # Create prefix
        level_prefix = f"[{level.name}]"
        component_prefix = f"[{component.upper()}]" if component != 'main' else ""
        custom_prefix = f"[{prefix}]" if prefix else ""

        # Format message
        formatted_message = f"{timestamp} {level_prefix} {component_prefix} {custom_prefix} {message}"

        # Output based on level
        if level == DebugLevel.ERROR:
            logging.error(formatted_message)
        elif level == DebugLevel.WARNING:
            logging.warning(formatted_message)
        elif level == DebugLevel.INFO:
            logging.info(formatted_message)
        else:
            logging.debug(formatted_message)

    def error(self, message: str, component: str = 'main', prefix: str = '') -> None:
        """Log an error message"""
        self.log(message, DebugLevel.ERROR, component, prefix)

    def warning(self, message: str, component: str = 'main', prefix: str = '') -> None:
        """Log a warning message"""
        self.log(message, DebugLevel.WARNING, component, prefix)

    def info(self, message: str, component: str = 'main', prefix: str = '') -> None:
        """Log an info message"""
        self.log(message, DebugLevel.INFO, component, prefix)

    def debug(self, message: str, component: str = 'main', prefix: str = '') -> None:
        """Log a debug message"""
        self.log(message, DebugLevel.DEBUG, component, prefix)

    def verbose(self, message: str, component: str = 'main', prefix: str = '') -> None:
        """Log a verbose message"""
        self.log(message, DebugLevel.VERBOSE, component, prefix)

    def port_debug(self, message: str, prefix: str = '') -> None:
        """Debug logging specifically for port configuration"""
        self.debug(message, 'port_config', prefix)

    def host_debug(self, message: str, prefix: str = '') -> None:
        """Debug logging specifically for host card info"""
        self.debug(message, 'host_card', prefix)

    def cache_debug(self, message: str, prefix: str = '') -> None:
        """Debug logging specifically for cache operations"""
        self.debug(message, 'cache_manager', prefix)

    def parser_debug(self, message: str, prefix: str = '') -> None:
        """Debug logging specifically for sysinfo parsing"""
        self.debug(message, 'sysinfo_parser', prefix)

    def demo_debug(self, message: str, prefix: str = '') -> None:
        """Debug logging specifically for demo mode"""
        self.debug(message, 'demo_mode', prefix)

    def cli_debug(self, message: str, prefix: str = '') -> None:
        """Debug logging specifically for CLI operations"""
        self.debug(message, 'cli_interface', prefix)

    def enable_component(self, component: str) -> None:
        """Enable debug for a specific component"""
        self.components[component] = True
        self.info(f"Debug enabled for component: {component}")

    def disable_component(self, component: str) -> None:
        """Disable debug for a specific component"""
        self.components[component] = False
        self.info(f"Debug disabled for component: {component}")

    def set_level(self, level: DebugLevel) -> None:
        """Set the global debug level"""
        old_level = self.level
        self.level = level
        self.info(f"Debug level changed from {old_level.name} to {level.name}")

        # Update logging level
        log_level = logging.DEBUG if level.value >= DebugLevel.DEBUG.value else logging.INFO
        logging.getLogger().setLevel(log_level)

    def get_status(self) -> Dict[str, Any]:
        """Get current debug configuration status"""
        return {
            'enabled': self.enabled,
            'level': self.level.name,
            'log_to_file': self.log_to_file,
            'log_to_console': self.log_to_console,
            'log_directory': self.log_directory,
            'log_filename': self.log_filename,
            'components': self.components.copy()
        }

    def print_status(self) -> None:
        """Print current debug configuration status"""
        status = self.get_status()
        print("\n" + "=" * 50)
        print("CalypsoPy Debug Configuration")
        print("=" * 50)
        print(f"Enabled: {status['enabled']}")
        print(f"Level: {status['level']}")
        print(f"Log to File: {status['log_to_file']}")
        print(f"Log to Console: {status['log_to_console']}")

        if status['log_to_file']:
            log_path = os.path.join(status['log_directory'], status['log_filename'])
            print(f"Log File: {log_path}")

        print("\nComponent Status:")
        for component, enabled in status['components'].items():
            status_str = "✅ ENABLED" if enabled else "❌ DISABLED"
            print(f"  {component:15}: {status_str}")
        print("=" * 50 + "\n")


# Global debug instance
debug = DebugConfig()


# ==============================================================================
# STANDALONE CONVENIENCE FUNCTIONS - THESE WERE MISSING!
# ==============================================================================
# These functions provide the interface that main.py expects to import

def debug_print(message: str, component: str = 'main', prefix: str = '') -> None:
    """
    Standard debug_print function used throughout CalypsoPy
    This provides backward compatibility for existing code
    """
    debug.debug(message, component, prefix)


def debug_error(message: str, component: str = 'main', prefix: str = '') -> None:
    """
    Standard debug_error function used throughout CalypsoPy
    This provides backward compatibility for existing code
    """
    debug.error(message, component, prefix)


def debug_warning(message: str, component: str = 'main', prefix: str = '') -> None:
    """
    Standard debug_warning function used throughout CalypsoPy
    This provides backward compatibility for existing code
    """
    debug.warning(message, component, prefix)


def debug_info(message: str, component: str = 'main', prefix: str = '') -> None:
    """
    Standard debug_info function used throughout CalypsoPy
    This provides backward compatibility for existing code
    """
    debug.info(message, component, prefix)


def is_debug_enabled(component: str = 'main') -> bool:
    """Check if debug is enabled for a component"""
    return debug.is_enabled(component)


def get_debug_status() -> Dict[str, Any]:
    """Get current debug status"""
    return debug.get_status()


def toggle_debug() -> None:
    """Toggle debug on/off"""
    debug.enabled = not debug.enabled
    status = "enabled" if debug.enabled else "disabled"
    print(f"Debug {status}")


def enable_debug() -> None:
    """Enable debug output"""
    debug.enabled = True
    print("Debug enabled")


def disable_debug() -> None:
    """Disable debug output"""
    debug.enabled = False
    print("Debug disabled")


# ==============================================================================
# ADDITIONAL CONVENIENCE FUNCTIONS
# ==============================================================================

def debug_enabled(component: str = 'main') -> bool:
    """Check if debug is enabled"""
    return debug.is_enabled(component)


def log_error(message: str, component: str = 'main', prefix: str = '') -> None:
    """Log error message"""
    debug.error(message, component, prefix)


def log_warning(message: str, component: str = 'main', prefix: str = '') -> None:
    """Log warning message"""
    debug.warning(message, component, prefix)


def log_info(message: str, component: str = 'main', prefix: str = '') -> None:
    """Log info message"""
    debug.info(message, component, prefix)


def log_debug(message: str, component: str = 'main', prefix: str = '') -> None:
    """Log debug message"""
    debug.debug(message, component, prefix)


def log_verbose(message: str, component: str = 'main', prefix: str = '') -> None:
    """Log verbose message"""
    debug.verbose(message, component, prefix)


# Component-specific convenience functions
def port_debug(message: str, prefix: str = '') -> None:
    """Port configuration debug logging"""
    debug.port_debug(message, prefix)


def host_debug(message: str, prefix: str = '') -> None:
    """Host card debug logging"""
    debug.host_debug(message, prefix)


def cache_debug(message: str, prefix: str = '') -> None:
    """Cache manager debug logging"""
    debug.cache_debug(message, prefix)


def parser_debug(message: str, prefix: str = '') -> None:
    """Parser debug logging"""
    debug.parser_debug(message, prefix)


def demo_debug(message: str, prefix: str = '') -> None:
    """Demo mode debug logging"""
    debug.demo_debug(message, prefix)


def cli_debug(message: str, prefix: str = '') -> None:
    """CLI debug logging"""
    debug.cli_debug(message, prefix)


# Environment variable configuration examples:
# export CALYPSOPY_DEBUG=true
# export CALYPSOPY_DEBUG_LEVEL=DEBUG
# export CALYPSOPY_LOG_FILE=true
# export CALYPSOPY_LOG_CONSOLE=true


if __name__ == "__main__":
    # Test the debug configuration
    print("Testing Debug Configuration...")

    debug.print_status()

    # Test different log levels
    debug.error("This is an error message", "test")
    debug.warning("This is a warning message", "test")
    debug.info("This is an info message", "test")
    debug.debug("This is a debug message", "test")
    debug.verbose("This is a verbose message", "test")

    # Test component-specific logging
    port_debug("Testing port configuration debug")
    host_debug("Testing host card debug")
    cache_debug("Testing cache debug")

    # Test standalone functions
    print("\nTesting standalone functions...")
    debug_print("Testing debug_print function")
    debug_error("Testing debug_error function")
    debug_info("Testing debug_info function")
    debug_warning("Testing debug_warning function")

    print("Debug configuration test completed!")