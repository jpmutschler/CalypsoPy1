#!/usr/bin/env python3
"""
link_status_dashboard.py

Link Status Dashboard module for CalypsoPy application.
Handles showport command execution, parsing, and display of port link status information.
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
from PIL import Image, ImageTk


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
            print(f"ERROR: Failed to create port info: {e}")
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
            print(f"ERROR: Failed to create golden finger info: {e}")
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

    def __init__(self, cli_instance):
        """Initialize with CLI instance"""
        self.cli = cli_instance
        self.parser = LinkStatusParser()
        self.cached_info: Optional[LinkStatusInfo] = None
        self.last_refresh: Optional[datetime] = None
        self.refresh_interval = 30  # seconds
        self._lock = threading.Lock()

    def get_link_status_info(self, force_refresh: bool = False) -> LinkStatusInfo:
        """Get link status information using showport command"""
        with self._lock:
            needs_refresh = (
                    force_refresh or
                    self.cached_info is None or
                    self.last_refresh is None or
                    (datetime.now() - self.last_refresh).seconds > self.refresh_interval
            )

            if needs_refresh:
                self._refresh_info()

            return self.cached_info or LinkStatusInfo()

    def _refresh_info(self) -> None:
        """Send showport command and parse response"""
        try:
            # Send showport command
            showport_success = self.cli.send_command("showport")
            if not showport_success:
                self.cached_info = self._get_error_info("Failed to send showport command")
                return

            # Wait for showport response
            showport_response = self._wait_for_response("showport", timeout=5.0)

            if showport_response:
                # Parse response
                self.cached_info = self.parser.parse_showport_response(showport_response)
                self.last_refresh = datetime.now()
            else:
                self.cached_info = self._get_error_info("No response received from showport command")

        except Exception as e:
            self.cached_info = self._get_error_info(f"Error getting link status: {str(e)}")

    def _wait_for_response(self, command: str, timeout: float = 5.0) -> Optional[str]:
        """Wait for command response"""
        start_time = time.time()
        response_parts = []

        while (time.time() - start_time) < timeout:
            response = self.cli.read_response()
            if response:
                response_parts.append(response)
                if self._is_response_complete(command, response_parts):
                    return '\n'.join(response_parts)
            time.sleep(0.1)

        return '\n'.join(response_parts) if response_parts else None

    def _is_response_complete(self, command: str, response_parts: List[str]) -> bool:
        """Check if command response appears complete"""
        if not response_parts:
            return False

        full_response = '\n'.join(response_parts).lower()

        # Command-specific completion checks
        if command == "showport":
            if "golden finger" in full_response or "port upstream" in full_response:
                return True

        # General completion indicators
        completion_indicators = ['ok>', 'cmd>', '# ', 'end>']
        for indicator in completion_indicators:
            if indicator in full_response:
                return True

        if len(response_parts) > 3:
            last_line = response_parts[-1].strip().lower()
            if len(last_line) < 10 and ('>' in last_line or '#' in last_line):
                return True

        return False

    def _get_error_info(self, error_message: str) -> LinkStatusInfo:
        """Create LinkStatusInfo object for error conditions"""
        info = LinkStatusInfo()
        # Create an error port entry
        error_port = PortInfo()
        error_port.port_number = "Error"
        error_port.display_speed = error_message
        error_port.status_color = "#ff4444"
        info.ports["error"] = error_port
        info.last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return info


class LinkStatusDashboardUI:
    """UI components for the Link Status dashboard"""

    def __init__(self, dashboard_app):
        """Initialize with reference to main dashboard app"""
        self.app = dashboard_app
        self.link_status_manager = LinkStatusManager(self.app.cli)
        self.hc_image = None

    def create_link_dashboard(self):
        """Create the complete link status dashboard with full window layout"""
        # Load the HCFront.png image first
        self._load_hc_image()

        # Get real link status information
        link_info = self.link_status_manager.get_link_status_info()

        # Create main container that fills entire viewing window with no padding
        main_container = ttk.Frame(self.app.scrollable_frame, style='Content.TFrame')
        main_container.pack(fill='both', expand=True)

        # Create port status section (takes up upper portion - about 60% of space)
        port_frame = ttk.Frame(main_container, style='Content.TFrame')
        port_frame.pack(fill='both', expand=True)
        self.create_port_status_section(port_frame, link_info)

        # Display the HCFront.png image if loaded (takes up lower portion - about 40% of space)
        if self.hc_image:
            image_frame = ttk.Frame(main_container, style='Content.TFrame')
            image_frame.pack(fill='both', padx=(650, 15), expand=True)
            self.create_image_section(image_frame)
        else:
            # Show message if image not found
            no_image_frame = ttk.Frame(main_container, style='Content.TFrame')
            no_image_frame.pack(fill='both', expand=True)
            no_image_label = ttk.Label(no_image_frame,
                                       text="HCFront.png not found in Images directory",
                                       style='Info.TLabel', font=('Arial', 12, 'italic'))
            no_image_label.pack(expand=True)

        # Add refresh controls at the very bottom
        self.create_link_refresh_controls(link_info)

    def _load_hc_image(self):
        """Load the HCFront.png image from Images directory with larger size for high-res displays"""
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
                    # Load and resize image to much larger size for high-resolution displays
                    image = Image.open(path)
                    # Resize to larger size for 2400x1600 displays (80% = ~1920x1280 window)
                    image = image.resize((800, 600), Image.Resampling.LANCZOS)
                    self.hc_image = ImageTk.PhotoImage(image)
                    print(f"DEBUG: Loaded HCFront.png from {path} at high-res size (800x600)")
                    break
                except Exception as e:
                    print(f"DEBUG: Error loading image from {path}: {e}")

        if not self.hc_image:
            print("DEBUG: HCFront.png not found in Images directory")

    def create_image_section(self, parent):
        """Create image display section optimized for large high-resolution displays"""
        image_frame = ttk.Frame(parent, style='Content.TFrame')
        image_frame.pack(fill='both', expand=True, padx=15, pady=(8, 15))

        # Center the image horizontally and vertically in remaining space
        image_container = ttk.Frame(image_frame, style='Content.TFrame')
        image_container.pack(fill='both', expand=True)

        # Create inner frame to hold image and caption
        inner_frame = ttk.Frame(image_container, style='Content.TFrame')
        inner_frame.pack(expand=True)

        image_label = tk.Label(inner_frame, image=self.hc_image, bg='#1e1e1e')
        image_label.pack()

        # Add image caption with larger font for high-res displays
        caption_label = ttk.Label(inner_frame,
                                  text="Gen6 PCIe Atlas 3 Host Card",
                                  style='Info.TLabel',
                                  font=('Arial', 18, 'italic'))  # Larger caption font
        caption_label.pack(pady=(20, 0))

    def create_port_status_section(self, parent, link_info: LinkStatusInfo):
        """Create port status section properly centered without stretching the border"""
        # Create a centering container with large left padding to move the entire frame toward center
        centering_container = ttk.Frame(parent, style='Content.TFrame')
        centering_container.pack(fill='both', expand=True, padx=(650, 15), pady=(15, 8))  # Large left padding

        # Create the actual section frame centered within the container
        section_frame = ttk.Frame(centering_container, style='Content.TFrame',
                                  relief='solid', borderwidth=1)
        section_frame.pack(expand=True)  # This centers it without stretching

        # Section header with larger font for high-res displays - centered
        header_frame = ttk.Frame(section_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=40, pady=(30, 25))

        header_label = ttk.Label(header_frame, text="🔗 Port and Link Status",
                                 style='Dashboard.TLabel', font=('Arial', 24, 'bold'))
        header_label.pack()  # Center the header

        # Create content frame with appropriate padding inside the bordered section
        content_frame = ttk.Frame(section_frame, style='Content.TFrame')
        content_frame.pack(padx=60, pady=(0, 30))

        # Display port information
        if link_info.ports:
            # Create a container for port data
            ports_container = ttk.Frame(content_frame, style='Content.TFrame')
            ports_container.pack(pady=(0, 15))

            for port_key, port_info in link_info.ports.items():
                self.create_port_row(ports_container, port_info)

        # Display golden finger information
        if link_info.golden_finger and link_info.golden_finger.port_number:
            # Add separator
            separator = ttk.Separator(content_frame, orient='horizontal')
            separator.pack(fill='x', pady=15)

            # Golden finger container
            gf_container = ttk.Frame(content_frame, style='Content.TFrame')
            gf_container.pack()

            self.create_port_row(gf_container, link_info.golden_finger)

        # If no ports, show message
        if not link_info.ports and not link_info.golden_finger.port_number:
            no_data_label = ttk.Label(content_frame,
                                      text="No port data available - click refresh to load",
                                      style='Info.TLabel',
                                      font=('Arial', 18, 'italic'))
            no_data_label.pack(pady=20)

    def create_port_row(self, parent, port_info: PortInfo):
        """Create a single port row properly aligned within the centered section"""
        row_frame = ttk.Frame(parent, style='Content.TFrame')
        row_frame.pack(fill='x', pady=20)

        # Port name/number (left side)
        name_frame = ttk.Frame(row_frame, style='Content.TFrame')
        name_frame.pack(side='left', fill='x', expand=True)

        port_name = f"Port {port_info.port_number}" if port_info.port_number != "Golden Finger" else port_info.port_number
        name_label = ttk.Label(name_frame, text=port_name,
                               style='Info.TLabel', font=('Arial', 20, 'bold'))
        name_label.pack(side='left')

        # Status indicators (right side)
        status_frame = ttk.Frame(row_frame, style='Content.TFrame')
        status_frame.pack(side='right')

        # Create custom checkbox with proper styling
        active_var = tk.BooleanVar(value=port_info.active)

        # Create custom checkbox that appears green when active (for ALL active ports)
        if port_info.active:
            # For ALL active ports, create a green checkbutton
            checkbox_frame = ttk.Frame(status_frame, style='Content.TFrame')
            checkbox_frame.pack(side='right', padx=(30, 0))

            # Create a custom green checkbox
            active_check = ttk.Checkbutton(checkbox_frame, variable=active_var, state='disabled')
            active_check.pack(side='left')

            # Add GREEN "Active" text for ALL active ports
            active_label = ttk.Label(checkbox_frame, text="Active",
                                     foreground='#00ff00', background='#1e1e1e',
                                     font=('Arial', 16, 'bold'))
            active_label.pack(side='left', padx=(8, 0))
        else:
            # For inactive ports, use regular styling
            active_check = ttk.Checkbutton(status_frame, text="Active",
                                           variable=active_var, state='disabled')
            active_check.pack(side='right', padx=(30, 0))

        # Status light and text
        status_info_frame = ttk.Frame(status_frame, style='Content.TFrame')
        status_info_frame.pack(side='right', padx=(30, 30))

        # Create status light (colored circle)
        status_canvas = tk.Canvas(status_info_frame, width=28, height=28,
                                  bg='#1e1e1e', highlightthickness=0)
        status_canvas.pack(side='left', padx=(0, 15))
        status_canvas.create_oval(4, 4, 24, 24, fill=port_info.status_color, outline='')

        # Speed and width display
        if port_info.display_speed == "No Link":
            status_text = "No Link"
        else:
            width_text = f" {port_info.display_width}" if port_info.display_width else ""
            status_text = f"{port_info.display_speed}{width_text}"

        status_label = ttk.Label(status_info_frame, text=status_text,
                                 style='Info.TLabel', font=('Arial', 18, 'bold'))
        status_label.pack(side='left')

    def create_link_refresh_controls(self, link_info: LinkStatusInfo):
        """Create refresh controls at the very bottom"""
        controls_frame = ttk.Frame(self.app.scrollable_frame, style='Content.TFrame')
        controls_frame.pack(fill='x', side='bottom', padx=20, pady=10)

        # Refresh button with larger styling
        refresh_btn = ttk.Button(controls_frame, text="🔄 Refresh Link Status",
                                 command=self.refresh_link_status)
        refresh_btn.pack(side='left')

        # Last update time with larger font
        if link_info.last_updated:
            update_label = ttk.Label(controls_frame,
                                     text=f"Last updated: {link_info.last_updated}",
                                     style='Info.TLabel', font=('Arial', 10))
            update_label.pack(side='right')

    def refresh_link_status(self):
        """Refresh link status information"""
        try:
            # Force refresh of link status info
            self.link_status_manager.get_link_status_info(force_refresh=True)

            # Refresh the dashboard display if we're currently on link dashboard
            if self.app.current_dashboard == "link":
                self.app.update_content_area()

            # Log the refresh action
            self.app.log_data.append(f"[{datetime.now().strftime('%H:%M:%S')}] Link status refreshed (showport)")

        except Exception as e:
            # Handle any errors during refresh
            error_msg = f"Failed to refresh link status: {str(e)}"
            self.app.log_data.append(f"[{datetime.now().strftime('%H:%M:%S')}] {error_msg}")

            # Show error to user
            messagebox.showerror("Refresh Error", error_msg)


# Demo mode support functions
def load_demo_showport_file():
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
                print(f"DEBUG: Loaded showport.txt from {path} ({len(content)} chars)")
                return content
            except Exception as e:
                print(f"DEBUG: Error reading {path}: {e}")

    print("DEBUG: showport.txt not found in DemoData directory")
    return None


def get_demo_showport_response():
    """Generate demo showport command response"""
    # Try to load from file first
    demo_content = load_demo_showport_file()
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


# Testing function
if __name__ == "__main__":
    print("Testing Link Status Dashboard Module...")

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

    print("\nModule test completed!")