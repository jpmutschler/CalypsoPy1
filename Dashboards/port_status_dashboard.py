#!/usr/bin/env python3
"""
port_status_dashboard.py

Port Status Dashboard module for CalypsoPy application.
Handles showmode command execution, SBR mode display, and mode changing functionality.
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
class PortStatusInfo:
    """Data class to store parsed showmode command information"""
    current_mode: int = 0
    mode_name: str = "SBR0"
    last_updated: str = ""
    raw_showmode_response: str = ""

    def get_mode_image_filename(self) -> str:
        """Get the image filename for current mode"""
        return f"SBR{self.current_mode}.png"

    def get_display_data(self) -> List[Tuple[str, str]]:
        """Get organized display data"""
        return [
            ("Current SBR Mode", self.mode_name),
            ("Mode Number", str(self.current_mode)),
            ("Last Updated", self.last_updated)
        ]


class PortStatusParser:
    """Parser for showmode command responses"""

    def __init__(self):
        # Pattern for parsing showmode response
        self.showmode_patterns = {
            'sbr_mode': [
                r'SBR\s*mode\s*:\s*(\d+)',
                r'mode\s*:\s*(\d+)',
                r'SBR\s*(\d+)',
                r'current.*?mode.*?(\d+)'
            ]
        }

    def parse_showmode_response(self, showmode_response: str) -> PortStatusInfo:
        """Parse showmode command response"""
        info = PortStatusInfo()
        info.raw_showmode_response = showmode_response
        info.last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Parse the SBR mode
        mode_lower = showmode_response.lower()
        for field_name, patterns in self.showmode_patterns.items():
            value = self._extract_field(mode_lower, patterns)
            if value and field_name == 'sbr_mode':
                try:
                    mode_num = int(value.strip())
                    if 0 <= mode_num <= 6:  # Valid SBR mode range
                        info.current_mode = mode_num
                        info.mode_name = f"SBR{mode_num}"
                        break
                except ValueError:
                    continue

        return info

    def _extract_field(self, text: str, patterns: List[str]) -> Optional[str]:
        """Try multiple regex patterns to extract a field value"""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        return None


class PortStatusManager:
    """Manager class for handling port status information requests"""

    def __init__(self, cli_instance):
        """Initialize with CLI instance"""
        self.cli = cli_instance
        self.parser = PortStatusParser()
        self.cached_info: Optional[PortStatusInfo] = None
        self.last_refresh: Optional[datetime] = None
        self.refresh_interval = 30  # seconds
        self._lock = threading.Lock()

    def get_port_status_info(self, force_refresh: bool = False) -> PortStatusInfo:
        """Get port status information using showmode command"""
        with self._lock:
            needs_refresh = (
                    force_refresh or
                    self.cached_info is None or
                    self.last_refresh is None or
                    (datetime.now() - self.last_refresh).seconds > self.refresh_interval
            )

            if needs_refresh:
                self._refresh_info()

            return self.cached_info or PortStatusInfo()

    def _refresh_info(self) -> None:
        """Send showmode command and parse response"""
        try:
            # Send showmode command
            showmode_success = self.cli.send_command("showmode")
            if not showmode_success:
                self.cached_info = self._get_error_info("Failed to send showmode command")
                return

            # Wait for showmode response
            showmode_response = self._wait_for_response("showmode", timeout=5.0)

            if showmode_response:
                # Parse the response
                self.cached_info = self.parser.parse_showmode_response(showmode_response)
                self.last_refresh = datetime.now()
            else:
                self.cached_info = self._get_error_info("No response received from showmode command")

        except Exception as e:
            self.cached_info = self._get_error_info(f"Error getting port status info: {str(e)}")

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
        if command == "showmode":
            if "mode" in full_response and any(char.isdigit() for char in full_response):
                return True

        # General completion indicators
        completion_indicators = ['ok>', 'cmd>', '# ', 'end>']
        for indicator in completion_indicators:
            if indicator in full_response:
                return True

        if len(response_parts) > 2:
            last_line = response_parts[-1].strip().lower()
            if len(last_line) < 10 and ('>' in last_line or '#' in last_line):
                return True

        return False

    def _get_error_info(self, error_message: str) -> PortStatusInfo:
        """Create PortStatusInfo object for error conditions"""
        info = PortStatusInfo()
        info.mode_name = f"Error: {error_message}"
        info.last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return info

    def send_setmode_command(self, mode_number: int) -> bool:
        """Send setmode command to change SBR mode"""
        if not (0 <= mode_number <= 6):
            return False

        command = f"setmode {mode_number}"
        return self.cli.send_command(command)


class PortStatusDashboardUI:
    """UI components for the Port Status dashboard"""

    def __init__(self, dashboard_app):
        """Initialize with reference to main dashboard app"""
        self.app = dashboard_app
        self.image_cache = {}  # Cache for loaded images

        # SBR mode options for dropdown
        self.sbr_modes = [
            "SBR0", "SBR1", "SBR2", "SBR3",
            "SBR4", "SBR5", "SBR6"
        ]

    def create_port_dashboard(self):
        """Create the complete port status dashboard"""
        # Get real port status information
        port_info = self.app.port_status_manager.get_port_status_info()

        # Create main sections
        self.create_current_mode_section(port_info)
        self.create_mode_change_section()
        self.create_mode_image_section(port_info)
        self.create_warning_section()
        self.create_refresh_controls(port_info)

        # Add raw command output for debugging (collapsible)
        if self.app.is_demo_mode or port_info.raw_showmode_response:
            self.create_raw_output_section(port_info)

    def create_current_mode_section(self, port_info: PortStatusInfo):
        """Create section showing current SBR mode"""
        section_frame = ttk.Frame(self.app.scrollable_frame, style='Content.TFrame',
                                  relief='solid', borderwidth=1)
        section_frame.pack(fill='both', expand=True, padx=50, pady=15)

        # Section header
        header_frame = ttk.Frame(section_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=10, pady=(20, 15))

        header_label = ttk.Label(header_frame, text="🔌 Current Port Mode",
                                 style='Dashboard.TLabel', font=('Arial', 14, 'bold'))
        header_label.pack(anchor='center')

        # Section content - centered and enlarged
        content_frame = ttk.Frame(section_frame, style='Content.TFrame')
        content_frame.pack(fill='both', expand=True, padx=10, pady=(0, 20))

        # Center the content with larger spacing
        center_frame = ttk.Frame(content_frame, style='Content.TFrame')
        center_frame.pack(expand=True, fill='both')

        # Display current mode data with larger fonts
        display_data = port_info.get_display_data()
        for field_name, value in display_data:
            if value and value != "Unknown":
                self.create_centered_data_row(center_frame, field_name, value)

    def create_centered_data_row(self, parent, field_name, value):
        """Create a centered data row with field name and value"""
        row_frame = ttk.Frame(parent, style='Content.TFrame')
        row_frame.pack(pady=8, padx=10)

        # Create a frame to hold both labels and center them
        data_frame = ttk.Frame(row_frame, style='Content.TFrame')
        data_frame.pack(expand=True)

        # Field name with larger font
        field_label = ttk.Label(data_frame, text=f"{field_name}:",
                                style='Info.TLabel', font=('Arial', 12, 'bold'))
        field_label.pack(side='left', padx=(0, 15))

        # Value with status color and larger font
        value_color = self.get_mode_status_color(field_name, value)

        if value_color != '#cccccc':  # Default color
            style_name = f"ModeStatus_{field_name.replace(' ', '_')}.TLabel"
            style = ttk.Style()
            style.configure(style_name, background='#1e1e1e',
                            foreground=value_color, font=('Arial', 12, 'bold'))
            value_label = ttk.Label(data_frame, text=value, style=style_name)
        else:
            value_label = ttk.Label(data_frame, text=value, style='Info.TLabel',
                                    font=('Arial', 12, 'bold'))

        value_label.pack(side='left')

    def get_mode_status_color(self, field_name, value):
        """Get appropriate color for mode status values"""
        if "SBR Mode" in field_name or "Mode Number" in field_name:
            return '#00ff00'  # Green for active mode
        return '#cccccc'  # Default color

    def create_mode_change_section(self):
        """Create section for changing SBR mode"""
        section_frame = ttk.Frame(self.app.scrollable_frame, style='Content.TFrame',
                                  relief='solid', borderwidth=1)
        section_frame.pack(fill='both', expand=True, padx=50, pady=15)

        # Section header
        header_frame = ttk.Frame(section_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=30, pady=(20, 15))

        header_label = ttk.Label(header_frame, text="⚙️ Change Host Card Mode",
                                 style='Dashboard.TLabel', font=('Arial', 14, 'bold'))
        header_label.pack(anchor='center')

        # Section content - centered and enlarged
        content_frame = ttk.Frame(section_frame, style='Content.TFrame')
        content_frame.pack(fill='both', expand=True, padx=30, pady=(0, 20))

        # Center the controls with more spacing
        center_frame = ttk.Frame(content_frame, style='Content.TFrame')
        center_frame.pack(expand=True, fill='both')

        # Mode selection dropdown with larger spacing
        mode_frame = ttk.Frame(center_frame, style='Content.TFrame')
        mode_frame.pack(pady=15)

        ttk.Label(mode_frame, text="Select SBR Mode:",
                  style='Info.TLabel', font=('Arial', 12, 'bold')).pack(side='left', padx=(0, 15))

        self.mode_var = tk.StringVar(value="SBR0")
        self.mode_combo = ttk.Combobox(mode_frame, textvariable=self.mode_var,
                                       values=self.sbr_modes, state='readonly',
                                       width=12, font=('Arial', 11))
        self.mode_combo.pack(side='left')

        # Change mode button with larger size
        button_frame = ttk.Frame(center_frame, style='Content.TFrame')
        button_frame.pack(pady=20)

        self.change_mode_btn = ttk.Button(button_frame, text="Change Host Card Mode",
                                          command=self.change_host_card_mode,
                                          style='Connect.TButton')
        self.change_mode_btn.pack()

    def create_mode_image_section(self, port_info: PortStatusInfo):
        """Create section showing mode-specific image"""
        section_frame = ttk.Frame(self.app.scrollable_frame, style='Content.TFrame',
                                  relief='solid', borderwidth=1)
        section_frame.pack(fill='both', expand=True, padx=50, pady=15)

        # Section header
        header_frame = ttk.Frame(section_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=30, pady=(20, 15))

        header_label = ttk.Label(header_frame, text="📊 Mode Configuration Diagram",
                                 style='Dashboard.TLabel', font=('Arial', 14, 'bold'))
        header_label.pack(anchor='center')

        # Image content - centered with more space
        image_content_frame = ttk.Frame(section_frame, style='Content.TFrame')
        image_content_frame.pack(fill='both', expand=True, padx=30, pady=(0, 20))

        # Center the image with larger area
        self.image_center_frame = ttk.Frame(image_content_frame, style='Content.TFrame')
        self.image_center_frame.pack(expand=True, fill='both')

        # Load and display the appropriate image
        self.display_mode_image(port_info.current_mode)

    def display_mode_image(self, mode_number: int):
        """Display the image for the specified mode"""
        try:
            # Clear existing image
            for widget in self.image_center_frame.winfo_children():
                widget.destroy()

            # Get image filename
            image_filename = f"SBR{mode_number}.png"

            # Try multiple image paths
            image_paths = [
                os.path.join("../Images", image_filename),
                os.path.join("../assets", "Images", image_filename),
                os.path.join("../DemoData", "Images", image_filename),
                os.path.join(os.path.dirname(__file__), "Images", image_filename),
                os.path.join(os.path.dirname(__file__), "assets", "Images", image_filename)
            ]

            image_loaded = False
            for image_path in image_paths:
                if os.path.exists(image_path):
                    try:
                        # Load image
                        if image_path not in self.image_cache:
                            pil_image = Image.open(image_path)
                            # Resize for larger display (max 600x450)
                            pil_image.thumbnail((600, 450), Image.Resampling.LANCZOS)
                            self.image_cache[image_path] = ImageTk.PhotoImage(pil_image)

                        # Display image with centered alignment
                        image_label = ttk.Label(self.image_center_frame,
                                                image=self.image_cache[image_path])
                        image_label.pack(expand=True, pady=20)
                        image_loaded = True
                        break

                    except Exception as e:
                        print(f"Error loading image {image_path}: {e}")
                        continue

            if not image_loaded:
                # Show placeholder if image not found with larger font
                placeholder_label = ttk.Label(self.image_center_frame,
                                              text=f"📊 SBR{mode_number} Configuration\n(Image not available)",
                                              style='Info.TLabel',
                                              font=('Arial', 14, 'italic'),
                                              justify='center')
                placeholder_label.pack(expand=True, pady=30)

        except Exception as e:
            print(f"Error displaying mode image: {e}")
            # Show error placeholder with larger font
            error_label = ttk.Label(self.image_center_frame,
                                    text=f"Error loading image for SBR{mode_number}",
                                    style='Info.TLabel',
                                    font=('Arial', 12, 'italic'))
            error_label.pack(expand=True, pady=30)

    def create_warning_section(self):
        """Create warning section about power cycling"""
        warning_frame = ttk.Frame(self.app.scrollable_frame, style='Content.TFrame',
                                  relief='solid', borderwidth=2)
        warning_frame.pack(fill='both', expand=True, padx=50, pady=15)

        # Configure warning style
        style = ttk.Style()
        style.configure('Warning.TFrame', background='#ffeeaa', relief='solid', borderwidth=2)
        style.configure('Warning.TLabel', background='#ffeeaa', foreground='#cc6600',
                        font=('Arial', 12, 'bold'))

        warning_frame.configure(style='Warning.TFrame')

        # Warning content - centered with more padding
        warning_content = ttk.Frame(warning_frame, style='Warning.TFrame')
        warning_content.pack(fill='both', expand=True, padx=30, pady=20)

        # Center the warning text
        center_warning = ttk.Frame(warning_content, style='Warning.TFrame')
        center_warning.pack(expand=True, fill='both')

        warning_text = "⚠️ WARNING ⚠️\n\nThe host card must be power cycled after changing the SBR mode.\nThe new mode will not take effect until the card is restarted."

        warning_label = ttk.Label(center_warning, text=warning_text,
                                  style='Warning.TLabel', justify='center')
        warning_label.pack(expand=True)

    def create_refresh_controls(self, port_info: PortStatusInfo):
        """Create refresh controls and status display"""
        controls_frame = ttk.Frame(self.app.scrollable_frame, style='Content.TFrame')
        controls_frame.pack(fill='x', padx=50, pady=20)

        # Center the controls
        center_controls = ttk.Frame(controls_frame, style='Content.TFrame')
        center_controls.pack(expand=True)

        # Refresh button with larger size
        refresh_btn = ttk.Button(center_controls, text="🔄 Refresh Port Status",
                                 command=self.refresh_port_status,
                                 style='Connect.TButton')
        refresh_btn.pack(side='left', padx=(0, 20))

        # Last update time with larger font
        if port_info.last_updated:
            update_label = ttk.Label(center_controls,
                                     text=f"Last updated: {port_info.last_updated}",
                                     style='Info.TLabel', font=('Arial', 10))
            update_label.pack(side='left')

    def create_raw_output_section(self, port_info: PortStatusInfo):
        """Create collapsible raw output section for debugging"""
        # Create expandable frame
        raw_frame = ttk.Frame(self.app.scrollable_frame, style='Content.TFrame',
                              relief='solid', borderwidth=1)
        raw_frame.pack(fill='x', pady=20)

        # Header with expand/collapse button
        header_frame = ttk.Frame(raw_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=15, pady=(15, 10))

        self.expand_btn = ttk.Button(header_frame,
                                     text="▶ Raw Command Output",
                                     command=lambda: self.toggle_raw_output(raw_frame))
        self.expand_btn.pack(side='left')

        # Content frame (initially hidden)
        self.raw_content_frame = ttk.Frame(raw_frame, style='Content.TFrame')

        # Add content to raw frame
        self.populate_raw_content(port_info)
        self.raw_output_expanded = False

    def toggle_raw_output(self, raw_frame):
        """Toggle raw output visibility"""
        self.raw_output_expanded = not self.raw_output_expanded

        if self.raw_output_expanded:
            self.expand_btn.config(text="▼ Raw Command Output")
            self.raw_content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))
        else:
            self.expand_btn.config(text="▶ Raw Command Output")
            self.raw_content_frame.pack_forget()

    def populate_raw_content(self, port_info: PortStatusInfo):
        """Populate the raw content frame with command outputs"""
        # Clear existing content
        for widget in self.raw_content_frame.winfo_children():
            widget.destroy()

        # Showmode command output
        if port_info.raw_showmode_response:
            ttk.Label(self.raw_content_frame, text="showmode Command Output:",
                      style='Dashboard.TLabel', font=('Arial', 10, 'bold')).pack(anchor='w', pady=(0, 5))

            showmode_text = tk.Text(self.raw_content_frame, height=4, wrap='word',
                                    bg='#2d2d2d', fg='#ffffff',
                                    font=('Consolas', 9),
                                    relief='flat', borderwidth=0)

            showmode_scrollbar = ttk.Scrollbar(self.raw_content_frame, orient='vertical',
                                               command=showmode_text.yview)
            showmode_text.configure(yscrollcommand=showmode_scrollbar.set)

            showmode_text.insert('1.0', port_info.raw_showmode_response)
            showmode_text.config(state='disabled')

            text_frame = ttk.Frame(self.raw_content_frame, style='Content.TFrame')
            text_frame.pack(fill='x', pady=5)

            showmode_text.pack(in_=text_frame, side='left', fill='both', expand=True)
            showmode_scrollbar.pack(in_=text_frame, side='right', fill='y')

        # If no raw data, show message
        if not port_info.raw_showmode_response:
            no_data_label = ttk.Label(self.raw_content_frame,
                                      text="No raw command output available",
                                      style='Info.TLabel',
                                      font=('Arial', 10, 'italic'))
            no_data_label.pack(pady=20)

    def refresh_port_status(self):
        """Refresh port status information"""
        try:
            # Force refresh of port status info
            port_info = self.app.port_status_manager.get_port_status_info(force_refresh=True)

            # Refresh the dashboard display
            self.app.update_content_area()

            # Log the refresh action
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.app.log_data.append(f"[{timestamp}] Port status refreshed (showmode)")

        except Exception as e:
            # Handle any errors during refresh
            error_msg = f"Failed to refresh port status: {str(e)}"
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.app.log_data.append(f"[{timestamp}] {error_msg}")

            # Show error to user
            messagebox.showerror("Refresh Error", error_msg)

    def change_host_card_mode(self):
        """Handle host card mode change"""
        try:
            # Get selected mode
            selected_mode = self.mode_var.get()
            if not selected_mode.startswith("SBR"):
                messagebox.showerror("Invalid Mode", "Please select a valid SBR mode.")
                return

            # Extract mode number
            mode_number = int(selected_mode.replace("SBR", ""))

            # Confirm the change
            confirm_msg = (f"Change host card mode to {selected_mode}?\n\n"
                           f"Warning: The card must be power cycled after this change.\n"
                           f"The new mode will not take effect until restart.")

            if not messagebox.askyesno("Confirm Mode Change", confirm_msg):
                return

            # Send setmode command
            if self.app.port_status_manager.send_setmode_command(mode_number):
                # Log the command
                timestamp = datetime.now().strftime('%H:%M:%S')
                self.app.log_data.append(f"[{timestamp}] setmode {mode_number} command sent")

                # Show success message
                success_msg = (f"Mode change command sent successfully.\n\n"
                               f"New mode: {selected_mode}\n"
                               f"Remember to power cycle the host card!")
                messagebox.showinfo("Mode Change Initiated", success_msg)

                # Refresh status after a short delay
                self.app.root.after(2000, self.refresh_port_status)

            else:
                messagebox.showerror("Command Failed",
                                     f"Failed to send setmode {mode_number} command.")

        except Exception as e:
            error_msg = f"Error changing mode: {str(e)}"
            messagebox.showerror("Mode Change Error", error_msg)

            timestamp = datetime.now().strftime('%H:%M:%S')
            self.app.log_data.append(f"[{timestamp}] {error_msg}")


# Demo mode support functions
def get_demo_showmode_response(device_state=None):
    """Generate demo showmode command response"""
    # Use mode from device state or default to 0
    mode = device_state.get('current_mode', 0) if device_state else 0

    return f"""Cmd>showmode

SBR mode: {mode}

OK>"""


def update_demo_device_state(device_state, new_mode):
    """Update demo device state with new mode"""
    if device_state is None:
        device_state = {}
    device_state['current_mode'] = new_mode
    return device_state


# Testing function
if __name__ == "__main__":
    print("Testing Port Status Dashboard Module...")

    # Test with sample data
    sample_showmode = """Cmd>showmode

SBR mode: 2

OK>"""

    # Test parser
    parser = PortStatusParser()
    info = parser.parse_showmode_response(sample_showmode)

    print("Parsed Information:")
    print(f"Current Mode: {info.current_mode}")
    print(f"Mode Name: {info.mode_name}")
    print(f"Image Filename: {info.get_mode_image_filename()}")

    display_data = info.get_display_data()
    for field_name, value in display_data:
        print(f"  {field_name}: {value}")

    # Test demo functions
    print("\n" + "=" * 50)
    print("Testing Demo Functions:")

    demo_device_state = {'current_mode': 3}

    print("\nDemo showmode response:")
    print(get_demo_showmode_response(demo_device_state))

    # Test mode update
    updated_state = update_demo_device_state(demo_device_state, 5)
    print(f"\nUpdated demo state: {updated_state}")
    print("Updated showmode response:")
    print(get_demo_showmode_response(updated_state))

    print("\nModule test completed!")