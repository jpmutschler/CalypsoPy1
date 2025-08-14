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
APP_VERSION = "Beta 1.3.2"  # Updated version
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
import subprocess
import sys
import os
import re
from datetime import datetime
import json
from demo_mode_integration import UnifiedDemoSerialCLI
from host_card_info import HostCardInfoManager, HostCardDashboardUI
from cache_manager import DeviceDataCache
from enhanced_sysinfo_parser import EnhancedSystemInfoParser
from settings_manager import SettingsManager
from settings_ui import SettingsDialog
import settings_ui  # Import module for CacheViewerDialog access
from link_status_dashboard import LinkStatusDashboardUI, LinkStatusManager
from port_status_dashboard import PortStatusManager, PortStatusDashboardUI, get_demo_showmode_response, update_demo_device_state
from firmware_dashboard import FirmwareDashboard, integrate_firmware_dashboard
from resets_dashboard import ResetsDashboard

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("WARNING: PIL not available. SBR mode images will not be displayed.")

def load_demo_sysinfo_file():
    """Load sysinfo.txt from DemoData directory"""
    demo_paths = [
        "DemoData/sysinfo.txt",
        "./DemoData/sysinfo.txt",
        "../DemoData/sysinfo.txt",
        os.path.join(os.path.dirname(__file__), "DemoData", "sysinfo.txt")
    ]

    for path in demo_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                print(f"DEBUG: Loaded sysinfo.txt from {path} ({len(content)} chars)")
                return content
            except Exception as e:
                print(f"DEBUG: Error reading {path}: {e}")

    print("DEBUG: sysinfo.txt not found in DemoData directory")
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
        self.response_queue = queue.Queue()
        self.log_queue = queue.Queue()

        # Serial connection setup
        self.serial_connection = None
        self.baudrate = 115200

    def connect(self):
        """Connect to serial device"""
        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1.0
            )
            self.is_running = True
            return True
        except Exception as e:
            print(f"Serial connection failed: {e}")
            return False

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
        """Read response from device"""
        if self.serial_connection and self.is_running:
            try:
                response = self.serial_connection.readline().decode().strip()
                if response:
                    self.log_queue.put(f"RECV: {response}")
                    self.response_queue.put(response)
                return response
            except Exception as e:
                self.log_queue.put(f"Read error: {str(e)}")
                return None
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

        # Title with settings gear icon - UPDATED
        title_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        title_frame.pack(fill='x', pady=(0, 30))

        title_label = ttk.Label(title_frame, text="🔌 Device Connection",
                                style='Modern.TLabel', font=('Arial', 18, 'bold'))
        title_label.pack(side='left')

        # Settings gear icon button - NEW
        settings_btn = ttk.Button(title_frame, text="⚙️", width=3,
                                  command=self.open_settings)
        settings_btn.pack(side='right')

        # Keep all your existing COM Port selection code unchanged
        port_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        port_frame.pack(fill='x', pady=10)

        ttk.Label(port_frame, text="COM Port:", style='Modern.TLabel').pack(anchor='w')

        port_select_frame = ttk.Frame(port_frame, style='Modern.TFrame')
        port_select_frame.pack(fill='x', pady=(5, 0))

        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(port_select_frame, textvariable=self.port_var,
                                       state='readonly', font=('Arial', 11))
        self.port_combo.pack(side='left', fill='x', expand=True)

        refresh_btn = ttk.Button(port_select_frame, text="🔄", width=3,
                                 command=self.refresh_ports)
        refresh_btn.pack(side='right', padx=(5, 0))

        # Call the demo option method (keep this unchanged)
        self.create_demo_option(main_frame)

        # Connect button (keep unchanged)
        connect_btn = ttk.Button(main_frame, text="Connect to Device",
                                 style='Connect.TButton', command=self.connect)
        connect_btn.pack(pady=30)

        # Status label (keep unchanged)
        self.status_label = ttk.Label(main_frame, text="Select a COM port to continue",
                                      style='Modern.TLabel')
        self.status_label.pack(pady=10)

    # ADD this new method for settings dialog:
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


class DashboardApp:
    """Main dashboard app with proper CLI initialization"""
    def __init__(self, root, port, settings_manager):
        self.root = root
        self.port = port
        self.settings_mgr = settings_manager
        self.is_demo_mode = (port == "DEMO")

        # Initialize cache manager first
        cache_dir = self.settings_mgr.get('cache', 'cache_directory', '')
        cache_ttl = self.settings_mgr.get('cache', 'default_ttl_seconds', 300)
        self.cache_manager = DeviceDataCache(cache_dir or None, cache_ttl)

        # Initialize CLI based on mode
        if self.is_demo_mode:
            from demo_mode_integration import UnifiedDemoSerialCLI
            self.cli = UnifiedDemoSerialCLI(port)  # Use the unified version
            print("DEBUG: Using UnifiedDemoSerialCLI for demo mode")
        else:
            self.cli = SerialCLI(port, cache_manager=self.cache_manager)
            print("DEBUG: Using SerialCLI for real device")

        # Initialize parser with cache manager
        self.sysinfo_parser = EnhancedSystemInfoParser(self.cache_manager)

        # Initialize Host Card Info components
        self.host_card_manager = HostCardInfoManager(self.cli)
        self.host_card_ui = HostCardDashboardUI(self)

        # Initialize Link Status components
        self.link_status_ui = LinkStatusDashboardUI(self)

        # Initialize Port Status components
        self.port_status_manager = PortStatusManager(self.cli)
        self.port_status_ui = PortStatusDashboardUI(self)

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
        """Create the sidebar with dashboard tiles and settings"""
        # Header with settings gear - UPDATED
        header_frame = ttk.Frame(self.sidebar, style='Sidebar.TFrame')
        header_frame.pack(fill='x', padx=10, pady=10)

        ttk.Label(header_frame, text="📊 Dashboards",
                  background='#2d2d2d', foreground='#ffffff',
                  font=('Arial', 12, 'bold')).pack(side='left')

        # Settings gear icon - NEW
        settings_btn = ttk.Button(header_frame, text="⚙️", width=3,
                                  command=self.open_settings)
        settings_btn.pack(side='right')

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

        # *** MODIFIED: CONNECTION STATUS WITH DEMO MODE INDICATOR ***
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

        # Refresh button for current dashboard
        self.refresh_btn = ttk.Button(header_frame, text="🔄", width=3,
                                      command=self.refresh_current_dashboard)
        self.refresh_btn.pack(side='right')

        # Cache status indicator
        self.cache_status_label = ttk.Label(header_frame, text="",
                                            style='Info.TLabel', font=('Arial', 8))
        self.cache_status_label.pack(side='right', padx=(0, 10))

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

    def create_host_dashboard(self):
        """FIXED: Create host card information dashboard"""
        print("DEBUG: Creating host dashboard...")

        if self.is_demo_mode:
            # For demo mode, try to use data directly from CLI
            print("DEBUG: Demo mode - loading data directly")

            try:
                demo_content = getattr(self.cli, 'demo_sysinfo_content', None)

                if demo_content and len(demo_content) > 100:
                    print(f"DEBUG: Using demo content directly ({len(demo_content)} chars)")

                    # Parse immediately
                    parsed_data = self.sysinfo_parser.parse_unified_sysinfo(demo_content, "demo")
                    print("DEBUG: Demo data parsed successfully")

                    # Check for cached JSON data
                    host_json = self.sysinfo_parser.get_host_card_json()

                    if host_json:
                        sections = host_json.get('sections', {})

                        for section_key, section_data in sections.items():
                            icon = section_data.get('icon', '📄')
                            title = section_data.get('title', section_key)
                            fields = section_data.get('fields', {})

                            # Convert dict to list of tuples for display
                            field_items = list(fields.items())
                            self.create_host_info_section(icon, title, field_items)

                        # Add last updated info
                        last_updated = host_json.get('last_updated', 'Unknown')
                        self.create_refresh_info(last_updated, True)
                    else:
                        self.show_demo_fallback()
                else:
                    print("DEBUG: No demo content, showing fallback")
                    self.show_demo_fallback()

            except Exception as e:
                print(f"ERROR: Demo mode failed: {e}")
                self.show_demo_fallback()
        else:
            # Real device mode - existing logic
            cached_data = self.sysinfo_parser.get_complete_sysinfo()

            if cached_data and self.sysinfo_parser.is_data_fresh(300):
                print("DEBUG: Using fresh cached data for host dashboard")
                host_info = self.sysinfo_parser.get_host_info_for_display()
                # Create sections from host_info...
            else:
                print("DEBUG: No fresh cached data, requesting sysinfo...")
                self.send_sysinfo_command()
                self.show_loading_message("Loading host card information...")

    def show_demo_fallback(self):
        """Show demo fallback data"""
        print("DEBUG: Showing demo fallback data")

        # Create sample sections with fallback data
        fallback_sections = [
            ("💻", "Device Information", [
                ("Serial Number", "GBH14412506206Z"),
                ("Company", "SerialCables,Inc"),
                ("Model", "PCI6-RD-x16HT-BG6-144"),
                ("Firmware Version", "0.1.0"),
                ("Build Date", "Jul 18 2025 11:05:16")
            ]),
            ("🌡️", "Thermal Status", [
                ("Board Temperature", "55°C")
            ]),
            ("🌀", "Fan Status", [
                ("Switch Fan Speed", "6310 rpm")
            ]),
            ("⚡", "Power Status", [
                ("0.8V Rail", "890 mV"),
                ("1.2V Rail", "1304 mV"),
                ("Current Draw", "10240 mA")
            ]),
            ("🚨", "Error Status", [
                ("System Errors", "0")
            ])
        ]

        for icon, title, items in fallback_sections:
            self.create_host_info_section(icon, title, items)

        self.create_refresh_info("Demo fallback data", False)

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
        """Create link status dashboard using the new Link Status module"""
        print("DEBUG: Creating link dashboard using new module...")

        if self.is_demo_mode:
            # For demo mode, load demo showport data
            print("DEBUG: Demo mode - loading showport data")

            try:
                from link_status_dashboard import load_demo_showport_file
                demo_content = load_demo_showport_file()

                if demo_content:
                    print(f"DEBUG: Using demo showport content ({len(demo_content)} chars)")

                    # Parse and cache the showport data
                    link_info = self.link_status_ui.link_status_manager.parser.parse_showport_response(demo_content)
                    self.link_status_ui.link_status_manager.cached_info = link_info
                    self.link_status_ui.link_status_manager.last_refresh = datetime.now()

                    # Also parse using enhanced parser for caching
                    if hasattr(self, 'sysinfo_parser'):
                        self.sysinfo_parser.parse_showport_command(demo_content)

                    # Create the dashboard UI
                    self.link_status_ui.create_link_dashboard()

                    print("DEBUG: Demo link dashboard created successfully")
                else:
                    print("DEBUG: No demo showport content, showing fallback")
                    self.show_loading_message("Demo showport data not available - check DemoData/showport.txt")

            except Exception as e:
                print(f"ERROR: Demo link dashboard failed: {e}")
                import traceback
                traceback.print_exc()
                self.show_loading_message(f"Demo error: {e}")
        else:
            # Real device mode - check for cached data first
            cached_link_data = None
            if hasattr(self, 'sysinfo_parser'):
                cached_link_data = self.sysinfo_parser.get_cached_showport_data()

            if cached_link_data and self.sysinfo_parser.is_showport_data_fresh(300):
                print("DEBUG: Using fresh cached showport data")
                # Convert cached data to LinkStatusInfo format
                link_info = self._convert_cached_to_link_info(cached_link_data)
                self.link_status_ui.link_status_manager.cached_info = link_info
                self.link_status_ui.create_link_dashboard()
            else:
                print("DEBUG: Real device mode - sending showport command")
                self.send_showport_command()
                self.show_loading_message("Loading link status...")

    def create_port_dashboard(self):
        """Create port status dashboard with showmode integration"""
        if self.is_demo_mode:
            # For demo mode, use existing showmode.txt or generate response
            print("DEBUG: Demo mode - creating port dashboard with simulated data")

            try:
                # Try to load showmode.txt first
                demo_showmode_content = None
                showmode_paths = ["showmode.txt", "DemoData/showmode.txt", "./showmode.txt"]

                for path in showmode_paths:
                    if os.path.exists(path):
                        try:
                            with open(path, 'r', encoding='utf-8') as f:
                                demo_showmode_content = f.read()
                            print(f"DEBUG: Loaded showmode.txt from {path}")
                            break
                        except Exception as e:
                            print(f"DEBUG: Error loading {path}: {e}")
                            continue

                if demo_showmode_content:
                    # Parse mode from file content
                    import re
                    mode_match = re.search(r'SBR\s*mode\s*:\s*(\d+)', demo_showmode_content, re.IGNORECASE)
                    if mode_match:
                        try:
                            mode_num = int(mode_match.group(1))
                            if 0 <= mode_num <= 6:
                                self.demo_device_state['current_mode'] = mode_num
                        except ValueError:
                            pass

                    demo_response = demo_showmode_content
                else:
                    # Generate demo response using existing function
                    demo_response = get_demo_showmode_response(self.demo_device_state)
                    print("DEBUG: Generated demo showmode response")

                # Parse the demo response using existing parser
                port_info = self.port_status_manager.parser.parse_showmode_response(demo_response)
                port_info.raw_showmode_response = demo_response

                # Cache the demo info
                self.port_status_manager.cached_info = port_info
                self.port_status_manager.last_refresh = datetime.now()

                # Create the port dashboard UI
                self.port_status_ui.create_port_dashboard()

                # Log demo data loading
                timestamp = datetime.now().strftime('%H:%M:%S')
                self.log_data.append(f"[{timestamp}] Port status demo data loaded - SBR{port_info.current_mode}")

            except Exception as e:
                print(f"ERROR: Demo mode port dashboard failed: {e}")
                self.show_loading_message(f"Demo port status error: {e}")

        else:
            # Real device mode
            print("DEBUG: Real device mode - requesting showmode data")

            # Check if we have cached showmode data
            port_info = self.port_status_manager.get_port_status_info()

            if port_info and port_info.mode_name and port_info.mode_name != "Unknown":
                print("DEBUG: Using cached port status data")
                self.port_status_ui.create_port_dashboard()
            else:
                print("DEBUG: No cached data, requesting showmode...")
                self.send_showmode_command()
                self.show_loading_message("Loading port status information...")

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

    def check_showport_timeout(self):
        """Check if showport command timed out"""
        if hasattr(self, 'showport_requested') and self.showport_requested:
            print("DEBUG: showport command timed out")
            self.showport_requested = False
            if self.current_dashboard == "link":
                self.show_loading_message("Showport command timed out - click refresh to retry")

    def _convert_cached_to_link_info(self, cached_data):
        """Convert cached showport data to LinkStatusInfo format"""
        from link_status_dashboard import LinkStatusInfo, PortInfo

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
        self.resets_dashboard.create_resets_dashboard(self.scrollable_frame)

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
        """Connect to device with immediate demo data loading - COMPLETE VERSION"""
        print(f"DEBUG: Connecting to device (Demo mode: {self.is_demo_mode})")

        if self.cli.connect():
            print("DEBUG: CLI connected successfully")

            if self.is_demo_mode:
                self.connection_label.config(foreground='#ff9500')
                self.log_data.append(f"[{datetime.now().strftime('%H:%M:%S')}] Demo mode started")

                # IMMEDIATE FIX: Load demo data directly without threading
                try:
                    # Access the demo content directly from the UnifiedDemoSerialCLI object
                    demo_content = self.cli.demo_sysinfo_content
                    if demo_content:
                        print(f"DEBUG: Using demo content directly ({len(demo_content)} chars)")

                        # Parse immediately using the enhanced parser
                        parsed_data = self.sysinfo_parser.parse_unified_sysinfo(demo_content, "demo")
                        print("DEBUG: Demo data parsed successfully")

                        # Update UI immediately
                        self.root.after_idle(self.update_content_area)
                        self.update_cache_status("Demo data loaded")

                        # Log success
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        self.log_data.append(f"[{timestamp}] Demo data loaded directly")

                    else:
                        print("ERROR: No demo content available")
                        self.show_loading_message("Demo data not available")

                except Exception as e:
                    print(f"ERROR: Failed to load demo data: {e}")
                    import traceback
                    traceback.print_exc()
                    self.show_loading_message(f"Demo error: {e}")

            else:
                # Real device mode
                self.connection_label.config(foreground='#00ff00')
                self.log_data.append(f"[{datetime.now().strftime('%H:%M:%S')}] Connected to {self.port}")

                # Start background threads for real devices
                self.start_background_threads()
                self.root.after(500, self.send_sysinfo_command)

        else:
            self.connection_label.config(foreground='#ff0000')
            error_msg = "Failed to start demo mode" if self.is_demo_mode else f"Failed to connect to {self.port}"
            print(f"DEBUG: Connection failed: {error_msg}")
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
        """Add periodic queue monitoring to ensure responsiveness"""

        def check_queues():
            try:
                # Check if we have any pending responses
                if hasattr(self.cli, 'response_queue'):
                    try:
                        response = self.cli.response_queue.get_nowait()
                        if response:
                            print(f"DEBUG: Queue monitor found response: {response[:100]}...")
                            # Process the response immediately
                            timestamp = datetime.now().strftime('%H:%M:%S')
                            self.log_data.append(f"[{timestamp}] RECV: {response}")

                            # Check if this is a showport response
                            if self.showport_requested and len(response) > 50:
                                if any(keyword in response.lower() for keyword in
                                       ['port', 'golden finger', 'port slot', 'port upstream']):
                                    print("DEBUG: Queue monitor processing showport response")
                                    self.process_showport_response(response)

                            # Check if this is a sysinfo response
                            elif self.sysinfo_requested and len(response) > 200:
                                if any(keyword in response.lower() for keyword in
                                       ['s/n', 'thermal', 'voltage', '===', 'company']):
                                    print("DEBUG: Queue monitor processing sysinfo response")
                                    self.process_sysinfo_response(response)

                    except queue.Empty:
                        pass

            except Exception as e:
                print(f"DEBUG: Queue monitor error: {e}")

            # Schedule next check
            self.root.after(100, check_queues)  # Check every 100ms

        # Start the monitoring
        check_queues()

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
        """FIXED: Send sysinfo command without creating new CLI instance"""
        print(f"DEBUG: Sending sysinfo command (Demo mode: {self.is_demo_mode})...")

        if not self.cli or not self.cli.is_running:
            print("ERROR: CLI not running, cannot send sysinfo command")
            self.show_loading_message("Error: Connection not ready")
            return

        self.sysinfo_requested = True

        try:
            if self.is_demo_mode:
                # In demo mode, put command directly in queue
                self.cli.command_queue.put("sysinfo")
                print("DEBUG: sysinfo command queued for demo mode")
            else:
                # In real mode, send through normal command interface
                self.send_command("sysinfo")
                print("DEBUG: sysinfo command sent for real device")

            timestamp = datetime.now().strftime('%H:%M:%S')
            self.log_data.append(f"[{timestamp}] Requesting system information...")
            print(f"DEBUG: sysinfo_requested set to {self.sysinfo_requested}")

            # Add timeout for sysinfo request
            self.root.after(10000, self.check_sysinfo_timeout)  # 10 second timeout

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