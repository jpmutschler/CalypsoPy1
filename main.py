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

CLEANED VERSION: Link Status methods moved to dedicated dashboard module
"""

# Application Information
APP_NAME = "CalypsoPy"
APP_VERSION = "1.5.0"  # Updated version to reflect refactoring
APP_BUILD = "20250820-001"  # Updated build
APP_DESCRIPTION = "Serial Cables Atlas 3 Serial UI for CLI Interface"
APP_AUTHOR = "Serial Cables, LLC"
APP_COPYRIGHT = "© 2025"

# Version History - UPDATED WITH REFACTORING
VERSION_HISTORY = {
    "Beta 1.2.0": {
        "date": "2025-08-20",
        "changes": [
            "Refactored Link Status Dashboard to be fully self-contained",
            "Cleaned up main.py by removing dashboard-specific methods",
            "Improved dashboard initialization consistency",
            "Enhanced modular architecture",
            "Better separation of concerns"
        ]
    },
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


# =====================================================================
# STANDARD LIBRARY IMPORTS
# =====================================================================
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import queue
import sys
import os
import re
from datetime import datetime

# =====================================================================
# THIRD-PARTY IMPORTS
# =====================================================================
import serial
import serial.tools.list_ports

# =====================================================================
# ADMIN MODULE IMPORTS - System management and utilities
# =====================================================================
from Admin.cache_manager import DeviceDataCache
from Admin.enhanced_sysinfo_parser import EnhancedSystemInfoParser
from Admin.settings_manager import SettingsManager
from Admin.settings_ui import SettingsDialog
from Admin.advanced_response_handler import AdvancedResponseHandler
from Admin.debug_config import (
    debug,
    port_debug,
    host_debug,
    cache_debug,
    log_info,
    log_error,
    log_debug
)
import Admin.settings_ui as settings_ui

# =====================================================================
# DASHBOARD MODULE IMPORTS - UI components and dashboard logic
# =====================================================================
from Dashboards.host_card_info import (
    HostCardInfoManager,
    HostCardDashboardUI
)
from Dashboards.link_status_dashboard import LinkStatusDashboardUI
from Dashboards.port_status_dashboard import (
    PortStatusManager,
    PortStatusDashboardUI,
    get_demo_showmode_response,
    update_demo_device_state
)
from Dashboards.firmware_dashboard import FirmwareDashboard
from Dashboards.resets_dashboard import ResetsDashboard

# =====================================================================
# OPTIONAL IMPORTS - PIL for image support
# =====================================================================
try:
    from PIL import Image, ImageTk

    PIL_AVAILABLE = True
    print("DEBUG: PIL available for image support")
except ImportError:
    PIL_AVAILABLE = False
    print("WARNING: PIL not available. SBR mode images will not be displayed.")


# =====================================================================
# UTILITY FUNCTIONS
# =====================================================================
def get_window_title(subtitle="", demo_mode=False):
    """Generate window title with proper branding"""
    base_title = f"{APP_NAME} {APP_VERSION}"

    if subtitle:
        base_title += f" - {subtitle}"

    if demo_mode:
        base_title += " 🎭 [DEMO MODE]"

    return base_title


class SerialCLI:
    """
    Background CLI handler for serial communication with caching support

    This class handles the actual serial communication with hardware devices,
    providing queued command/response handling and logging capabilities.
    """

    def __init__(self, port, cache_manager=None):
        """
        Initialize SerialCLI instance

        Args:
            port (str): Serial port identifier (e.g., 'COM3', '/dev/ttyUSB0')
            cache_manager (DeviceDataCache, optional): Cache manager for response caching
        """
        self.port = port
        self.cache_manager = cache_manager
        self.is_running = False

        # Initialize communication queues
        self.command_queue = queue.Queue()
        self.response_queue = queue.Queue()  # CRITICAL: Required for response handling
        self.log_queue = queue.Queue()

        # Serial connection configuration
        self.serial_connection = None
        self.baudrate = 115200
        self.timeout = 1.0

        # Background thread control
        self.background_thread = None

        print(f"DEBUG: SerialCLI initialized for port {port}")

    def connect(self):
        """
        Establish serial connection to device

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )

            self.is_running = True
            self.log_queue.put(f"Connected to {self.port} at {self.baudrate} baud")
            print(f"DEBUG: Serial connection established to {self.port}")
            return True

        except serial.SerialException as e:
            error_msg = f"Serial connection failed: {e}"
            self.log_queue.put(error_msg)
            print(f"ERROR: {error_msg}")
            return False
        except Exception as e:
            error_msg = f"Unexpected connection error: {e}"
            self.log_queue.put(error_msg)
            print(f"ERROR: {error_msg}")
            return False

    def disconnect(self):
        """
        Close serial connection and cleanup resources
        """
        print("DEBUG: Disconnecting SerialCLI")
        self.is_running = False

        # Wait for background thread to finish
        if self.background_thread and self.background_thread.is_alive():
            self.background_thread.join(timeout=2.0)

        # Close serial connection
        if self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.close()
                self.log_queue.put("Serial connection closed")
                print("DEBUG: Serial connection closed successfully")
            except Exception as e:
                print(f"WARNING: Error closing serial connection: {e}")

    def send_command(self, command):
        """
        Send command to device

        Args:
            command (str): Command string to send

        Returns:
            bool: True if command sent successfully, False otherwise
        """
        if not self.is_running or not self.serial_connection:
            print("WARNING: Cannot send command - not connected")
            return False

        try:
            # Ensure command has proper line ending
            cmd_with_ending = f"{command.strip()}\r\n"
            self.serial_connection.write(cmd_with_ending.encode('utf-8'))

            # Log the sent command
            self.log_queue.put(f"SENT: {command}")
            print(f"DEBUG: Command sent: {command}")
            return True

        except serial.SerialException as e:
            error_msg = f"Serial send error: {e}"
            self.log_queue.put(error_msg)
            print(f"ERROR: {error_msg}")
            return False
        except Exception as e:
            error_msg = f"Unexpected send error: {e}"
            self.log_queue.put(error_msg)
            print(f"ERROR: {error_msg}")
            return False

    def read_response(self):
        """
        Read response from device and queue it

        Returns:
            str: Response string if available, None otherwise
        """
        if not self.is_running or not self.serial_connection:
            return None

        try:
            # Check if data is available
            if self.serial_connection.in_waiting > 0:
                # Read available data
                raw_data = self.serial_connection.readline()

                if raw_data:
                    # Decode and clean up response
                    response = raw_data.decode('utf-8', errors='ignore').strip()

                    if response:  # Only process non-empty responses
                        # Queue for processing
                        self.response_queue.put(response)
                        self.log_queue.put(f"RECV: {response}")

                        # Cache response if cache manager available
                        if self.cache_manager:
                            self._cache_response(response)

                        return response

        except serial.SerialException as e:
            error_msg = f"Serial read error: {e}"
            self.log_queue.put(error_msg)
            print(f"ERROR: {error_msg}")
        except UnicodeDecodeError as e:
            error_msg = f"Response decode error: {e}"
            self.log_queue.put(error_msg)
            print(f"WARNING: {error_msg}")
        except Exception as e:
            error_msg = f"Unexpected read error: {e}"
            self.log_queue.put(error_msg)
            print(f"ERROR: {error_msg}")

        return None

    def _cache_response(self, response):
        """
        Cache response data if cache manager is available

        Args:
            response (str): Response string to cache
        """
        try:
            if self.cache_manager and len(response) > 10:  # Only cache substantial responses
                # Basic response classification for caching
                if "S/N" in response or "Version" in response:
                    self.cache_manager.set('last_ver_response', response)
                elif "Temperature" in response or "Voltage" in response:
                    self.cache_manager.set('last_lsd_response', response)
                elif "Port" in response and "speed" in response:
                    self.cache_manager.set('last_showport_response', response)
                elif "mode" in response.lower():
                    self.cache_manager.set('last_showmode_response', response)

        except Exception as e:
            print(f"WARNING: Response caching failed: {e}")

    def start_background(self):
        """
        Start background thread for continuous reading
        """
        if not self.is_running:
            print("WARNING: Cannot start background thread - not connected")
            return

        if self.background_thread and self.background_thread.is_alive():
            print("DEBUG: Background thread already running")
            return

        def background_reader():
            """Background thread function for reading responses"""
            print("DEBUG: Background reader thread started")
            while self.is_running:
                try:
                    self.read_response()
                    time.sleep(0.01)  # Small delay to prevent excessive CPU usage
                except Exception as e:
                    print(f"ERROR: Background reader error: {e}")

            print("DEBUG: Background reader thread stopped")

        # Start the background thread
        self.background_thread = threading.Thread(target=background_reader, daemon=True)
        self.background_thread.start()
        print("DEBUG: Background reading thread started")

    def get_stats(self):
        """
        Get connection statistics

        Returns:
            dict: Statistics about the serial connection
        """
        return {
            'port': self.port,
            'baudrate': self.baudrate,
            'is_running': self.is_running,
            'is_connected': self.serial_connection and self.serial_connection.is_open if self.serial_connection else False,
            'command_queue_size': self.command_queue.qsize(),
            'response_queue_size': self.response_queue.qsize(),
            'log_queue_size': self.log_queue.qsize(),
            'cache_enabled': self.cache_manager is not None
        }


class ConnectionWindow:
    """
    Connection window for device selection and demo mode configuration

    This class provides the initial connection interface where users can:
    - Select COM ports for real device connections
    - Enable demo mode for testing without hardware
    - Access application settings
    - Connect to devices and launch the main dashboard
    """

    def __init__(self, root, settings_manager):
        """
        Initialize connection window

        Args:
            root (tk.Tk): Root tkinter window
            settings_manager (SettingsManager): Application settings manager
        """
        self.root = root
        self.settings_mgr = settings_manager

        # Demo mode state
        self.demo_var = tk.BooleanVar()
        self.demo_var.set(self.settings_mgr.get('demo', 'enabled_by_default', False))

        # Auto-refresh job tracking
        self.auto_refresh_job = None

        # Port selection state
        self.port_var = tk.StringVar()

        print("DEBUG: ConnectionWindow initialized")

        # Set up the window and widgets
        self.setup_window()
        self.create_widgets()
        self.refresh_ports()

    def setup_window(self):
        """Configure the connection window properties"""
        # Window title and basic properties
        self.root.title(get_window_title("Connection"))
        self.root.geometry("500x550")  # Slightly larger for better layout
        self.root.resizable(False, False)  # Fixed size for consistency

        # Center the window on screen
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

        # Set application icon if available
        try:
            self.root.iconbitmap("assets/Logo_gal_ico.ico")
        except:
            pass  # Ignore if icon file not found

        # Configure window closing behavior
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Configure modern styling
        self._configure_styles()

    def _configure_styles(self):
        """Configure modern ttk styles for the connection window"""
        style = ttk.Style()

        # Modern theme configuration
        try:
            style.theme_use('clam')
        except:
            pass  # Use default if clam not available

        # Custom styles for connection window
        style.configure('Modern.TFrame', background='#1e1e1e')
        style.configure('Modern.TLabel',
                        background='#1e1e1e',
                        foreground='#ffffff',
                        font=('Arial', 11))
        style.configure('Title.TLabel',
                        background='#1e1e1e',
                        foreground='#ffffff',
                        font=('Arial', 18, 'bold'))
        style.configure('Modern.TCombobox', font=('Arial', 11))
        style.configure('Connect.TButton',
                        font=('Arial', 12, 'bold'),
                        padding=(20, 10))
        style.configure('Demo.TCheckbutton',
                        background='#1e1e1e',
                        foreground='#ff9500',
                        font=('Arial', 11, 'bold'))

    def create_widgets(self):
        """Create and layout the connection window widgets"""
        # Main container frame
        main_frame = ttk.Frame(self.root, style='Modern.TFrame', padding=40)
        main_frame.pack(fill='both', expand=True)

        # Title section with settings button
        self._create_title_section(main_frame)

        # COM Port selection section
        self._create_port_section(main_frame)

        # Demo mode section
        self._create_demo_section(main_frame)

        # Connection button section
        self._create_connection_section(main_frame)

        # Status section
        self._create_status_section(main_frame)

    def _create_title_section(self, parent):
        """Create the title section with settings button"""
        title_frame = ttk.Frame(parent, style='Modern.TFrame')
        title_frame.pack(fill='x', pady=(0, 30))

        # Application title
        title_label = ttk.Label(title_frame,
                                text="🔌 Device Connection",
                                style='Title.TLabel')
        title_label.pack(side='left')

        # Settings button
        settings_btn = ttk.Button(title_frame,
                                  text="⚙️",
                                  width=3,
                                  command=self.open_settings)
        settings_btn.pack(side='right')

    def _create_port_section(self, parent):
        """Create the COM port selection section"""
        port_frame = ttk.Frame(parent, style='Modern.TFrame')
        port_frame.pack(fill='x', pady=15)

        # Port selection label
        ttk.Label(port_frame,
                  text="COM Port:",
                  style='Modern.TLabel').pack(anchor='w')

        # Port selection controls
        port_select_frame = ttk.Frame(port_frame, style='Modern.TFrame')
        port_select_frame.pack(fill='x', pady=(5, 0))

        # Port dropdown
        self.port_combo = ttk.Combobox(port_select_frame,
                                       textvariable=self.port_var,
                                       state='readonly',
                                       font=('Arial', 11),
                                       style='Modern.TCombobox')
        self.port_combo.pack(side='left', fill='x', expand=True)

        # Refresh button
        self.refresh_btn = ttk.Button(port_select_frame,
                                      text="🔄",
                                      width=3,
                                      command=self.refresh_ports_with_feedback)
        self.refresh_btn.pack(side='right', padx=(5, 0))

        # Port status label
        port_status_frame = ttk.Frame(port_frame, style='Modern.TFrame')
        port_status_frame.pack(fill='x', pady=(5, 0))

        self.port_status_label = ttk.Label(port_status_frame,
                                           text="",
                                           style='Modern.TLabel',
                                           font=('Arial', 9))
        self.port_status_label.pack(anchor='w')

    def _create_demo_section(self, parent):
        """Create the demo mode section"""
        demo_frame = ttk.Frame(parent, style='Modern.TFrame')
        demo_frame.pack(fill='x', pady=15)

        # Demo mode checkbox
        demo_check = ttk.Checkbutton(demo_frame,
                                     text="🎭 Demo Mode (No hardware required)",
                                     variable=self.demo_var,
                                     style='Demo.TCheckbutton',
                                     command=self.on_demo_toggle)
        demo_check.pack(anchor='w')

        # Demo mode description
        self.demo_info = ttk.Label(demo_frame,
                                   text="Perfect for training, testing, or when no device is available",
                                   style='Modern.TLabel',
                                   font=('Arial', 9, 'italic'))
        self.demo_info.pack(anchor='w', pady=(5, 0))

    def _create_connection_section(self, parent):
        """Create the connection button section"""
        # Connect button
        self.connect_btn = ttk.Button(parent,
                                      text="Connect to Device",
                                      style='Connect.TButton',
                                      command=self.connect_device)
        self.connect_btn.pack(pady=30)

    def _create_status_section(self, parent):
        """Create the status display section"""
        # Status label
        self.status_label = ttk.Label(parent,
                                      text="Select a port or enable demo mode",
                                      style='Modern.TLabel',
                                      font=('Arial', 10))
        self.status_label.pack(pady=10)

    def refresh_ports(self):
        """Refresh available COM ports"""
        if self.demo_var.get():
            return  # Skip port refresh in demo mode

        try:
            # Get available serial ports
            ports = [port.device for port in serial.tools.list_ports.comports()]

            # Update combobox values
            self.port_combo['values'] = ports

            if ports:
                # Select first port if none selected
                if not self.port_var.get() or self.port_var.get() not in ports:
                    self.port_combo.current(0)

                self.port_status_label.config(text=f"Found {len(ports)} available ports")
                self.connect_btn.config(state='normal')
            else:
                self.port_status_label.config(text="No COM ports found")
                self.connect_btn.config(state='disabled')

        except Exception as e:
            error_msg = f"Error scanning ports: {e}"
            self.port_status_label.config(text=error_msg)
            print(f"ERROR: {error_msg}")

    def refresh_ports_with_feedback(self):
        """Enhanced port refresh with visual feedback"""
        # Disable button and show refreshing state
        self.refresh_btn.config(state='disabled', text="⟳")
        self.port_status_label.config(text="🔄 Scanning for COM ports...")
        self.root.update()

        # Store current selection
        current_selection = self.port_var.get()

        try:
            # Perform refresh
            self.refresh_ports()

            # Restore selection if still available
            if current_selection and current_selection in self.port_combo['values']:
                self.port_var.set(current_selection)

        except Exception as e:
            self.port_status_label.config(text=f"Refresh failed: {e}")
        finally:
            # Restore button state
            self.refresh_btn.config(state='normal', text="🔄")

    def on_demo_toggle(self):
        """Handle demo mode toggle"""
        if self.demo_var.get():
            # Demo mode enabled
            self.port_combo.config(state='disabled')
            self.refresh_btn.config(state='disabled')
            self.port_status_label.config(text="🎭 Demo mode active - COM port scanning disabled")
            self.connect_btn.config(state='normal')
            self.status_label.config(text="Ready to start training session")
        else:
            # Demo mode disabled
            self.port_combo.config(state='readonly')
            self.refresh_btn.config(state='normal')
            self.refresh_ports()
            self.status_label.config(text="Select a port to connect")

    def connect_device(self):
        """Connect to the selected device or start demo mode"""
        try:
            # Determine connection target
            if self.demo_var.get():
                selected_port = "DEMO"
                self.status_label.config(text="Starting demo mode...")
            else:
                selected_port = self.port_var.get()
                if not selected_port:
                    messagebox.showerror("No Port Selected",
                                         "Please select a COM port or enable demo mode")
                    return
                self.status_label.config(text=f"Connecting to {selected_port}...")

            # Update UI for connection attempt
            self.connect_btn.config(state='disabled', text="Connecting...")
            self.root.update()

            # Save demo mode preference
            self.settings_mgr.set('demo', 'enabled_by_default', self.demo_var.get())
            self.settings_mgr.save()

            # Attempt connection with delay for UI feedback
            self.root.after(1000, lambda: self.open_dashboard(selected_port))

        except Exception as e:
            error_msg = f"Connection setup failed: {e}"
            self.status_label.config(text="Connection failed")
            self.connect_btn.config(state='normal', text="Connect to Device")
            messagebox.showerror("Connection Error", error_msg)
            print(f"ERROR: {error_msg}")

    def open_dashboard(self, port):
        """
        Open the main dashboard window

        Args:
            port (str): Port identifier or "DEMO" for demo mode
        """
        try:
            # Get screen dimensions for proper window sizing
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()

            print(f"DEBUG: Opening dashboard for {port}")
            print(f"DEBUG: Screen resolution: {screen_width}x{screen_height}")

            # Hide connection window
            self.root.withdraw()

            # Create dashboard window
            dashboard_root = tk.Toplevel()

            # Configure dashboard window size (85% of screen)
            window_width = int(screen_width * 0.85)
            window_height = int(screen_height * 0.85)
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2

            dashboard_root.geometry(f"{window_width}x{window_height}+{x}+{y}")
            dashboard_root.minsize(1400, 1000)

            # Try to maximize for best experience on large displays
            try:
                dashboard_root.state('zoomed')
                print("DEBUG: Dashboard window maximized")
            except:
                print("DEBUG: Window maximize not supported on this platform")

            print(f"DEBUG: Dashboard window size: {window_width}x{window_height}")

            # Create dashboard application
            dashboard_app = DashboardApp(dashboard_root, port, self.settings_mgr)

            # Handle dashboard window closing
            def on_dashboard_close():
                """Handle dashboard window close event"""
                try:
                    # Disconnect from device
                    if hasattr(dashboard_app, 'cli') and dashboard_app.cli:
                        dashboard_app.cli.disconnect()

                    # Destroy dashboard window
                    dashboard_root.destroy()

                    # Show connection window again
                    self.root.deiconify()

                    # Reset connection button
                    self.connect_btn.config(state='normal', text="Connect to Device")
                    self.status_label.config(text="Select a port or enable demo mode")

                except Exception as e:
                    print(f"ERROR: Error during dashboard close: {e}")

            dashboard_root.protocol("WM_DELETE_WINDOW", on_dashboard_close)

            # Start the dashboard main loop
            dashboard_root.mainloop()

        except Exception as e:
            error_msg = f"Failed to open dashboard: {e}"
            print(f"ERROR: {error_msg}")
            messagebox.showerror("Dashboard Error", error_msg)

            # Show connection window again
            self.root.deiconify()
            self.connect_btn.config(state='normal', text="Connect to Device")
            self.status_label.config(text="Dashboard launch failed")

    def open_settings(self):
        """Open the settings dialog"""
        try:
            # Create settings dialog
            settings_ui.SettingsDialog(self.root, None)  # No cache manager in connection window
        except Exception as e:
            error_msg = f"Failed to open settings: {e}"
            print(f"ERROR: {error_msg}")
            messagebox.showerror("Settings Error", error_msg)

    def start_auto_refresh(self):
        """Start automatic port refresh if enabled"""
        if self.settings_mgr.get('refresh', 'enabled', False) and not self.demo_var.get():
            interval = self.settings_mgr.get('refresh', 'interval_seconds', 30) * 1000
            self.auto_refresh_job = self.root.after(interval, self._auto_refresh_ports)

    def _auto_refresh_ports(self):
        """Automatically refresh ports"""
        if not self.demo_var.get():
            try:
                self.refresh_ports()
            except Exception as e:
                print(f"WARNING: Auto-refresh failed: {e}")

            # Schedule next refresh
            if self.settings_mgr.get('refresh', 'enabled', False):
                interval = self.settings_mgr.get('refresh', 'interval_seconds', 30) * 1000
                self.auto_refresh_job = self.root.after(interval, self._auto_refresh_ports)

    def stop_auto_refresh(self):
        """Stop automatic port refresh"""
        if self.auto_refresh_job:
            try:
                self.root.after_cancel(self.auto_refresh_job)
                self.auto_refresh_job = None
            except Exception as e:
                print(f"WARNING: Error stopping auto-refresh: {e}")

    def on_closing(self):
        """Handle connection window closing"""
        try:
            # Stop auto-refresh
            self.stop_auto_refresh()

            # Save any pending settings
            try:
                self.settings_mgr.save()
            except Exception as e:
                print(f"WARNING: Error saving settings: {e}")

            # Destroy the window
            self.root.destroy()

        except Exception as e:
            print(f"ERROR: Error during window close: {e}")
            # Force close anyway
            self.root.destroy()

    def __del__(self):
        """Cleanup when object is destroyed"""
        if hasattr(self, 'auto_refresh_job') and self.auto_refresh_job:
            try:
                self.root.after_cancel(self.auto_refresh_job)
            except:
                pass  # Ignore cleanup errors


class DashboardApp:
    """
    Main dashboard application with cleaned architecture

    This class manages the main dashboard interface, CLI communication,
    and coordinates between different dashboard modules. Link Status
    functionality has been properly encapsulated in its dedicated module.
    """

    def __init__(self, root, port, settings_manager):
        """Initialize DashboardApp with proper attribute initialization order"""
        print("DEBUG: DashboardApp.__init__ starting...")

        self.root = root
        self.port = port
        self.settings_mgr = settings_manager
        self.is_demo_mode = (port == "DEMO")

        # CRITICAL: Initialize all required attributes FIRST
        self.log_data = []  # MISSING ATTRIBUTE FIX
        self.current_dashboard = "host"
        self.background_tasks_enabled = True  # MISSING ATTRIBUTE FIX
        self.sysinfo_requested = False
        self.showport_requested = False
        self.tile_frames = {}  # Initialize early to prevent errors

        print("DEBUG: Basic attributes initialized")

        # Initialize cache manager first
        cache_dir = self.settings_mgr.get('cache', 'cache_directory', '')
        cache_ttl = self.settings_mgr.get('cache', 'default_ttl_seconds', 300)
        self.cache_manager = DeviceDataCache(cache_dir or None, cache_ttl)
        print("DEBUG: Cache manager initialized")

        # Initialize CLI based on mode
        if self.is_demo_mode:
            from Dashboards.demo_mode_integration import UnifiedDemoSerialCLI
            self.cli = UnifiedDemoSerialCLI(port)  # Use the unified version
            print("DEBUG: Using UnifiedDemoSerialCLI for demo mode")
        else:
            self.cli = SerialCLI(port, cache_manager=self.cache_manager)
            print("DEBUG: Using SerialCLI for real device")

        # Initialize parser with cache manager
        self.sysinfo_parser = EnhancedSystemInfoParser(self.cache_manager)
        print("DEBUG: Sysinfo parser initialized")

        # Initialize the advanced response handler
        self.init_advanced_response_handler()

        # Initialize Host Card Info components
        self.host_card_manager = HostCardInfoManager(self.cli)
        self.host_card_ui = HostCardDashboardUI(self)  # MISSING ATTRIBUTE FIX
        print("DEBUG: Host card components initialized")

        # Initialize Link Status components
        self.link_status_ui = LinkStatusDashboardUI(self)
        print("DEBUG: Link status components initialized")

        # Initialize Port Status components
        self.port_status_manager = PortStatusManager(self.cli)
        self.port_status_ui = PortStatusDashboardUI(self)
        print("DEBUG: Port status components initialized")

        # Initialize Resets Dashboard components
        self.resets_dashboard = ResetsDashboard(self)
        print("DEBUG: Resets dashboard initialized")

        # Initialize Firmware Dashboard
        self.firmware_dashboard = FirmwareDashboard(self)
        print("DEBUG: Firmware dashboard initialized")

        # Demo device state for port status (if demo mode)
        self.demo_device_state = {'current_mode': 0}

        # Auto-refresh setup
        self.auto_refresh_enabled = self.settings_mgr.get('refresh', 'enabled', False)
        self.auto_refresh_interval = self.settings_mgr.get('refresh', 'interval_seconds', 30)
        self.auto_refresh_timer = None
        print("DEBUG: Auto-refresh settings loaded")

        # UI Setup - CRITICAL ORDER
        print("DEBUG: Starting UI setup...")
        self.setup_window()
        print("DEBUG: Window setup complete")

        self.create_layout()  # This creates self.sidebar
        print("DEBUG: Layout creation complete")

        # Connect device and start background tasks
        self.connect_device()
        print("DEBUG: Device connection complete")

        self.start_background_threads()
        print("DEBUG: Background threads started")

        if self.auto_refresh_enabled:
            self.start_auto_refresh()
            print("DEBUG: Auto-refresh started")

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        print("DEBUG: DashboardApp initialization complete")

    def _init_cache_manager(self):
        """Initialize cache manager"""
        try:
            cache_dir = self.settings_mgr.get('cache', 'cache_directory', '')
            cache_ttl = self.settings_mgr.get('cache', 'default_ttl_seconds', 300)
            self.cache_manager = DeviceDataCache(cache_dir or None, cache_ttl)
            print("DEBUG: Cache manager initialized")
        except Exception as e:
            print(f"ERROR: Failed to initialize cache manager: {e}")
            self.cache_manager = None

    def _init_cli(self):
        """Initialize CLI based on mode"""
        try:
            if self.is_demo_mode:
                from Dashboards.demo_mode_integration import UnifiedDemoSerialCLI
                self.cli = UnifiedDemoSerialCLI(self.port)
                print("DEBUG: Using UnifiedDemoSerialCLI for demo mode")
            else:
                self.cli = SerialCLI(self.port, cache_manager=self.cache_manager)
                print("DEBUG: Using SerialCLI for real device")
        except Exception as e:
            print(f"ERROR: Failed to initialize CLI: {e}")
            raise

    def _init_admin_components(self):
        """Initialize admin components"""
        try:
            # Enhanced sysinfo parser
            self.sysinfo_parser = EnhancedSystemInfoParser(self.cache_manager)
            print("DEBUG: Enhanced sysinfo parser initialized")

            # Advanced response handler
            self.init_advanced_response_handler()

        except Exception as e:
            print(f"ERROR: Failed to initialize admin components: {e}")

    def _init_dashboard_components(self):
        """Initialize ALL dashboard components consistently - CORRECTED"""
        try:
            # Host Card Info components - NOW properly initialized
            self.host_card_manager = HostCardInfoManager(self.cli)
            self.host_card_ui = HostCardDashboardUI(self)
            print("DEBUG: Host Card Dashboard initialized")

            # Link Status components - NOW properly initialized
            self.link_status_ui = LinkStatusDashboardUI(self)
            print("DEBUG: Link Status Dashboard initialized")

            # Port Status components - already correctly initialized
            self.port_status_manager = PortStatusManager(self.cli)
            self.port_status_ui = PortStatusDashboardUI(self)
            print("DEBUG: Port Status Dashboard initialized")

            # Resets Dashboard components - already correctly initialized
            self.resets_dashboard = ResetsDashboard(self)
            print("DEBUG: Resets Dashboard initialized")

            # Firmware Dashboard - already correctly initialized
            self.firmware_dashboard = FirmwareDashboard(self)
            print("DEBUG: Firmware Dashboard initialized")

            print("DEBUG: All dashboard components initialized consistently")

        except Exception as e:
            print(f"ERROR: Failed to initialize dashboard components: {e}")
            messagebox.showerror("Initialization Error",
                                 f"Failed to initialize dashboard components: {e}")

    def init_advanced_response_handler(self):
        """Initialize advanced response handler"""
        try:
            if not self.is_demo_mode:
                self.response_handler = AdvancedResponseHandler(self)
                print("DEBUG: Advanced response handler initialized")
            else:
                self.response_handler = None
                print("DEBUG: Skipping advanced response handler for demo mode")
        except Exception as e:
            print(f"WARNING: Could not initialize advanced response handler: {e}")
            self.response_handler = None

    def setup_window(self):
        """Configure the main dashboard window"""
        # Window title
        title = get_window_title(APP_DESCRIPTION, self.is_demo_mode)
        self.root.title(title)

        # Set application icon
        try:
            self.root.iconbitmap("assets/Logo_gal_ico.ico")
        except:
            pass  # Ignore if icon not found

        # Calculate window size (85% of screen)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = int(screen_width * 0.85)
        window_height = int(screen_height * 0.85)

        # Center window
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2

        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(1400, 1000)

        print(f"DEBUG: Dashboard window configured: {window_width}x{window_height}")

        # Try to maximize for large displays
        try:
            self.root.state('zoomed')
            print("DEBUG: Dashboard window maximized")
        except:
            print("DEBUG: Window maximize not supported on this platform")

    def create_layout(self):
        """Create layout with centered content area"""
        print("DEBUG: Creating layout with centered content")

        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True)

        # Sidebar (fixed width on left)
        self.sidebar = ttk.Frame(main_frame, style='Sidebar.TFrame', width=200)
        self.sidebar.pack(side='left', fill='y', padx=(0, 1))
        self.sidebar.pack_propagate(False)

        # Content area container (takes remaining space)
        content_container = ttk.Frame(main_frame, style='Content.TFrame')
        content_container.pack(side='left', fill='both', expand=True)

        # CENTERING MAGIC: Create the actual content frame inside the container
        # This will be centered with percentage-based margins
        self.content_frame = ttk.Frame(content_container, style='Content.TFrame')

        # Center the content frame with percentage-based padding
        # Adjust these percentages to control centering (10% margin = 80% content width)
        self.content_frame.place(relx=0.35, rely=0.05, relwidth=0.8, relheight=0.9)

        print("DEBUG: Content frame centered with place geometry manager")

        # Initialize content
        self.create_sidebar()
        self.create_content_area()

    def create_sidebar(self):
        """Create the sidebar with dashboard tiles - FIXED VERSION"""
        print("DEBUG: Starting sidebar creation...")

        # Header - simplified without settings gear
        header_frame = ttk.Frame(self.sidebar, style='Sidebar.TFrame')
        header_frame.pack(fill='x', padx=10, pady=10)

        ttk.Label(header_frame, text="📊 Dashboards",
                  background='#2d2d2d', foreground='#ffffff',
                  font=('Arial', 12, 'bold')).pack()

        # Dashboard tiles
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

        # CRITICAL FIX: Initialize tile_frames dictionary BEFORE creating tiles
        self.tile_frames = {}
        print("DEBUG: tile_frames dictionary initialized")

        # Create all tiles first (without setting active state)
        for dashboard_id, icon, title in self.dashboards:
            print(f"DEBUG: Creating tile for {dashboard_id}")
            self.create_dashboard_tile(dashboard_id, icon, title)

        # CRITICAL FIX: Set the active tile AFTER all tiles are created
        print("DEBUG: All tiles created, setting active state...")
        if hasattr(self, 'current_dashboard') and self.current_dashboard in self.tile_frames:
            try:
                self.set_tile_active(self.current_dashboard, True)
                print(f"DEBUG: Set {self.current_dashboard} as active")
            except Exception as e:
                print(f"ERROR: Failed to set active tile: {e}")
        else:
            # Default to host if not set
            if 'host' in self.tile_frames:
                try:
                    self.current_dashboard = 'host'
                    self.set_tile_active('host', True)
                    print("DEBUG: Set host as default active tile")
                except Exception as e:
                    print(f"ERROR: Failed to set default active tile: {e}")

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

        print("DEBUG: Sidebar creation completed successfully")

    def create_content_area(self):
        """Create the main content display area - FIXED to work with pack layout"""
        print("DEBUG: Creating content area with pack-compatible layout")

        try:
            # Header frame at the top
            header_frame = ttk.Frame(self.content_frame, style='Content.TFrame')
            header_frame.pack(fill='x', padx=20, pady=20)
            print("DEBUG: Header frame created and packed")

            # Left side of header: title
            self.content_title = ttk.Label(header_frame, text="Host Card Information",
                                           style='Dashboard.TLabel')
            self.content_title.pack(side='left')
            print("DEBUG: Content title created")

            # Right side of header: buttons
            button_group = ttk.Frame(header_frame, style='Content.TFrame')
            button_group.pack(side='right')

            # Cache status indicator
            self.cache_status_label = ttk.Label(header_frame, text="",
                                                style='Info.TLabel', font=('Arial', 8))
            self.cache_status_label.pack(side='right', padx=(20, 10))

            # Settings button
            self.settings_btn = ttk.Button(button_group, text="⚙️", width=3,
                                           command=self.open_settings)
            self.settings_btn.pack(side='right', padx=(5, 0))

            # Refresh button
            self.refresh_btn = ttk.Button(button_group, text="🔄", width=3,
                                          command=self.refresh_current_dashboard)
            self.refresh_btn.pack(side='right')
            print("DEBUG: Header buttons created")

            # Main content area with scrolling (takes remaining vertical space)
            content_container = ttk.Frame(self.content_frame, style='Content.TFrame')
            content_container.pack(fill='both', expand=True, padx=20, pady=(0, 20))
            print("DEBUG: Content container created")

            # Canvas and scrollbar for scrolling content
            canvas = tk.Canvas(content_container, bg='#1e1e1e', highlightthickness=0)
            scrollbar = ttk.Scrollbar(content_container, orient='vertical', command=canvas.yview)

            # Create the scrollable frame
            self.scrollable_frame = ttk.Frame(canvas, style='Content.TFrame')

            # Configure scrolling
            self.scrollable_frame.bind('<Configure>',
                                       lambda e: canvas.configure(scrollregion=canvas.bbox('all')))

            canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw')
            canvas.configure(yscrollcommand=scrollbar.set)

            # Pack canvas and scrollbar
            canvas.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')
            print("DEBUG: Canvas and scrollbar created and packed")

            # Store canvas reference
            self.content_canvas = canvas

            # Load the initial dashboard content
            self.update_content_area()
            print("DEBUG: Content area creation completed successfully")

        except Exception as e:
            print(f"ERROR: Exception in create_content_area: {e}")
            import traceback
            traceback.print_exc()

    def _create_scrollable_content(self):
        """Create scrollable content area"""
        # Canvas and scrollbar for scrollable content
        canvas = tk.Canvas(self.content_frame, bg='#1e1e1e', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.content_frame, orient='vertical', command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas, style='Content.TFrame')

        # Configure scrolling
        self.scrollable_frame.bind('<Configure>',
                                   lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack canvas and scrollbar
        canvas.pack(side='left', fill='both', expand=True, padx=20, pady=(0, 20))
        scrollbar.pack(side='right', fill='y', pady=(0, 20))

        self.content_canvas = canvas

    def connect_device(self):
        """Connect to the device and load initial data"""
        try:
            if self.cli.connect():
                print("DEBUG: CLI connected successfully")

                if self.is_demo_mode:
                    # Load demo data immediately
                    self.load_demo_data_directly()
                else:
                    # Start background communication for real devices
                    self.cli.start_background()

                return True
            else:
                print("ERROR: CLI connection failed")
                return False

        except Exception as e:
            print(f"ERROR: Device connection failed: {e}")
            return False

    def load_demo_data_directly(self):
        """Load demo data directly for immediate UI update"""
        try:
            if hasattr(self.cli, 'demo_sysinfo_content') and self.cli.demo_sysinfo_content:
                demo_content = self.cli.demo_sysinfo_content
                print(f"DEBUG: Loading demo sysinfo content ({len(demo_content)} chars)")

                # Parse demo data
                parsed_data = self.sysinfo_parser.parse_unified_sysinfo(demo_content, "demo")
                print("DEBUG: Demo data parsed successfully")

                # Update UI
                self.root.after_idle(self.update_content_area)
                self.update_cache_status("Demo data loaded")

                # Log success
                timestamp = datetime.now().strftime('%H:%M:%S')
                self.log_data.append(f"[{timestamp}] Demo data loaded successfully")
            else:
                print("DEBUG: No demo content available")
                self.show_loading_message("Demo data not available")

        except Exception as e:
            print(f"ERROR: Failed to load demo data: {e}")
            self.show_loading_message(f"Demo error: {e}")

    # =====================================================================
    # DASHBOARD MANAGEMENT - CLEANED UP WITH LINK STATUS REMOVED
    # =====================================================================

    def switch_dashboard(self, dashboard_id):
        """Switch to a different dashboard - SAFE VERSION"""
        if dashboard_id == getattr(self, 'current_dashboard', None):
            return

        print(f"DEBUG: Switching to {dashboard_id} dashboard")

        # Update tile appearances safely
        if hasattr(self, 'current_dashboard') and hasattr(self, 'tile_frames'):
            self.set_tile_active(self.current_dashboard, False)
            self.set_tile_active(dashboard_id, True)

        self.current_dashboard = dashboard_id

        # Send appropriate command when switching to specific dashboards
        if dashboard_id == "link":
            print("DEBUG: Switching to link dashboard - will send showport command")
        elif dashboard_id == "host":
            # Warm cache if needed before updating content
            try:
                cache_warmed = self.warm_cache_if_needed()
                if cache_warmed:
                    self.update_cache_status("Loading fresh data...")
            except:
                pass  # Ignore cache warming errors

        # Update content area
        try:
            self.update_content_area()
        except Exception as e:
            print(f"ERROR: Failed to update content area: {e}")

    def update_content_area(self):
        """Update content area based on current dashboard"""
        # Clear existing content
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Update dashboard title
        dashboard_titles = {
            "host": "💻 Host Card Information",
            "link": "🔗 Link Status",
            "port": "🔌 Port Configuration",
            "compliance": "✅ Compliance",
            "registers": "📋 Registers",
            "advanced": "⚙️ Advanced",
            "resets": "🔄 Resets",
            "firmware": "📦 Firmware Updates",
            "help": "❓ Help"
        }

        self.content_title.config(text=dashboard_titles.get(self.current_dashboard, "Dashboard"))

        # Update cache status
        self.update_cache_status()

        # Create dashboard-specific content
        try:
            if self.current_dashboard == "host":
                self.create_host_dashboard()
            elif self.current_dashboard == "link":
                self.create_link_dashboard()  # CLEANED: Simple delegation
            elif self.current_dashboard == "port":
                self.create_port_dashboard()
            elif self.current_dashboard == "resets":
                self.create_resets_dashboard()
            elif self.current_dashboard == "firmware":
                self.create_firmware_dashboard()
            else:
                # Placeholder for other dashboards
                self.create_placeholder_dashboard()

        except Exception as e:
            print(f"ERROR: Failed to create {self.current_dashboard} dashboard: {e}")
            self.show_dashboard_error(self.current_dashboard, e)

    def create_dashboard_tile(self, dashboard_id, icon, title):
        """Create an individual dashboard tile - FIXED VERSION"""
        print(f"DEBUG: create_dashboard_tile called for {dashboard_id}")

        # CRITICAL FIX: Don't try to set active state during tile creation
        # This prevents the "sidebar not initialized" error

        try:
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

            print(f"DEBUG: Successfully created tile for {dashboard_id}")

            # REMOVED THE PROBLEMATIC LINE:
            # if dashboard_id == self.current_dashboard:
            #     self.set_tile_active(dashboard_id, True)

        except Exception as e:
            print(f"ERROR: Exception creating tile for {dashboard_id}: {e}")
            import traceback
            traceback.print_exc()

    def set_tile_active(self, dashboard_id, active):
        """Set tile active/inactive appearance - FIXED VERSION"""
        print(f"DEBUG: set_tile_active called for {dashboard_id}, active={active}")

        # CRITICAL FIX: Add comprehensive safety checks
        if not hasattr(self, 'tile_frames'):
            print(f"ERROR: tile_frames not initialized")
            return

        if not self.tile_frames:
            print(f"ERROR: tile_frames is empty")
            return

        if dashboard_id not in self.tile_frames:
            print(f"ERROR: {dashboard_id} not found in tile_frames")
            print(f"DEBUG: Available tiles: {list(self.tile_frames.keys())}")
            return

        try:
            tile = self.tile_frames[dashboard_id]
            style_prefix = 'ActiveTile' if active else 'Tile'

            # Update frame styles
            for widget_name in ['frame', 'content']:
                if widget_name in tile and tile[widget_name]:
                    tile[widget_name].configure(style=f'{style_prefix}.TFrame')

            # Update label styles
            for widget_name in ['icon', 'title']:
                if widget_name in tile and tile[widget_name]:
                    tile[widget_name].configure(style=f'{style_prefix}.TLabel')

            print(f"DEBUG: Successfully set {dashboard_id} active={active}")

        except Exception as e:
            print(f"ERROR: Failed to set tile active for {dashboard_id}: {e}")
            import traceback
            traceback.print_exc()

    def create_host_dashboard(self):
        """FIXED: Create host card information dashboard"""
        print("DEBUG: create_host_dashboard called")

        # Verify host_card_ui exists
        if not hasattr(self, 'host_card_ui'):
            print("ERROR: host_card_ui not initialized")
            self.show_loading_message("Host dashboard not properly initialized")
            return

        try:
            # Call the host card UI to create the dashboard
            self.host_card_ui.create_host_dashboard()
            print("DEBUG: Host dashboard created successfully")

        except Exception as e:
            print(f"ERROR: Failed to create host dashboard: {e}")
            import traceback
            traceback.print_exc()

            # Show error message in the dashboard
            error_frame = ttk.Frame(self.scrollable_frame, style='Content.TFrame')
            error_frame.pack(fill='both', expand=True, padx=20, pady=20)

            ttk.Label(error_frame,
                      text="❌ Error Loading Host Dashboard",
                      style='Dashboard.TLabel',
                      font=('Arial', 16, 'bold')).pack(pady=(0, 10))

            ttk.Label(error_frame,
                      text=f"Error: {str(e)}",
                      style='Info.TLabel',
                      font=('Arial', 10)).pack()

    def create_link_dashboard(self):
        """Create link status dashboard - FULLY DELEGATED to dashboard module"""
        try:
            # Dashboard is pre-initialized, just call its create method
            if hasattr(self.link_status_ui, 'create_dashboard'):
                self.link_status_ui.create_dashboard()
            elif hasattr(self.link_status_ui, 'create_link_dashboard'):
                self.link_status_ui.create_link_dashboard()
            else:
                print("WARNING: Link dashboard create method not found")
        except Exception as e:
            print(f"ERROR: Error creating link dashboard: {e}")
            raise

    def create_port_dashboard(self):
        """Create port configuration dashboard - delegate to dashboard module"""
        try:
            if hasattr(self.port_status_ui, 'create_port_dashboard'):
                self.port_status_ui.create_port_dashboard()
            else:
                print("WARNING: Port dashboard create method not found")
        except Exception as e:
            print(f"ERROR: Error creating port dashboard: {e}")
            raise

    def create_resets_dashboard(self):
        """Create resets dashboard - delegate to dashboard module"""
        try:
            self.resets_dashboard.create_resets_dashboard(self.scrollable_frame)
        except Exception as e:
            print(f"ERROR: Error creating resets dashboard: {e}")
            raise

    def create_firmware_dashboard(self):
        """Create firmware dashboard - delegate to dashboard module"""
        try:
            self.firmware_dashboard.create_firmware_dashboard()
        except Exception as e:
            print(f"ERROR: Error creating firmware dashboard: {e}")
            raise

    def create_placeholder_dashboard(self):
        """Create placeholder for unimplemented dashboards"""
        placeholder_frame = ttk.Frame(self.scrollable_frame, style='Content.TFrame')
        placeholder_frame.pack(fill='both', expand=True, padx=20, pady=20)

        ttk.Label(placeholder_frame,
                  text=f"{self.current_dashboard.title()} Dashboard",
                  style='Dashboard.TLabel',
                  font=('Arial', 16, 'bold')).pack(pady=(0, 10))

        ttk.Label(placeholder_frame,
                  text="⚠️ Coming Soon",
                  style='Info.TLabel',
                  font=('Arial', 12)).pack()

    def show_dashboard_error(self, dashboard_name, error):
        """Show dashboard error in the UI"""
        error_frame = ttk.Frame(self.scrollable_frame, style='Content.TFrame')
        error_frame.pack(fill='both', expand=True, padx=20, pady=20)

        ttk.Label(error_frame,
                  text=f"❌ Error Loading {dashboard_name.title()} Dashboard",
                  style='Dashboard.TLabel',
                  font=('Arial', 16, 'bold')).pack(pady=(0, 10))

        ttk.Label(error_frame,
                  text=f"Error: {str(error)}",
                  style='Info.TLabel',
                  font=('Arial', 10)).pack()

    # =====================================================================
    # BACKGROUND OPERATIONS AND MONITORING
    # =====================================================================

    def start_background_threads(self):
        """Start background monitoring threads"""
        try:
            # Start log monitoring thread
            self.log_monitor_thread = threading.Thread(target=self.monitor_logs, daemon=True)
            self.log_monitor_thread.start()
            print("DEBUG: Background monitoring started")
        except Exception as e:
            print(f"ERROR: Failed to start background threads: {e}")

    def monitor_logs(self):
        """Monitor logs from CLI with proper attribute checking"""
        print("DEBUG: Log monitoring thread started")

        try:
            while getattr(self, 'background_tasks_enabled', False) and self.cli and self.cli.is_running:
                try:
                    if hasattr(self.cli, 'log_queue'):
                        log_message = self.cli.log_queue.get(timeout=1.0)
                        if log_message and hasattr(self, 'log_data'):
                            self.log_data.append(log_message)

                            # Keep log size manageable
                            if len(self.log_data) > 1000:
                                self.log_data = self.log_data[-500:]

                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"ERROR: Log monitoring error: {e}")
                    break

        except Exception as e:
            print(f"ERROR: Log monitoring thread failed: {e}")
        finally:
            print("DEBUG: Log monitoring thread ended")

    def _process_log_entry(self, log_entry):
        """Process incoming log entries and delegate to dashboards"""
        try:
            # Extract response content
            if "DEMO RECV:" in log_entry:
                response = log_entry.replace("DEMO RECV:", "").strip()
                is_demo = True
            elif "RECV:" in log_entry:
                response = log_entry.replace("RECV:", "").strip()
                is_demo = False
            else:
                return

            # Handle showport responses - DELEGATE to Link Status Dashboard
            if "showport" in log_entry.lower() and len(response) > 50:
                if hasattr(self.link_status_ui, 'handle_showport_response'):
                    success = self.link_status_ui.handle_showport_response(response)
                    if success:
                        print("DEBUG: Showport response processed by Link Status Dashboard")

            # Handle sysinfo responses
            elif "sysinfo" in log_entry.lower() and len(response) > 200:
                self._handle_sysinfo_response(response, is_demo)

            # Handle showmode responses
            elif "showmode" in log_entry.lower() and "mode" in response.lower():
                self._handle_showmode_response(response)

        except Exception as e:
            print(f"ERROR: Error processing log entry: {e}")

    def _handle_sysinfo_response(self, response, is_demo):
        """Handle sysinfo responses"""
        try:
            if len(response) > 200 and ("S/N" in response or "Thermal:" in response):
                print(f"DEBUG: Processing sysinfo response ({len(response)} chars)")

                # Parse using enhanced parser
                mode = "demo" if is_demo else "device"
                parsed_data = self.sysinfo_parser.parse_unified_sysinfo(response, mode)

                print(f"DEBUG: Sysinfo parsed with sections: {list(parsed_data.keys())}")

                # Update UI if on host dashboard
                if self.current_dashboard == "host":
                    self.root.after_idle(self.update_content_area)

                self.update_cache_status("Fresh data loaded")

        except Exception as e:
            print(f"ERROR: Error handling sysinfo response: {e}")

    def _handle_showmode_response(self, response):
        """Handle showmode responses"""
        try:
            if "mode" in response.lower() and any(char.isdigit() for char in response):
                print("DEBUG: Processing showmode response")

                # Update UI if on port dashboard
                if self.current_dashboard == "port":
                    self.root.after_idle(self.update_content_area)

        except Exception as e:
            print(f"ERROR: Error handling showmode response: {e}")

    # =====================================================================
    # UTILITY METHODS AND UI HELPERS
    # =====================================================================

    def refresh_current_dashboard(self):
        """Refresh the current dashboard"""
        dashboard_name = self.current_dashboard

        try:
            if dashboard_name == "host":
                # Check if we need fresh data
                if self.sysinfo_parser.force_refresh_needed():
                    self.sysinfo_parser.invalidate_all_data()
                    self.send_sysinfo_command()
                    self.update_cache_status("Requesting fresh data...")
                else:
                    self.update_content_area()
                    self.update_cache_status("Using cached data")

            elif dashboard_name == "link":
                # DELEGATE to Link Status Dashboard
                if hasattr(self.link_status_ui, 'refresh_link_status'):
                    self.link_status_ui.refresh_link_status()
                else:
                    self.update_content_area()

            elif dashboard_name == "port":
                # Port dashboard refresh
                if hasattr(self.port_status_manager, 'get_port_status_info'):
                    self.port_status_manager.get_port_status_info(force_refresh=True)
                self.update_content_area()
                self.update_cache_status("Port status refreshed")

            else:
                # Generic refresh for other dashboards
                self.update_content_area()

            # Log the refresh
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.log_data.append(f"[{timestamp}] Refreshed {dashboard_name} dashboard")

        except Exception as e:
            print(f"ERROR: Error refreshing {dashboard_name} dashboard: {e}")

    def update_cache_status(self, message=""):
        """Update cache status display"""
        if not message and self.cache_manager:
            try:
                stats = self.cache_manager.get_stats()
                is_fresh = self.sysinfo_parser.is_data_fresh(300)
                freshness = "Fresh" if is_fresh else "Stale"
                message = f"Cache: {stats['valid_entries']} entries ({freshness})"
            except:
                message = "Cache: Available"

        self.cache_status_label.config(text=message)

        # Clear temporary messages after 3 seconds
        if any(word in message for word in ["Cleared", "Requesting", "Fresh data loaded"]):
            self.root.after(3000, lambda: self.update_cache_status())

    def warm_cache_if_needed(self):
        """Warm cache if data is stale or missing"""
        if self.sysinfo_parser.force_refresh_needed():
            self.send_sysinfo_command()
            return True
        return False

    def send_sysinfo_command(self):
        """Send sysinfo command for fresh data"""
        if self.cli and self.cli.is_running and not self.sysinfo_requested:
            self.sysinfo_requested = True
            self.cli.send_command("sysinfo")
            print("DEBUG: sysinfo command sent")

    def show_loading_message(self, message):
        """Show loading message in content area"""
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
            self.load_demo_data_directly()
        except Exception as e:
            print(f"ERROR: Demo retry failed: {e}")
            self.show_loading_message(f"Demo retry failed: {e}")

    def open_settings(self):
        """Open settings dialog with error handling"""
        try:
            from Admin import settings_ui
            dialog = settings_ui.SettingsDialog(
                self.root,
                self.settings_mgr,
                on_settings_changed=self.on_settings_changed
            )
        except tk.TclError as e:
            if "geometry manager" in str(e).lower():
                print(f"Geometry manager error caught: {e}")
                messagebox.showinfo("Settings",
                                    "Settings dialog layout error. Please try again.\n\n"
                                    "If this persists, restart the application.")
            else:
                raise
        except Exception as e:
            print(f"Settings dialog error: {e}")
            messagebox.showinfo("Settings", "Settings dialog temporarily unavailable")

    def start_auto_refresh(self):
        """Start automatic refresh if enabled"""
        if self.auto_refresh_enabled and not self.is_demo_mode:
            interval = self.auto_refresh_interval * 1000  # Convert to milliseconds
            self.auto_refresh_timer = self.root.after(interval, self._auto_refresh_callback)
            print(f"DEBUG: Auto-refresh started ({self.auto_refresh_interval}s interval)")

    def _auto_refresh_callback(self):
        """Auto-refresh callback"""
        try:
            if self.auto_refresh_enabled and self.current_dashboard == "host":
                # Only auto-refresh host dashboard to avoid excessive commands
                if self.sysinfo_parser.force_refresh_needed():
                    self.send_sysinfo_command()

            # Schedule next refresh
            if self.auto_refresh_enabled:
                interval = self.auto_refresh_interval * 1000
                self.auto_refresh_timer = self.root.after(interval, self._auto_refresh_callback)

        except Exception as e:
            print(f"WARNING: Auto-refresh error: {e}")

    def stop_auto_refresh(self):
        """Stop automatic refresh"""
        if self.auto_refresh_timer:
            try:
                self.root.after_cancel(self.auto_refresh_timer)
                self.auto_refresh_timer = None
                print("DEBUG: Auto-refresh stopped")
            except Exception as e:
                print(f"WARNING: Error stopping auto-refresh: {e}")

    def on_closing(self):
        """Handle application closing"""
        print("DEBUG: Dashboard closing...")

        try:
            # Stop background tasks
            self.background_tasks_enabled = False
            self.stop_auto_refresh()

            # Save window position if enabled
            if self.settings_mgr.get('ui', 'remember_window_position', True):
                try:
                    self.settings_mgr.set('ui', 'last_window_x', self.root.winfo_x())
                    self.settings_mgr.set('ui', 'last_window_y', self.root.winfo_y())
                    self.settings_mgr.save()
                except Exception as e:
                    print(f"WARNING: Error saving window position: {e}")

            # Disconnect from device
            if hasattr(self, 'cli') and self.cli and self.cli.is_running:
                self.cli.disconnect()
                print("DEBUG: CLI disconnected")

            # Destroy the window
            self.root.destroy()
            print("DEBUG: Dashboard closed successfully")

        except Exception as e:
            print(f"ERROR: Error during dashboard close: {e}")
            # Force close anyway
            try:
                self.root.destroy()
            except:
                pass


def configure_styles():
    """Configure modern ttk styles for the application"""
    style = ttk.Style()

    # Use modern theme
    try:
        style.theme_use('clam')
    except:
        pass  # Use default if clam not available

    # Configure custom styles for dark theme
    style.configure('Dashboard.TLabel',
                    background='#1e1e1e',
                    foreground='#ffffff',
                    font=('Arial', 14, 'bold'))

    style.configure('Info.TLabel',
                    background='#1e1e1e',
                    foreground='#cccccc',
                    font=('Arial', 10))

    style.configure('Sidebar.TFrame',
                    background='#2d2d2d')

    style.configure('Content.TFrame',
                    background='#1e1e1e')

    style.configure('SidebarTitle.TLabel',
                    font=('Arial', 12, 'bold'),
                    background='#2d2d2d',
                    foreground='white')

    style.configure('Sidebar.TButton',
                    background='#3d3d3d',
                    foreground='white',
                    font=('Arial', 9),
                    padding=(5, 5))


def main():
    """
    Main application entry point with proper error handling and cleanup

    This function:
    1. Initializes the application environment
    2. Sets up platform-specific optimizations
    3. Creates and runs the connection window
    4. Handles application-level errors gracefully
    """
    try:
        print(f"DEBUG: Starting {APP_NAME} v{APP_VERSION}")

        # Platform-specific optimizations
        if sys.platform.startswith('win'):
            try:
                # Windows DPI awareness for high-resolution displays
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
                print("DEBUG: Windows DPI awareness enabled")
            except Exception as e:
                print(f"DEBUG: Could not set DPI awareness: {e}")

        # Initialize settings manager
        try:
            settings_mgr = SettingsManager()
            print("DEBUG: Settings manager initialized")
        except Exception as e:
            print(f"ERROR: Failed to initialize settings manager: {e}")
            # Continue with None - connection window will handle gracefully
            settings_mgr = None

        # Create main application window
        root = tk.Tk()

        # Configure application-wide styles
        configure_styles()

        # Set window properties
        root.withdraw()  # Hide initially while setting up

        # Configure window icon if available
        try:
            root.iconbitmap("assets/Logo_gal_ico.ico")
        except:
            pass  # Ignore if icon not found

        # Create and show connection window
        try:
            connection_app = ConnectionWindow(root, settings_mgr)
            root.deiconify()  # Show window after setup
            print("DEBUG: Connection window created")
        except Exception as e:
            print(f"ERROR: Failed to create connection window: {e}")
            messagebox.showerror("Startup Error",
                                 f"Failed to create connection window:\n\n{e}")
            root.destroy()
            return

        # Configure global error handling
        def handle_tk_error(exc, val, tb):
            """Handle tkinter errors gracefully"""
            error_msg = f"GUI Error: {val}"
            print(f"ERROR: {error_msg}")
            try:
                messagebox.showerror("Application Error", error_msg)
            except:
                pass  # If we can't show messagebox, just log

        root.report_callback_exception = handle_tk_error

        # Configure application closing
        def on_app_close():
            """Handle application close event"""
            try:
                # Save settings before closing
                if settings_mgr:
                    settings_mgr.save()
                    print("DEBUG: Settings saved")

                # Stop any auto-refresh timers
                if hasattr(connection_app, 'stop_auto_refresh'):
                    connection_app.stop_auto_refresh()

                # Destroy the window
                root.quit()
                root.destroy()
                print("DEBUG: Application closed successfully")

            except Exception as e:
                print(f"ERROR: Error during application close: {e}")
                # Force close
                try:
                    root.quit()
                    root.destroy()
                except:
                    pass

        root.protocol("WM_DELETE_WINDOW", on_app_close)

        # Start the main application loop
        print("DEBUG: Starting main application loop")
        root.mainloop()

        print("DEBUG: Application shutdown complete")

    except KeyboardInterrupt:
        print("DEBUG: Application interrupted by user")

    except Exception as e:
        error_msg = f"Fatal application error: {e}"
        print(f"FATAL ERROR: {error_msg}")

        # Try to show error dialog
        try:
            import traceback
            traceback.print_exc()

            # Create emergency error window
            error_root = tk.Tk()
            error_root.withdraw()
            messagebox.showerror("Fatal Error",
                                 f"{APP_NAME} encountered a fatal error:\n\n{error_msg}\n\n"
                                 "Please check the console output for more details.")
            error_root.destroy()
        except:
            # If GUI fails, just print to console
            print("ERROR: Could not display error dialog")

        # Exit with error code
        sys.exit(1)

    finally:
        # Final cleanup
        try:
            # Ensure all windows are closed
            #import tkinter as tk
            for widget in tk._default_root.children.values() if tk._default_root else []:
                try:
                    widget.destroy()
                except:
                    pass
        except:
            pass


if __name__ == "__main__":
    main()