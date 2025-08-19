#!/usr/bin/env python3
"""
Dashboards/__init__.py

Dashboard module for CalypsoPy - Contains dashboard components and UI elements

This module provides:
- Host card information dashboard and management
- Link status dashboard with showport parsing and UI
- Demo mode integration for testing and training
- Dashboard UI components and utilities

Author: Serial Cables Development Team
"""

# Version info
__version__ = "1.4.0"
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
    from .link_status_dashboard import (
        LinkStatusInfo,
        PortInfo,
        LinkStatusParser,
        LinkStatusManager,
        LinkStatusDashboardUI,
        get_demo_showport_response
    )

    print("DEBUG: Link Status Dashboard components imported successfully")
except ImportError as e:
    print(f"WARNING: Could not import Link Status Dashboard: {e}")
    LinkStatusInfo = None
    PortInfo = None
    LinkStatusParser = None
    LinkStatusManager = None
    LinkStatusDashboardUI = None
    get_demo_showport_response = None

try:
    from .demo_mode_integration import UnifiedDemoSerialCLI

    print("DEBUG: Demo Mode Integration imported successfully")
except ImportError as e:
    print(f"WARNING: Could not import Demo Mode Integration: {e}")
    UnifiedDemoSerialCLI = None

# Module metadata
__all__ = [
    # Host Card Components
    'HostCardInfo',
    'HostCardInfoParser',
    'HostCardInfoManager',
    'HostCardDashboardUI',
    'get_demo_ver_response',
    'get_demo_lsd_response',

    # Link Status Components
    'LinkStatusInfo',
    'PortInfo',
    'LinkStatusParser',
    'LinkStatusManager',
    'LinkStatusDashboardUI',
    'get_demo_showport_response',

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
            'Link Status Dashboard',
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


def create_link_status_dashboard(app):
    """Convenience function to create Link Status Dashboard UI"""
    if LinkStatusDashboardUI is not None:
        return LinkStatusDashboardUI(app)
    else:
        raise ImportError("LinkStatusDashboardUI not available")


def create_host_card_dashboard(app):
    """Convenience function to create Host Card Dashboard UI"""
    if HostCardDashboardUI is not None:
        return HostCardDashboardUI(app)
    else:
        raise ImportError("HostCardDashboardUI not available")


# Initialize dashboard module
print(f"DEBUG: Dashboard module initialized (version {__version__})")

# Check if all components loaded successfully
if check_dashboard_dependencies():
    print("DEBUG: All dashboard components ready for use")
else:
    print("WARNING: Some dashboard components are missing - check imports")