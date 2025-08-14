#!/usr/bin/env python3
"""
Dashboards/__init__.py

Dashboard modules package for CalypsoPy application.
Contains all dashboard-specific modules for the application.
"""

from .resets_dashboard import ResetsDashboard

# Export all dashboard classes
__all__ = [
    'ResetsDashboard'
]

# Package metadata
__version__ = '1.0.0'
__author__ = 'Serial Cables, LLC'
__description__ = 'Dashboard modules for CalypsoPy application'

# Future dashboard imports will be added here as they are developed:
# from .host_dashboard import HostDashboard
# from .link_dashboard import LinkDashboard
# from .port_dashboard import PortDashboard
# from .compliance_dashboard import ComplianceDashboard
# from .registers_dashboard import RegistersDashboard
# from .advanced_dashboard import AdvancedDashboard
# from .firmware_dashboard import FirmwareDashboard
# from .help_dashboard import HelpDashboard