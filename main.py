#!/usr/bin/env python3
"""
CalypsoPy by Serial Cables
A modern GUI application for serial communication with the Gen6 PCIe Atlas 3 Host Card from Serial Cables

Developed by:
Joshua Mutschler, Serial Cables

CalypsoPy Dependencies:
- tkinter (built-in)
- pySerial
- Pillow (PIL) - for dashboard image display
- Standard library modules: threading, queue, json, os, re, datetime
"""

# Application Information
APP_NAME = "CalypsoPy"
APP_VERSION = "1.3.4"  # Updated version
APP_BUILD = "20250809-001"  # Updated build
APP_DESCRIPTION = "Serial Cables Atlas 3 Serial UI for CLI Interface"
APP_AUTHOR = "Serial Cables, LLC"
APP_COPYRIGHT = "© 2025"

# Version History - UPDATED WITH NEW FEATURES
VERSION_HISTORY = {
    "Beta 1.1.0": {
        "date": "2024-12-09",
        "changes": [
            "Added data caching with JSON persistence",
            "Implemented environment settings management",
            "Added auto-refresh capabilities",
            "Created settings UI with gear icon",
            "Optimized dashboard performance"
        ]
    },
    "Beta 1.0.0": {
        "date": "2024-12-08",
        "changes": [
            "Initial beta release",
        ]
    }
}


def get_version_info():
    """Get formatted version information"""
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "build": APP_BUILD,
        "description": APP_DESCRIPTION,
        "author": APP_AUTHOR,
        "copyright": APP_COPYRIGHT,
        "full_title": f"{APP_NAME} {APP_VERSION}"
    }


import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import serial
import serial.tools.list_ports
import threading
import time
import queue
import sys
import os
import re
from datetime import datetime
from Dashboards.host_card_info import HostCardInfoManager, HostCardDashboardUI
from Admin.cache_manager import DeviceDataCache
from Admin.enhanced_sysinfo_parser import EnhancedSystemInfoParser
from Admin.settings_manager import SettingsManager
from Admin.settings_ui import SettingsDialog
from Dashboards.link_status_dashboard import LinkStatusDashboardUI
from Dashboards.port_status_dashboard import PortStatusManager, PortStatusDashboardUI, get_demo_showmode_response, update_demo_device_state
from Dashboards.firmware_dashboard import FirmwareDashboard
from Dashboards.resets_dashboard import ResetsDashboard
from Admin.advanced_response_handler import AdvancedResponseHandler
import Admin.settings_ui as settings_ui
try:
    from Admin.debug_config import (
        debug_print,
        debug_error,
        debug_warning,
        debug_info,
        is_debug_enabled,
        get_debug_status,
        toggle_debug,
        enable_debug,
        disable_debug,
        port_debug,
        log_info
    )
    DEBUG_FUNCTIONS_AVAILABLE = True
    print("DEBUG: Successfully imported debug functions from Admin.debug_config")
except ImportError as e:
    print(f"Warning: Could not import from Admin.debug_config: {e}")

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("WARNING: PIL not available. SBR mode images will not be displayed.")


def load_demo_sysinfo_file(self):
    """Load sysinfo.txt from DemoData directory"""
    debug_print("Loading demo sysinfo file...", "DEMO")

    # Load from DemoData directory where all sample TXT files are located
    sysinfo_path = "DemoData/sysinfo.txt"

    if os.path.exists(sysinfo_path):
        try:
            with open(sysinfo_path, 'r', encoding='utf-8') as f:
                content = f.read()
            debug_print(f"✓ Loaded DemoData/sysinfo.txt ({len(content)} chars)", "DEMO")
            return content
        except Exception as e:
            debug_print(f"✗ Error reading DemoData/sysinfo.txt: {e}", "DEMO")
            return None
    else:
        debug_print("✗ DemoData/sysinfo.txt not found", "DEMO")
        return None

def parse_demo_sysinfo_simple(sysinfo_content):
    """Simple parser for demo sysinfo content"""
    if not sysinfo_content:
        return None

    parsed = {
        'device_info': {},
        'thermal_info': {},
        'fan_info': {},
        'power_info': {},
        'error_info': {},
        'link_info': {},
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'data_fresh': True
    }

    # Parse device info (ver section)
    sn_match = re.search(r'S/N\s*:\s*([A-Za-z0-9]+)', sysinfo_content)
    if sn_match:
        parsed['device_info']['Serial Number'] = sn_match.group(1)

    company_match = re.search(r'Company\s*:\s*([^,\n]+)', sysinfo_content)
    if company_match:
        parsed['device_info']['Company'] = company_match.group(1).strip()

    model_match = re.search(r'Model\s*:\s*([^\n]+)', sysinfo_content)
    if model_match:
        parsed['device_info']['Model'] = model_match.group(1).strip()

    version_match = re.search(r'Version\s*:\s*([\d\.]+)\s+Date\s*:\s*(.+?)(?:\n|$)', sysinfo_content)
    if version_match:
        parsed['device_info']['Firmware Version'] = version_match.group(1)
        parsed['device_info']['Build Date'] = version_match.group(2).strip()

    sbr_match = re.search(r'SBR\s*Version\s*:\s*([\d\s]+)', sysinfo_content)
    if sbr_match:
        parsed['device_info']['SBR Version'] = sbr_match.group(1).strip()

    # Parse thermal info (lsd section)
    temp_match = re.search(r'Board\s+Temperature\s*:\s*(\d+)\s*degree', sysinfo_content)
    if temp_match:
        parsed['thermal_info']['Board Temperature'] = f"{temp_match.group(1)}°C"

    # Parse fan info (lsd section)
    fan_match = re.search(r'Switch\s+Fan\s*:\s*(\d+)\s*rpm', sysinfo_content)
    if fan_match:
        parsed['fan_info']['Switch Fan Speed'] = f"{fan_match.group(1)} rpm"

    # Parse power info (lsd section)
    voltage_patterns = [
        (r'Board\s+0\.8V\s+Voltage\s*:\s*(\d+)\s*mV', '0.8V Rail'),
        (r'Board\s+0\.89V\s+Voltage\s*:\s*(\d+)\s*mV', '0.89V Rail'),
        (r'Board\s+1\.2V\s+Voltage\s*:\s*(\d+)\s*mV', '1.2V Rail'),
        (r'Board\s+1\.5v\s+Voltage\s*:\s*(\d+)\s*mV', '1.5V Rail')
    ]

    for pattern, label in voltage_patterns:
        match = re.search(pattern, sysinfo_content)
        if match:
            parsed['power_info'][label] = f"{match.group(1)} mV"

    current_match = re.search(r'Current\s*:\s*(\d+)\s*mA', sysinfo_content)
    if current_match:
        parsed['power_info']['Current Draw'] = f"{current_match.group(1)} mA"

    # Parse error info (lsd section)
    error_patterns = [
        (r'Voltage\s+0\.8V\s+error\s*:\s*(\d+)', '0.8V Rail Errors'),
        (r'Voltage\s+0\.89V\s+error\s*:\s*(\d+)', '0.89V Rail Errors'),
        (r'Voltage\s+1\.2V\s+error\s*:\s*(\d+)', '1.2V Rail Errors'),
        (r'Voltage\s+1\.5V\s+error\s*:\s*(\d+)', '1.5V Rail Errors')
    ]

    for pattern, label in error_patterns:
        match = re.search(pattern, sysinfo_content)
        if match:
            parsed['error_info'][label] = match.group(1)

    # Parse link info (showport section)
    port_pattern = r'Port(\d+)\s*:\s*speed\s+(\w+)'
    port_matches = re.findall(port_pattern, sysinfo_content)

    for port_num, speed in port_matches:
        status = "✅ Active" if speed != '00' else "❌ Inactive"
        parsed['link_info'][f'Port {port_num}'] = status

    golden_match = re.search(r'Golden\s+finger:\s*speed\s+(\w+)', sysinfo_content)
    if golden_match:
        status = "✅ Active" if golden_match.group(1) != '00' else "❌ Inactive"
        parsed['link_info']['Golden Finger'] = status

    print(
        f"DEBUG: Parsed demo sysinfo - {len(parsed['device_info'])} device fields, {len(parsed['link_info'])} link fields")
    return parsed


def get_window_title(subtitle="", demo_mode=False):
    """Generate window title with proper branding"""
    base_title = f"{APP_NAME} {APP_VERSION}"

    if subtitle:
        base_title += f" - {subtitle}"

    if demo_mode:
        base_title += " 🎭 [DEMO MODE]"

    return base_title


class SerialCLI:
    """Background CLI handler for serial communication with caching support"""

    def __init__(self, port, cache_manager=None):
        self.port = port
        self.cache_manager = cache_manager  # Store cache manager reference
        self.is_running = False

        # Initialize queues
        self.command_queue = queue.Queue()
        self.response_queue = queue.Queue()  # CRITICAL: Must have this
        self.log_queue = queue.Queue()

        # Serial connection setup
        self.serial_connection = None
        self.baudrate = 115200

    def connect(self):
        """Enhanced connection method with demo mode support"""
        debug_info("Starting device connection", "CONNECTION")

        if self.demo_var.get():
            debug_info("Demo mode selected", "DEMO_CONNECTION")
            self.status_label.config(text="Starting enhanced demo mode...")
            self.root.update()
            self.root.after(1000, lambda: self.open_dashboard("DEMO"))
            return

        selected_port = self.port_var.get()
        if not selected_port:
            debug_error("No COM port selected", "CONNECTION_ERROR")
            messagebox.showerror("Error", "Please select a COM port")
            return

        debug_info(f"Connecting to real device: {selected_port}", "REAL_CONNECTION")
        self.status_label.config(text="Connecting...")
        self.root.update()

        # Test connection (with cache manager for real connections)
        cache_manager = DeviceDataCache()
        cli = SerialCLI(selected_port, cache_manager=cache_manager)

        if cli.connect():
            cli.disconnect()
            self.status_label.config(text="Connection successful!")
            debug_info(f"Connection successful to {selected_port}", "CONNECTION_SUCCESS")
            self.root.after(1000, lambda: self.open_dashboard(selected_port))
        else:
            self.status_label.config(text="Connection failed")
            debug_error(f"Connection failed to {selected_port}", "CONNECTION_FAILED")
            messagebox.showerror("Connection Error",
                                 f"Failed to connect to {selected_port}\n\nPlease check:\n"
                                 "• Device is connected\n• Port is not in use\n• Correct port selected")

    def disconnect(self):
        """Close serial connection"""
        self.is_running = False
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()

    def send_command(self, command):
        """Send command to device"""
        if self.serial_connection and self.is_running:
            try:
                self.serial_connection.write(f"{command}\r\n".encode())
                self.log_queue.put(f"SENT: {command}")
                return True
            except Exception as e:
                self.log_queue.put(f"Send error: {str(e)}")
                return False
        return False

    def read_response(self):
        """UPDATED: Make sure this puts responses in response_queue"""
        if self.serial_connection and self.is_running:
            try:
                if self.serial_connection.in_waiting > 0:
                    response = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()

                    if response:
                        # Put in log queue
                        self.log_queue.put(f"RECV: {response}")

                        # CRITICAL: Also put in response_queue for advanced handler
                        self.response_queue.put(response)

                        return response

            except Exception as e:
                self.log_queue.put(f"Read error: {str(e)}")

        return None

    def run_background(self):
        """Background thread for handling serial communication"""
        while self.is_running:
            # Handle outgoing commands
            try:
                command = self.command_queue.get_nowait()
                self.send_command(command)
            except queue.Empty:
                pass

            # Handle incoming responses
            self.read_response()
            time.sleep(0.01)  # Small delay to prevent CPU spinning


class ConnectionWindow:
    """Modified ConnectionWindow with demo mode support"""

    def __init__(self, root, settings_manager):
        self.root = root
        self.settings_mgr = settings_manager
        self.demo_var = tk.BooleanVar()

        self.demo_var.set(self.settings_mgr.get('demo', 'enabled_by_default', False))

        self.setup_window()
        self.create_widgets()
        self.refresh_ports()

    def create_demo_option(self, main_frame):
        """Add demo mode option to connection window"""
        demo_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        demo_frame.pack(fill='x', pady=15)

        # Create demo mode checkbox
        self.demo_var = tk.BooleanVar()

        # Configure demo checkbox style
        style = ttk.Style()
        style.configure('Demo.TCheckbutton',
                        background='#1e1e1e',
                        foreground='#ff9500',
                        font=('Arial', 11, 'bold'))

        demo_check = ttk.Checkbutton(demo_frame,
                                     text="🎭 Demo Mode (No hardware required)",
                                     variable=self.demo_var,
                                     style='Demo.TCheckbutton',
                                     command=self.on_demo_toggle)
        demo_check.pack(anchor='w')

        # Demo mode description
        self.demo_info = ttk.Label(demo_frame,
                                   text="• Perfect for training and testing without real hardware\n• All features work with simulated responses\n• Safe environment for learning the interface",
                                   style='Modern.TLabel',
                                   font=('Arial', 9),
                                   justify='left')
        self.demo_info.pack(anchor='w', padx=(25, 0), pady=(5, 0))

    def on_demo_toggle(self):
        """Handle demo mode checkbox toggle"""
        if self.demo_var.get():
            # Demo mode enabled
            self.port_combo.config(state='disabled')
            self.status_label.config(text="Demo mode enabled - click Connect to start training session")
        else:
            # Demo mode disabled
            self.port_combo.config(state='readonly')
            self.refresh_ports()

    def setup_window(self):
        self.root.title(get_window_title("Device Connection"))

        # Set icon if available
        try:
            self.root.iconbitmap("assets/Logo_gal_ico.ico")
        except:
            pass

        # Use window size from settings - UPDATED
        window_width = self.settings_mgr.get('ui', 'window_width', 600)
        window_height = self.settings_mgr.get('ui', 'window_height', 600)

        # Get screen dimensions for centering
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Center the window
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2

        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(480, 420)
        self.root.configure(bg='#1e1e1e')

        # Configure style
        self.setup_styles()

    def setup_styles(self):
        """Configure styles using settings"""
        style = ttk.Style()

        # Get theme from settings
        theme = self.settings_mgr.get('ui', 'theme', 'dark')
        if theme == 'dark':
            style.theme_use('clam')
            style.configure('Modern.TFrame', background='#1e1e1e')
            style.configure('Modern.TLabel', background='#1e1e1e', foreground='#ffffff',
                            font=('Arial', 12))
        else:  # light theme
            style.theme_use('default')
            style.configure('Modern.TFrame', background='#ffffff')
            style.configure('Modern.TLabel', background='#ffffff', foreground='#000000',
                            font=('Arial', 12))

        style.configure('Modern.TCombobox', font=('Arial', 11))
        style.configure('Connect.TButton', font=('Arial', 12, 'bold'))

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, style='Modern.TFrame', padding=40)
        main_frame.pack(fill='both', expand=True)

        # Title with settings gear icon
        title_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        title_frame.pack(fill='x', pady=(0, 30))

        title_label = ttk.Label(title_frame, text="🔌 Device Connection",
                                style='Modern.TLabel', font=('Arial', 18, 'bold'))
        title_label.pack(side='left')

        # Settings gear icon button
        settings_btn = ttk.Button(title_frame, text="⚙️", width=3,
                                  command=self.open_settings)
        settings_btn.pack(side='right')

        # COM Port selection with enhanced refresh
        port_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        port_frame.pack(fill='x', pady=10)

        ttk.Label(port_frame, text="COM Port:", style='Modern.TLabel').pack(anchor='w')

        port_select_frame = ttk.Frame(port_frame, style='Modern.TFrame')
        port_select_frame.pack(fill='x', pady=(5, 0))

        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(port_select_frame, textvariable=self.port_var,
                                       state='readonly', font=('Arial', 11))
        self.port_combo.pack(side='left', fill='x', expand=True)

        # Enhanced refresh button with animation
        self.refresh_btn = ttk.Button(port_select_frame, text="🔄", width=3,
                                      command=self.refresh_ports_with_feedback)
        self.refresh_btn.pack(side='right', padx=(5, 0))

        # Port status frame for better feedback
        port_status_frame = ttk.Frame(port_frame, style='Modern.TFrame')
        port_status_frame.pack(fill='x', pady=(5, 0))

        self.port_status_label = ttk.Label(port_status_frame, text="",
                                           style='Modern.TLabel', font=('Arial', 9))
        self.port_status_label.pack(anchor='w')

        # Demo mode section
        self.create_demo_option(main_frame)

        # Connect button
        connect_btn = ttk.Button(main_frame, text="Connect to Device",
                                 style='Connect.TButton', command=self.connect)
        connect_btn.pack(pady=30)

        # Status label
        self.status_label = ttk.Label(main_frame, text="Select a COM port to continue",
                                      style='Modern.TLabel')
        self.status_label.pack(pady=10)

        # Auto-refresh option
        auto_refresh_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        auto_refresh_frame.pack(fill='x', pady=(20, 0))

        self.auto_refresh_var = tk.BooleanVar()
        auto_refresh_check = ttk.Checkbutton(auto_refresh_frame,
                                             text="🔄 Auto-refresh COM ports every 3 seconds",
                                             variable=self.auto_refresh_var,
                                             command=self.toggle_auto_refresh)
        auto_refresh_check.pack(anchor='w')

        # Initial port scan
        self.refresh_ports()

    def open_settings(self):
        """Open settings dialog"""

        def on_settings_changed():
            # Reload window settings
            self.setup_styles()

        SettingsDialog(self.root, self.settings_mgr, on_settings_changed)

    def refresh_ports(self):
        """Refresh available COM ports"""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports:
            self.port_combo.set(ports[0])
            self.status_label.config(text=f"Found {len(ports)} COM port(s)")
        else:
            self.status_label.config(text="No COM ports detected")

    def connect(self):
        """Attempt to connect to selected COM port or start demo mode"""
        if self.demo_var.get():
            self.status_label.config(text="Starting demo mode...")
            self.root.update()
            self.root.after(1000, lambda: self.open_dashboard("DEMO"))
            return

        selected_port = self.port_var.get()
        if not selected_port:
            messagebox.showerror("Error", "Please select a COM port")
            return

        self.status_label.config(text="Connecting...")
        self.root.update()

        # Test connection (with cache manager for real connections) - UPDATED
        cache_manager = DeviceDataCache()
        cli = SerialCLI(selected_port, cache_manager=cache_manager)
        if cli.connect():
            cli.disconnect()
            self.status_label.config(text="Connection successful!")
            self.root.after(1000, lambda: self.open_dashboard(selected_port))
        else:
            self.status_label.config(text="Connection failed")
            messagebox.showerror("Connection Error",
                                 f"Failed to connect to {selected_port}\n\nPlease check:\n"
                                 "• Device is connected\n• Port is not in use\n• Correct port selected")

    def open_dashboard(self, port):
        """Open the main dashboard window with 80% screen sizing for large displays"""
        # Get screen dimensions before destroying connection window
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        print(f"DEBUG: Detected screen resolution: {screen_width}x{screen_height}")

        self.root.destroy()
        dashboard_root = tk.Tk()

        # Force the window to be maximized state for large displays
        # For 2400x1600, this ensures we get a properly large window
        try:
            dashboard_root.state('zoomed')  # Windows maximize
            print("DEBUG: Window set to maximized state")
        except:
            print("DEBUG: Maximize failed, using manual sizing")

        # Also set explicit geometry as backup
        window_width = int(screen_width * 0.85)  # Slightly larger - 85%
        window_height = int(screen_height * 0.85)
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2

        # Set geometry and then maximize
        dashboard_root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        dashboard_root.minsize(1400, 1000)  # Much larger minimum for high-res displays

        print(f"DEBUG: Opening dashboard with size {window_width}x{window_height} at position {x},{y}")
        print(f"DEBUG: For your 2400x1600 display, this should be approximately 2040x1360")

        # Ensure window is properly sized before creating DashboardApp
        dashboard_root.update_idletasks()

        DashboardApp(dashboard_root, port, self.settings_mgr)
        dashboard_root.mainloop()

    def refresh_ports_with_feedback(self):
        """Enhanced refresh with visual feedback"""
        # Disable button and show refreshing state
        self.refresh_btn.config(state='disabled', text="⟳")
        self.port_status_label.config(text="🔄 Scanning for COM ports...")
        self.root.update()

        # Store current selection
        current_selection = self.port_var.get()

        # Perform refresh
        try:
            ports = [port.device for port in serial.tools.list_ports.comports()]

            # Update combo box
            self.port_combo['values'] = ports

            if ports:
                # Try to maintain previous selection if still available
                if current_selection in ports:
                    self.port_combo.set(current_selection)
                    self.port_status_label.config(text=f"✅ {len(ports)} port(s) found - Previous selection maintained")
                else:
                    # Select first port if previous selection no longer available
                    self.port_combo.set(ports[0])
                    if current_selection:
                        self.port_status_label.config(
                            text=f"⚠️ {len(ports)} port(s) found - Previous port {current_selection} no longer available")
                    else:
                        self.port_status_label.config(text=f"✅ {len(ports)} port(s) found")

                self.status_label.config(text=f"Found {len(ports)} COM port(s) - Ready to connect")
            else:
                self.port_combo.set("")
                self.port_status_label.config(text="❌ No COM ports detected")
                self.status_label.config(text="No COM ports detected - Connect a device and refresh")

        except Exception as e:
            self.port_status_label.config(text=f"❌ Error scanning ports: {str(e)}")
            self.status_label.config(text="Error scanning COM ports")

        # Re-enable button
        self.refresh_btn.config(state='normal', text="🔄")

    def refresh_ports(self):
        """Standard refresh method (backwards compatibility)"""
        self.refresh_ports_with_feedback()

    def toggle_auto_refresh(self):
        """Toggle automatic COM port refresh"""
        if self.auto_refresh_var.get():
            self.start_auto_refresh()
            self.port_status_label.config(text="🔄 Auto-refresh enabled - checking every 3 seconds")
        else:
            self.stop_auto_refresh()
            self.port_status_label.config(text="Auto-refresh disabled")

    def start_auto_refresh(self):
        """Start automatic COM port refresh"""
        if hasattr(self, 'auto_refresh_job'):
            self.root.after_cancel(self.auto_refresh_job)

        def auto_refresh_task():
            if self.auto_refresh_var.get():
                current_ports = set(port.device for port in serial.tools.list_ports.comports())
                current_combo_ports = set(self.port_combo['values'])

                # Only refresh if ports have changed
                if current_ports != current_combo_ports:
                    self.refresh_ports_with_feedback()

                # Schedule next refresh
                self.auto_refresh_job = self.root.after(3000, auto_refresh_task)

        auto_refresh_task()

    def stop_auto_refresh(self):
        """Stop automatic COM port refresh"""
        if hasattr(self, 'auto_refresh_job'):
            self.root.after_cancel(self.auto_refresh_job)
            delattr(self, 'auto_refresh_job')

    def create_demo_option(self, main_frame):
        """Add demo mode option to connection window"""
        demo_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        demo_frame.pack(fill='x', pady=15)

        # Create demo mode checkbox
        self.demo_var = tk.BooleanVar()
        self.demo_var.set(self.settings_mgr.get('demo', 'enabled_by_default', False))

        # Configure demo checkbox style
        style = ttk.Style()
        style.configure('Demo.TCheckbutton',
                        background='#1e1e1e',
                        foreground='#ff9500',
                        font=('Arial', 11, 'bold'))

        demo_check = ttk.Checkbutton(demo_frame,
                                     text="🎭 Demo Mode (No hardware required)",
                                     variable=self.demo_var,
                                     style='Demo.TCheckbutton',
                                     command=self.on_demo_toggle)
        demo_check.pack(anchor='w')

        # Demo mode description
        self.demo_info = ttk.Label(demo_frame,
                                   text="• Perfect for training and testing without real hardware\n• All features work with simulated responses\n• Safe environment for learning the interface",
                                   style='Modern.TLabel',
                                   font=('Arial', 9),
                                   justify='left')
        self.demo_info.pack(anchor='w', padx=(25, 0), pady=(5, 0))

    def on_demo_toggle(self):
        """Handle demo mode checkbox toggle"""
        if self.demo_var.get():
            # Demo mode enabled - disable COM port controls
            self.port_combo.config(state='disabled')
            self.refresh_btn.config(state='disabled')
            self.auto_refresh_var.set(False)
            self.stop_auto_refresh()
            self.status_label.config(text="Demo mode enabled - click Connect to start training session")
            self.port_status_label.config(text="🎭 Demo mode active - COM port scanning disabled")
        else:
            # Demo mode disabled - re-enable COM port controls
            self.port_combo.config(state='readonly')
            self.refresh_btn.config(state='normal')
            self.refresh_ports()

    def __del__(self):
        """Cleanup when window is destroyed"""
        if hasattr(self, 'auto_refresh_job'):
            try:
                self.root.after_cancel(self.auto_refresh_job)
            except:
                pass


class DashboardApp:
    """Main dashboard app with proper CLI initialization"""

    def __init__(self, root, port, settings_manager):
        self.root = root
        self.port = port
        self.settings_mgr = settings_manager
        self.is_demo_mode = (port == "DEMO")

        debug_info(f"Initializing DashboardApp for {'Demo' if self.is_demo_mode else 'Real'} mode", "DASHBOARD_INIT")

        # Initialize cache manager first
        cache_dir = self.settings_mgr.get('cache', 'cache_directory', '')
        cache_ttl = self.settings_mgr.get('cache', 'default_ttl_seconds', 300)
        self.cache_manager = DeviceDataCache(cache_dir or None, cache_ttl)

        # Enhanced CLI initialization based on mode
        if self.is_demo_mode:
            # Import enhanced demo CLI
            try:
                from Dashboards.demo_mode_integration import create_enhanced_demo_cli
                self.cli = create_enhanced_demo_cli(
                    port=port,
                    cache_manager=self.cache_manager,
                    settings_manager=self.settings_mgr
                )
                debug_info("Using Enhanced UnifiedDemoSerialCLI for demo mode", "CLI_ENHANCED_DEMO")

                # Start background thread for demo CLI
                if hasattr(self.cli, 'run_background'):
                    self.demo_bg_thread = threading.Thread(target=self.cli.run_background, daemon=True)
                    self.demo_bg_thread.start()
                    debug_info("Demo background thread started", "DEMO_BG_THREAD")

            except ImportError as e:
                debug_error(f"Enhanced demo CLI import failed: {e}", "CLI_IMPORT_ERROR")
                # Fallback to basic demo CLI
                from Dashboards.demo_mode_integration import UnifiedDemoSerialCLI
                self.cli = UnifiedDemoSerialCLI(port)
                debug_warning("Using basic UnifiedDemoSerialCLI as fallback", "CLI_FALLBACK")
        else:
            self.cli = SerialCLI(port, cache_manager=self.cache_manager)
            debug_info("Using SerialCLI for real device", "CLI_REAL_DEVICE")

        # Initialize parser with cache manager
        self.sysinfo_parser = EnhancedSystemInfoParser(self.cache_manager)

        # Initialize the advanced response handler
        self.init_advanced_response_handler()

        # Initialize Host Card Info components
        self.host_card_manager = HostCardInfoManager(self.cli)
        self.host_card_ui = HostCardDashboardUI(self)

        # Initialize Link Status components
        self.link_status_ui = LinkStatusDashboardUI(self)

        # Initialize Port Status components
        self.port_status_manager = PortStatusManager(self.cli)
        self.port_status_ui = PortStatusDashboardUI(self)

        # Initialize Resets Dashboard components
        self.resets_dashboard = ResetsDashboard(self)

        # Initialize Firmware Dashboard
        self.firmware_dashboard = FirmwareDashboard(self)

        # Demo device state for port status (if demo mode)
        self.demo_device_state = {'current_mode': 0}

        # Rest of initialization...
        self.log_data = []
        self.current_dashboard = "host"

        # Auto-refresh setup
        self.auto_refresh_enabled = self.settings_mgr.get('refresh', 'enabled', False)
        self.auto_refresh_interval = self.settings_mgr.get('refresh', 'interval_seconds', 30)
        self.auto_refresh_timer = None

        # Background task control
        self.background_tasks_enabled = True
        self.sysinfo_requested = False
        self.showport_requested = False

        self.setup_window()
        self.create_layout()
        self.connect_device()
        self.start_background_threads()

        if self.auto_refresh_enabled:
            self.start_auto_refresh()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def init_advanced_response_handler(self):
        """Initialize the advanced response handler"""
        try:
            self.response_handler = AdvancedResponseHandler(self)
            print("DEBUG: Advanced Response Handler integrated with DashboardApp")
        except Exception as e:
            print(f"ERROR: Failed to initialize Advanced Response Handler: {e}")
            # Fallback to basic handling if advanced handler fails
            self.response_handler = None

    def setup_window(self):
        """Configure the main dashboard window with 85% screen resolution"""
        title = get_window_title(APP_DESCRIPTION, self.is_demo_mode)
        self.root.title(title)

        # Set icon if available
        try:
            self.root.iconbitmap("assets/Logo_gal_ico.ico")
        except:
            pass

        # Calculate 85% of screen resolution for much larger window
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        window_width = int(screen_width * 0.85)
        window_height = int(screen_height * 0.85)

        # Center the window on screen
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2

        print(
            f"DEBUG: Setting dashboard window size to {window_width}x{window_height} (85% of {screen_width}x{screen_height})")

        # Position window with calculated size and position
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Try to maximize the window for best experience
        try:
            self.root.state('zoomed')
            print("DEBUG: Dashboard window maximized")
        except:
            print("DEBUG: Dashboard maximize failed, using manual size")

        self.root.configure(bg='#1e1e1e')
        # Set minimum size to be reasonable but allow large windows
        self.root.minsize(1400, 1000)  # Much larger minimum for 2400x1600 displays

        # Configure styles
        self.setup_styles()

    def setup_styles(self):
        """Configure modern UI styles based on settings"""
        style = ttk.Style()

        # Get theme from settings - NEW
        theme = self.settings_mgr.get('ui', 'theme', 'dark')
        if theme == 'dark':
            style.theme_use('clam')
            # Dark theme styles
            style.configure('Sidebar.TFrame', background='#2d2d2d')
            style.configure('Content.TFrame', background='#1e1e1e')
            style.configure('Dashboard.TLabel', background='#1e1e1e', foreground='#ffffff',
                            font=('Arial', 14, 'bold'))
            style.configure('Info.TLabel', background='#1e1e1e', foreground='#cccccc',
                            font=('Arial', 10))
        else:
            style.theme_use('default')
            # Light theme styles
            style.configure('Sidebar.TFrame', background='#f0f0f0')
            style.configure('Content.TFrame', background='#ffffff')
            style.configure('Dashboard.TLabel', background='#ffffff', foreground='#000000',
                            font=('Arial', 14, 'bold'))
            style.configure('Info.TLabel', background='#ffffff', foreground='#333333',
                            font=('Arial', 10))

        # Dashboard tile styles (keep existing)
        style.configure('Tile.TFrame', background='#3d3d3d', relief='flat')
        style.configure('ActiveTile.TFrame', background='#0078d4', relief='flat')
        style.configure('Tile.TLabel', background='#3d3d3d', foreground='#ffffff',
                        font=('Arial', 10, 'bold'))
        style.configure('ActiveTile.TLabel', background='#0078d4', foreground='#ffffff',
                        font=('Arial', 10, 'bold'))

    def create_layout(self):
        """Create the main application layout"""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True)

        # Sidebar for dashboard navigation
        self.sidebar = ttk.Frame(main_frame, style='Sidebar.TFrame', width=200)
        self.sidebar.pack(side='left', fill='y', padx=(0, 1))
        self.sidebar.pack_propagate(False)

        # Content area
        self.content_frame = ttk.Frame(main_frame, style='Content.TFrame')
        self.content_frame.pack(side='right', fill='both', expand=True)

        self.create_sidebar()
        self.create_content_area()

    def create_sidebar(self):
        """Create the sidebar with dashboard tiles"""
        # Header - simplified without settings gear
        header_frame = ttk.Frame(self.sidebar, style='Sidebar.TFrame')
        header_frame.pack(fill='x', padx=10, pady=10)

        ttk.Label(header_frame, text="📊 Dashboards",
                  background='#2d2d2d', foreground='#ffffff',
                  font=('Arial', 12, 'bold')).pack()

        # Dashboard tiles (existing code stays the same)
        self.dashboards = [
            ("host", "💻", "Host Card Information"),
            ("link", "🔗", "Link Status"),
            ("port", "🔌", "Port Configuration"),
            ("compliance", "✅", "Compliance"),
            ("registers", "📋", "Registers"),
            ("advanced", "⚙️", "Advanced"),
            ("resets", "🔄", "Resets"),
            ("firmware", "📦", "Firmware Updates"),
            ("help", "❓", "Help")
        ]

        self.tile_frames = {}
        for dashboard_id, icon, title in self.dashboards:
            self.create_dashboard_tile(dashboard_id, icon, title)

        # *** CONNECTION STATUS WITH DEMO MODE INDICATOR ***
        status_frame = ttk.Frame(self.sidebar, style='Sidebar.TFrame')
        status_frame.pack(side='bottom', fill='x', padx=10, pady=10)

        # Set status text and color based on mode
        if self.is_demo_mode:
            status_text = "🎭 DEMO MODE"
            status_color = '#ff9500'  # Orange for demo
        else:
            status_text = f"🔌 {self.port}"
            status_color = '#00ff00'  # Green for real connection

        self.connection_label = ttk.Label(status_frame,
                                          text=status_text,
                                          background='#2d2d2d',
                                          foreground=status_color,
                                          font=('Arial', 9, 'bold'))
        self.connection_label.pack()

        # *** ADD DEMO MODE INFO ***
        if self.is_demo_mode:
            demo_info_label = ttk.Label(status_frame,
                                        text="Training Environment",
                                        background='#2d2d2d',
                                        foreground='#cccccc',
                                        font=('Arial', 8))
            demo_info_label.pack()

        # Add settings access hint
        hint_label = ttk.Label(status_frame,
                               text="Settings: ⚙️ (top right)",
                               background='#2d2d2d',
                               foreground='#888888',
                               font=('Arial', 7))
        hint_label.pack(pady=(5, 0))

    def create_dashboard_tile(self, dashboard_id, icon, title):
        """Create an individual dashboard tile"""
        tile_frame = ttk.Frame(self.sidebar, style='Tile.TFrame', cursor='hand2')
        tile_frame.pack(fill='x', padx=10, pady=2)

        # Tile content
        content_frame = ttk.Frame(tile_frame, style='Tile.TFrame')
        content_frame.pack(fill='both', expand=True, padx=15, pady=10)

        icon_label = ttk.Label(content_frame, text=icon, style='Tile.TLabel',
                               font=('Arial', 16))
        icon_label.pack()

        title_label = ttk.Label(content_frame, text=title, style='Tile.TLabel',
                                font=('Arial', 8))
        title_label.pack()

        # Store references
        self.tile_frames[dashboard_id] = {
            'frame': tile_frame,
            'content': content_frame,
            'icon': icon_label,
            'title': title_label
        }

        # Bind click events
        for widget in [tile_frame, content_frame, icon_label, title_label]:
            widget.bind('<Button-1>', lambda e, d=dashboard_id: self.switch_dashboard(d))

        # Set initial active state
        if dashboard_id == self.current_dashboard:
            self.set_tile_active(dashboard_id, True)

    def set_tile_active(self, dashboard_id, active):
        """Set tile active/inactive appearance"""
        tile = self.tile_frames[dashboard_id]
        style_prefix = 'ActiveTile' if active else 'Tile'

        for widget_name in ['frame', 'content']:
            tile[widget_name].configure(style=f'{style_prefix}.TFrame')

        for widget_name in ['icon', 'title']:
            tile[widget_name].configure(style=f'{style_prefix}.TLabel')

    def switch_dashboard(self, dashboard_id):
        """Switch to a different dashboard with automatic command execution"""
        if dashboard_id == self.current_dashboard:
            return

        # Update tile appearances
        self.set_tile_active(self.current_dashboard, False)
        self.set_tile_active(dashboard_id, True)

        self.current_dashboard = dashboard_id

        # Send appropriate command when switching to specific dashboards
        if dashboard_id == "link":
            print("DEBUG: Switching to link dashboard - will send showport command")
            # The create_link_dashboard method will handle sending the command
        elif dashboard_id == "host":
            # Warm cache if needed before updating content
            cache_warmed = self.warm_cache_if_needed()
            if cache_warmed:
                self.update_cache_status("Loading fresh data...")

        # Update content area
        self.update_content_area()

    def create_content_area(self):
        """Create the main content display area"""
        # Header
        header_frame = ttk.Frame(self.content_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=20, pady=20)

        self.content_title = ttk.Label(header_frame, text="Host Card Information",
                                       style='Dashboard.TLabel')
        self.content_title.pack(side='left')

        # Right side button group
        button_group = ttk.Frame(header_frame, style='Content.TFrame')
        button_group.pack(side='right')

        # Settings button
        self.settings_btn = ttk.Button(button_group, text="⚙️", width=3,
                                       command=self.open_settings)
        self.settings_btn.pack(side='right', padx=(5, 0))

        # Refresh button for current dashboard
        self.refresh_btn = ttk.Button(button_group, text="🔄", width=3,
                                      command=self.refresh_current_dashboard)
        self.refresh_btn.pack(side='right')

        # Cache status indicator (between title and buttons)
        self.cache_status_label = ttk.Label(header_frame, text="",
                                            style='Info.TLabel', font=('Arial', 8))
        self.cache_status_label.pack(side='right', padx=(20, 10))

        # Scrollable content area
        canvas = tk.Canvas(self.content_frame, bg='#1e1e1e', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.content_frame, orient='vertical', command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas, style='Content.TFrame')

        self.scrollable_frame.bind('<Configure>',
                                   lambda e: canvas.configure(scrollregion=canvas.bbox('all')))

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side='left', fill='both', expand=True, padx=20, pady=(0, 20))
        scrollbar.pack(side='right', fill='y', pady=(0, 20))

        self.content_canvas = canvas
        self.update_content_area()

    def update_content_area(self):
        """Update content area based on current dashboard"""
        # Clear existing content
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Update title
        dashboard_titles = {
            "host": "💻 Host Card Information",
            "link": "🔗 Link Status",
            "port": "🔌 Port Configuration",
            "compliance": "✅ Compliance",
            "registers": "📋 Registers",
            "advanced": "⚙️ Advanced",
            "resets": "🔄 Resets",  # Updated title
            "firmware": "📦 Firmware Updates",
            "help": "❓ Help"
        }

        self.content_title.config(text=dashboard_titles[self.current_dashboard])

        # Update cache status
        self.update_cache_status()

        # Create dashboard-specific content
        if self.current_dashboard == "host":
            self.create_host_dashboard()
        elif self.current_dashboard == "link":
            self.create_link_dashboard()
        elif self.current_dashboard == "port":
            self.create_port_dashboard()
        elif self.current_dashboard == "compliance":
            self.create_compliance_dashboard()
        elif self.current_dashboard == "registers":
            self.create_registers_dashboard()
        elif self.current_dashboard == "advanced":
            self.create_advanced_dashboard()
        elif self.current_dashboard == "resets":
            self.create_resets_dashboard()
        elif self.current_dashboard == "firmware":
            self.create_firmware_dashboard()
        elif self.current_dashboard == "help":
            self.create_help_dashboard()

    def create_info_card(self, parent, title, content):
        """Create a styled information card"""
        card_frame = ttk.Frame(parent, style='Content.TFrame', relief='solid', borderwidth=1)
        card_frame.pack(fill='x', pady=10)

        # Card header
        header_frame = ttk.Frame(card_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=15, pady=(15, 10))

        ttk.Label(header_frame, text=title, style='Dashboard.TLabel',
                  font=('Arial', 12, 'bold')).pack(anchor='w')

        # Card content
        content_frame = ttk.Frame(card_frame, style='Content.TFrame')
        content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        if isinstance(content, str):
            ttk.Label(content_frame, text=content, style='Info.TLabel').pack(anchor='w')
        else:
            content(content_frame)

        return card_frame

    def refresh_current_dashboard(self):
        """Refresh current dashboard with cache-first approach"""
        dashboard_name = self.current_dashboard

        if dashboard_name == "port":
            # Special handling for port dashboard
            self.port_status_manager.get_port_status_info(force_refresh=True)
            self.update_content_area()
            self.update_cache_status("Port status refreshed")
        elif dashboard_name == "host":
            # Check if we need fresh data
            if self.sysinfo_parser.force_refresh_needed():
                # Clear old cache and request fresh data
                self.sysinfo_parser.invalidate_all_data()
                self.send_sysinfo_command()
                self.update_cache_status("Requesting fresh data...")
            else:
                # Use cached data and update UI immediately
                self.update_content_area()
                self.update_cache_status("Using cached data")
        else:
            # Other dashboards - use existing logic
            self.update_content_area()

        # Log the refresh
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_data.append(f"[{timestamp}] Refreshed {dashboard_name} dashboard")

    def update_cache_status(self, message=""):
        """Update cache status with more detailed information"""
        if not message and self.cache_manager:
            stats = self.cache_manager.get_stats()
            # Check data freshness
            is_fresh = self.sysinfo_parser.is_data_fresh(300)
            freshness = "Fresh" if is_fresh else "Stale"
            message = f"Cache: {stats['valid_entries']} entries ({freshness})"

        self.cache_status_label.config(text=message)

        # Clear status message after 3 seconds for temporary messages
        if any(word in message for word in ["Cleared", "Requesting", "Fresh data loaded"]):
            self.root.after(3000, lambda: self.update_cache_status())

    def warm_cache_if_needed(self):
        """Warm cache if data is stale or missing"""
        if self.sysinfo_parser.force_refresh_needed():
            self.send_sysinfo_command()
            return True
        return False

    def start_auto_refresh(self):
        """Start auto-refresh timer"""
        if self.auto_refresh_enabled:
            dashboard_enabled = self.settings_mgr.get('refresh', 'dashboards', {}).get(
                self.current_dashboard, False)

            if dashboard_enabled:
                self.refresh_current_dashboard()

            # Schedule next refresh
            self.auto_refresh_timer = self.root.after(
                self.auto_refresh_interval * 1000,
                self.start_auto_refresh
            )

    def stop_auto_refresh(self):
        """Stop auto-refresh timer"""
        if self.auto_refresh_timer:
            self.root.after_cancel(self.auto_refresh_timer)
            self.auto_refresh_timer = None

    def open_settings(self):
        """Open settings dialog"""

        def on_settings_changed():
            # Reload settings-dependent features
            self.auto_refresh_enabled = self.settings_mgr.get('refresh', 'enabled', False)
            self.auto_refresh_interval = self.settings_mgr.get('refresh', 'interval_seconds', 30)

            # Restart auto-refresh with new settings
            self.stop_auto_refresh()
            if self.auto_refresh_enabled:
                self.start_auto_refresh()

            # Update cache manager settings
            cache_ttl = self.settings_mgr.get('cache', 'default_ttl_seconds', 300)
            if hasattr(self.cache_manager, 'default_ttl'):
                self.cache_manager.default_ttl = cache_ttl

            # Update UI theme
            self.setup_styles()

        SettingsDialog(self.root, self.settings_mgr, on_settings_changed)

    def check_sysinfo_timeout(self):
        """
        IMPROVED: Timeout handling with advanced response handler
        """
        # The advanced handler manages its own timeouts, but we keep this for compatibility
        if self.sysinfo_requested:
            print("DEBUG: Checking sysinfo timeout...")

            # Check if advanced handler is managing this
            if hasattr(self, 'response_handler') and self.response_handler:
                status = self.response_handler.get_status()
                if status['active_buffers'] > 0:
                    print("DEBUG: Advanced handler has active buffers, letting it manage timeout")
                    return

            # Fallback timeout handling
            print("DEBUG: Fallback timeout - no active advanced handler buffers")
            self.sysinfo_requested = False
            self.show_loading_message("Request timed out. Click refresh to try again.")
            self.update_cache_status("Request timed out")

    def process_sysinfo_response(self, response):
        """
        Process sysinfo response from queue monitoring
        """
        try:
            print(f"DEBUG: Processing sysinfo response ({len(response)} chars)")

            # Parse using the enhanced parser
            parsed_data = self.sysinfo_parser.parse_unified_sysinfo(
                response,
                "demo" if self.is_demo_mode else "device"
            )

            print(f"DEBUG: Sysinfo parsed successfully")

            # Reset request flag
            self.sysinfo_requested = False

            # Update UI on main thread
            self.root.after_idle(self.update_content_area)
            self.update_cache_status("Fresh data loaded")

            # Log success
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.log_data.append(f"[{timestamp}] System information updated successfully")

        except Exception as e:
            print(f"ERROR: Failed to process sysinfo response: {e}")

            # Reset request flag
            self.sysinfo_requested = False

            # Show error in UI
            self.show_loading_message(f"Error processing response: {e}")

            # Log error
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.log_data.append(f"[{timestamp}] Error processing sysinfo: {e}")

    def create_host_dashboard(self):
        """Create host card information dashboard with enhanced Demo Mode support"""
        debug_info("Creating host dashboard", "HOST_DASHBOARD_CREATE")

        if self.is_demo_mode:
            # Enhanced Demo Mode - use Admin-integrated demo CLI
            try:
                from Dashboards.demo_mode_integration import get_demo_host_card_data
                host_data = get_demo_host_card_data(self.cli)

                if host_data:
                    debug_info("Using enhanced demo data for host dashboard", "HOST_DEMO_DATA")
                    sections = host_data.get('sections', {})

                    # Clear existing content
                    for widget in self.scrollable_frame.winfo_children():
                        widget.destroy()

                    # Create sections from parsed data
                    for section_key, section_data in sections.items():
                        icon = section_data.get('icon', '📄')
                        title = section_data.get('title', section_key.replace('_', ' ').title())
                        fields = section_data.get('fields', {})

                        # Convert dict to list of tuples for display
                        field_items = list(fields.items())
                        self.create_host_info_section(icon, title, field_items)

                    # Add last updated info
                    last_updated = host_data.get('last_updated', 'Unknown')
                    self.create_refresh_info(last_updated, True)

                    debug_info("Host dashboard created from enhanced demo data", "HOST_DEMO_SUCCESS")
                    return

            except Exception as e:
                debug_error(f"Enhanced demo host dashboard failed: {e}", "HOST_DEMO_ERROR")
                # Fall through to existing logic

        # Existing logic for real device mode or demo fallback
        if self.is_demo_mode:
            # Original demo mode logic as fallback
            try:
                demo_content = getattr(self.cli, 'demo_sysinfo_content', None)

                if demo_content and len(demo_content) > 100:
                    debug_info(f"Using demo content directly ({len(demo_content)} chars)", "HOST_DEMO_FALLBACK")

                    # Parse using existing parser
                    parsed_data = self.sysinfo_parser.parse_unified_sysinfo(demo_content, "demo")
                    debug_info("Demo data parsed successfully", "HOST_DEMO_PARSED")

                    # Use existing dashboard creation logic
                    host_json = self.sysinfo_parser.get_host_card_json()
                    if host_json:
                        sections = host_json.get('sections', {})
                        for section_key, section_data in sections.items():
                            icon = section_data.get('icon', '📄')
                            title = section_data.get('title', section_key)
                            fields = section_data.get('fields', {})
                            field_items = list(fields.items())
                            self.create_host_info_section(icon, title, field_items)

                        last_updated = host_json.get('last_updated', 'Unknown')
                        self.create_refresh_info(last_updated, True)
                    else:
                        self.show_demo_fallback()
                else:
                    debug_info("No demo content, showing fallback", "HOST_DEMO_NO_CONTENT")
                    self.show_demo_fallback()

            except Exception as e:
                debug_error(f"Demo mode fallback failed: {e}", "HOST_DEMO_FALLBACK_ERROR")
                self.show_demo_fallback()
        else:
            # Real device mode - existing logic
            cached_data = self.sysinfo_parser.get_complete_sysinfo()

            if cached_data and self.sysinfo_parser.is_data_fresh(300):
                debug_info("Using fresh cached data for host dashboard", "HOST_CACHED")
                host_info = self.sysinfo_parser.get_host_info_for_display()
                # Create sections from host_info... (existing code)
            else:
                debug_info("No fresh cached data, requesting sysinfo", "HOST_REQUEST")
                self.send_sysinfo_command()
                self.show_loading_message("Loading host card information...")

    def create_link_status_dashboard(self):
        """Create link status dashboard with proper Admin integration"""
        debug_info("Creating link status dashboard", "LINK_DASHBOARD_CREATE")

        if self.is_demo_mode:
            # Enhanced Demo Mode - try multiple data sources
            debug_info("Demo mode - attempting to load link status data", "DEMO_LINK_LOAD")

            try:
                # Method 1: Try enhanced demo CLI first
                if hasattr(self.cli, 'get_link_status_data'):
                    link_data = self.cli.get_link_status_data()
                    if link_data:
                        debug_info("Using enhanced CLI link data", "DEMO_CLI_DATA")
                        self._create_link_dashboard_from_enhanced_data(link_data)
                        return

                # Method 2: Check if sysinfo was already parsed and cached
                link_json = self.sysinfo_parser.get_link_status_json()
                if link_json and link_json.get('data_fresh', False):
                    debug_info("Using cached link status JSON from sysinfo", "DEMO_CACHED_JSON")
                    self._create_link_dashboard_from_enhanced_data(link_json)
                    return

                # Method 3: Try to extract showport from demo sysinfo content
                demo_content = getattr(self.cli, 'demo_sysinfo_content', None)
                if demo_content:
                    debug_info("Extracting showport from demo sysinfo content", "DEMO_EXTRACT_SHOWPORT")
                    showport_content = self._extract_showport_from_sysinfo(demo_content)

                    if showport_content:
                        # Parse the showport content
                        self.sysinfo_parser.parse_showport_command(showport_content)

                        # Get the newly cached data
                        link_json = self.sysinfo_parser.get_link_status_json()
                        if link_json:
                            debug_info("Successfully parsed showport from sysinfo", "DEMO_SHOWPORT_PARSED")
                            self._create_link_dashboard_from_enhanced_data(link_json)
                            return

                # Method 4: Load separate showport file
                debug_info("Loading separate demo showport file", "DEMO_SHOWPORT_FILE")
                showport_content = self._load_demo_showport_file()
                if showport_content:
                    # Parse and use the showport file
                    self.sysinfo_parser.parse_showport_command(showport_content)
                    link_json = self.sysinfo_parser.get_link_status_json()
                    if link_json:
                        debug_info("Successfully loaded showport from file", "DEMO_SHOWPORT_FILE_SUCCESS")
                        self._create_link_dashboard_from_enhanced_data(link_json)
                        return

                # Method 5: Create fallback demo data
                debug_warning("Using fallback demo link data", "DEMO_LINK_FALLBACK")
                self._create_link_dashboard_fallback()

            except Exception as e:
                debug_error(f"Demo link dashboard creation failed: {e}", "DEMO_LINK_ERROR")
                import traceback
                traceback.print_exc()
                self._create_link_dashboard_fallback()
        else:
            # Real device mode
            debug_info("Real device mode - checking for cached link data", "REAL_LINK_CHECK")

            # Check for cached data first
            link_json = self.sysinfo_parser.get_link_status_json()
            if link_json and self.sysinfo_parser.is_data_fresh(300):
                debug_info("Using fresh cached link data", "REAL_LINK_CACHED")
                self._create_link_dashboard_from_enhanced_data(link_json)
            else:
                debug_info("No fresh link data, requesting showport", "REAL_LINK_REQUEST")
                self.send_showport_command()
                self.show_loading_message("Loading link status...")

    def _create_link_dashboard_from_enhanced_data(self, link_data):
        """Create link dashboard from enhanced parser JSON data"""
        debug_info("Creating link dashboard from enhanced data", "LINK_CREATE_ENHANCED")

        try:
            # Import the existing Link Status dashboard components
            from Dashboards.link_status_dashboard import LinkStatusParser, PortInfo

            # Clear existing content
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()

            # Get sections from enhanced data
            sections = link_data.get('sections', {})
            port_status_section = sections.get('port_status', {})
            items = port_status_section.get('items', [])

            if not items:
                debug_warning("No port items found in enhanced data", "LINK_NO_ITEMS")
                self._create_link_dashboard_fallback()
                return

            debug_info(f"Processing {len(items)} port items", "LINK_PROCESS_ITEMS")

            # Create header
            header_frame = ttk.Frame(self.scrollable_frame, style='Content.TFrame')
            header_frame.pack(fill='x', padx=20, pady=(20, 10))

            header_label = ttk.Label(header_frame, text="🔗 Link Status",
                                     style='SectionHeader.TLabel',
                                     font=('Arial', 24, 'bold'))
            header_label.pack(anchor='w')

            # Process each port item and create display
            for item in items:
                self._create_enhanced_port_row(item)

            # Add refresh controls
            self._create_link_refresh_controls(link_data.get('last_updated', 'Unknown'))

            debug_info("Link dashboard created from enhanced data successfully", "LINK_CREATE_SUCCESS")

        except Exception as e:
            debug_error(f"Enhanced link dashboard creation failed: {e}", "LINK_CREATE_ERROR")
            import traceback
            traceback.print_exc()
            self._create_link_dashboard_fallback()

    def _create_enhanced_port_row(self, item):
        """Create port row from enhanced parser item data"""
        debug_info(f"Creating enhanced port row for: {item.get('label', 'Unknown')}", "PORT_ROW_CREATE")

        try:
            # Extract information from the enhanced parser item format
            port_label = item.get('label', 'Unknown Port')
            port_value = item.get('value', 'Unknown')
            port_details = item.get('details', '')

            # Parse the details to extract speed and width information
            speed_level = "00"
            width = "00"
            max_speed = "00"
            max_width = "00"

            # Extract speed level from details
            speed_match = re.search(r'Speed:\s*Level\s*(\d+)', port_details, re.IGNORECASE)
            if speed_match:
                speed_level = speed_match.group(1).zfill(2)

            # Extract width from details
            width_match = re.search(r'Width:\s*(\d+)', port_details, re.IGNORECASE)
            if width_match:
                width = width_match.group(1).zfill(2)

            # Extract max width from details
            max_width_match = re.search(r'Max Width:\s*(\d+)', port_details, re.IGNORECASE)
            if max_width_match:
                max_width = max_width_match.group(1)

            # Determine display values using the existing Link Status logic
            display_speed, display_width, status_color, active = self._process_port_display_logic(
                speed_level, width, max_width
            )

            # Create the port display row
            self._create_port_display_row(
                port_name=port_label,
                display_speed=display_speed,
                display_width=display_width,
                status_color=status_color,
                active=active
            )

        except Exception as e:
            debug_error(f"Enhanced port row creation failed: {e}", "PORT_ROW_ERROR")

    def _process_port_display_logic(self, speed_level, width, max_width):
        """Process port display logic using existing Link Status dashboard logic"""

        # Check for no link condition first (speed 01, width 00)
        if speed_level == "01" and width == "00":
            return "No Link", "", "#ff4444", False  # Red for no link

        # Speed mappings with proper Gen6/Gen5 colors
        speed_mappings = {
            "06": ("Gen6", "#00ff00"),  # Green for Gen6
            "05": ("Gen5", "#ff9500"),  # Yellow/Orange for Gen5
            "04": ("Gen4", "#ff9500"),  # Yellow/Orange for Gen4
            "03": ("Gen3", "#ff9500"),  # Yellow/Orange for Gen3
            "02": ("Gen2", "#ff9500"),  # Yellow/Orange for Gen2
            "01": ("Gen1", "#ff4444"),  # Red for Gen1
        }

        # Get display speed and color
        if speed_level in speed_mappings:
            display_speed, status_color = speed_mappings[speed_level]
            active = True
        else:
            display_speed = f"Level {speed_level}"
            status_color = "#cccccc"  # Gray for unknown
            active = False

        # Process width display
        if width in ["02", "04", "08", "16"]:
            display_width = f"x{width}"
        else:
            display_width = f"x{width}" if width != "00" else ""

        return display_speed, display_width, status_color, active

    def _create_port_display_row(self, port_name, display_speed, display_width, status_color, active):
        """Create the visual port display row"""
        debug_info(f"Creating port display: {port_name} - {display_speed} {display_width}", "PORT_DISPLAY")

        # Create main row frame
        row_frame = ttk.Frame(self.scrollable_frame, style='Content.TFrame')
        row_frame.pack(fill='x', padx=40, pady=8)

        # Port name (left side)
        name_frame = ttk.Frame(row_frame, style='Content.TFrame')
        name_frame.pack(side='left', fill='x', expand=True)

        name_label = ttk.Label(name_frame, text=port_name,
                               style='Info.TLabel', font=('Arial', 20, 'bold'))
        name_label.pack(side='left')

        # Status indicators (right side)
        status_frame = ttk.Frame(row_frame, style='Content.TFrame')
        status_frame.pack(side='right')

        # Active checkbox with proper styling (matches existing Link Status dashboard)
        if active:
            checkbox_frame = ttk.Frame(status_frame, style='Content.TFrame')
            checkbox_frame.pack(side='right', padx=(30, 0))

            active_var = tk.BooleanVar(value=True)
            active_check = ttk.Checkbutton(checkbox_frame, variable=active_var, state='disabled')
            active_check.pack(side='left')

            # Green "Active" text for active ports
            active_label = ttk.Label(checkbox_frame, text="Active",
                                     foreground='#00ff00', background='#1e1e1e',
                                     font=('Arial', 16, 'bold'))
            active_label.pack(side='left', padx=(8, 0))
        else:
            active_var = tk.BooleanVar(value=False)
            active_check = ttk.Checkbutton(status_frame, text="Active",
                                           variable=active_var, state='disabled')
            active_check.pack(side='right', padx=(30, 0))

        # Status light and text (matches existing dashboard)
        status_info_frame = ttk.Frame(status_frame, style='Content.TFrame')
        status_info_frame.pack(side='right', padx=(30, 30))

        # Create status light (colored circle) - Gen6=green, Gen5=yellow
        status_canvas = tk.Canvas(status_info_frame, width=28, height=28,
                                  bg='#1e1e1e', highlightthickness=0)
        status_canvas.pack(side='left', padx=(0, 15))
        status_canvas.create_oval(4, 4, 24, 24, fill=status_color, outline='')

        # Speed and width text
        if display_speed == "No Link":
            status_text = "No Link"
        else:
            status_text = f"{display_speed}{' ' + display_width if display_width else ''}"

        status_label = ttk.Label(status_info_frame, text=status_text,
                                 style='Info.TLabel', font=('Arial', 18, 'bold'))
        status_label.pack(side='left')

    def _create_link_dashboard_from_showport_content(self, showport_content):
        """Create link dashboard from raw showport content"""
        debug_info("Creating link dashboard from showport content", "LINK_CREATE_SHOWPORT")

        try:
            # Parse showport content using existing link status parser
            from Dashboards.link_status_dashboard import LinkStatusParser
            parser = LinkStatusParser()
            link_info = parser.parse_showport_response(showport_content)

            # Clear existing content
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()

            # Create header
            self._create_link_section_header("🔗", "Link Status")

            # Create port displays
            for port_key, port_info in link_info.ports.items():
                self._create_port_status_display(port_info)

            # Create golden finger display
            if link_info.golden_finger and link_info.golden_finger.port_number:
                self._create_port_status_display(link_info.golden_finger)

            # Add refresh controls
            self._create_link_refresh_controls(link_info.last_updated)

            debug_info("Link dashboard created from showport content successfully", "LINK_SHOWPORT_SUCCESS")

        except Exception as e:
            debug_error(f"Showport content link dashboard creation failed: {e}", "LINK_SHOWPORT_ERROR")
            self._create_link_dashboard_fallback()

    def _extract_showport_from_sysinfo(self, sysinfo_content):
        """Extract showport section from sysinfo content"""
        debug_info("Extracting showport section from sysinfo", "EXTRACT_SHOWPORT")

        try:
            # Look for showport section using multiple patterns
            patterns = [
                r'showport\s*=+\s*(.*?)(?:\s*=+|$)',
                r'================================================================================\s*showport\s*================================================================================\s*(.*?)(?:\s*================================================================================|$)',
                r'showport\s*-+\s*(.*?)(?:\s*-+|$)'
            ]

            for pattern in patterns:
                match = re.search(pattern, sysinfo_content, re.DOTALL | re.IGNORECASE)
                if match:
                    showport_content = match.group(1).strip()
                    debug_info(f"Extracted showport section ({len(showport_content)} chars)", "SHOWPORT_EXTRACTED")
                    return showport_content

            debug_warning("No showport section found in sysinfo content", "SHOWPORT_NOT_FOUND")
            return None

        except Exception as e:
            debug_error(f"Failed to extract showport from sysinfo: {e}", "EXTRACT_SHOWPORT_ERROR")
            return None

    def _load_demo_showport_file(self):
        """Load showport.txt from DemoData directory"""
        debug_info("Loading demo showport file", "LOAD_SHOWPORT_FILE")

        showport_paths = [
            "DemoData/showport.txt",
            "./DemoData/showport.txt",
            "../DemoData/showport.txt",
            os.path.join(os.path.dirname(__file__), "DemoData", "showport.txt"),
            os.path.join(os.getcwd(), "DemoData", "showport.txt")
        ]

        for i, path in enumerate(showport_paths):
            abs_path = os.path.abspath(path)
            debug_info(f"Checking showport path {i + 1}: {abs_path}", "SHOWPORT_PATH_CHECK")

            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    debug_info(f"Loaded demo showport from {path} ({len(content)} chars)", "SHOWPORT_FILE_LOADED")
                    return content
                except Exception as e:
                    debug_error(f"Error loading showport {path}: {e}", "SHOWPORT_FILE_ERROR")
                    continue
            else:
                debug_info(f"Showport file not found: {abs_path}", "SHOWPORT_FILE_NOT_FOUND")

        debug_warning("No showport file found", "SHOWPORT_FILE_MISSING")
        return None

    def _create_link_section_header(self, icon, title):
        """Create section header for link status"""
        header_frame = ttk.Frame(self.scrollable_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=20, pady=(20, 10))

        header_label = ttk.Label(header_frame, text=f"{icon} {title}",
                                 style='SectionHeader.TLabel',
                                 font=('Arial', 24, 'bold'))
        header_label.pack(anchor='w')

    def _create_enhanced_port_display(self, item):
        """Create enhanced port display from enhanced parser data"""
        debug_info(f"Creating enhanced port display for: {item}", "PORT_DISPLAY")

        try:
            # Extract port information from enhanced data format
            port_name = item.get('name', 'Unknown Port')
            speed_info = item.get('speed', {})
            width_info = item.get('width', {})
            status_info = item.get('status', {})

            # Create the port display row
            self._create_port_row(
                port_name=port_name,
                speed_level=speed_info.get('level', '00'),
                width=width_info.get('value', '00'),
                display_speed=speed_info.get('display', 'Unknown'),
                display_width=width_info.get('display', ''),
                status=status_info.get('status', 'Unknown'),
                status_color=status_info.get('color', '#cccccc'),
                active=status_info.get('active', False)
            )

        except Exception as e:
            debug_error(f"Enhanced port display creation failed: {e}", "PORT_DISPLAY_ERROR")

    def _create_port_status_display(self, port_info):
        """Create port status display from LinkStatusParser PortInfo"""
        debug_info(f"Creating port status display for: {port_info.port_number}", "PORT_STATUS_DISPLAY")

        self._create_port_row(
            port_name=f"Port {port_info.port_number}" if port_info.port_number != "Golden Finger" else port_info.port_number,
            speed_level=port_info.speed_level,
            width=port_info.width,
            display_speed=port_info.display_speed,
            display_width=port_info.display_width,
            status=port_info.status,
            status_color=port_info.status_color,
            active=port_info.active
        )

    def _create_port_row(self, port_name, speed_level, width, display_speed, display_width, status, status_color,
                         active):
        """Create a port row with proper Gen6/Gen5 formatting"""
        debug_info(f"Creating port row: {port_name} - {display_speed} {display_width}", "PORT_ROW")

        # Create main row frame
        row_frame = ttk.Frame(self.scrollable_frame, style='Content.TFrame')
        row_frame.pack(fill='x', padx=40, pady=8)

        # Port name (left side)
        name_frame = ttk.Frame(row_frame, style='Content.TFrame')
        name_frame.pack(side='left', fill='x', expand=True)

        name_label = ttk.Label(name_frame, text=port_name,
                               style='Info.TLabel', font=('Arial', 20, 'bold'))
        name_label.pack(side='left')

        # Status indicators (right side)
        status_frame = ttk.Frame(row_frame, style='Content.TFrame')
        status_frame.pack(side='right')

        # Active checkbox with proper styling
        if active:
            checkbox_frame = ttk.Frame(status_frame, style='Content.TFrame')
            checkbox_frame.pack(side='right', padx=(30, 0))

            active_var = tk.BooleanVar(value=True)
            active_check = ttk.Checkbutton(checkbox_frame, variable=active_var, state='disabled')
            active_check.pack(side='left')

            # Green "Active" text for active ports
            active_label = ttk.Label(checkbox_frame, text="Active",
                                     foreground='#00ff00', background='#1e1e1e',
                                     font=('Arial', 16, 'bold'))
            active_label.pack(side='left', padx=(8, 0))
        else:
            active_var = tk.BooleanVar(value=False)
            active_check = ttk.Checkbutton(status_frame, text="Active",
                                           variable=active_var, state='disabled')
            active_check.pack(side='right', padx=(30, 0))

        # Status light and text
        status_info_frame = ttk.Frame(status_frame, style='Content.TFrame')
        status_info_frame.pack(side='right', padx=(30, 30))

        # Create status light (colored circle) with proper Gen6/Gen5 colors
        status_canvas = tk.Canvas(status_info_frame, width=28, height=28,
                                  bg='#1e1e1e', highlightthickness=0)
        status_canvas.pack(side='left', padx=(0, 15))

        # Use the status color from the parser (Gen6=green, Gen5=yellow/orange)
        status_canvas.create_oval(4, 4, 24, 24, fill=status_color, outline='')

        # Speed and width display
        if display_speed == "No Link":
            status_text = "No Link"
        else:
            width_text = f" {display_width}" if display_width else ""
            status_text = f"{display_speed}{width_text}"

        status_label = ttk.Label(status_info_frame, text=status_text,
                                 style='Info.TLabel', font=('Arial', 18, 'bold'))
        status_label.pack(side='left')

    def _create_link_refresh_controls(self, last_updated):
        """Create refresh controls for link status"""
        controls_frame = ttk.Frame(self.scrollable_frame, style='Content.TFrame')
        controls_frame.pack(fill='x', side='bottom', padx=20, pady=10)

        # Refresh button
        refresh_btn = ttk.Button(controls_frame, text="🔄 Refresh Link Status",
                                 command=self.refresh_link_status_enhanced)
        refresh_btn.pack(side='left')

        # Last update time
        if last_updated and last_updated != 'Unknown':
            update_label = ttk.Label(controls_frame,
                                     text=f"Last updated: {last_updated}",
                                     style='Info.TLabel', font=('Arial', 10))
            update_label.pack(side='right')

    def _create_link_dashboard_fallback(self):
        """Create fallback link dashboard with proper Gen6/Gen5 demo data"""
        debug_info("Creating fallback link dashboard with demo data", "LINK_FALLBACK")

        # Clear existing content
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Create header
        header_frame = ttk.Frame(self.scrollable_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=20, pady=(20, 10))

        header_label = ttk.Label(header_frame, text="🔗 Link Status (Demo)",
                                 style='SectionHeader.TLabel',
                                 font=('Arial', 24, 'bold'))
        header_label.pack(anchor='w')

        # Create demo ports with proper Gen6/Gen5 formatting from DemoData/showport.txt format
        demo_ports = [
            {
                "name": "Port 80",
                "display_speed": "Gen6",
                "display_width": "x4",
                "status_color": "#00ff00",  # Green for Gen6
                "active": True
            },
            {
                "name": "Port 112",
                "display_speed": "No Link",
                "display_width": "",
                "status_color": "#ff4444",  # Red for No Link
                "active": False
            },
            {
                "name": "Port 128",
                "display_speed": "Gen5",
                "display_width": "x16",
                "status_color": "#ff9500",  # Yellow/Orange for Gen5
                "active": True
            },
            {
                "name": "Golden Finger",
                "display_speed": "Gen6",
                "display_width": "x16",
                "status_color": "#00ff00",  # Green for Gen6
                "active": True
            }
        ]

        for port in demo_ports:
            self._create_port_display_row(
                port_name=port["name"],
                display_speed=port["display_speed"],
                display_width=port["display_width"],
                status_color=port["status_color"],
                active=port["active"]
            )

        # Add refresh controls
        self._create_link_refresh_controls("Demo Mode - Fallback Data")

        debug_info("Fallback link dashboard created successfully", "LINK_FALLBACK_SUCCESS")

    def send_sysinfo_command_enhanced(self, force_refresh=False):
        """Enhanced sysinfo command with Demo Mode Admin integration"""
        debug_info(f"Sending enhanced sysinfo command (force={force_refresh})", "SYSINFO_ENHANCED")

        if self.sysinfo_requested:
            debug_info("Sysinfo already requested, skipping", "SYSINFO_SKIP")
            return

        self.sysinfo_requested = True

        if self.is_demo_mode:
            # Enhanced Demo Mode
            try:
                # Check if enhanced CLI has fresh data
                if hasattr(self.cli, 'is_data_fresh') and not force_refresh:
                    if self.cli.is_data_fresh(300):  # 5 minutes
                        debug_info("Using fresh enhanced demo data", "DEMO_FRESH")
                        self.process_enhanced_demo_sysinfo_success()
                        self.sysinfo_requested = False
                        return

                # Execute sysinfo command through enhanced CLI
                def enhanced_demo_background():
                    try:
                        # Use enhanced CLI's sysinfo command
                        response = self.cli.send_command("sysinfo", timeout=5)

                        if response and len(response) > 100:
                            # Process successful response
                            self.root.after_idle(self.process_enhanced_demo_sysinfo_success)
                        else:
                            self.root.after_idle(lambda: self.process_sysinfo_error("Enhanced demo sysinfo failed"))

                    except Exception as e:
                        self.root.after_idle(lambda: self.process_sysinfo_error(str(e)))
                    finally:
                        self.sysinfo_requested = False

                threading.Thread(target=enhanced_demo_background, daemon=True).start()
                debug_info("Enhanced demo sysinfo command started", "DEMO_SYSINFO_STARTED")

            except Exception as e:
                debug_error(f"Enhanced demo sysinfo failed: {e}", "DEMO_SYSINFO_ERROR")
                self.sysinfo_requested = False
        else:
            # Real device mode - use existing send_sysinfo_command logic
            self.send_sysinfo_command()

    def process_enhanced_demo_sysinfo_success(self):
        """Process successful enhanced demo sysinfo execution"""
        debug_info("Processing enhanced demo sysinfo success", "DEMO_SUCCESS")

        try:
            # Log success
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.log_data.append(f"[{timestamp}] Enhanced demo sysinfo completed successfully")

            # Update UI
            self.root.after_idle(self.update_content_area)
            self.update_cache_status("Fresh enhanced demo data loaded")

            debug_info("Enhanced demo sysinfo success processing completed", "DEMO_SUCCESS_DONE")

        except Exception as e:
            debug_error(f"Enhanced demo success processing failed: {e}", "DEMO_SUCCESS_ERROR")

    def refresh_host_info_enhanced(self):
        """Enhanced refresh for host card information"""
        debug_info("Refreshing host info with enhanced support", "HOST_REFRESH_ENHANCED")

        try:
            if self.is_demo_mode and hasattr(self.cli, 'force_refresh_data'):
                # Force refresh demo data
                if self.cli.force_refresh_data():
                    debug_info("Demo data force refreshed", "DEMO_FORCE_REFRESH")
                else:
                    debug_error("Demo data force refresh failed", "DEMO_FORCE_REFRESH_ERROR")

            # Use enhanced sysinfo command if available
            if hasattr(self, 'send_sysinfo_command_enhanced'):
                self.send_sysinfo_command_enhanced(force_refresh=True)
            else:
                # Fallback to regular refresh
                if hasattr(self.host_card_manager, 'get_host_card_info'):
                    self.host_card_manager.get_host_card_info(force_refresh=True)

            # Refresh the dashboard display if we're currently on host dashboard
            if self.current_dashboard == "host":
                self.update_content_area()

            # Log the refresh action
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.log_data.append(f"[{timestamp}] Enhanced host card info refreshed")

        except Exception as e:
            error_msg = f"Failed to refresh enhanced host info: {str(e)}"
            self.log_data.append(f"[{datetime.now().strftime('%H:%M:%S')}] {error_msg}")
            debug_error(error_msg, "HOST_REFRESH_ERROR")
            messagebox.showerror("Refresh Error", error_msg)

    def refresh_link_status_enhanced(self):
        """Enhanced refresh for link status information"""
        debug_info("Refreshing link status with enhanced support", "LINK_REFRESH")

        try:
            if self.is_demo_mode and hasattr(self.cli, 'force_refresh_data'):
                # Force refresh demo data
                self.cli.force_refresh_data()

            # Use enhanced sysinfo command for showport data
            if hasattr(self, 'send_sysinfo_command_enhanced'):
                self.send_sysinfo_command_enhanced(force_refresh=True)
            else:
                # Fallback to recreating dashboard
                self.create_link_status_dashboard()

            # Log the refresh action
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.log_data.append(f"[{timestamp}] Enhanced link status refreshed")

        except Exception as e:
            error_msg = f"Failed to refresh enhanced link status: {str(e)}"
            self.log_data.append(f"[{datetime.now().strftime('%H:%M:%S')}] {error_msg}")
            debug_error(error_msg, "LINK_REFRESH_ERROR")
            messagebox.showerror("Refresh Error", error_msg)

    def get_demo_data_with_fallback(self, data_type="host"):
        """Get demo data with fallback to original methods"""
        if not self.is_demo_mode:
            return None

        debug_info(f"Getting demo data with fallback for: {data_type}", "DEMO_DATA_FALLBACK")

        try:
            # Try enhanced methods first
            if data_type == "host":
                from Dashboards.demo_mode_integration import get_demo_host_card_data
                enhanced_data = get_demo_host_card_data(self.cli)
                if enhanced_data:
                    debug_info("Using enhanced host card data", "ENHANCED_DATA")
                    return enhanced_data

            elif data_type == "link":
                from Dashboards.demo_mode_integration import get_demo_link_status_data
                enhanced_data = get_demo_link_status_data(self.cli)
                if enhanced_data:
                    debug_info("Using enhanced link status data", "ENHANCED_DATA")
                    return enhanced_data

            # Fallback to original demo data methods
            debug_info(f"Using fallback demo data for {data_type}", "FALLBACK_DATA")

            # Use existing demo content parsing
            demo_content = getattr(self.cli, 'demo_sysinfo_content', None)
            if demo_content:
                parsed_data = self.sysinfo_parser.parse_unified_sysinfo(demo_content, "demo")

                if data_type == "host":
                    return self.sysinfo_parser.get_host_card_json()
                elif data_type == "link":
                    return self.sysinfo_parser.get_link_status_json()

            return None

        except Exception as e:
            debug_error(f"Demo data retrieval failed for {data_type}: {e}", "DEMO_DATA_ERROR")
            return None

    def create_host_info_section(self, icon, section_title, section_data):
        """Create a section with enhanced data validation"""
        # Create section frame
        section_frame = ttk.Frame(self.scrollable_frame, style='Content.TFrame',
                                  relief='solid', borderwidth=1)
        section_frame.pack(fill='x', pady=10)

        # Section header with icon
        header_frame = ttk.Frame(section_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=15, pady=(15, 10))

        header_label = ttk.Label(header_frame, text=f"{icon} {section_title}",
                                 style='Dashboard.TLabel', font=('Arial', 12, 'bold'))
        header_label.pack(anchor='w')

        # Section content
        content_frame = ttk.Frame(section_frame, style='Content.TFrame')
        content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        # Display data items with validation
        if section_data:
            items_displayed = 0
            for field_name, value in section_data:
                # Skip empty or "Unknown" values unless it's sample data
                if value and value != "Unknown":
                    self.create_data_row(content_frame, field_name, value)
                    items_displayed += 1

            # If no valid items were displayed, show a message
            if items_displayed == 0:
                no_data_label = ttk.Label(content_frame,
                                          text="Waiting for device data...",
                                          style='Info.TLabel',
                                          font=('Arial', 10, 'italic'))
                no_data_label.pack(anchor='w')
        else:
            # No data available message
            no_data_label = ttk.Label(content_frame,
                                      text="No data available",
                                      style='Info.TLabel',
                                      font=('Arial', 10, 'italic'))
            no_data_label.pack(anchor='w')

    def create_data_row(self, parent, field_name, value):
        """Create a single data row with field name and value"""
        row_frame = ttk.Frame(parent, style='Content.TFrame')
        row_frame.pack(fill='x', pady=3)

        # Field name (left aligned)
        field_label = ttk.Label(row_frame, text=f"{field_name}:",
                                style='Info.TLabel', font=('Arial', 10, 'bold'))
        field_label.pack(side='left')

        # Value (right aligned with status color if applicable)
        value_color = self.get_status_color(field_name, value)

        # Create a custom style for this value if it has a special color
        if value_color != '#cccccc':  # Default color
            style_name = f"Status_{field_name.replace(' ', '_').replace('.', '_')}.TLabel"
            style = ttk.Style()
            style.configure(style_name, background='#1e1e1e',
                            foreground=value_color, font=('Arial', 10))
            value_label = ttk.Label(row_frame, text=value, style=style_name)
        else:
            value_label = ttk.Label(row_frame, text=value, style='Info.TLabel')

        value_label.pack(side='right')

    def get_status_color(self, field_name, value):
        """Get appropriate color for status values"""
        # Temperature status colors
        if "temperature" in field_name.lower():
            try:
                temp_val = int(re.search(r'\d+', str(value)).group())
                if temp_val > 70:
                    return '#ff4444'  # Red for high temp
                elif temp_val > 60:
                    return '#ff9500'  # Orange for warm temp
                else:
                    return '#00ff00'  # Green for normal temp
            except:
                return '#cccccc'

        # Error status colors
        if "error" in field_name.lower():
            try:
                error_count = int(value)
                if error_count > 0:
                    return '#ff4444'  # Red for errors
                else:
                    return '#00ff00'  # Green for no errors
            except:
                return '#cccccc'

        # Voltage status colors
        if "rail" in field_name.lower() and "mv" in str(value).lower():
            try:
                voltage = int(re.search(r'\d+', str(value)).group())
                rail_type = field_name.lower()

                # Basic voltage range checks
                if "0.8v" in rail_type and (voltage < 750 or voltage > 950):
                    return '#ff9500'
                elif "1.2v" in rail_type and (voltage < 1100 or voltage > 1300):
                    return '#ff9500'
                elif "1.5v" in rail_type and (voltage < 1400 or voltage > 1600):
                    return '#ff9500'
                else:
                    return '#00ff00'
            except:
                return '#cccccc'

        # Current status colors
        if "current" in field_name.lower() and "ma" in str(value).lower():
            try:
                current = int(re.search(r'\d+', str(value)).group())
                if current > 15000:
                    return '#ff9500'
                else:
                    return '#00ff00'
            except:
                return '#cccccc'

        return '#cccccc'  # Default color

    def show_loading_message(self, message: str):
        """Show a loading/error message in the content area"""
        # Clear existing content
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        loading_frame = ttk.Frame(self.scrollable_frame, style='Content.TFrame')
        loading_frame.pack(fill='x', pady=20)

        ttk.Label(loading_frame, text=message, style='Info.TLabel',
                  font=('Arial', 12, 'italic')).pack()

        # Add retry button for demo mode
        if self.is_demo_mode:
            ttk.Button(loading_frame, text="🔄 Retry Demo Loading",
                       command=self.retry_demo_connection).pack(pady=(10, 0))

    def retry_demo_connection(self):
        """Retry demo connection"""
        print("DEBUG: Retrying demo connection...")
        try:
            # Try to reconnect and load data
            if hasattr(self.cli, 'demo_sysinfo_content') and self.cli.demo_sysinfo_content:
                demo_content = self.cli.demo_sysinfo_content
                parsed_data = self.sysinfo_parser.parse_unified_sysinfo(demo_content, "demo")
                self.update_content_area()
                self.update_cache_status("Demo data loaded")

                timestamp = datetime.now().strftime('%H:%M:%S')
                self.log_data.append(f"[{timestamp}] Demo retry successful")
            else:
                self.show_loading_message("Demo data still not available")

        except Exception as e:
            print(f"ERROR: Demo retry failed: {e}")
            self.show_loading_message(f"Demo retry failed: {e}")

    def create_refresh_info(self, last_updated: str, data_fresh: bool):
        """Create refresh information section with freshness indicator"""
        info_frame = ttk.Frame(self.scrollable_frame, style='Content.TFrame')
        info_frame.pack(fill='x', pady=15)

        # Show data freshness
        freshness_color = '#00ff00' if data_fresh else '#ff9500'
        freshness_text = "Live data" if data_fresh else "Cached data"

        ttk.Label(info_frame, text=f"Last updated: {last_updated} ({freshness_text})",
                  style='Info.TLabel', font=('Arial', 9)).pack(side='left')

        ttk.Button(info_frame, text="🔄 Refresh Data",
                   command=self.refresh_current_dashboard).pack(side='right')

    def create_link_dashboard(self):
        """
        FIXED: Create link status dashboard using showport parsed data
        Replace your existing create_link_dashboard method with this
        """
        debug_print("Creating link status dashboard...", "UI")

        try:
            # Get cached data
            if self.is_demo_mode:
                complete_data = self.cache_manager.get('demo_sysinfo_complete')
            else:
                complete_data = self.sysinfo_parser.get_complete_sysinfo()

            if complete_data:
                showport_section = complete_data.get('showport_section', {})
                debug_print(f"Link data: showport={len(showport_section)}", "UI")

                def link_content(frame):
                    if not showport_section:
                        ttk.Label(frame, text="No port/link data available",
                                  style='Info.TLabel', font=('Arial', 10, 'italic')).pack(anchor='w')
                        return

                    # Display ports
                    ports = showport_section.get('ports', {})
                    for port_key, port_info in ports.items():
                        port_num = port_info.get('port_number', '?')
                        status = port_info.get('status', 'Unknown')
                        speed = port_info.get('speed', '00')
                        width = port_info.get('width', '00')

                        # Port status row
                        row_frame = ttk.Frame(frame, style='Content.TFrame')
                        row_frame.pack(fill='x', pady=2)

                        status_text = "✅ Active" if status == 'Active' else "❌ Inactive"

                        ttk.Label(row_frame, text=f"Port {port_num}:", style='Info.TLabel',
                                  font=('Arial', 10, 'bold')).pack(side='left')
                        ttk.Label(row_frame, text=status_text, style='Info.TLabel').pack(side='right')

                        # Port details
                        detail_frame = ttk.Frame(frame, style='Content.TFrame')
                        detail_frame.pack(fill='x', pady=(0, 5))
                        ttk.Label(detail_frame, text=f"    Speed: Level {speed}, Width: {width}",
                                  style='Info.TLabel', font=('Arial', 9)).pack(anchor='w')

                    # Display golden finger
                    golden = showport_section.get('golden_finger', {})
                    if golden:
                        speed = golden.get('speed', '00')
                        width = golden.get('width', '00')
                        status = golden.get('status', 'Unknown')

                        row_frame = ttk.Frame(frame, style='Content.TFrame')
                        row_frame.pack(fill='x', pady=2)

                        status_text = "✅ Active" if status == 'Active' else "❌ Inactive"

                        ttk.Label(row_frame, text="Golden Finger:", style='Info.TLabel',
                                  font=('Arial', 10, 'bold')).pack(side='left')
                        ttk.Label(row_frame, text=status_text, style='Info.TLabel').pack(side='right')

                        detail_frame = ttk.Frame(frame, style='Content.TFrame')
                        detail_frame.pack(fill='x', pady=(0, 5))
                        ttk.Label(detail_frame, text=f"    Speed: Level {speed}, Width: {width}",
                                  style='Info.TLabel', font=('Arial', 9)).pack(anchor='w')

                self.create_info_card(self.scrollable_frame, "🔗 Port and Link Status", link_content)
                debug_print("Link dashboard created successfully", "UI")

            else:
                debug_print("No data available for link dashboard", "UI")
                self.show_loading_message("Loading link status...")
                if not self.is_demo_mode:
                    self.send_sysinfo_command()

        except Exception as e:
            debug_print(f"Error creating link dashboard: {e}", "ERROR")
            self.show_loading_message(f"Link dashboard error: {e}")

    def create_port_dashboard(self):
        """Create port configuration dashboard with real device data"""
        port_debug("Creating port configuration dashboard", "DASHBOARD_INIT")

        # Get cached showport JSON data
        showport_json = self.sysinfo_parser.get_showport_status_json()

        if showport_json and showport_json.get('data_fresh', False):
            port_debug("Using cached showport data for port dashboard", "DATA_SOURCE")
            log_info(f"Port data sections: {list(showport_json.get('sections', {}).keys())}", "port_config")

            # Display port status section
            self.create_port_status_section(showport_json)

            # Display port configuration controls
            self.create_port_configuration_controls()

            # Display link speed and width information
            self.create_link_details_section(showport_json)

            # Add last updated info
            last_updated = showport_json.get('last_updated', 'Unknown')
            self.create_refresh_info(last_updated, True)

            port_debug("Port dashboard created successfully", "DASHBOARD_COMPLETE")

        else:
            # Show loading and request fresh data
            port_debug("No fresh port data available, requesting sysinfo", "DATA_REQUEST")
            self.show_loading_message("Loading port configuration...")
            self.send_sysinfo_command()

    def create_port_status_section(self, showport_json):
        """Create port status display section with debug logging"""
        port_debug("Creating port status section", "STATUS_SECTION")

        ports_data = showport_json.get('sections', {}).get('port_status', {})
        port_debug(f"Port status data contains {len(ports_data.get('items', []))} items", "DATA_ANALYSIS")

        # Create port status card
        port_frame = ttk.Frame(self.scrollable_frame, style='Content.TFrame',
                               relief='solid', borderwidth=1)
        port_frame.pack(fill='x', pady=10)

        # Header
        header_frame = ttk.Frame(port_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=15, pady=(15, 10))

        ttk.Label(header_frame, text="🔌 Port Status Overview",
                  style='Dashboard.TLabel', font=('Arial', 12, 'bold')).pack(anchor='w')

        # Content
        content_frame = ttk.Frame(port_frame, style='Content.TFrame')
        content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        # Display port items
        items = ports_data.get('items', [])
        if items:
            port_debug(f"Displaying {len(items)} port items", "UI_CREATION")
            for i, item in enumerate(items):
                label = item.get('label', 'Unknown Port')
                value = item.get('value', 'Unknown')
                details = item.get('details', '')

                port_debug(f"Port {i + 1}: {label} = {value}", "PORT_ITEM")

                # Create port row
                port_row_frame = ttk.Frame(content_frame, style='Content.TFrame')
                port_row_frame.pack(fill='x', pady=3)

                # Port name and status
                ttk.Label(port_row_frame, text=f"{label}:",
                          style='Info.TLabel', font=('Arial', 10, 'bold')).pack(side='left')

                # Status with color coding
                status_color = self.get_port_status_color(value)
                port_debug(f"Port {label} color: {status_color}", "COLOR_CODING")

                if status_color != '#cccccc':
                    style_name = f"PortStatus_{label.replace(' ', '_')}.TLabel"
                    style = ttk.Style()
                    style.configure(style_name, background='#1e1e1e',
                                    foreground=status_color, font=('Arial', 10))
                    status_label = ttk.Label(port_row_frame, text=value, style=style_name)
                else:
                    status_label = ttk.Label(port_row_frame, text=value, style='Info.TLabel')

                status_label.pack(side='right')

                # Details on separate line if available
                if details:
                    detail_frame = ttk.Frame(content_frame, style='Content.TFrame')
                    detail_frame.pack(fill='x', pady=(0, 5))
                    ttk.Label(detail_frame, text=f"    {details}",
                              style='Info.TLabel', font=('Arial', 9)).pack(anchor='w')
                    port_debug(f"Port {label} details: {details}", "PORT_DETAILS")
        else:
            port_debug("No port data available for display", "NO_DATA")
            ttk.Label(content_frame, text="No port data available",
                      style='Info.TLabel', font=('Arial', 10, 'italic')).pack(anchor='w')

        port_debug("Port status section created", "SECTION_COMPLETE")

    def create_port_configuration_controls(self):
        """Create port configuration controls with debug logging"""
        port_debug("Creating port configuration controls", "CONFIG_CONTROLS")

        config_frame = ttk.Frame(self.scrollable_frame, style='Content.TFrame',
                                 relief='solid', borderwidth=1)
        config_frame.pack(fill='x', pady=20)

        # Header
        header_frame = ttk.Frame(config_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=15, pady=(15, 10))

        ttk.Label(header_frame, text="⚙️ Port Configuration",
                  style='Dashboard.TLabel', font=('Arial', 12, 'bold')).pack(anchor='w')

        # Content
        content_frame = ttk.Frame(config_frame, style='Content.TFrame')
        content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        # Port selection
        port_select_frame = ttk.Frame(content_frame, style='Content.TFrame')
        port_select_frame.pack(fill='x', pady=10)

        ttk.Label(port_select_frame, text="Select Port:",
                  style='Info.TLabel', font=('Arial', 10, 'bold')).pack(side='left')

        self.selected_port = tk.StringVar()
        port_values = ['Port 80', 'Port 112', 'Port 128', 'Golden Finger']
        port_combo = ttk.Combobox(port_select_frame, textvariable=self.selected_port,
                                  values=port_values, state='readonly', width=15)
        port_combo.pack(side='right')
        port_combo.set('Port 80')  # Default selection

        port_debug(f"Port selection dropdown created with values: {port_values}", "UI_CONTROLS")

        # Port mode configuration
        mode_frame = ttk.Frame(content_frame, style='Content.TFrame')
        mode_frame.pack(fill='x', pady=10)

        ttk.Label(mode_frame, text="Port Mode:",
                  style='Info.TLabel', font=('Arial', 10, 'bold')).pack(side='left')

        self.port_mode = tk.StringVar()
        mode_values = ['Auto', 'Forced Speed 1', 'Forced Speed 2', 'Forced Speed 3',
                       'Forced Speed 4', 'Forced Speed 5', 'Forced Speed 6', 'Disabled']
        mode_combo = ttk.Combobox(mode_frame, textvariable=self.port_mode,
                                  values=mode_values, width=15)
        mode_combo.pack(side='right')
        mode_combo.set('Auto')  # Default mode

        port_debug(f"Port mode dropdown created with values: {mode_values}", "UI_CONTROLS")

        # Width configuration
        width_frame = ttk.Frame(content_frame, style='Content.TFrame')
        width_frame.pack(fill='x', pady=10)

        ttk.Label(width_frame, text="Link Width:",
                  style='Info.TLabel', font=('Arial', 10, 'bold')).pack(side='left')

        self.link_width = tk.StringVar()
        width_values = ['Auto', 'x1', 'x2', 'x4', 'x8', 'x16']
        width_combo = ttk.Combobox(width_frame, textvariable=self.link_width,
                                   values=width_values, width=15)
        width_combo.pack(side='right')
        width_combo.set('Auto')  # Default width

        port_debug(f"Link width dropdown created with values: {width_values}", "UI_CONTROLS")

        # Action buttons
        button_frame = ttk.Frame(content_frame, style='Content.TFrame')
        button_frame.pack(fill='x', pady=15)

        ttk.Button(button_frame, text="🔍 Query Current Mode",
                   command=self.get_current_port_mode).pack(side='left', padx=(0, 10))

        ttk.Button(button_frame, text="🔧 Apply Configuration",
                   command=self.apply_port_configuration).pack(side='left', padx=10)

        ttk.Button(button_frame, text="🔄 Reset Port",
                   command=self.reset_port).pack(side='left', padx=10)

        port_debug("Port configuration controls created successfully", "CONTROLS_COMPLETE")

    def create_port_mode_status(self, parent):
        """Create current port mode status section with fixed width"""
        status_frame = ttk.Frame(parent, style='Content.TFrame',
                                 relief='solid', borderwidth=1)
        status_frame.pack(pady=10)
        status_frame.configure(width=600)  # Fixed width

        # Header
        header_frame = ttk.Frame(status_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=15, pady=(15, 10))

        ttk.Label(header_frame, text="⚡ Current Port Mode",
                  style='Dashboard.TLabel', font=('Arial', 12, 'bold')).pack(anchor='w')

        # Content
        content_frame = ttk.Frame(status_frame, style='Content.TFrame')
        content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        # Get current mode data
        current_mode_data = self.get_current_port_mode()

        # Display current mode information
        for field_name, value in current_mode_data.items():
            self.create_data_row(content_frame, field_name, value)

    def create_mode_change_controls(self, parent):
        """Create mode change controls section with fixed width"""
        control_frame = ttk.Frame(parent, style='Content.TFrame',
                                  relief='solid', borderwidth=1)
        control_frame.pack(pady=10)
        control_frame.configure(width=600)  # Fixed width

        # Header
        header_frame = ttk.Frame(control_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=15, pady=(15, 10))

        ttk.Label(header_frame, text="⚙️ Change Host Card Mode",
                  style='Dashboard.TLabel', font=('Arial', 12, 'bold')).pack(anchor='w')

        # Content
        content_frame = ttk.Frame(control_frame, style='Content.TFrame')
        content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        # Mode selection - centered within fixed width
        mode_select_frame = ttk.Frame(content_frame, style='Content.TFrame')
        mode_select_frame.pack(fill='x', pady=10)

        ttk.Label(mode_select_frame, text="Select SBR Mode:",
                  style='Info.TLabel', font=('Arial', 10, 'bold')).pack(side='left')

        self.sbr_mode_var = tk.StringVar(value="SBR0")
        mode_combo = ttk.Combobox(mode_select_frame, textvariable=self.sbr_mode_var,
                                  values=["SBR0", "SBR1", "SBR2", "SBR3", "SBR4", "SBR5", "SBR6"],
                                  state='readonly', width=15)
        mode_combo.pack(side='right')

        # Change button - centered
        button_frame = ttk.Frame(content_frame, style='Content.TFrame')
        button_frame.pack(fill='x', pady=15)

        change_btn = ttk.Button(button_frame, text="Change Host Card Mode",
                                command=self.change_host_card_mode)
        change_btn.pack(anchor='center')

    def create_mode_diagram_section(self, parent):
        """Create mode configuration diagram section with fixed width"""
        diagram_frame = ttk.Frame(parent, style='Content.TFrame',
                                  relief='solid', borderwidth=1)
        diagram_frame.pack(pady=10)
        diagram_frame.configure(width=600)  # Fixed width

        # Header
        header_frame = ttk.Frame(diagram_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=15, pady=(15, 10))

        ttk.Label(header_frame, text="📊 Mode Configuration Diagram",
                  style='Dashboard.TLabel', font=('Arial', 12, 'bold')).pack(anchor='w')

        # Content with image - centered within fixed width
        content_frame = ttk.Frame(diagram_frame, style='Content.TFrame')
        content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        # Try to load and display the configuration image
        self.load_configuration_image(content_frame)

    def load_configuration_image(self, parent_frame):
        """Load configuration diagram image from Images directory"""
        import tkinter as tk
        from PIL import Image, ImageTk

        # Define possible image paths
        image_paths = [
            "Images/SBR0.png",
            "Images/SBR1.png",
            "Images/SBR2.png",
            "Images/SBR3.png",
            "Images/SBR4.png",
            "Images/SBR5.png",
            "Images/SBR6.png"
        ]

        image_loaded = False

        for image_path in image_paths:
            try:
                if os.path.exists(image_path):
                    print(f"DEBUG: Found image at {image_path}")

                    # Load and resize image
                    pil_image = Image.open(image_path)

                    # Resize image to fit in fixed width dashboard (max 500x350)
                    max_width, max_height = 500, 350
                    pil_image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

                    # Convert to Tkinter format
                    self.config_image = ImageTk.PhotoImage(pil_image)

                    # Create image label - centered
                    image_label = ttk.Label(parent_frame, image=self.config_image)
                    image_label.pack(anchor='center', pady=10)

                    # Add image info - centered
                    image_info = f"📏 Image: {pil_image.size[0]}x{pil_image.size[1]} pixels"
                    ttk.Label(parent_frame, text=image_info,
                              style='Info.TLabel', font=('Arial', 8)).pack(anchor='center')

                    image_loaded = True
                    print(f"DEBUG: Successfully loaded image from {image_path}")
                    break

            except Exception as e:
                print(f"DEBUG: Failed to load image from {image_path}: {e}")
                continue

        if not image_loaded:
            # Show centered placeholder if no image found
            self.show_image_placeholder(parent_frame, image_paths)

    def show_image_placeholder(self, parent_frame, attempted_paths):
        """Show centered placeholder when image cannot be loaded"""
        # Placeholder content - all centered
        ttk.Label(parent_frame, text="📊 SBR0 Configuration",
                  style='Info.TLabel', font=('Arial', 14, 'bold')).pack(anchor='center', pady=5)

        ttk.Label(parent_frame, text="(Configuration diagram not available)",
                  style='Info.TLabel', font=('Arial', 10, 'italic')).pack(anchor='center', pady=5)

        # Show browse button for demo mode - centered
        if self.is_demo_mode:
            ttk.Button(parent_frame, text="📁 Browse for Image",
                       command=self.browse_for_config_image).pack(anchor='center', pady=15)

    def show_pil_not_available(self, parent_frame):
        """Show message when PIL is not available"""
        ttk.Label(parent_frame, text="📊 Configuration Diagram",
                  style='Info.TLabel', font=('Arial', 14, 'bold')).pack(anchor='center', pady=5)

        ttk.Label(parent_frame, text="Image support requires Pillow",
                  style='Info.TLabel', font=('Arial', 10, 'italic')).pack(anchor='center', pady=5)

        ttk.Label(parent_frame, text="Install with: pip install Pillow",
                  style='Info.TLabel', font=('Arial', 9)).pack(anchor='center', pady=5)

    def browse_for_config_image(self):
        """Allow user to browse for configuration image"""
        from tkinter import filedialog

        filename = filedialog.askopenfilename(
            title="Select Configuration Diagram",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("PNG files", "*.png"),
                ("All files", "*.*")
            ]
        )

        if filename:
            try:
                # Copy image to Images directory
                import shutil
                os.makedirs("Images", exist_ok=True)
                dest_path = os.path.join("Images", "port_config.png")
                shutil.copy2(filename, dest_path)

                # Refresh the dashboard
                self.update_content_area()

                messagebox.showinfo("Image Loaded",
                                    f"Configuration image loaded successfully!\nSaved to: {dest_path}")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {e}")

    def create_mode_warning_section(self, parent):
        """Create warning section about power cycling with fixed width"""
        warning_frame = ttk.Frame(parent, style='Content.TFrame')
        warning_frame.pack(pady=10)
        warning_frame.configure(width=600)  # Fixed width

        # Create warning box with yellow background
        warning_box = tk.Frame(warning_frame, bg='#fff3cd', relief='solid', borderwidth=1)
        warning_box.pack(fill='x', padx=5, pady=5)

        # Warning header
        header_frame = tk.Frame(warning_box, bg='#fff3cd')
        header_frame.pack(fill='x', padx=15, pady=(10, 5))

        warning_label = tk.Label(header_frame, text="⚠️ WARNING ⚠️",
                                 bg='#fff3cd', fg='#856404',
                                 font=('Arial', 12, 'bold'))
        warning_label.pack()

        # Warning text
        text_frame = tk.Frame(warning_box, bg='#fff3cd')
        text_frame.pack(fill='x', padx=15, pady=(0, 10))

        warning_text = ("The host card must be power cycled after changing the SBR mode.\n"
                        "The new mode will not take effect until the card is restarted.")

        text_label = tk.Label(text_frame, text=warning_text,
                              bg='#fff3cd', fg='#856404',
                              font=('Arial', 10), justify='center')
        text_label.pack()

    def create_port_refresh_controls(self, parent):
        """Create refresh controls for port configuration with fixed width"""
        controls_frame = ttk.Frame(parent, style='Content.TFrame')
        controls_frame.pack(pady=15)
        controls_frame.configure(width=600)  # Fixed width

        # Create container for centered controls
        controls_container = ttk.Frame(controls_frame, style='Content.TFrame')
        controls_container.pack(fill='x')

        # Refresh button - centered
        refresh_btn = ttk.Button(controls_container, text="🔄 Refresh Port Status",
                                 command=self.refresh_port_configuration)
        refresh_btn.pack(anchor='center')

        # Last update time - centered
        last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        update_label = ttk.Label(controls_container,
                                 text=f"Last updated: {last_updated}",
                                 style='Info.TLabel', font=('Arial', 9))
        update_label.pack(anchor='center', pady=(10, 0))

    def create_link_details_section(self, showport_json):
        """Create detailed link information section - FIXED VERSION"""
        port_debug("Creating link details section", "LINK_DETAILS")

        details_frame = ttk.Frame(self.scrollable_frame, style='Content.TFrame',
                                  relief='solid', borderwidth=1)
        details_frame.pack(fill='x', pady=20)

        # Header
        header_frame = ttk.Frame(details_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=15, pady=(15, 10))

        ttk.Label(header_frame, text="📊 Link Details",
                  style='Dashboard.TLabel', font=('Arial', 12, 'bold')).pack(anchor='w')

        # Content
        content_frame = ttk.Frame(details_frame, style='Content.TFrame')
        content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        # Parse and display detailed port information
        sections = showport_json.get('sections', {})
        port_section = sections.get('port_status', {})
        items = port_section.get('items', [])

        port_debug(f"Processing {len(items)} items for link details", "LINK_PROCESSING")

        if items:
            # Create a table-like display
            for item in items:
                label = item.get('label', 'Unknown')
                value = item.get('value', 'Unknown')
                details = item.get('details', '')

                port_debug(f"Processing link details for {label}", "LINK_ITEM")

                # Extract speed and width from details if available
                if details:
                    speed_match = re.search(r'Speed: Level (\w+)', details)
                    width_match = re.search(r'Width: (\w+)', details)

                    if speed_match or width_match:
                        detail_row_frame = ttk.Frame(content_frame, style='Content.TFrame')
                        detail_row_frame.pack(fill='x', pady=5)

                        # Port name
                        ttk.Label(detail_row_frame, text=label,
                                  style='Info.TLabel', font=('Arial', 10, 'bold')).pack(anchor='w')

                        # Speed and width in sub-frame
                        sub_frame = ttk.Frame(detail_row_frame, style='Content.TFrame')
                        sub_frame.pack(anchor='w', padx=(20, 0))

                        if speed_match:
                            speed_level = speed_match.group(1)
                            speed_text = f"PCIe Gen {self.convert_speed_level(speed_level)}"
                            ttk.Label(sub_frame, text=f"Speed: {speed_text}",
                                      style='Info.TLabel').pack(anchor='w')
                            port_debug(f"{label} speed: {speed_text}", "LINK_SPEED")

                        if width_match:
                            width_value = width_match.group(1)
                            if width_value == '00':
                                width_text = "Inactive"
                            else:
                                try:
                                    # Fixed the width parsing logic
                                    if len(width_value) <= 2:
                                        width_num = int(width_value, 16)
                                    else:
                                        width_num = int(width_value)
                                    width_text = f"x{width_num}"
                                except Exception as e:
                                    # Fixed exception handling
                                    port_debug(f"Width parsing error for {width_value}: {e}", "WIDTH_ERROR")
                                    width_text = f"x{width_value}"

                            ttk.Label(sub_frame, text=f"Width: {width_text}",
                                      style='Info.TLabel').pack(anchor='w')
                            port_debug(f"{label} width: {width_text}", "LINK_WIDTH")
        else:
            port_debug("No link details available", "NO_LINK_DATA")
            ttk.Label(content_frame, text="No detailed link information available",
                      style='Info.TLabel', font=('Arial', 10, 'italic')).pack(anchor='w')

        port_debug("Link details section created", "LINK_COMPLETE")

    def change_host_card_mode(self):
        """Change the host card mode"""
        selected_mode = self.sbr_mode_var.get()

        # Confirm the change
        result = messagebox.askyesno(
            "Confirm Mode Change",
            f"Change host card mode to {selected_mode}?\n\n"
            "⚠️ WARNING: The card must be power cycled after this change.\n"
            "The new mode will not take effect until restart."
        )

        if result:
            if self.is_demo_mode:
                # Demo mode - simulate the change
                self.log_data.append(f"[{datetime.now().strftime('%H:%M:%S')}] DEMO: Changed mode to {selected_mode}")
                messagebox.showinfo("Mode Changed",
                                    f"Demo: Host card mode changed to {selected_mode}\n"
                                    "Remember to power cycle the card!")
            else:
                # Real mode - send command to device
                command = f"set_sbr_mode {selected_mode.lower()}"
                self.send_command(command)
                self.log_data.append(f"[{datetime.now().strftime('%H:%M:%S')}] Sent: {command}")
                messagebox.showinfo("Command Sent",
                                    f"Mode change command sent: {selected_mode}\n"
                                    "Remember to power cycle the card!")

    def refresh_port_configuration(self):
        """Refresh port configuration data"""
        if self.is_demo_mode:
            # Demo mode refresh
            self.log_data.append(f"[{datetime.now().strftime('%H:%M:%S')}] DEMO: Refreshed port configuration")
            self.update_content_area()
        else:
            # Real mode - query device
            self.send_command("get_port_config")
            self.log_data.append(f"[{datetime.now().strftime('%H:%M:%S')}] Queried port configuration")

    # Add this import at the top of main.py if not already present
    try:
        from PIL import Image, ImageTk
        PIL_AVAILABLE = True
    except ImportError:
        PIL_AVAILABLE = False
        print("WARNING: PIL (Pillow) not available. Images will not be displayed.")
        print("Install with: pip install Pillow")

    def send_showmode_command(self):
        """Send showmode command to get current SBR mode"""
        print("DEBUG: Sending showmode command...")

        if not self.cli or not self.cli.is_running:
            print("ERROR: CLI not running, cannot send showmode command")
            self.show_loading_message("Error: Connection not ready")
            return

        try:
            # Send showmode command
            if self.is_demo_mode:
                # In demo mode, handle the command differently
                self.cli.command_queue.put("showmode")
                print("DEBUG: showmode command queued for demo mode")
            else:
                # In real mode, send through normal command interface
                self.send_command("showmode")
                print("DEBUG: showmode command sent for real device")

            timestamp = datetime.now().strftime('%H:%M:%S')
            self.log_data.append(f"[{timestamp}] Requesting port status (showmode)...")

            # Add timeout for showmode request
            self.root.after(5000, self.check_showmode_timeout)  # 5 second timeout

        except Exception as e:
            print(f"ERROR: Failed to send showmode command: {e}")
            self.show_loading_message(f"Error sending showmode command: {e}")

    def check_showmode_timeout(self):
        """Check if showmode request timed out"""
        port_info = self.port_status_manager.get_port_status_info()

        if not port_info or port_info.mode_name == "Unknown":
            print("DEBUG: showmode request timed out")
            self.show_loading_message("Showmode request timed out - please try refreshing")

    def create_compliance_dashboard(self):
        """Create compliance dashboard"""

        def compliance_content(frame):
            tests = [
                ("USB 3.0 Compliance", "✅ Passed"),
                ("EMI/EMC Test", "✅ Passed"),
                ("Power Consumption", "✅ Within Limits"),
                ("Signal Integrity", "✅ Passed"),
                ("Interoperability", "✅ Passed")
            ]

            for test, result in tests:
                row_frame = ttk.Frame(frame, style='Content.TFrame')
                row_frame.pack(fill='x', pady=2)
                ttk.Label(row_frame, text=f"{test}:", style='Info.TLabel',
                          font=('Arial', 10, 'bold')).pack(side='left')
                ttk.Label(row_frame, text=result, style='Info.TLabel').pack(side='right')

        self.create_info_card(self.scrollable_frame, "Compliance Status", compliance_content)

    def create_registers_dashboard(self):
        """Create registers dashboard"""

        def registers_content(frame):
            # Sample register values
            registers = [
                ("0x00", "Device ID", "0x1234"),
                ("0x04", "Vendor ID", "0x5678"),
                ("0x08", "Status", "0x0001"),
                ("0x0C", "Control", "0x8000"),
                ("0x10", "Config", "0x4321")
            ]

            for addr, name, value in registers:
                row_frame = ttk.Frame(frame, style='Content.TFrame')
                row_frame.pack(fill='x', pady=2)

                addr_label = ttk.Label(row_frame, text=addr, style='Info.TLabel',
                                       font=('Arial', 10, 'bold'))
                addr_label.pack(side='left')

                name_label = ttk.Label(row_frame, text=name, style='Info.TLabel')
                name_label.pack(side='left', padx=(10, 0))

                value_label = ttk.Label(row_frame, text=value, style='Info.TLabel',
                                        font=('Arial', 10, 'bold'))
                value_label.pack(side='right')

        self.create_info_card(self.scrollable_frame, "Register Values", registers_content)

        # Add read/write controls
        control_frame = ttk.Frame(self.scrollable_frame, style='Content.TFrame')
        control_frame.pack(fill='x', pady=10)

        ttk.Label(control_frame, text="Register Address:", style='Info.TLabel').pack(anchor='w')
        addr_entry = ttk.Entry(control_frame)
        addr_entry.pack(fill='x', pady=(5, 10))

        button_frame = ttk.Frame(control_frame, style='Content.TFrame')
        button_frame.pack(fill='x')

        ttk.Button(button_frame, text="Read Register",
                   command=lambda: self.send_command(f"read_reg {addr_entry.get()}")).pack(side='left', padx=(0, 10))
        ttk.Button(button_frame, text="Write Register",
                   command=lambda: self.send_command(f"write_reg {addr_entry.get()}")).pack(side='left')

    def create_advanced_dashboard(self):
        """Create advanced dashboard"""

        def advanced_content(frame):
            # Advanced settings
            settings = [
                ("Debug Mode", "Disabled"),
                ("Logging Level", "Info"),
                ("Buffer Size", "4096 bytes"),
                ("Timeout", "5000 ms"),
                ("Retry Count", "3")
            ]

            for setting, value in settings:
                row_frame = ttk.Frame(frame, style='Content.TFrame')
                row_frame.pack(fill='x', pady=2)
                ttk.Label(row_frame, text=f"{setting}:", style='Info.TLabel',
                          font=('Arial', 10, 'bold')).pack(side='left')
                ttk.Label(row_frame, text=value, style='Info.TLabel').pack(side='right')

        self.create_info_card(self.scrollable_frame, "Advanced Settings", advanced_content)

        # Command interface
        cmd_frame = ttk.Frame(self.scrollable_frame, style='Content.TFrame')
        cmd_frame.pack(fill='x', pady=20)

        ttk.Label(cmd_frame, text="🔧 Direct Command Interface", style='Dashboard.TLabel').pack(anchor='w')

        input_frame = ttk.Frame(cmd_frame, style='Content.TFrame')
        input_frame.pack(fill='x', pady=10)

        self.command_entry = ttk.Entry(input_frame, font=('Consolas', 10))
        self.command_entry.pack(side='left', fill='x', expand=True)

        ttk.Button(input_frame, text="Send",
                   command=self.send_direct_command).pack(side='right', padx=(10, 0))

        self.command_entry.bind('<Return>', lambda e: self.send_direct_command())

        # Cache management section
        cache_frame = ttk.Frame(self.scrollable_frame, style='Content.TFrame', relief='solid', borderwidth=1)
        cache_frame.pack(fill='x', pady=20)

        header_frame = ttk.Frame(cache_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=15, pady=(15, 10))

        ttk.Label(header_frame, text="💾 Cache Management", style='Dashboard.TLabel').pack(anchor='w')

        content_frame = ttk.Frame(cache_frame, style='Content.TFrame')
        content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        if self.cache_manager:
            stats = self.cache_manager.get_stats()
            ttk.Label(content_frame, text=f"Cache entries: {stats['valid_entries']}",
                      style='Info.TLabel').pack(anchor='w', pady=2)
            ttk.Label(content_frame, text=f"Cache size: {stats['cache_file_size']} bytes",
                      style='Info.TLabel').pack(anchor='w', pady=2)

        button_frame = ttk.Frame(content_frame, style='Content.TFrame')
        button_frame.pack(fill='x', pady=10)

        ttk.Button(button_frame, text="View Cache Contents",
                   command=self.view_cache_contents).pack(side='left', padx=(0, 10))
        ttk.Button(button_frame, text="Clear Cache",
                   command=self.clear_cache).pack(side='left')

        def add_response_handler_section_to_advanced_dashboard(self):
            """
            ADD this to the end of your create_advanced_dashboard method
            """
            # Response Handler Debug Section
            handler_frame = ttk.Frame(self.scrollable_frame, style='Content.TFrame',
                                      relief='solid', borderwidth=1)
            handler_frame.pack(fill='x', pady=20)

            header_frame = ttk.Frame(handler_frame, style='Content.TFrame')
            header_frame.pack(fill='x', padx=15, pady=(15, 10))

            ttk.Label(header_frame, text="🔧 Advanced Response Handler",
                      style='Dashboard.TLabel').pack(anchor='w')

            content_frame = ttk.Frame(handler_frame, style='Content.TFrame')
            content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

            # Status display
            self.handler_status_text = tk.Text(content_frame, height=8, wrap='word',
                                               state='disabled', bg='#f8f8f8',
                                               font=('Consolas', 9))
            self.handler_status_text.pack(fill='x', pady=(0, 10))

            # Control buttons
            button_frame = ttk.Frame(content_frame, style='Content.TFrame')
            button_frame.pack(fill='x')

            ttk.Button(button_frame, text="📊 Show Handler Status",
                       command=self.show_handler_status).pack(side='left', padx=(0, 5))
            ttk.Button(button_frame, text="⚡ Force Process Buffers",
                       command=self.force_process_responses).pack(side='left', padx=5)
            ttk.Button(button_frame, text="🗑️ Clear All Buffers",
                       command=self.clear_response_buffers).pack(side='left', padx=5)
            ttk.Button(button_frame, text="🔄 Restart Handler",
                       command=self.restart_response_handler).pack(side='left', padx=5)

        self.add_response_handler_section()

    def add_response_handler_section(self):
        """
        ADD this method to create the advanced handler debug section
        """
        if not hasattr(self, 'response_handler') or not self.response_handler:
            return  # Don't add section if handler not available

        # Advanced Response Handler Section
        handler_frame = ttk.Frame(self.scrollable_frame, style='Content.TFrame',
                                  relief='solid', borderwidth=1)
        handler_frame.pack(fill='x', pady=20)

        header_frame = ttk.Frame(handler_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=15, pady=(15, 10))

        ttk.Label(header_frame, text="🚀 Advanced Response Handler",
                  style='Dashboard.TLabel').pack(anchor='w')

        content_frame = ttk.Frame(handler_frame, style='Content.TFrame')
        content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        # Status display
        self.handler_status_text = tk.Text(content_frame, height=8, wrap='word',
                                           state='disabled', bg='#f8f8f8',
                                           font=('Consolas', 9))
        self.handler_status_text.pack(fill='x', pady=(0, 10))

        # Control buttons
        button_frame = ttk.Frame(content_frame, style='Content.TFrame')
        button_frame.pack(fill='x')

        ttk.Button(button_frame, text="📊 Show Status",
                   command=self.show_handler_status).pack(side='left', padx=(0, 5))
        ttk.Button(button_frame, text="⚡ Force Process",
                   command=self.force_process_responses).pack(side='left', padx=5)
        ttk.Button(button_frame, text="🗑️ Clear Buffers",
                   command=self.clear_response_buffers).pack(side='left', padx=5)
        ttk.Button(button_frame, text="🔄 Restart Handler",
                   command=self.restart_response_handler).pack(side='left', padx=5)

    def send_showport_command(self):
        """Send showport command for link status data"""
        print("DEBUG: Sending showport command...")

        if not self.cli or not self.cli.is_running:
            print("ERROR: CLI not running, cannot send showport command")
            self.show_loading_message("Error: Connection not ready")
            return

        self.showport_requested = True

        try:
            if self.is_demo_mode:
                # In demo mode, put command directly in queue
                self.cli.command_queue.put("showport")
                print("DEBUG: showport command queued for demo mode")
            else:
                # In real mode, send through normal command interface
                self.send_command("showport")
                print("DEBUG: showport command sent for real device")

            timestamp = datetime.now().strftime('%H:%M:%S')
            self.log_data.append(f"[{timestamp}] Requesting link status information...")
            print(f"DEBUG: showport_requested set to {self.showport_requested}")

            # Add timeout for showport request
            self.root.after(8000, self.check_showport_timeout)  # 8 second timeout

        except Exception as e:
            print(f"ERROR: Failed to send showport command: {e}")
            self.showport_requested = False
            self.show_loading_message(f"Error sending showport command: {e}")

    def show_handler_status(self):
        """Show advanced response handler status"""
        if not hasattr(self, 'response_handler') or not self.response_handler:
            self.handler_status_text.config(state='normal')
            self.handler_status_text.delete(1.0, tk.END)
            self.handler_status_text.insert(1.0, "Advanced Response Handler not available")
            self.handler_status_text.config(state='disabled')
            return

        try:
            status = self.response_handler.get_status()

            status_text = f"Advanced Response Handler Status\n"
            status_text += f"{'=' * 40}\n\n"
            status_text += f"State: {status['state'].upper()}\n"
            status_text += f"Active Buffers: {status['active_buffers']}\n\n"

            if status['buffer_details']:
                status_text += "Buffer Details:\n"
                for cmd, details in status['buffer_details'].items():
                    status_text += f"  {cmd}: {details['lines']} lines, "
                    status_text += f"{details['age_seconds']:.1f}s old\n"

            status_text += f"\nStatistics:\n"
            stats = status['statistics']
            status_text += f"  Processed: {stats['responses_processed']}\n"
            status_text += f"  Failed: {stats['responses_failed']}\n"
            status_text += f"  Timeouts: {stats['responses_timeout']}\n"
            status_text += f"  Fragments: {stats['fragments_collected']}\n"
            status_text += f"  Avg fragments/response: {stats['average_fragments_per_response']:.1f}\n"

            # Calculate success rate
            total = stats['responses_processed'] + stats['responses_failed'] + stats['responses_timeout']
            if total > 0:
                success_rate = (stats['responses_processed'] / total) * 100
                status_text += f"  Success rate: {success_rate:.1f}%\n"

            self.handler_status_text.config(state='normal')
            self.handler_status_text.delete(1.0, tk.END)
            self.handler_status_text.insert(1.0, status_text)
            self.handler_status_text.config(state='disabled')

        except Exception as e:
            error_text = f"Error getting handler status: {e}"
            self.handler_status_text.config(state='normal')
            self.handler_status_text.delete(1.0, tk.END)
            self.handler_status_text.insert(1.0, error_text)
            self.handler_status_text.config(state='disabled')

    def force_process_responses(self):
        """Force process all pending response buffers"""
        if not hasattr(self, 'response_handler') or not self.response_handler:
            messagebox.showerror("Handler Error", "Advanced Response Handler not available.")
            return

        try:
            status_before = self.response_handler.get_status()
            active_before = status_before['active_buffers']

            if active_before == 0:
                messagebox.showinfo("No Buffers", "No active response buffers to process.")
                return

            self.response_handler.force_process_all()

            status_after = self.response_handler.get_status()
            active_after = status_after['active_buffers']
            processed = active_before - active_after

            timestamp = datetime.now().strftime('%H:%M:%S')
            self.log_data.append(f"[{timestamp}] Forced processing: {processed} buffers")

            messagebox.showinfo("Processing Complete",
                                f"Processed {processed} response buffers.\n"
                                f"{active_after} buffers remain active.")

            self.show_handler_status()

        except Exception as e:
            messagebox.showerror("Processing Error", f"Error forcing response processing: {e}")

    def clear_response_buffers(self):
        """Clear all response buffers after confirmation"""
        if not hasattr(self, 'response_handler') or not self.response_handler:
            messagebox.showerror("Handler Error", "Advanced Response Handler not available.")
            return

        try:
            status = self.response_handler.get_status()
            active_buffers = status['active_buffers']

            if active_buffers == 0:
                messagebox.showinfo("No Buffers", "No active response buffers to clear.")
                return

            if messagebox.askyesno("Clear Response Buffers",
                                   f"Clear all {active_buffers} active response buffers?\n\n"
                                   "This will discard any pending response data."):
                self.response_handler.clear_all_buffers()
                self.sysinfo_requested = False

                timestamp = datetime.now().strftime('%H:%M:%S')
                self.log_data.append(f"[{timestamp}] All response buffers cleared")

                messagebox.showinfo("Buffers Cleared", f"All {active_buffers} buffers cleared.")
                self.show_handler_status()

        except Exception as e:
            messagebox.showerror("Clear Error", f"Error clearing response buffers: {e}")

    def restart_response_handler(self):
        """Restart the response handler"""
        try:
            if messagebox.askyesno("Restart Handler",
                                   "Restart the advanced response handler?\n\n"
                                   "This will clear all buffers and reinitialize."):

                # Clear existing handler
                if hasattr(self, 'response_handler') and self.response_handler:
                    self.response_handler.clear_all_buffers()
                    del self.response_handler

                # Reinitialize
                self.init_advanced_response_handler()

                timestamp = datetime.now().strftime('%H:%M:%S')
                self.log_data.append(f"[{timestamp}] Advanced response handler restarted")

                messagebox.showinfo("Handler Restarted", "Handler has been restarted.")
                self.show_handler_status()

        except Exception as e:
            messagebox.showerror("Restart Error", f"Error restarting handler: {e}")

    def check_showport_timeout(self):
        """Check if showport command timed out"""
        if hasattr(self, 'showport_requested') and self.showport_requested:
            print("DEBUG: showport command timed out")
            self.showport_requested = False
            if self.current_dashboard == "link":
                self.show_loading_message("Showport command timed out - click refresh to retry")

    def _convert_cached_to_link_info(self, cached_data):
        """Convert cached showport data to LinkStatusInfo format"""
        from Dashboards.link_status_dashboard import LinkStatusInfo, PortInfo

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

    def handle_demo_setmode(self, mode_number: int):
        """Handle setmode command in demo mode"""
        try:
            # Update demo device state
            self.demo_device_state = update_demo_device_state(self.demo_device_state, mode_number)

            # Log the demo mode change
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.log_data.append(f"[{timestamp}] DEMO: setmode {mode_number} - mode changed to SBR{mode_number}")

            # Refresh the port dashboard after mode change
            self.root.after(1000, lambda: self.update_content_area() if self.current_dashboard == "port" else None)

            return True

        except Exception as e:
            print(f"ERROR: Demo setmode failed: {e}")
            return False

    def view_cache_contents(self):
        """Open cache viewer dialog"""
        if self.cache_manager:
            settings_ui.CacheViewerDialog(self.root, self.cache_manager)

    def clear_cache(self):
        """Clear all cache data"""
        if self.cache_manager and messagebox.askyesno("Clear Cache",
                                                      "Clear all cached data?\n\nThis cannot be undone."):
            self.cache_manager.clear()
            self.update_cache_status("Cache cleared")
            messagebox.showinfo("Cache Cleared", "All cached data has been cleared.")

    def create_resets_dashboard(self):
        """Create resets dashboard using the dedicated module"""
        try:
            self.resets_dashboard.create_resets_dashboard(self.scrollable_frame)
        except Exception as e:
            print(f"ERROR: Failed to create resets dashboard: {e}")
            import traceback
            traceback.print_exc()

            # Show error message in the dashboard
            error_frame = ttk.Frame(self.scrollable_frame, style='Content.TFrame')
            error_frame.pack(fill='both', expand=True, padx=20, pady=20)

            ttk.Label(error_frame,
                      text="❌ Error Loading Resets Dashboard",
                      style='Dashboard.TLabel',
                      font=('Arial', 16, 'bold')).pack(pady=(0, 10))

            ttk.Label(error_frame,
                      text=f"Error: {str(e)}",
                      style='Info.TLabel',
                      font=('Arial', 10)).pack()

    def create_firmware_dashboard(self):
        """Create firmware updates dashboard"""
        self.firmware_dashboard.create_firmware_dashboard()

    def load_demo_data_directly(self):
        """Load demo data directly without waiting for threading"""
        print("DEBUG: Loading demo data directly...")

        try:
            # Try to load the sysinfo.txt file directly
            demo_content = self.load_sysinfo_file_direct()

            if demo_content:
                print(f"DEBUG: Loaded demo sysinfo content ({len(demo_content)} chars)")

                # Parse it immediately using the enhanced parser
                parsed_data = self.sysinfo_parser.parse_unified_sysinfo(demo_content, "demo")
                print(f"DEBUG: Parsed demo data successfully")

                # Update the UI immediately
                self.root.after_idle(self.update_content_area)
                self.update_cache_status("Demo data loaded")

                # Log success
                timestamp = datetime.now().strftime('%H:%M:%S')
                self.log_data.append(f"[{timestamp}] Demo data loaded successfully")

            else:
                print("DEBUG: Could not load demo sysinfo content")
                # Fall back to threading approach
                self.root.after(1000, self.send_sysinfo_command)

        except Exception as e:
            print(f"ERROR: Failed to load demo data directly: {e}")
            import traceback
            traceback.print_exc()
            # Fall back to threading approach
            self.root.after(1000, self.send_sysinfo_command)

    def load_sysinfo_file_direct(self):
        """Load sysinfo.txt file directly"""
        demo_paths = [
            "sysinfo.txt",  # Check current directory first
            "DemoData/sysinfo.txt",
            "./DemoData/sysinfo.txt",
            "../DemoData/sysinfo.txt",
            os.path.join(os.path.dirname(__file__), "sysinfo.txt"),
            os.path.join(os.path.dirname(__file__), "DemoData", "sysinfo.txt"),
            os.path.join(os.getcwd(), "sysinfo.txt"),
            os.path.join(os.getcwd(), "DemoData", "sysinfo.txt")
        ]

        print("DEBUG: Searching for sysinfo.txt file...")
        for i, path in enumerate(demo_paths):
            abs_path = os.path.abspath(path)
            print(f"DEBUG: Checking path {i + 1}: {abs_path}")

            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    print(f"DEBUG: ✓ Loaded sysinfo from {path} ({len(content)} chars)")
                    return content
                except Exception as e:
                    print(f"DEBUG: ✗ Error loading {path}: {e}")
                    continue
            else:
                print(f"DEBUG: ✗ Path does not exist: {abs_path}")

        print("DEBUG: No sysinfo.txt file found")
        return None

    def create_help_dashboard(self):
        """Create help dashboard with updated version info"""

        def about_content(frame):
            version_info = get_version_info()
            about_text = f"""{version_info['name']} {version_info['version']}
Build: {version_info['build']}

{APP_DESCRIPTION}
A professional serial communication tool with modern GUI interface

{version_info['copyright']} {version_info['author']}

NEW FEATURES:
• Data caching with JSON persistence
• Environment settings management
• Auto-refresh capabilities  
• Settings UI with gear icon
• Optimized dashboard performance
• Cache viewer and management
• Configurable refresh intervals"""

            ttk.Label(frame, text=about_text, style='Info.TLabel', justify='left').pack(anchor='w')

        self.create_info_card(self.scrollable_frame, f"ℹ️ About {APP_NAME}", about_content)

        # Version History section
        def version_history_content(frame):
            history_text = ""
            for version, info in VERSION_HISTORY.items():
                history_text += f"Version {version} - {info.get('date', 'Unknown')}\n"
                changes = info.get('changes', [])
                for i, change in enumerate(changes, 1):
                    history_text += f"{i}. {change}\n"
                history_text += "\n"

            ttk.Label(frame, text=history_text, style='Info.TLabel', justify='left').pack(anchor='w')

        self.create_info_card(self.scrollable_frame, "📋 Version History", version_history_content)

        # Quick start guide
        def quickstart_content(frame):
            guide_text = """1. Ensure device is properly connected to COM port
2. Use dashboards to monitor device status  
3. Configure ports and settings as needed
4. Monitor compliance and link status
5. Use Advanced dashboard for direct commands
6. Click ⚙️ gear icon to access settings
7. Use 🔄 refresh button to update data"""

            ttk.Label(frame, text=guide_text, style='Info.TLabel', justify='left').pack(anchor='w')

        self.create_info_card(self.scrollable_frame, "🚀 Quick Start Guide", quickstart_content)

        # Command reference
        def commands_content(frame):
            commands = [
                ("help", "Show available commands"),
                ("status", "Get device status"),
                ("version", "Get firmware version"),
                ("sysinfo", "Get system information"),
                ("ver", "Get detailed version info"),
                ("lsd", "Get system diagnostics"),
                ("reset", "Reset device"),
                ("link_status", "Check link status"),
                ("read_reg <addr>", "Read register"),
                ("write_reg <addr> <value>", "Write register")
            ]

            for cmd, desc in commands:
                row_frame = ttk.Frame(frame, style='Content.TFrame')
                row_frame.pack(fill='x', pady=2)

                cmd_label = ttk.Label(row_frame, text=cmd, style='Info.TLabel',
                                      font=('Consolas', 10, 'bold'))
                cmd_label.pack(side='left')

                desc_label = ttk.Label(row_frame, text=f"- {desc}", style='Info.TLabel')
                desc_label.pack(side='left', padx=(10, 0))

        self.create_info_card(self.scrollable_frame, "📝 Command Reference", commands_content)

        # Log export section
        log_frame = ttk.Frame(self.scrollable_frame, style='Content.TFrame', relief='solid', borderwidth=1)
        log_frame.pack(fill='x', pady=20)

        header_frame = ttk.Frame(log_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=15, pady=(15, 10))

        ttk.Label(header_frame, text="📋 Session Logs", style='Dashboard.TLabel').pack(anchor='w')

        content_frame = ttk.Frame(log_frame, style='Content.TFrame')
        content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        ttk.Label(content_frame, text=f"Current session has {len(self.log_data)} log entries",
                  style='Info.TLabel').pack(anchor='w', pady=(0, 10))

        ttk.Button(content_frame, text="💾 Export Logs to TXT",
                   command=self.export_logs).pack(anchor='w')

    def connect_device(self):
        """Enhanced device connection with immediate demo data loading"""
        debug_info(f"Connecting to device (Demo mode: {self.is_demo_mode})", "DEVICE_CONNECT")

        if self.cli.connect():
            debug_info("CLI connected successfully", "CLI_CONNECT_SUCCESS")

            if self.is_demo_mode:
                self.connection_label.config(foreground='#ff9500')
                timestamp = datetime.now().strftime('%H:%M:%S')
                self.log_data.append(f"[{timestamp}] Enhanced demo mode started")

                # Enhanced demo data loading
                try:
                    # Try enhanced data access first
                    if hasattr(self.cli, 'get_complete_sysinfo_data'):
                        complete_data = self.cli.get_complete_sysinfo_data()
                        if complete_data:
                            debug_info("Using enhanced demo data", "DEMO_ENHANCED_DATA")
                            self.root.after_idle(self.update_content_area)
                            self.update_cache_status("Enhanced demo data loaded")
                            self.log_data.append(f"[{timestamp}] Enhanced demo data loaded successfully")
                            return

                    # Fallback to direct content access
                    demo_content = getattr(self.cli, 'demo_sysinfo_content', None)
                    if demo_content:
                        debug_info(f"Using demo content directly ({len(demo_content)} chars)", "DEMO_DIRECT_CONTENT")

                        # Parse using enhanced parser
                        parsed_data = self.sysinfo_parser.parse_unified_sysinfo(demo_content, "demo")
                        if parsed_data:
                            debug_info("Demo data parsed successfully", "DEMO_PARSE_SUCCESS")

                            # Update UI immediately
                            self.root.after_idle(self.update_content_area)
                            self.update_cache_status("Demo data loaded")
                            self.log_data.append(f"[{timestamp}] Demo data loaded and parsed")
                        else:
                            debug_error("Demo data parsing failed", "DEMO_PARSE_FAILED")
                            self.show_loading_message("Demo data parsing failed")
                    else:
                        debug_error("No demo content available", "DEMO_NO_CONTENT")
                        self.show_loading_message("Demo data not available")

                except Exception as e:
                    debug_error(f"Failed to load demo data: {e}", "DEMO_LOAD_ERROR")
                    import traceback
                    traceback.print_exc()
                    self.show_loading_message(f"Demo error: {e}")

            else:
                # Real device mode
                self.connection_label.config(foreground='#00ff00')
                timestamp = datetime.now().strftime('%H:%M:%S')
                self.log_data.append(f"[{timestamp}] Connected to {self.port}")
                debug_info(f"Real device connected: {self.port}", "REAL_DEVICE_CONNECTED")

                self.start_background_threads()
                self.root.after(500, self.send_sysinfo_command)

        else:
            self.connection_label.config(foreground='#ff0000')
            error_msg = "Failed to start demo mode" if self.is_demo_mode else f"Failed to connect to {self.port}"
            debug_print(f"Connection failed: {error_msg}", "ERROR")
            messagebox.showerror("Connection Error", error_msg)

    def start_background_threads(self):
        """FIXED: Start background threads with proper error handling"""
        print("DEBUG: Starting background threads...")

        if self.cli.is_running:
            try:
                # Start CLI background thread
                cli_thread = threading.Thread(target=self.cli.run_background, daemon=True)
                cli_thread.start()
                print("DEBUG: CLI background thread started")

                # Start log monitoring thread
                log_thread = threading.Thread(target=self.monitor_logs, daemon=True)
                log_thread.start()
                print("DEBUG: Log monitoring thread started")

                # CRITICAL FIX: Start periodic queue checking
                self.start_queue_monitoring()

            except Exception as e:
                print(f"ERROR: Failed to start background threads: {e}")
                messagebox.showerror("Thread Error", f"Failed to start background threads: {e}")
        else:
            print("ERROR: CLI not running, cannot start background threads")

    def start_queue_monitoring(self):
        """
        IMPROVED: Queue monitoring with advanced response handler
        """

        def check_queues():
            try:
                # Check for new responses
                if hasattr(self.cli, 'response_queue'):
                    try:
                        response = self.cli.response_queue.get_nowait()
                        if response:
                            print(f"DEBUG: Queue monitor received: {response[:80]}...")

                            # Try advanced handler first
                            if hasattr(self, 'response_handler') and self.response_handler:
                                handled = self.response_handler.add_response_fragment(response)

                                if not handled:
                                    print(f"DEBUG: Advanced handler didn't process: {response[:50]}...")
                                    # Fall back to basic handling
                                    self._basic_response_handling(response)
                            else:
                                # No advanced handler, use basic handling
                                self._basic_response_handling(response)

                    except queue.Empty:
                        pass

            except Exception as e:
                print(f"DEBUG: Queue monitor error: {e}")

            # Schedule next check
            self.root.after(100, check_queues)

        # Start monitoring
        check_queues()
        print("DEBUG: Queue monitoring started with advanced handler support")

    def _basic_response_handling(self, response):
        """
        Fallback response handling if advanced handler fails
        """
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_data.append(f"[{timestamp}] BASIC RECV: {response}")

        # Basic sysinfo detection (your original logic)
        if self.sysinfo_requested:
            sysinfo_indicators = [
                "port", "speed", "width", "golden", "s/n", "company",
                "model", "version", "thermal", "voltage", "current", "error"
            ]

            if any(indicator in response.lower() for indicator in sysinfo_indicators):
                print(f"DEBUG: Basic handler found sysinfo data: {response[:50]}...")

    def process_showport_response(self, response):
        """Process showport response from queue monitoring"""
        try:
            # Parse the showport response using link status manager
            link_info = self.link_status_ui.link_status_manager.parser.parse_showport_response(response)
            self.link_status_ui.link_status_manager.cached_info = link_info
            self.link_status_ui.link_status_manager.last_refresh = datetime.now()

            # Also parse using enhanced parser for caching
            if hasattr(self, 'sysinfo_parser'):
                self.sysinfo_parser.parse_showport_command(response)

            print(f"DEBUG: Successfully processed showport with {len(link_info.ports)} ports")

            self.showport_requested = False
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.log_data.append(f"[{timestamp}] Link status information processed successfully")

            # Update UI immediately if we're on link dashboard
            if self.current_dashboard == "link":
                self.root.after_idle(self.update_content_area)
                self.update_cache_status("Fresh link data loaded")

        except Exception as e:
            print(f"DEBUG: Error processing showport response: {e}")
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.log_data.append(f"[{timestamp}] Error processing showport: {e}")

    def check_showport_timeout(self):
        """Check if showport command timed out"""
        if hasattr(self, 'showport_requested') and self.showport_requested:
            print("DEBUG: showport command timed out")
            self.showport_requested = False
            self.show_loading_message("Showport command timed out - click refresh to retry")

    # monitor_logs method to handle showport responses
    def monitor_logs(self):
        """Monitor log queue with enhanced sysinfo and showmode handling for both modes"""
        while self.cli.is_running:
            try:
                log_entry = self.cli.log_queue.get_nowait()
                timestamp = datetime.now().strftime('%H:%M:%S')
                self.log_data.append(f"[{timestamp}] {log_entry}")

                # Enhanced showmode detection for both demo and real modes
                if "showmode" in log_entry.lower() and ("RECV:" in log_entry or "DEMO RECV:" in log_entry):
                    # Extract the actual response content
                    if "DEMO RECV:" in log_entry:
                        response = log_entry.replace("DEMO RECV:", "").strip()
                    else:
                        response = log_entry.replace("RECV:", "").strip()

                    print(f"DEBUG: Processing showmode response, length: {len(response)}")

                    # Check if this looks like a showmode response
                    if "mode" in response.lower() and any(char.isdigit() for char in response):
                        print("DEBUG: Parsing showmode response...")

                        try:
                            # Parse and cache the showmode response
                            port_info = self.port_status_manager.parser.parse_showmode_response(response)
                            port_info.raw_showmode_response = response

                            # Cache the parsed info
                            self.port_status_manager.cached_info = port_info
                            self.port_status_manager.last_refresh = datetime.now()

                            print(f"DEBUG: Successfully parsed showmode - mode: SBR{port_info.current_mode}")
                            self.log_data.append(
                                f"[{timestamp}] Port status cached successfully - SBR{port_info.current_mode}")

                            # Update UI immediately if on port dashboard
                            if self.current_dashboard == "port":
                                self.root.after_idle(self.update_content_area)

                        except Exception as e:
                            print(f"DEBUG: Error parsing showmode: {e}")
                            self.log_data.append(f"[{timestamp}] Error parsing showmode: {e}")

                # Handle setmode command responses
                elif "setmode" in log_entry.lower() and ("SENT:" in log_entry or "DEMO SENT:" in log_entry):
                    print("DEBUG: setmode command sent")
                    self.log_data.append(f"[{timestamp}] setmode command processed")

                    # Refresh showmode data after setmode
                    if self.current_dashboard == "port":
                        self.root.after(2000, self.send_showmode_command)  # Refresh after 2 seconds

                # Enhanced sysinfo detection (existing code)
                elif "sysinfo" in log_entry.lower() and ("RECV:" in log_entry or "DEMO RECV:" in log_entry):
                    if self.sysinfo_requested:
                        # Extract the actual response content
                        if "DEMO RECV:" in log_entry:
                            response = log_entry.replace("DEMO RECV:", "").strip()
                        else:
                            response = log_entry.replace("RECV:", "").strip()

                        print(f"DEBUG: Processing sysinfo response, length: {len(response)}")

                        # Check if this looks like a complete sysinfo response
                        if (len(response) > 200 and
                                ("===" in response or "S/N" in response or "Thermal:" in response)):

                            print("DEBUG: Parsing complete sysinfo response...")

                            try:
                                # Parse and cache the complete sysinfo response using unified method
                                parsed_data = self.sysinfo_parser.parse_unified_sysinfo(response,
                                                                                        "demo" if self.is_demo_mode else "device")
                                print(f"DEBUG: Successfully parsed sysinfo with sections: {list(parsed_data.keys())}")

                                self.sysinfo_requested = False
                                self.log_data.append(f"[{timestamp}] System information cached successfully")

                                # Update UI immediately with fresh cached data
                                self.root.after_idle(self.update_content_area)
                                self.update_cache_status("Fresh data loaded")

                            except Exception as e:
                                print(f"DEBUG: Error parsing sysinfo: {e}")
                                self.log_data.append(f"[{timestamp}] Error parsing sysinfo: {e}")

            except queue.Empty:
                pass
            time.sleep(0.1)

    def send_sysinfo_command(self):

        print(f"DEBUG: Sending sysinfo command with advanced handler (Demo mode: {self.is_demo_mode})")

        if not self.cli or not self.cli.is_running:
            print("ERROR: CLI not running, cannot send sysinfo command")
            self.show_loading_message("Error: Connection not ready")
            return

        if self.sysinfo_requested:
            print("DEBUG: sysinfo request already pending, skipping")
            return

        self.sysinfo_requested = True

        try:
            # Start advanced response collection if available
            if hasattr(self, 'response_handler') and self.response_handler:
                self.response_handler.start_response_collection("sysinfo")
                print("DEBUG: Advanced response collection started")
            else:
                print("DEBUG: No advanced handler, using basic collection")

            if self.is_demo_mode:
                self.cli.command_queue.put("sysinfo")
                print("DEBUG: sysinfo command queued for demo mode")
            else:
                success = self.cli.send_command("sysinfo")
                if not success:
                    print("ERROR: Failed to send sysinfo command")
                    self.sysinfo_requested = False
                    self.show_loading_message("Failed to send command")
                    return
                print("DEBUG: sysinfo command sent for real device")

            timestamp = datetime.now().strftime('%H:%M:%S')
            self.log_data.append(f"[{timestamp}] Requesting system information with advanced handler...")

            # Set timeout (advanced handler manages its own, but keep for fallback)
            self.root.after(15000, self.check_sysinfo_timeout)  # 15 second timeout

        except Exception as e:
            print(f"ERROR: Failed to send sysinfo command: {e}")
            self.sysinfo_requested = False
            self.show_loading_message(f"Error sending command: {e}")

    def send_command(self, command):
        """Send command to device with caching awareness"""
        if self.cli.is_running:
            self.cli.command_queue.put(command)

            # Log command for debugging
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.log_data.append(f"[{timestamp}] Command queued: {command}")

    def send_direct_command(self):
        """Send direct command from advanced dashboard"""
        command = self.command_entry.get().strip()
        if command:
            self.send_command(command)
            self.command_entry.delete(0, tk.END)

    def confirm_reset(self, reset_type):
        """Confirm reset operation"""
        result = messagebox.askyesno("Confirm Reset",
                                     f"Are you sure you want to perform a {reset_type.replace('_', ' ')}?\n\n"
                                     "This action cannot be undone.")
        if result:
            self.send_command(reset_type)

            # Clear cache after reset
            if self.cache_manager:
                self.cache_manager.clear()
                self.update_cache_status("Cache cleared after reset")

            messagebox.showinfo("Reset Initiated", f"{reset_type.replace('_', ' ').title()} has been initiated.")

    def browse_firmware(self):
        """Browse for firmware file"""
        filename = filedialog.askopenfilename(
            title="Select Firmware File",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")]
        )
        if filename:
            self.firmware_path.set(os.path.basename(filename))

    def check_firmware_updates(self):
        """Check for firmware updates"""
        messagebox.showinfo("Update Check",
                            "Checking for updates...\n\nNo updates available.\nCurrent firmware is up to date.")

    def upload_firmware(self):
        """Upload firmware to device"""
        if self.firmware_path.get() == "No file selected":
            messagebox.showerror("Error", "Please select a firmware file first.")
            return

        result = messagebox.askyesno("Confirm Upload",
                                     "Are you sure you want to upload the firmware?\n\n"
                                     "This will overwrite the current firmware and may take several minutes.")
        if result:
            messagebox.showinfo("Upload Started", "Firmware upload initiated.\nPlease do not disconnect the device.")

    def export_logs(self):
        """Export session logs to text file"""
        if not self.log_data:
            messagebox.showinfo("No Logs", "No log data to export.")
            return

        filename = filedialog.asksaveasfilename(
            title="Export Logs",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialname=f"serial_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )

        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(f"Serial COM Dashboard - Session Log\n")
                    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Port: {self.port}\n")
                    f.write(f"Cache enabled: {self.cache_manager is not None}\n")
                    f.write(f"Auto-refresh: {self.auto_refresh_enabled}\n")
                    f.write("-" * 50 + "\n\n")

                    for log_entry in self.log_data:
                        f.write(log_entry + "\n")

                messagebox.showinfo("Export Complete", f"Logs exported successfully to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export logs:\n{str(e)}")

    def on_closing(self):
        """Handle application closing"""
        # Save window position if enabled
        if self.settings_mgr.get('ui', 'remember_window_position', True):
            try:
                self.settings_mgr.set('ui', 'last_window_x', self.root.winfo_x())
                self.settings_mgr.set('ui', 'last_window_y', self.root.winfo_y())
                self.settings_mgr.save()
            except:
                pass  # Ignore errors during shutdown

        # Stop auto-refresh
        self.stop_auto_refresh()

        # Disconnect from device
        if self.cli.is_running:
            self.cli.disconnect()

        self.root.destroy()


def main():
    """Main application entry point with settings integration"""
    try:
        # Check if running on Windows or Linux
        if sys.platform.startswith('win'):
            # Windows-specific optimizations
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)

        # Initialize settings manager
        settings_mgr = SettingsManager()

        # Create and run connection window
        root = tk.Tk()
        app = ConnectionWindow(root, settings_mgr)
        root.mainloop()

    except Exception as e:
        messagebox.showerror("Application Error", f"An error occurred:\n{str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()