#!/usr/bin/env python3
"""
CalypsoPy by Serial Cables
A modern GUI application for serial communication with the Broadcom Atlas 3 switch

Developed by:
Joshua Mutschler, Serial Cables

Dependencies:
pySerial
"""

# Application Information
APP_NAME = "CalypsoPy"
APP_VERSION = "Beta 1.0.0"
APP_BUILD = "20250808-001"  # Update this with each build
APP_DESCRIPTION = "Atlas 3 Serial Interface"
APP_AUTHOR = "Serial Cables, LLC"
APP_COPYRIGHT = "© 2025"

# Version History
VERSION_HISTORY = {
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
from datetime import datetime
import json
from demo_mode_integration import DemoSerialCLI
from host_card_info import HostCardInfoManager, HostCardDashboardUI




def get_window_title(subtitle="", demo_mode=False):
    """Generate window title with proper branding"""
    base_title = f"{APP_NAME} {APP_VERSION}"

    if subtitle:
        base_title += f" - {subtitle}"

    if demo_mode:
        base_title += " 🎭 [DEMO MODE]"

    return base_title


class SerialCLI:
    """Background CLI handler for serial communication"""

    def __init__(self, port, baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None
        self.is_running = False
        self.command_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.log_queue = queue.Queue()

    def connect(self):
        """Establish serial connection"""
        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=115200,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
                timeout=1
            )
            self.is_running = True
            return True
        except Exception as e:
            self.log_queue.put(f"Connection error: {str(e)}")
            return False

    def disconnect(self):
        """Close serial connection"""
        self.is_running = False
        if self.serial_connection:
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

    def __init__(self, root):
        self.root = root
        self.demo_var = tk.BooleanVar()
        self.setup_window()
        self.create_widgets()
        self.refresh_ports()

    def create_demo_option(self, main_frame):
        """Add demo mode option to connection window - ADD THIS METHOD"""
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
        """Handle demo mode checkbox toggle - ADD THIS METHOD"""
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

        # Set icon if you have one (optional)
        try:
            self.root.iconbitmap("assets/Logo_gal_ico.ico")  # Windows
            # self.root.iconphoto(True, tk.PhotoImage(file="assets/calypsopy_icon.png"))  # Cross-platform
            pass
        except:
            pass

            # *** Calculate proper window size based on content ***
        base_width = 600  # Increased from 400
        base_height = 600  # Increased from 300 to accommodate demo mode content

        # Get screen dimensions for centering
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Center the window
        x = (screen_width - base_width) // 2
        y = (screen_height - base_height) // 2

        self.root.geometry(f"{base_width}x{base_height}+{x}+{y}")
        self.root.minsize(480, 420)  # Prevent window from being too small
        self.root.configure(bg='#1e1e1e')

        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Modern.TFrame', background='#1e1e1e')
        style.configure('Modern.TLabel', background='#1e1e1e', foreground='#ffffff', font=('Arial', 12))
        style.configure('Modern.TCombobox', font=('Arial', 11))
        style.configure('Connect.TButton', font=('Arial', 12, 'bold'))

    def create_widgets(self):
        """Create and layout the connection widgets"""
        main_frame = ttk.Frame(self.root, style='Modern.TFrame', padding=40)
        main_frame.pack(fill='both', expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="🔌 Device Connection",
                                style='Modern.TLabel', font=('Arial', 18, 'bold'))
        title_label.pack(pady=(0, 30))

        # COM Port selection
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

        self.create_demo_option(main_frame)

        # Connect button
        connect_btn = ttk.Button(main_frame, text="Connect to Device",
                                 style='Connect.TButton', command=self.connect)
        connect_btn.pack(pady=30)

        # Status label
        self.status_label = ttk.Label(main_frame, text="Select a COM port to continue",
                                      style='Modern.TLabel')
        self.status_label.pack(pady=10)

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

        # Check if demo mode is enabled
        if self.demo_var.get():
            self.status_label.config(text="Starting demo mode...")
            self.root.update()
            # Start demo mode after short delay
            self.root.after(1000, lambda: self.open_dashboard("DEMO"))
            return

        # Original connection logic for real hardware
        selected_port = self.port_var.get()
        if not selected_port:
            messagebox.showerror("Error", "Please select a COM port")
            return

        self.status_label.config(text="Connecting...")
        self.root.update()

        # Test connection
        cli = SerialCLI(selected_port)
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
        """Open the main dashboard window"""
        self.root.destroy()
        dashboard_root = tk.Tk()
        DashboardApp(dashboard_root, port)
        dashboard_root.mainloop()


class DashboardApp:
    """Main dashboard app with simple host card integration"""

    def __init__(self, root, port):
        self.root = root
        self.port = port

        # Existing demo mode detection
        self.is_demo_mode = (port == "DEMO")

        # Use appropriate CLI class based on mode
        if self.is_demo_mode:
            self.cli = DemoSerialCLI(port)
        else:
            self.cli = SerialCLI(port)

        # *** NEW: Initialize Host Card Info components ***
        self.host_card_manager = HostCardInfoManager(self.cli)
        self.host_card_ui = HostCardDashboardUI(self)

        self.log_data = []
        self.current_dashboard = "host"

        self.setup_window()
        self.create_layout()
        self.connect_device()
        self.start_background_threads()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_window(self):
        """Configure the main dashboard window"""
        # Update title to show demo mode
        title = get_window_title(APP_DESCRIPTION, self.is_demo_mode)
        self.root.title(title)

        # Set icon if available
        try:
            # Uncomment and modify if you have an icon
            self.root.iconbitmap("assets/Logo_gal_ico.ico")
            pass
        except:
            pass


        # Calculate window size (60% of screen)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = int(screen_width * 0.6)
        window_height = int(screen_height * 0.6)

        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2

        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.configure(bg='#1e1e1e')
        self.root.minsize(800, 600)

        # Configure styles
        self.setup_styles()

    def setup_styles(self):
        """Configure modern UI styles"""
        style = ttk.Style()
        style.theme_use('clam')

        # Main styles
        style.configure('Sidebar.TFrame', background='#2d2d2d')
        style.configure('Content.TFrame', background='#1e1e1e')
        style.configure('Dashboard.TLabel', background='#1e1e1e', foreground='#ffffff',
                        font=('Arial', 14, 'bold'))
        style.configure('Info.TLabel', background='#1e1e1e', foreground='#cccccc',
                        font=('Arial', 10))

        # Dashboard tile styles
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
        # Header
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

        # *** NEW: ADD DEMO MODE INFO ***
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
        """Switch to a different dashboard"""
        if dashboard_id == self.current_dashboard:
            return

        # Update tile appearances
        self.set_tile_active(self.current_dashboard, False)
        self.set_tile_active(dashboard_id, True)

        self.current_dashboard = dashboard_id
        self.update_content_area()

    def create_content_area(self):
        """Create the main content display area"""
        # Header
        header_frame = ttk.Frame(self.content_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=20, pady=20)

        self.content_title = ttk.Label(header_frame, text="Host Card Information",
                                       style='Dashboard.TLabel')
        self.content_title.pack(anchor='w')

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
            "resets": "🔄 Resets",
            "firmware": "📦 Firmware Updates",
            "help": "❓ Help"
        }

        self.content_title.config(text=dashboard_titles[self.current_dashboard])

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

    def create_host_dashboard(self):
        """Create host card information dashboard - SIMPLIFIED VERSION"""
        # Simply delegate to the UI component
        self.host_card_ui.create_host_dashboard()
        def status_content(frame):
            status_items = [
                ("Connection Status", "✅ Connected", "#00ff00"),
                ("Power Status", "✅ Powered", "#00ff00"),
                ("Temperature Status", "✅ Normal (45°C)", "#00ff00"),
                ("Error Status", "✅ No Errors", "#00ff00")
            ]

            for label, status, color in status_items:
                row_frame = ttk.Frame(frame, style='Content.TFrame')
                row_frame.pack(fill='x', pady=5)
                ttk.Label(row_frame, text=f"{label}:", style='Info.TLabel',
                          font=('Arial', 10, 'bold')).pack(side='left')
                status_label = ttk.Label(row_frame, text=status, style='Info.TLabel')
                status_label.pack(side='right')

        self.create_info_card(self.scrollable_frame, "Status Information", status_content)

    def create_link_dashboard(self):
        """Create link status dashboard"""

        def link_content(frame):
            link_data = [
                ("Link State", "✅ Active"),
                ("Speed", "5.0 Gbps (USB 3.0)"),
                ("Link Training", "✅ Complete"),
                ("Error Rate", "0.00%"),
                ("Packets Transmitted", "1,234,567"),
                ("Packets Received", "1,234,321"),
                ("CRC Errors", "0"),
                ("Timeout Errors", "0")
            ]

            for label, value in link_data:
                row_frame = ttk.Frame(frame, style='Content.TFrame')
                row_frame.pack(fill='x', pady=2)
                ttk.Label(row_frame, text=f"{label}:", style='Info.TLabel',
                          font=('Arial', 10, 'bold')).pack(side='left')
                ttk.Label(row_frame, text=value, style='Info.TLabel').pack(side='right')

        self.create_info_card(self.scrollable_frame, "Link Status", link_content)

        # Add refresh button
        button_frame = ttk.Frame(self.scrollable_frame, style='Content.TFrame')
        button_frame.pack(fill='x', pady=10)
        ttk.Button(button_frame, text="🔄 Refresh Link Status",
                   command=lambda: self.send_command("link_status")).pack()

    def create_port_dashboard(self):
        """Create port configuration dashboard"""

        def port_content(frame):
            # Port configuration options
            configs = [
                ("Port 1", "Enabled", "High Speed"),
                ("Port 2", "Enabled", "Super Speed"),
                ("Port 3", "Disabled", "N/A"),
                ("Port 4", "Enabled", "High Speed")
            ]

            for port, status, speed in configs:
                row_frame = ttk.Frame(frame, style='Content.TFrame')
                row_frame.pack(fill='x', pady=5)

                ttk.Label(row_frame, text=port, style='Info.TLabel',
                          font=('Arial', 10, 'bold')).pack(side='left')
                ttk.Label(row_frame, text=f"{status} ({speed})",
                          style='Info.TLabel').pack(side='right')

        self.create_info_card(self.scrollable_frame, "Port Configuration", port_content)

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

    def create_resets_dashboard(self):
        """Create resets dashboard"""
        reset_frame = ttk.Frame(self.scrollable_frame, style='Content.TFrame')
        reset_frame.pack(fill='x', pady=20)

        ttk.Label(reset_frame, text="⚠️  Device Reset Options", style='Dashboard.TLabel').pack(anchor='w', pady=(0, 20))

        reset_options = [
            ("Soft Reset", "Restart device software", "soft_reset"),
            ("Hard Reset", "Full hardware reset", "hard_reset"),
            ("Factory Reset", "Reset to factory defaults", "factory_reset"),
            ("Link Reset", "Reset communication link", "link_reset")
        ]

        for title, description, command in reset_options:
            option_frame = ttk.Frame(reset_frame, style='Content.TFrame', relief='solid', borderwidth=1)
            option_frame.pack(fill='x', pady=5)

            content_frame = ttk.Frame(option_frame, style='Content.TFrame')
            content_frame.pack(fill='both', expand=True, padx=15, pady=10)

            ttk.Label(content_frame, text=title, style='Dashboard.TLabel',
                      font=('Arial', 11, 'bold')).pack(anchor='w')
            ttk.Label(content_frame, text=description, style='Info.TLabel').pack(anchor='w', pady=(2, 10))

            ttk.Button(content_frame, text=f"Execute {title}",
                       command=lambda c=command: self.confirm_reset(c)).pack(anchor='w')

    def create_firmware_dashboard(self):
        """Create firmware updates dashboard"""

        def firmware_info_content(frame):
            info = [
                ("Current Version", "v2.1.3"),
                ("Release Date", "2024-01-15"),
                ("Build Number", "20240115-001"),
                ("Last Update", "Never"),
                ("Update Available", "❌ Up to date")
            ]

            for label, value in info:
                row_frame = ttk.Frame(frame, style='Content.TFrame')
                row_frame.pack(fill='x', pady=2)
                ttk.Label(row_frame, text=f"{label}:", style='Info.TLabel',
                          font=('Arial', 10, 'bold')).pack(side='left')
                ttk.Label(row_frame, text=value, style='Info.TLabel').pack(side='right')

        self.create_info_card(self.scrollable_frame, "Current Firmware", firmware_info_content)

        # Firmware update section
        update_frame = ttk.Frame(self.scrollable_frame, style='Content.TFrame', relief='solid', borderwidth=1)
        update_frame.pack(fill='x', pady=20)

        header_frame = ttk.Frame(update_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=15, pady=(15, 10))

        ttk.Label(header_frame, text="📦 Firmware Update", style='Dashboard.TLabel').pack(anchor='w')

        content_frame = ttk.Frame(update_frame, style='Content.TFrame')
        content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        ttk.Label(content_frame, text="Select firmware file (.bin):", style='Info.TLabel').pack(anchor='w')

        file_frame = ttk.Frame(content_frame, style='Content.TFrame')
        file_frame.pack(fill='x', pady=(5, 10))

        self.firmware_path = tk.StringVar(value="No file selected")
        ttk.Label(file_frame, textvariable=self.firmware_path, style='Info.TLabel').pack(side='left')
        ttk.Button(file_frame, text="Browse", command=self.browse_firmware).pack(side='right')

        button_frame = ttk.Frame(content_frame, style='Content.TFrame')
        button_frame.pack(fill='x', pady=10)

        ttk.Button(button_frame, text="🔍 Check for Updates",
                   command=self.check_firmware_updates).pack(side='left', padx=(0, 10))
        ttk.Button(button_frame, text="📤 Upload Firmware",
                   command=self.upload_firmware).pack(side='left')

    def create_help_dashboard(self):
        """Create help dashboard"""

        def about_content(frame):
            version_info = get_version_info()
            about_text = f"""{version_info['name']} {version_info['version']}
        Build: {version_info['build']}

        {APP_DESCRIPTION}
        A professional serial communication tool with modern GUI interface

        {version_info['copyright']} {version_info['author']}

        FEATURES:
        • Modern dark theme interface
        • Multi-dashboard layout
        • Real-time device communication
        • Demo mode for training
        • Comprehensive device monitoring
        • Professional logging system"""

            ttk.Label(frame, text=about_text, style='Info.TLabel', justify='left').pack(anchor='w')

        self.create_info_card(self.scrollable_frame, f"ℹ️ About {APP_NAME}", about_content)

        # *** NEW: Version History section ***
        def version_history_content(frame):
            current_version = VERSION_HISTORY.get(APP_VERSION, {})

            if current_version:
                history_text = f"Version {APP_VERSION} - {current_version.get('date', 'Unknown')}\n\n"
                changes = current_version.get('changes', [])

                for i, change in enumerate(changes, 1):
                    history_text += f"{i}. {change}\n"
            else:
                history_text = f"Version {APP_VERSION}\nNo detailed history available."

            ttk.Label(frame, text=history_text, style='Info.TLabel', justify='left').pack(anchor='w')

        self.create_info_card(self.scrollable_frame, "📋 Version History", version_history_content)

        # Quick start guide (existing)
        def quickstart_content(frame):
            guide_text = """1. Ensure device is properly connected to COM port
        2. Use dashboards to monitor device status
        3. Configure ports and settings as needed
        4. Monitor compliance and link status
        5. Use Advanced dashboard for direct commands"""

            ttk.Label(frame, text=guide_text, style='Info.TLabel', justify='left').pack(anchor='w')

        self.create_info_card(self.scrollable_frame, "🚀 Quick Start Guide", quickstart_content)

        # Command reference (existing)
        def commands_content(frame):
            commands = [
                ("help", "Show available commands"),
                ("status", "Get device status"),
                ("version", "Get firmware version"),
                ("sysinfo", "Get system information"),
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

        # Log export section (existing)
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
        """Connect to the serial device"""
        if self.cli.connect():
            if self.is_demo_mode:
                self.connection_label.config(foreground='#ff9500')
                self.log_data.append(f"[{datetime.now().strftime('%H:%M:%S')}] Demo mode started")
            else:
                self.connection_label.config(foreground='#00ff00')
                self.log_data.append(f"[{datetime.now().strftime('%H:%M:%S')}] Connected to {self.port}")
        else:
            self.connection_label.config(foreground='#ff0000')
            error_msg = "Failed to start demo mode" if self.is_demo_mode else f"Failed to connect to {self.port}"
            messagebox.showerror("Connection Error", error_msg)

    def start_background_threads(self):
        """Start background threads for CLI and logging"""
        if self.cli.is_running:
            # Start CLI background thread
            cli_thread = threading.Thread(target=self.cli.run_background, daemon=True)
            cli_thread.start()

            # Start log monitoring thread
            log_thread = threading.Thread(target=self.monitor_logs, daemon=True)
            log_thread.start()

    def monitor_logs(self):
        """Monitor log queue and update log data"""
        while self.cli.is_running:
            try:
                log_entry = self.cli.log_queue.get_nowait()
                timestamp = datetime.now().strftime('%H:%M:%S')
                self.log_data.append(f"[{timestamp}] {log_entry}")
            except queue.Empty:
                pass
            time.sleep(0.1)

    def send_command(self, command):
        """Send command to device"""
        if self.cli.is_running:
            self.cli.command_queue.put(command)

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
                    f.write("-" * 50 + "\n\n")

                    for log_entry in self.log_data:
                        f.write(log_entry + "\n")

                messagebox.showinfo("Export Complete", f"Logs exported successfully to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export logs:\n{str(e)}")

    def on_closing(self):
        """Handle application closing"""
        if self.cli.is_running:
            self.cli.disconnect()
        self.root.destroy()


def main():
    """Main application entry point"""
    try:
        # Check if running on Windows or Linux
        if sys.platform.startswith('win'):
            # Windows-specific optimizations
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)

        # Create and run connection window
        root = tk.Tk()
        app = ConnectionWindow(root)
        root.mainloop()

    except Exception as e:
        messagebox.showerror("Application Error", f"An error occurred:\n{str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()