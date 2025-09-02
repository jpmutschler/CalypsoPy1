#!/usr/bin/env python3
"""
advanced_dashboard.py

Advanced Dashboard module for CalypsoPy application.
Provides direct command interface for device control and configuration.
Includes support for clock, fmode, and other device-specific commands.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
import time
from typing import Dict, List, Optional


class AdvancedDashboard:
    """
    Advanced Dashboard for device command execution and control
    """

    def __init__(self, parent_app):
        """
        Initialize Advanced Dashboard

        Args:
            parent_app: Reference to main dashboard application
        """
        self.app = parent_app
        self.is_demo_mode = parent_app.is_demo_mode
        print(f"DEBUG: AdvancedDashboard initialized (Demo Mode: {self.is_demo_mode})")

        # Command history
        self.command_history = []
        self.history_index = -1
        self.max_history = 50

        # Session tracking
        self.session_start = time.time()
        self.command_count = 0

        # Command output widget (will be created later)
        self.command_output = None
        self.command_entry = None

        # Demo responses for various commands
        self.demo_responses = self._init_demo_responses()

    def _init_demo_responses(self) -> Dict[str, str]:
        """Initialize demo mode responses for various commands"""
        return {
            # Clock commands
            'clock': """Cmd>clock
MCIO Left clock disable.
MCIO Right clock enable.
Straddle clock enable.
Cmd>""",

            'clock l d': """Cmd>clock l d
Set MCIO Left clock disable success.
Cmd>""",

            'clock l e': """Cmd>clock l e
Set MCIO Left clock enable success.
Cmd>""",

            'clock r d': """Cmd>clock r d
Set MCIO Right clock disable success.
Cmd>""",

            'clock r e': """Cmd>clock r e
Set MCIO Right clock enable success.
Cmd>""",

            'clock srise5': """Cmd>clock srise5
Set SRIS Clock mode enable 0.5% success.
Cmd>""",

            'clock srise2': """Cmd>clock srise2
Set SRIS Clock mode enable 0.25% success.
Cmd>""",

            'clock srisd': """Cmd>clock srisd
Set SRIS Clock mode disable success.
Cmd>""",

            # Fmode commands
            'fmode': """Cmd>fmode

Port 32 enable flitmode.
Port 80 disable flitmode.
Port 112 enable flitmode.
Port 128 enable flitmode.
Cmd>""",

            'fmode 32 en': """Cmd>fmode 32 en

Write enable Flitmode page success.
Set enable Flitmode success.
Cmd>""",

            'fmode 32 dis': """Cmd>fmode 32 dis

Write disable Flitmode page success.
Set disable Flitmode success.
Cmd>""",

            'fmode 80 en': """Cmd>fmode 80 en

Write enable Flitmode page success.
Set enable Flitmode success.
Cmd>""",

            'fmode 80 dis': """Cmd>fmode 80 dis

Write disable Flitmode page success.
Set disable Flitmode success.
Cmd>""",

            'fmode 112 en': """Cmd>fmode 112 en

Write enable Flitmode page success.
Set enable Flitmode success.
Cmd>""",

            'fmode 112 dis': """Cmd>fmode 112 dis

Write disable Flitmode page success.
Set disable Flitmode success.
Cmd>""",

            'fmode 128 en': """Cmd>fmode 128 en

Write enable Flitmode page success.
Set enable Flitmode success.
Cmd>""",

            'fmode 128 dis': """Cmd>fmode 128 dis

Write disable Flitmode page success.
Set disable Flitmode success.
Cmd>""",

            # Other common commands
            'help': """Available Commands:
=================
System Commands:
  help              - Show this help message
  ver               - Display version information
  sysinfo           - Display complete system information
  lsd               - Display system diagnostics
  showport          - Display port status
  showmode          - Display current mode

Clock Commands:
  clock             - Display clock status
  clock [l|r] [e|d] - Enable/disable left/right MCIO clock
  clock srise5      - Set SRIS clock spread to 0.5%
  clock srise2      - Set SRIS clock spread to 0.25%
  clock srisd       - Disable SRIS clock spread

Flit Mode Commands:
  fmode             - Display flit mode status
  fmode [port] [en|dis] - Enable/disable flit mode for port
    Ports: 32, 80, 112, 128

Reset Commands:
  reset             - System reset
  msrst             - Module specific reset
  swreset           - Software reset

Port Commands:
  setmode [0-7]     - Set operating mode

Cmd>""",

            'ver': """Cmd>ver
=====================================
ver
=====================================
S/N: DEMO12345678
Company: SerialCables,Inc
Model: Gen6-Atlas3-x16HT-BG6-144
Version: 1.0.0
Build: Aug 19 2025 12:00:00
SBR Version: 0 34 160 28
Cmd>""",

            'showport': """Cmd>showport

Port Slot------------------------------------------------------------------------------
Port32 : speed 06, width 16, max_speed06, max_width16
Port80 : speed 06, width 04, max_speed06, max_width16
Port112: speed 01, width 00, max_speed06, max_width16
Port128: speed 05, width 16, max_speed06, max_width16

Port Upstream--------------------------------------------------------------------------
Golden finger: speed 05, width 16, max_width = 16

Cmd>""",

            'showmode': """Cmd>showmode

SBR mode: 0

Cmd>""",
        }

    def create_advanced_dashboard(self, scrollable_frame):
        """
        Create the advanced dashboard for command execution

        Args:
            scrollable_frame: Parent frame to contain the dashboard content
        """
        print("DEBUG: Creating advanced dashboard content")

        try:
            # Clear existing content
            for widget in scrollable_frame.winfo_children():
                widget.destroy()

            # Main container
            main_frame = ttk.Frame(scrollable_frame, style='Content.TFrame')
            main_frame.pack(fill='both', expand=True, padx=20, pady=20)

            # Title
            title_frame = ttk.Frame(main_frame, style='Content.TFrame')
            title_frame.pack(fill='x', pady=(0, 20))

            ttk.Label(title_frame, text="🖥️ Advanced Command Interface",
                      style='Dashboard.TLabel',
                      font=('Arial', 18, 'bold')).pack(side='left')

            if self.is_demo_mode:
                ttk.Label(title_frame, text="[DEMO MODE]",
                          style='Info.TLabel',
                          foreground='#ff9500').pack(side='left', padx=(20, 0))

            # Create sections
            self._create_quick_commands_section(main_frame)
            self._create_command_terminal_section(main_frame)
            self._create_command_reference_section(main_frame)

            print("DEBUG: Advanced dashboard created successfully")

        except Exception as e:
            print(f"ERROR: Failed to create advanced dashboard: {e}")
            import traceback
            traceback.print_exc()
            self._create_error_display(scrollable_frame, str(e))

    def _create_quick_commands_section(self, parent):
        """Create quick command buttons section"""
        # Quick commands frame
        quick_frame = ttk.LabelFrame(parent, text="Quick Commands",
                                     style='Content.TFrame')
        quick_frame.pack(fill='x', pady=(0, 15))

        # Button container
        button_container = ttk.Frame(quick_frame, style='Content.TFrame')
        button_container.pack(padx=10, pady=10)

        # Row 1: System commands
        row1 = ttk.Frame(button_container, style='Content.TFrame')
        row1.pack(fill='x', pady=2)

        ttk.Button(row1, text="📋 Help", width=15,
                   command=lambda: self._execute_command("help")).pack(side='left', padx=2)
        ttk.Button(row1, text="📊 System Info", width=15,
                   command=lambda: self._execute_command("sysinfo")).pack(side='left', padx=2)
        ttk.Button(row1, text="🔍 Version", width=15,
                   command=lambda: self._execute_command("ver")).pack(side='left', padx=2)
        ttk.Button(row1, text="🔌 Show Ports", width=15,
                   command=lambda: self._execute_command("showport")).pack(side='left', padx=2)
        ttk.Button(row1, text="⚙️ Show Mode", width=15,
                   command=lambda: self._execute_command("showmode")).pack(side='left', padx=2)

        # Row 2: Clock commands
        row2 = ttk.Frame(button_container, style='Content.TFrame')
        row2.pack(fill='x', pady=2)

        ttk.Label(row2, text="Clock:", style='Info.TLabel').pack(side='left', padx=(0, 10))
        ttk.Button(row2, text="Status", width=10,
                   command=lambda: self._execute_command("clock")).pack(side='left', padx=2)
        ttk.Button(row2, text="Left Enable", width=12,
                   command=lambda: self._execute_command("clock l e")).pack(side='left', padx=2)
        ttk.Button(row2, text="Left Disable", width=12,
                   command=lambda: self._execute_command("clock l d")).pack(side='left', padx=2)
        ttk.Button(row2, text="SRIS 0.5%", width=12,
                   command=lambda: self._execute_command("clock srise5")).pack(side='left', padx=2)
        ttk.Button(row2, text="SRIS Disable", width=12,
                   command=lambda: self._execute_command("clock srisd")).pack(side='left', padx=2)

        # Row 3: Fmode commands
        row3 = ttk.Frame(button_container, style='Content.TFrame')
        row3.pack(fill='x', pady=2)

        ttk.Label(row3, text="Flit Mode:", style='Info.TLabel').pack(side='left', padx=(0, 10))
        ttk.Button(row3, text="Status", width=10,
                   command=lambda: self._execute_command("fmode")).pack(side='left', padx=2)

        # Port selection for fmode
        self.fmode_port_var = tk.StringVar(value="32")
        port_combo = ttk.Combobox(row3, textvariable=self.fmode_port_var,
                                  values=["32", "80", "112", "128"],
                                  width=8, state='readonly')
        port_combo.pack(side='left', padx=2)

        ttk.Button(row3, text="Enable", width=10,
                   command=lambda: self._execute_command(f"fmode {self.fmode_port_var.get()} en")).pack(side='left',
                                                                                                        padx=2)
        ttk.Button(row3, text="Disable", width=10,
                   command=lambda: self._execute_command(f"fmode {self.fmode_port_var.get()} dis")).pack(side='left',
                                                                                                         padx=2)

    def _create_command_terminal_section(self, parent):
        """Create command terminal section"""
        # Terminal frame
        terminal_frame = ttk.LabelFrame(parent, text="Command Terminal",
                                        style='Content.TFrame')
        terminal_frame.pack(fill='both', expand=True, pady=(0, 15))

        # Output text area
        output_container = ttk.Frame(terminal_frame, style='Content.TFrame')
        output_container.pack(fill='both', expand=True, padx=10, pady=(10, 5))

        # Create text widget with scrollbar
        self.command_output = scrolledtext.ScrolledText(
            output_container,
            wrap='word',
            height=20,
            bg='#1a1a1a',
            fg='#00ff00',
            font=('Consolas', 10),
            insertbackground='#00ff00'
        )
        self.command_output.pack(fill='both', expand=True)

        # Configure tags for different text styles
        self.command_output.tag_config('command', foreground='#ffff00')
        self.command_output.tag_config('response', foreground='#00ff00')
        self.command_output.tag_config('error', foreground='#ff0000')
        self.command_output.tag_config('info', foreground='#00ffff')

        # Welcome message
        welcome_msg = "=" * 60 + "\n"
        welcome_msg += "Advanced Command Terminal Ready\n"
        if self.is_demo_mode:
            welcome_msg += "🎭 DEMO MODE - Simulated responses enabled\n"
        else:
            welcome_msg += "🔌 Connected to device on port " + self.app.port + "\n"
        welcome_msg += "Type 'help' for available commands\n"
        welcome_msg += "=" * 60 + "\n\n"

        self.command_output.insert('end', welcome_msg, 'info')

        # Command input area
        input_frame = ttk.Frame(terminal_frame, style='Content.TFrame')
        input_frame.pack(fill='x', padx=10, pady=(0, 10))

        ttk.Label(input_frame, text="Cmd>", style='Info.TLabel',
                  font=('Consolas', 10, 'bold')).pack(side='left', padx=(0, 5))

        self.command_entry = ttk.Entry(input_frame, font=('Consolas', 10))
        self.command_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))

        # Bind events
        self.command_entry.bind('<Return>', lambda e: self._on_command_enter())
        self.command_entry.bind('<Up>', lambda e: self._navigate_history(-1))
        self.command_entry.bind('<Down>', lambda e: self._navigate_history(1))

        # Send button
        ttk.Button(input_frame, text="Send", width=10,
                   command=self._on_command_enter).pack(side='left', padx=2)

        # Clear button
        ttk.Button(input_frame, text="Clear", width=10,
                   command=self._clear_terminal).pack(side='left', padx=2)

        # Focus on entry
        self.command_entry.focus_set()

    def _create_command_reference_section(self, parent):
        """Create command reference section"""
        # Reference frame
        ref_frame = ttk.LabelFrame(parent, text="Command Reference",
                                   style='Content.TFrame')
        ref_frame.pack(fill='x')

        ref_container = ttk.Frame(ref_frame, style='Content.TFrame')
        ref_container.pack(padx=10, pady=10)

        # Create columns
        col1 = ttk.Frame(ref_container, style='Content.TFrame')
        col1.pack(side='left', padx=(0, 20))

        col2 = ttk.Frame(ref_container, style='Content.TFrame')
        col2.pack(side='left', padx=(0, 20))

        col3 = ttk.Frame(ref_container, style='Content.TFrame')
        col3.pack(side='left')

        # Column 1: Clock commands
        ttk.Label(col1, text="Clock Commands:", style='Info.TLabel',
                  font=('Arial', 10, 'bold')).pack(anchor='w', pady=(0, 5))

        clock_cmds = [
            "clock          - Show clock status",
            "clock l d      - Disable left MCIO clock",
            "clock l e      - Enable left MCIO clock",
            "clock r d      - Disable right MCIO clock",
            "clock r e      - Enable right MCIO clock",
            "clock srise5   - Set 0.5% spread",
            "clock srise2   - Set 0.25% spread",
            "clock srisd    - Disable spread"
        ]

        for cmd in clock_cmds:
            ttk.Label(col1, text=cmd, style='Info.TLabel',
                      font=('Consolas', 9)).pack(anchor='w')

        # Column 2: Fmode commands
        ttk.Label(col2, text="Flit Mode Commands:", style='Info.TLabel',
                  font=('Arial', 10, 'bold')).pack(anchor='w', pady=(0, 5))

        fmode_cmds = [
            "fmode              - Show flit mode status",
            "fmode [port] en    - Enable flit mode",
            "fmode [port] dis   - Disable flit mode",
            "",
            "Available ports:",
            "  32, 80, 112, 128",
            "",
            "Example: fmode 32 en"
        ]

        for cmd in fmode_cmds:
            ttk.Label(col2, text=cmd, style='Info.TLabel',
                      font=('Consolas', 9)).pack(anchor='w')

        # Column 3: General commands
        ttk.Label(col3, text="General Commands:", style='Info.TLabel',
                  font=('Arial', 10, 'bold')).pack(anchor='w', pady=(0, 5))

        general_cmds = [
            "help       - Show all commands",
            "ver        - Version information",
            "sysinfo    - System information",
            "lsd        - System diagnostics",
            "showport   - Port status",
            "showmode   - Current mode",
            "setmode N  - Set mode (0-7)",
            "reset      - System reset"
        ]

        for cmd in general_cmds:
            ttk.Label(col3, text=cmd, style='Info.TLabel',
                      font=('Consolas', 9)).pack(anchor='w')

    def _execute_command(self, command: str):
        """Execute a command and display the response"""
        if not command.strip():
            return

        # Add to history
        if command not in self.command_history:
            self.command_history.append(command)
            if len(self.command_history) > self.max_history:
                self.command_history.pop(0)
        self.history_index = len(self.command_history)

        # Display command in terminal
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.command_output.insert('end', f"[{timestamp}] Cmd> {command}\n", 'command')

        # Get response
        try:
            if self.is_demo_mode:
                response = self._get_demo_response(command)
            else:
                response = self._send_real_command(command)

            # Display response
            if response:
                self.command_output.insert('end', response + "\n", 'response')
            else:
                self.command_output.insert('end', "No response received\n", 'error')

        except Exception as e:
            error_msg = f"Error executing command: {str(e)}\n"
            self.command_output.insert('end', error_msg, 'error')
            print(f"ERROR: {error_msg}")

        # Auto-scroll to bottom
        self.command_output.see('end')

        # Update command count
        self.command_count += 1

        # Clear entry
        if self.command_entry:
            self.command_entry.delete(0, tk.END)

    def _get_demo_response(self, command: str) -> str:
        """Get demo response for a command"""
        cmd_lower = command.lower().strip()

        # Check for exact match first
        if cmd_lower in self.demo_responses:
            return self.demo_responses[cmd_lower]

        # Check for partial matches
        for demo_cmd, response in self.demo_responses.items():
            if demo_cmd in cmd_lower or cmd_lower in demo_cmd:
                return response

        # Default response for unknown commands
        return f"Cmd>{command}\nCommand executed (Demo Mode)\nCmd>"

    def _send_real_command(self, command: str) -> str:
        """Send real command to device"""
        if hasattr(self.app, 'cli') and self.app.cli:
            try:
                response = self.app.cli.send_command(command)
                return response if response else "No response from device"
            except Exception as e:
                return f"Communication error: {str(e)}"
        else:
            return "No device connection available"

    def _on_command_enter(self):
        """Handle command entry"""
        command = self.command_entry.get().strip()
        if command:
            self._execute_command(command)

    def _navigate_history(self, direction: int):
        """Navigate command history"""
        if not self.command_history:
            return

        if direction < 0:  # Up arrow
            if self.history_index > 0:
                self.history_index -= 1
        else:  # Down arrow
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
            else:
                # At the end of history, clear entry
                self.command_entry.delete(0, tk.END)
                self.history_index = len(self.command_history)
                return

        # Set entry to history command
        if 0 <= self.history_index < len(self.command_history):
            self.command_entry.delete(0, tk.END)
            self.command_entry.insert(0, self.command_history[self.history_index])

    def _clear_terminal(self):
        """Clear the terminal output"""
        self.command_output.delete('1.0', tk.END)

        # Re-add welcome message
        welcome_msg = "Terminal cleared\n"
        welcome_msg += "Type 'help' for available commands\n\n"
        self.command_output.insert('end', welcome_msg, 'info')

    def _create_error_display(self, parent, error_msg: str):
        """Create error display when dashboard fails to load"""
        # Clear existing content
        for widget in parent.winfo_children():
            widget.destroy()

        error_frame = ttk.Frame(parent, style='Content.TFrame')
        error_frame.pack(fill='both', expand=True, padx=20, pady=20)

        ttk.Label(error_frame, text="⚠️ Dashboard Error",
                  style='Dashboard.TLabel',
                  foreground='#ff0000').pack(pady=(0, 10))

        ttk.Label(error_frame, text=f"Error: {error_msg}",
                  style='Info.TLabel').pack(pady=(0, 20))

        ttk.Label(error_frame, text="Please check the console for details",
                  style='Info.TLabel').pack()


# Module test
if __name__ == "__main__":
    print("Advanced Dashboard Module Test")
    print("=" * 60)


    # Test class instantiation
    class MockApp:
        def __init__(self):
            self.is_demo_mode = True
            self.port = "DEMO"
            self.root = None
            self.cli = None


    try:
        app = MockApp()
        dashboard = AdvancedDashboard(app)
        print(f"✅ AdvancedDashboard created successfully")
        print(f"   Demo Mode: {dashboard.is_demo_mode}")
        print(f"   Demo responses loaded: {len(dashboard.demo_responses)}")

        # Test demo response
        test_cmd = "clock"
        response = dashboard._get_demo_response(test_cmd)
        print(f"\n✅ Demo response for '{test_cmd}':")
        print(response[:100] + "..." if len(response) > 100 else response)

        print("\n✅ Module test completed successfully!")

    except Exception as e:
        print(f"❌ Module test failed: {e}")
        import traceback

        traceback.print_exc()