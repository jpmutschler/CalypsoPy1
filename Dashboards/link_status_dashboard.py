#!/usr/bin/env python3
"""
link_status_dashboard.py

Enhanced Link Status Dashboard module for CalypsoPy application.
Self-contained module that handles all showport command execution, parsing,
caching, and display of port link status information.

This module is fully independent and contains all necessary functionality
previously scattered across main.py and other modules.
"""

import re
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Optional, Any, List, Tuple
import os
import queue
from PIL import Image, ImageTk

# Import Admin modules for parsing, caching, and debug
try:
    from Admin.enhanced_sysinfo_parser import EnhancedSystemInfoParser
    from Admin.cache_manager import DeviceDataCache
    from Admin.debug_config import debug_print, debug_error, debug_warning, debug_info
except ImportError as e:
    print(f"WARNING: Could not import Admin modules: {e}")
    EnhancedSystemInfoParser = None
    DeviceDataCache = None
    debug_print = print


@dataclass
class PortInfo:
    """Data class to store individual port information"""
    port_number: str = "Unknown"
    speed_level: str = "00"
    width: str = "00"
    max_speed: str = "00"
    max_width: str = "00"
    status: str = "Unknown"
    display_speed: str = "Unknown"
    display_width: str = "Unknown"
    status_color: str = "#cccccc"
    active: bool = False


@dataclass
class LinkStatusInfo:
    """Data class to store complete link status information from showport command"""
    # Port Information
    ports: Dict[str, PortInfo] = None
    golden_finger: PortInfo = None

    # Metadata
    last_updated: str = ""
    raw_showport_response: str = ""

    def __post_init__(self):
        if self.ports is None:
            self.ports = {}
        if self.golden_finger is None:
            self.golden_finger = PortInfo()


class LinkStatusParser:
    """Parser for showport command responses"""

    def __init__(self):
        # Patterns for showport command parsing
        self.port_patterns = [
            r'Port(\d+)\s*:\s*speed\s+(\w+),\s*width\s+(\w+),\s*max_speed(\w+),\s*max_width(\d+)',
            r'Port(\d+)\s*:\s*speed\s+(\w+),\s*width\s+(\w+)'
        ]

        self.golden_finger_patterns = [
            r'Golden\s+finger:\s*speed\s+(\w+),\s*width\s+(\w+),\s*max_width\s*=\s*(\d+)',
            r'Golden\s+finger:\s*speed\s+(\w+),\s*width\s+(\w+)'
        ]

    def parse_showport_response(self, showport_response: str) -> LinkStatusInfo:
        """Parse showport command response"""
        info = LinkStatusInfo()
        info.raw_showport_response = showport_response
        info.last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Parse individual ports
        showport_lower = showport_response.lower()

        # Parse regular ports
        for pattern in self.port_patterns:
            matches = re.finditer(pattern, showport_response, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                port_info = self._create_port_info(match.groups())
                if port_info:
                    info.ports[f"port_{port_info.port_number}"] = port_info

        # Parse golden finger
        for pattern in self.golden_finger_patterns:
            match = re.search(pattern, showport_response, re.IGNORECASE | re.MULTILINE)
            if match:
                info.golden_finger = self._create_golden_finger_info(match.groups())
                break

        debug_info(f"Parsed {len(info.ports)} ports and golden finger", "LINK_PARSER")
        return info

    def _create_port_info(self, match_groups: Tuple) -> Optional[PortInfo]:
        """Create PortInfo from regex match groups"""
        try:
            port_info = PortInfo()
            port_info.port_number = match_groups[0]
            port_info.speed_level = match_groups[1] if len(match_groups) > 1 else "00"
            port_info.width = match_groups[2] if len(match_groups) > 2 else "00"
            port_info.max_speed = match_groups[3] if len(match_groups) > 3 else "00"
            port_info.max_width = match_groups[4] if len(match_groups) > 4 else "00"

            # Process display format and status
            self._process_port_display_info(port_info)

            return port_info
        except Exception as e:
            debug_error(f"Failed to create port info: {e}", "LINK_PARSER")
            return None

    def _create_golden_finger_info(self, match_groups: Tuple) -> PortInfo:
        """Create PortInfo for golden finger from regex match groups"""
        try:
            port_info = PortInfo()
            port_info.port_number = "Golden Finger"
            port_info.speed_level = match_groups[0] if len(match_groups) > 0 else "00"
            port_info.width = match_groups[1] if len(match_groups) > 1 else "00"
            port_info.max_width = match_groups[2] if len(match_groups) > 2 else "00"

            # Process display format and status
            self._process_port_display_info(port_info)

            return port_info
        except Exception as e:
            debug_error(f"Failed to create golden finger info: {e}", "LINK_PARSER")
            return PortInfo()

    def _process_port_display_info(self, port_info: PortInfo):
        """Process port information for display formatting"""
        # Check for no link condition first
        if port_info.speed_level == "01" and port_info.width == "00":
            port_info.display_speed = "No Link"
            port_info.display_width = ""
            port_info.status = "No Link"
            port_info.status_color = "#ff4444"  # Red
            port_info.active = False
            return

        # Process speed level to generation
        speed_mappings = {
            "06": ("Gen6", "#00ff00"),  # Green
            "05": ("Gen5", "#ff9500"),  # Yellow/Orange
            "04": ("Gen4", "#ff9500"),  # Yellow/Orange
            "03": ("Gen3", "#ff9500"),  # Yellow/Orange
            "02": ("Gen2", "#ff9500"),  # Yellow/Orange
            "01": ("Gen1", "#ff4444"),  # Red
        }

        if port_info.speed_level in speed_mappings:
            port_info.display_speed, port_info.status_color = speed_mappings[port_info.speed_level]
            port_info.active = True
        else:
            port_info.display_speed = f"Level {port_info.speed_level}"
            port_info.status_color = "#cccccc"
            port_info.active = False

        # Process width
        if port_info.width in ["02", "04", "08", "16"]:
            port_info.display_width = f"x{port_info.width}"
        else:
            port_info.display_width = f"x{port_info.width}" if port_info.width != "00" else ""

        # Set overall status
        if port_info.active and port_info.speed_level != "01":
            port_info.status = "Active"
        else:
            port_info.status = "Inactive"


class LinkStatusManager:
    """Manager class for handling link status information requests"""

    def __init__(self, cli_instance, cache_manager=None, sysinfo_parser=None):
        """Initialize with CLI instance and optional cache/parser"""
        self.cli = cli_instance
        self.parser = LinkStatusParser()
        self.cached_info: Optional[LinkStatusInfo] = None
        self.last_refresh: Optional[datetime] = None
        self.refresh_interval = 30  # seconds
        self._lock = threading.Lock()

        # Admin integrations
        self.cache_manager = cache_manager
        self.sysinfo_parser = sysinfo_parser

        # Command state tracking
        self.showport_requested = False
        self.showport_timeout = 10  # seconds

    def get_link_status_info(self, force_refresh: bool = False) -> LinkStatusInfo:
        """Get link status information using showport command"""
        with self._lock:
            # Try cache first if not forcing refresh
            if not force_refresh and self._is_cache_fresh():
                debug_info("Using cached link status data", "LINK_MANAGER")
                return self.cached_info or LinkStatusInfo()

            # Try to get from enhanced parser cache
            if self.sysinfo_parser and not force_refresh:
                cached_data = self.sysinfo_parser.get_cached_showport_data()
                if cached_data and self.sysinfo_parser.is_showport_data_fresh(300):
                    debug_info("Using enhanced parser cached data", "LINK_MANAGER")
                    self.cached_info = self._convert_cached_to_link_info(cached_data)
                    return self.cached_info

            # Need fresh data - trigger refresh
            debug_info("Refreshing link status data", "LINK_MANAGER")
            self._refresh_info()
            return self.cached_info or LinkStatusInfo()

    def _is_cache_fresh(self) -> bool:
        """Check if cached data is still fresh"""
        if self.cached_info is None or self.last_refresh is None:
            return False

        age = (datetime.now() - self.last_refresh).seconds
        return age < self.refresh_interval

    def _refresh_info(self) -> None:
        """Send showport command and parse response"""
        try:
            if not self.cli or not self.cli.is_running:
                debug_error("CLI not available for showport command", "LINK_MANAGER")
                self.cached_info = self._get_error_info("CLI not connected")
                return

            # Check if showport already in progress
            if self.showport_requested:
                debug_warning("Showport already in progress", "LINK_MANAGER")
                return

            # Send showport command
            debug_info("Sending showport command", "LINK_MANAGER")
            self.showport_requested = True

            success = self.cli.send_command("showport")
            if not success:
                self.showport_requested = False
                self.cached_info = self._get_error_info("Failed to send showport command")
                return

            # Start timeout timer
            threading.Timer(self.showport_timeout, self._handle_showport_timeout).start()

        except Exception as e:
            debug_error(f"Error during showport refresh: {e}", "LINK_MANAGER")
            self.showport_requested = False
            self.cached_info = self._get_error_info(f"Refresh error: {e}")

    def process_showport_response(self, response: str) -> bool:
        """Process showport response from device"""
        try:
            if not self.showport_requested:
                debug_warning("Unexpected showport response received", "LINK_MANAGER")
                return False

            debug_info(f"Processing showport response ({len(response)} chars)", "LINK_MANAGER")

            # Parse the response
            self.cached_info = self.parser.parse_showport_response(response)
            self.last_refresh = datetime.now()
            self.showport_requested = False

            # Also cache in enhanced parser if available
            if self.sysinfo_parser:
                self.sysinfo_parser.parse_showport_command(response)

            debug_info(f"Successfully processed showport with {len(self.cached_info.ports)} ports", "LINK_MANAGER")
            return True

        except Exception as e:
            debug_error(f"Error processing showport response: {e}", "LINK_MANAGER")
            self.showport_requested = False
            self.cached_info = self._get_error_info(f"Parse error: {e}")
            return False

    def _handle_showport_timeout(self):
        """Handle showport command timeout"""
        if self.showport_requested:
            debug_warning("Showport command timed out", "LINK_MANAGER")
            self.showport_requested = False
            self.cached_info = self._get_error_info("Showport command timed out")

    def _convert_cached_to_link_info(self, cached_data: Dict[str, Any]) -> LinkStatusInfo:
        """Convert cached showport data to LinkStatusInfo format"""
        link_info = LinkStatusInfo()
        link_info.last_updated = cached_data.get('last_updated', 'Unknown')
        link_info.raw_showport_response = cached_data.get('raw_output', '')

        # Convert ports
        for port_key, port_data in cached_data.get('ports', {}).items():
            port_info = PortInfo()
            port_info.port_number = port_data.get('port_number', 'Unknown')
            port_info.speed_level = port_data.get('speed_level', '00')
            port_info.width = port_data.get('width', '00')
            port_info.display_speed = port_data.get('display_speed', 'Unknown')
            port_info.display_width = port_data.get('display_width', '')
            port_info.status = port_data.get('status', 'Unknown')
            port_info.status_color = port_data.get('status_color', '#cccccc')
            port_info.active = port_data.get('active', False)
            link_info.ports[port_key] = port_info

        # Convert golden finger
        gf_data = cached_data.get('golden_finger', {})
        if gf_data:
            link_info.golden_finger = PortInfo()
            link_info.golden_finger.port_number = gf_data.get('port_number', 'Golden Finger')
            link_info.golden_finger.speed_level = gf_data.get('speed_level', '00')
            link_info.golden_finger.width = gf_data.get('width', '00')
            link_info.golden_finger.display_speed = gf_data.get('display_speed', 'Unknown')
            link_info.golden_finger.display_width = gf_data.get('display_width', '')
            link_info.golden_finger.status = gf_data.get('status', 'Unknown')
            link_info.golden_finger.status_color = gf_data.get('status_color', '#cccccc')
            link_info.golden_finger.active = gf_data.get('active', False)

        return link_info

    def _get_error_info(self, error_message: str) -> LinkStatusInfo:
        """Create error LinkStatusInfo"""
        info = LinkStatusInfo()
        info.last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        info.raw_showport_response = f"ERROR: {error_message}"
        return info


class LinkStatusDashboardUI:
    """Enhanced UI components for the Link Status dashboard - fully self-contained"""

    def __init__(self, dashboard_app):
        """Initialize with reference to main dashboard app"""
        self.app = dashboard_app
        self.hc_image = None

        # Initialize Link Status Manager with admin integrations
        cache_manager = getattr(self.app, 'cache_manager', None)
        sysinfo_parser = getattr(self.app, 'sysinfo_parser', None)

        self.link_status_manager = LinkStatusManager(
            self.app.cli,
            cache_manager=cache_manager,
            sysinfo_parser=sysinfo_parser
        )

        # Set up log monitoring for showport responses
        self._setup_log_monitoring()

        debug_info("LinkStatusDashboardUI initialized", "LINK_UI")

    def _setup_log_monitoring(self):
        """Set up monitoring for showport responses in logs"""
        # This will be called by main app's log monitoring
        # We'll expose a method for main app to call when showport responses arrive
        pass

    def handle_showport_response(self, response: str) -> bool:
        """Handle showport response from log monitoring"""
        success = self.link_status_manager.process_showport_response(response)

        if success and self.app.current_dashboard == "link":
            # Refresh the UI if we're currently viewing the link dashboard
            self.app.root.after_idle(self.refresh_dashboard_display)

        return success

    def create_dashboard(self):
        """Create the complete link status dashboard - main entry point"""
        debug_info("Creating link status dashboard", "LINK_UI")

        # Clear existing content
        for widget in self.app.scrollable_frame.winfo_children():
            widget.destroy()

        # Check if demo mode
        if getattr(self.app, 'is_demo_mode', False):
            self._create_demo_dashboard()
        else:
            self._create_real_dashboard()

    def _create_demo_dashboard(self):
        """Create dashboard for demo mode"""
        debug_info("Creating demo link dashboard", "LINK_UI")

        try:
            # Load demo showport data
            demo_content = self._load_demo_showport_file()

            if demo_content:
                debug_info(f"Using demo showport content ({len(demo_content)} chars)", "LINK_UI")

                # Parse and cache the showport data
                link_info = self.link_status_manager.parser.parse_showport_response(demo_content)
                self.link_status_manager.cached_info = link_info
                self.link_status_manager.last_refresh = datetime.now()

                # Also parse using enhanced parser for caching
                if self.link_status_manager.sysinfo_parser:
                    self.link_status_manager.sysinfo_parser.parse_showport_command(demo_content)

                # Create the dashboard UI
                self._create_link_dashboard_ui(link_info)

                debug_info("Demo link dashboard created successfully", "LINK_UI")
            else:
                debug_warning("No demo showport content available", "LINK_UI")
                self._show_loading_message("Demo showport data not available - check DemoData/showport.txt")

        except Exception as e:
            debug_error(f"Demo link dashboard failed: {e}", "LINK_UI")
            self._show_loading_message(f"Demo error: {e}")

    def _create_real_dashboard(self):
        """Create dashboard for real device mode"""
        debug_info("Creating real device link dashboard", "LINK_UI")

        # Get link status info (will check cache first)
        link_info = self.link_status_manager.get_link_status_info()

        if link_info and link_info.ports:
            self._create_link_dashboard_ui(link_info)
        else:
            # Need to fetch data
            debug_info("No cached data, requesting fresh showport", "LINK_UI")
            self._show_loading_message("Loading link status...")
            self.link_status_manager.get_link_status_info(force_refresh=True)

    def _create_link_dashboard_ui(self, link_info: LinkStatusInfo):
        """Create the actual dashboard UI"""
        # Load the HCFront.png image first
        self._load_hc_image()

        # Create main container that fills entire viewing window
        main_container = ttk.Frame(self.app.scrollable_frame, style='Content.TFrame')
        main_container.pack(fill='both', expand=True)

        # Create port status section (upper portion)
        port_frame = ttk.Frame(main_container, style='Content.TFrame')
        port_frame.pack(fill='both', expand=True)
        self._create_port_status_section(port_frame, link_info)

        # Display the HCFront.png image if loaded (lower portion)
        if self.hc_image:
            image_frame = ttk.Frame(main_container, style='Content.TFrame')
            image_frame.pack(fill='both', padx=(10, 15), expand=True)
            self._create_image_section(image_frame)
        else:
            # Show message if image not found
            no_image_frame = ttk.Frame(main_container, style='Content.TFrame')
            no_image_frame.pack(fill='both', expand=True)
            no_image_label = ttk.Label(no_image_frame,
                                       text="HCFront.png not found in Images directory",
                                       style='Info.TLabel', font=('Arial', 12, 'italic'))
            no_image_label.pack(expand=True)

        # Add refresh controls at the bottom
        self._create_link_refresh_controls(link_info)

    def _create_port_status_section(self, parent, link_info: LinkStatusInfo):
        """Create the port status section"""
        # Create a bordered section container for ports/links - centered
        section_frame = ttk.Frame(parent, style='Content.TFrame',
                                  relief='solid', borderwidth=1)
        section_frame.pack(expand=True)

        # Section header with larger font - centered
        header_frame = ttk.Frame(section_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=40, pady=(30, 25))

        header_label = ttk.Label(header_frame, text="🔗 Port and Link Status",
                                 style='Dashboard.TLabel', font=('Arial', 24, 'bold'))
        header_label.pack()

        # Create content frame with appropriate padding
        content_frame = ttk.Frame(section_frame, style='Content.TFrame')
        content_frame.pack(padx=60, pady=(0, 30))

        # Display port information
        if link_info.ports:
            ports_container = ttk.Frame(content_frame, style='Content.TFrame')
            ports_container.pack(pady=(0, 15))

            for port_key, port_info in link_info.ports.items():
                self._create_port_row(ports_container, port_info)

        # Display golden finger information
        if link_info.golden_finger and link_info.golden_finger.port_number:
            # Add separator
            separator = ttk.Separator(content_frame, orient='horizontal')
            separator.pack(fill='x', pady=15)

            # Golden finger container
            gf_container = ttk.Frame(content_frame, style='Content.TFrame')
            gf_container.pack()

            self._create_port_row(gf_container, link_info.golden_finger)

        # If no ports, show message
        if not link_info.ports and not link_info.golden_finger.port_number:
            no_data_label = ttk.Label(content_frame,
                                      text="No port data available - click refresh to load",
                                      style='Info.TLabel',
                                      font=('Arial', 18, 'italic'))
            no_data_label.pack(pady=20)

    def _create_port_row(self, parent, port_info: PortInfo):
        """Create a single port row"""
        row_frame = ttk.Frame(parent, style='Content.TFrame')
        row_frame.pack(fill='x', pady=20)

        # Port name/number (left side)
        name_frame = ttk.Frame(row_frame, style='Content.TFrame')
        name_frame.pack(side='left', anchor='w')

        port_label = ttk.Label(name_frame, text=f"Port {port_info.port_number}:",
                               style='Dashboard.TLabel', font=('Arial', 20, 'bold'))
        port_label.pack(anchor='w')

        # Status information (right side)
        status_info_frame = ttk.Frame(row_frame, style='Content.TFrame')
        status_info_frame.pack(side='right', anchor='e')

        # Status text with color coding
        if port_info.status == "No Link":
            status_text = "❌ No Link"
        elif port_info.active:
            width_text = f" {port_info.display_width}" if port_info.display_width else ""
            status_text = f"✅ {port_info.display_speed}{width_text}"
        else:
            width_text = f" {port_info.display_width}" if port_info.display_width else ""
            status_text = f"⚪ {port_info.display_speed}{width_text}"

        status_label = ttk.Label(status_info_frame, text=status_text,
                                 style='Info.TLabel', font=('Arial', 18, 'bold'))
        status_label.pack(side='left')

    def _create_image_section(self, parent):
        """Create the image section"""
        if self.hc_image:
            image_label = ttk.Label(parent, image=self.hc_image, style='Content.TLabel')
            image_label.pack(expand=True)

    def _create_link_refresh_controls(self, link_info: LinkStatusInfo):
        """Create refresh controls at the bottom"""
        controls_frame = ttk.Frame(self.app.scrollable_frame, style='Content.TFrame')
        controls_frame.pack(fill='x', side='bottom', padx=20, pady=10)

        # Refresh button
        refresh_btn = ttk.Button(controls_frame, text="🔄 Refresh Link Status",
                                 command=self.refresh_link_status)
        refresh_btn.pack(side='left')

        # Last update time
        if link_info.last_updated:
            update_label = ttk.Label(controls_frame,
                                     text=f"Last updated: {link_info.last_updated}",
                                     style='Info.TLabel', font=('Arial', 10))
            update_label.pack(side='right')

    def refresh_link_status(self):
        """Refresh link status information"""
        try:
            debug_info("Manual refresh requested", "LINK_UI")

            # Force refresh of link status info
            self.link_status_manager.get_link_status_info(force_refresh=True)

            # Show loading message
            self._show_loading_message("Refreshing link status...")

            # Log the refresh action
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.app.log_data.append(f"[{timestamp}] Link status refresh requested")

        except Exception as e:
            # Handle any errors during refresh
            error_msg = f"Failed to refresh link status: {str(e)}"
            debug_error(error_msg, "LINK_UI")
            self.app.log_data.append(f"[{datetime.now().strftime('%H:%M:%S')}] {error_msg}")
            messagebox.showerror("Refresh Error", error_msg)

    def refresh_dashboard_display(self):
        """Refresh only the dashboard display with current data"""
        if self.app.current_dashboard == "link":
            debug_info("Refreshing link dashboard display", "LINK_UI")
            self.create_dashboard()

    def _load_hc_image(self):
        """Load the HCFront.png image from Images directory"""
        image_paths = [
            "Images/HCFront.png",
            "./Images/HCFront.png",
            "../Images/HCFront.png",
            os.path.join(os.path.dirname(__file__), "Images", "HCFront.png"),
            os.path.join(os.getcwd(), "Images", "HCFront.png")
        ]

        for path in image_paths:
            if os.path.exists(path):
                try:
                    # Load and resize image for high-res displays
                    pil_image = Image.open(path)
                    # Resize to reasonable size (larger for high-res)
                    pil_image = pil_image.resize((600, 400), Image.Resampling.LANCZOS)
                    self.hc_image = ImageTk.PhotoImage(pil_image)
                    debug_info(f"Loaded HCFront.png from {path}", "LINK_UI")
                    return
                except Exception as e:
                    debug_warning(f"Error loading image from {path}: {e}", "LINK_UI")

        debug_warning("HCFront.png not found in any standard location", "LINK_UI")

    def _load_demo_showport_file(self) -> Optional[str]:
        """Load showport.txt from DemoData directory"""
        demo_paths = [
            "DemoData/showport.txt",
            "./DemoData/showport.txt",
            "../DemoData/showport.txt",
            os.path.join(os.path.dirname(__file__), "DemoData", "showport.txt"),
            os.path.join(os.getcwd(), "DemoData", "showport.txt")
        ]

        for path in demo_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    debug_info(f"Loaded showport.txt from {path} ({len(content)} chars)", "LINK_UI")
                    return content
                except Exception as e:
                    debug_warning(f"Error reading {path}: {e}", "LINK_UI")

        debug_warning("showport.txt not found in DemoData directory", "LINK_UI")
        return self._get_fallback_demo_data()

    def _get_fallback_demo_data(self) -> str:
        """Get fallback demo data if file not found"""
        return """Cmd>showport

Port Slot------------------------------------------------------------------------------

Port80 : speed 06, width 04, max_speed06, max_width16
Port112: speed 01, width 00, max_speed06, max_width16  
Port128: speed 05, width 16, max_speed06, max_width16

Port Upstream------------------------------------------------------------------------------

Golden finger: speed 06, width 16, max_width = 16

Cmd>[]"""

    def _show_loading_message(self, message: str):
        """Show loading message in the dashboard area"""
        # Clear existing content
        for widget in self.app.scrollable_frame.winfo_children():
            widget.destroy()

        loading_frame = ttk.Frame(self.app.scrollable_frame, style='Content.TFrame')
        loading_frame.pack(fill='x', pady=20)

        ttk.Label(loading_frame, text=message, style='Info.TLabel',
                  font=('Arial', 12, 'italic')).pack()

        # Add retry button for demo mode
        if getattr(self.app, 'is_demo_mode', False):
            ttk.Button(loading_frame, text="🔄 Retry Demo Loading",
                       command=self._retry_demo_connection).pack(pady=(10, 0))

    def _retry_demo_connection(self):
        """Retry demo connection"""
        debug_info("Retrying demo connection", "LINK_UI")
        try:
            # Try to recreate the demo dashboard
            self._create_demo_dashboard()

            timestamp = datetime.now().strftime('%H:%M:%S')
            self.app.log_data.append(f"[{timestamp}] Demo link retry successful")

        except Exception as e:
            debug_error(f"Demo retry failed: {e}", "LINK_UI")
            self._show_loading_message(f"Demo retry failed: {e}")


# Demo mode support functions
def get_demo_showport_response():
    """Generate demo showport command response"""
    # Try to load from file first
    demo_content = _load_demo_showport_file_standalone()
    if demo_content:
        return f"Cmd>showport\n\n{demo_content}\n\nCmd>[]"

    # Fallback demo data
    return """Cmd>showport

Port Slot------------------------------------------------------------------------------

Port80 : speed 06, width 04, max_speed06, max_width16
Port112: speed 01, width 00, max_speed06, max_width16  
Port128: speed 05, width 16, max_speed06, max_width16

Port Upstream------------------------------------------------------------------------------

Golden finger: speed 06, width 16, max_width = 16

Cmd>[]"""


def _load_demo_showport_file_standalone():
    """Standalone function to load demo showport file"""
    demo_paths = [
        "DemoData/showport.txt",
        "./DemoData/showport.txt",
        "../DemoData/showport.txt",
        os.path.join(os.path.dirname(__file__), "DemoData", "showport.txt"),
        os.path.join(os.getcwd(), "DemoData", "showport.txt")
    ]

    for path in demo_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return content
            except Exception as e:
                print(f"DEBUG: Error reading {path}: {e}")

    return None


# Testing function
if __name__ == "__main__":
    print("Testing Enhanced Link Status Dashboard Module...")

    # Test with sample showport data
    sample_showport = """Cmd>showport

Port Slot------------------------------------------------------------------------------

Port80 : speed 06, width 04, max_speed06, max_width16
Port112: speed 01, width 00, max_speed06, max_width16
Port128: speed 05, width 16, max_speed06, max_width16

Port Upstream------------------------------------------------------------------------------

Golden finger: speed 06, width 16, max_width = 16

Cmd>[]"""

    # Test parser
    parser = LinkStatusParser()
    info = parser.parse_showport_response(sample_showport)

    print("Parsed Information:")
    print(f"Ports found: {len(info.ports)}")

    for port_key, port_info in info.ports.items():
        status_indicator = "🔴" if not port_info.active else ("🟢" if port_info.status_color == "#00ff00" else "🟡")
        print(
            f"  {status_indicator} Port {port_info.port_number}: {port_info.display_speed} {port_info.display_width} ({port_info.status})")

    if info.golden_finger.port_number:
        gf = info.golden_finger
        status_indicator = "🔴" if not gf.active else ("🟢" if gf.status_color == "#00ff00" else "🟡")
        print(f"  {status_indicator} {gf.port_number}: {gf.display_speed} {gf.display_width} ({gf.status})")

    print("\nEnhanced module test completed!")