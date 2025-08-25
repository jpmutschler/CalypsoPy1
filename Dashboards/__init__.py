#!/usr/bin/env python3
"""
Dashboards/__init__.py

Dashboard module for CalypsoPy - Contains dashboard components and UI elements

This module provides:
- Host card information dashboard and management
- Advanced dashboard with clock and FLIT mode controls
- Demo mode integration for testing and training
- Dashboard UI components and utilities

Author: Serial Cables Development Team
"""

# Version info
__version__ = "1.3.4"
__author__ = "Serial Cables Development Team"

# Import main dashboard classes for easy access
try:
    from .host_card_info import (
        HostCardInfo,
        HostCardInfoParser,
        HostCardInfoManager,
        HostCardDashboardUI,
        get_demo_ver_response,
        get_demo_lsd_response
    )

    print("DEBUG: Host Card Info components imported successfully")
except ImportError as e:
    print(f"WARNING: Could not import Host Card Info: {e}")
    HostCardInfo = None
    HostCardInfoParser = None
    HostCardInfoManager = None
    HostCardDashboardUI = None

try:
    from .demo_mode_integration import UnifiedDemoSerialCLI

    print("DEBUG: Demo Mode Integration imported successfully")
except ImportError as e:
    print(f"WARNING: Could not import Demo Mode Integration: {e}")
    UnifiedDemoSerialCLI = None

try:
    from .advanced_dashboard import (
        AdvancedDashboard,
        integrate_advanced_dashboard,
        extend_demo_mode_for_advanced
    )

    print("DEBUG: Advanced Dashboard components imported successfully")
except ImportError as e:
    print(f"WARNING: Could not import Advanced Dashboard: {e}")
    AdvancedDashboard = None
    integrate_advanced_dashboard = None
    extend_demo_mode_for_advanced = None

# Module metadata
__all__ = [
    # Host Card Components
    'HostCardInfo',
    'HostCardInfoParser',
    'HostCardInfoManager',
    'HostCardDashboardUI',
    'get_demo_ver_response',
    'get_demo_lsd_response',

    # Advanced Dashboard Components
    'AdvancedDashboard',
    'integrate_advanced_dashboard',
    'extend_demo_mode_for_advanced',

    # Demo Mode
    'UnifiedDemoSerialCLI'
]


def get_dashboard_info():
    """Get information about the Dashboard module"""
    return {
        'version': __version__,
        'author': __author__,
        'components': [
            'Host Card Information Dashboard',
            'Advanced Dashboard (Clock & FLIT Mode)',
            'Demo Mode Integration',
            'Dashboard UI Components'
        ],
        'available_classes': [cls for cls in __all__ if globals().get(cls) is not None]
    }


def check_dashboard_dependencies():
    """Check if all dashboard components are available"""
    missing = []
    for component in __all__:
        if globals().get(component) is None:
            missing.append(component)

    if missing:
        print(f"WARNING: Missing dashboard components: {missing}")
        return False
    else:
        print("DEBUG: All dashboard components loaded successfully")
        return True


# Initialize dashboard module
print(f"DEBUG: Dashboard module initialized (version {__version__})")