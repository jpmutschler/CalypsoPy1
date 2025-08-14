#!/usr/bin/env python3
"""
Admin/debug_config.py

Centralized Debug Configuration for CalypsoPy
Control all debug output from this single file

Place this file in: Admin/debug_config.py
"""

# ===================================================================
# 🔧 MAIN DEBUG CONTROL - CHANGE THIS TO ENABLE/DISABLE DEBUG
# ===================================================================

DEBUG_ENABLED = True  # Set to False to disable ALL debug messages

# ===================================================================
# 📊 GRANULAR DEBUG CONTROLS (optional - for fine-tuning)
# ===================================================================

# You can enable/disable specific debug categories
DEBUG_CATEGORIES = {
    'response_handler': True,  # Advanced Response Handler debug
    'cache_manager': True,  # Cache operations debug
    'serial_cli': True,  # Serial communication debug
    'sysinfo_parser': True,  # System info parsing debug
    'settings': True,  # Settings management debug
    'ui': True,  # UI operations debug
    'demo_mode': True,  # Demo mode debug
    'host_card': True,  # Host card info debug
    'queue_monitor': True,  # Queue monitoring debug
    'connection': True,  # Connection debug
}


# ===================================================================
# 🎯 DEBUG FUNCTIONS - USE THESE INSTEAD OF DIRECT PRINT
# ===================================================================

def debug_print(message, category='general'):
    """
    Centralized debug print function

    Args:
        message: Debug message to print
        category: Debug category (optional)
    """
    if DEBUG_ENABLED and DEBUG_CATEGORIES.get(category, True):
        print(f"DEBUG[{category.upper()}]: {message}")


def debug_error(message, category='general'):
    """Print error debug message (always shown if DEBUG_ENABLED)"""
    if DEBUG_ENABLED:
        print(f"ERROR[{category.upper()}]: {message}")


def debug_warning(message, category='general'):
    """Print warning debug message (always shown if DEBUG_ENABLED)"""
    if DEBUG_ENABLED:
        print(f"WARNING[{category.upper()}]: {message}")


def debug_info(message, category='general'):
    """Print info debug message"""
    if DEBUG_ENABLED and DEBUG_CATEGORIES.get(category, True):
        print(f"INFO[{category.upper()}]: {message}")


# ===================================================================
# 🔍 DEBUG STATUS FUNCTIONS
# ===================================================================

def is_debug_enabled(category='general'):
    """Check if debug is enabled for a category"""
    return DEBUG_ENABLED and DEBUG_CATEGORIES.get(category, True)


def get_debug_status():
    """Get current debug configuration status"""
    return {
        'debug_enabled': DEBUG_ENABLED,
        'active_categories': [cat for cat, enabled in DEBUG_CATEGORIES.items() if enabled],
        'total_categories': len(DEBUG_CATEGORIES)
    }


def print_debug_status():
    """Print current debug status (useful for startup)"""
    if DEBUG_ENABLED:
        print("=" * 50)
        print("🔧 DEBUG CONFIGURATION")
        print("=" * 50)
        print(f"Main Debug: {'ENABLED' if DEBUG_ENABLED else 'DISABLED'}")
        print(f"Active Categories: {len([c for c in DEBUG_CATEGORIES.values() if c])}/{len(DEBUG_CATEGORIES)}")

        if DEBUG_ENABLED:
            print("\nActive Debug Categories:")
            for category, enabled in DEBUG_CATEGORIES.items():
                status = "✅" if enabled else "❌"
                print(f"  {status} {category}")

        print("=" * 50)
        print("To disable debug: Set DEBUG_ENABLED = False in debug_config.py")
        print("=" * 50)
    else:
        print("DEBUG: Disabled (Enable in debug_config.py)")


# ===================================================================
# 🎛️ RUNTIME DEBUG CONTROL (optional advanced features)
# ===================================================================

def enable_debug():
    """Enable debug at runtime"""
    global DEBUG_ENABLED
    DEBUG_ENABLED = True
    print("DEBUG: Enabled at runtime")


def disable_debug():
    """Disable debug at runtime"""
    global DEBUG_ENABLED
    DEBUG_ENABLED = False
    print("DEBUG: Disabled at runtime")


def toggle_debug():
    """Toggle debug state"""
    global DEBUG_ENABLED
    DEBUG_ENABLED = not DEBUG_ENABLED
    print(f"DEBUG: {'Enabled' if DEBUG_ENABLED else 'Disabled'}")


def enable_category(category):
    """Enable debug for specific category"""
    if category in DEBUG_CATEGORIES:
        DEBUG_CATEGORIES[category] = True
        debug_print(f"Category '{category}' enabled", 'config')


def disable_category(category):
    """Disable debug for specific category"""
    if category in DEBUG_CATEGORIES:
        DEBUG_CATEGORIES[category] = False
        debug_print(f"Category '{category}' disabled", 'config')


# ===================================================================
# 📝 USAGE EXAMPLES
# ===================================================================

"""
USAGE EXAMPLES:

1. Basic usage in any file:
   from debug_config import debug_print, debug_error
   debug_print("This is a debug message")
   debug_error("This is an error message")

2. Category-specific usage:
   debug_print("Response received", 'response_handler')
   debug_print("Cache hit", 'cache_manager')
   debug_print("Serial data", 'serial_cli')

3. Check if debug is enabled:
   if is_debug_enabled('cache_manager'):
       # Do expensive debug operations only if needed
       debug_print(f"Complex debug data: {expensive_operation()}", 'cache_manager')

4. Runtime control (in your UI or advanced dashboard):
   toggle_debug()  # Toggle debug on/off
   enable_category('response_handler')  # Enable specific category
"""

# Initialize debug status on import
if __name__ != "__main__":
    print_debug_status()

# Module test
if __name__ == "__main__":
    print("Testing debug_config.py")
    print("=" * 40)

    # Test basic functions
    debug_print("Test message")
    debug_error("Test error")
    debug_warning("Test warning")
    debug_info("Test info")

    # Test categories
    debug_print("Response handler test", 'response_handler')
    debug_print("Cache test", 'cache_manager')

    # Test status
    print("\nDebug Status:")
    print(get_debug_status())

    # Test runtime controls
    print("\nTesting runtime controls...")
    disable_debug()
    debug_print("This should not print")
    enable_debug()
    debug_print("This should print again")

    print("\nDebug config test complete!")