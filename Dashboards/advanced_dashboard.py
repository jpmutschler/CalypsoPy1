#!/usr/bin/env python3
"""
advanced_dashboard.py

Advanced Dashboard module for CalypsoPy application.
Provides advanced system administration, debugging, and diagnostic tools.
Works in both real device and demo modes.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
import json
import time
from typing import Dict, Any, Optional


class AdvancedDashboard:
    """
    Advanced Dashboard for system administration and debugging
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

        # Status tracking
        self.last_command_time = None
        self.command_count = 0

    def create_advanced_dashboard(self, scrollable_frame):
        """
        Create the complete advanced dashboard

        Args:
            scrollable_frame: Parent frame to contain the dashboard content
        """
        print("DEBUG: Creating advanced dashboard content")

        try:
            # Clear existing content first
            for widget in scrollable_frame.winfo_children():
                widget.destroy()

            # Demo mode indicator
            if self.is_demo_mode:
                self._create_demo_mode_banner(scrollable_frame)

            # System Status Section
            self._create_system_status_section(scrollable_frame)

            # Command Interface Section
            self._create_command_interface_section(scrollable_frame)

            # Cache Management Section
            self._create_cache_management_section(scrollable_frame)

            # Response Handler Section
            self._create_response_handler_section(scrollable_frame)

            # Debug Controls Section
            self._create_debug_controls_section(scrollable_frame)

            # System Information Section
            self._create_system_info_section(scrollable_frame)

            print("DEBUG: Advanced dashboard created successfully")

        except Exception as e:
            print(f"ERROR: Failed to create advanced dashboard: {e}")
            self._create_error_fallback(scrollable_frame, str(e))

    def _create_demo_mode_banner(self, parent):
        """Create demo mode banner"""
        banner_frame = ttk.Frame(parent, style='Content.TFrame')
        banner_frame.pack(fill='x', pady=(0, 20))

        # Demo mode banner
        demo_banner = ttk.Frame(banner_frame, style='Content.TFrame', relief='solid', borderwidth=2)
        demo_banner.pack(fill='x')

        banner_content = ttk.Frame(demo_banner, style='Content.TFrame')
        banner_content.pack(fill='x', padx=15, pady=10)

        ttk.Label(banner_content, text="🎭 DEMO MODE - Advanced Dashboard",
                  style='Dashboard.TLabel', foreground='#ff9500',
                  font=('Arial', 14, 'bold')).pack(anchor='w')

        ttk.Label(banner_content, text="All advanced features available with simulated data • No hardware required",
                  style='Info.TLabel', foreground='#cccccc').pack(anchor='w', pady=(5, 0))

    def _create_system_status_section(self, parent):
        """Create system status section"""
        status_frame = ttk.Frame(parent, style='Content.TFrame', relief='solid', borderwidth=1)
        status_frame.pack(fill='x', pady=10)

        # Header
        header_frame = ttk.Frame(status_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=15, pady=(15, 10))

        ttk.Label(header_frame, text="📊 System Status", style='Dashboard.TLabel').pack(side='left')
        ttk.Button(header_frame, text="🔄", width=3,
                   command=self._refresh_system_status).pack(side='right')

        # Content
        content_frame = ttk.Frame(status_frame, style='Content.TFrame')
        content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        # Status grid
        self.status_vars = {}
        status_items = [
            ("Connection Status", "🟢 Connected" if not self.is_demo_mode else "🟠 Demo Mode"),
            ("Port", self.app.port),
            ("Commands Sent", "0"),
            ("Cache Entries", str(self._get_cache_stats()['valid_entries']) if hasattr(self.app,
                                                                                       'cache_manager') and self.app.cache_manager else "0"),
            ("Last Activity", "Session start"),
            ("Debug Mode", "Enabled" if self._is_debug_enabled() else "Disabled")
        ]

        for i, (label, value) in enumerate(status_items):
            row_frame = ttk.Frame(content_frame, style='Content.TFrame')
            row_frame.pack(fill='x', pady=2)

            ttk.Label(row_frame, text=f"{label}:", style='Info.TLabel',
                      font=('Arial', 10, 'bold')).pack(side='left')

            var = tk.StringVar(value=value)
            self.status_vars[label.lower().replace(' ', '_')] = var
            ttk.Label(row_frame, textvariable=var, style='Info.TLabel').pack(side='right')

    def _create_command_interface_section(self, parent):
        """Create command interface section"""
        cmd_frame = ttk.Frame(parent, style='Content.TFrame', relief='solid', borderwidth=1)
        cmd_frame.pack(fill='x', pady=10)

        # Header
        header_frame = ttk.Frame(cmd_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=15, pady=(15, 10))

        ttk.Label(header_frame, text="🔧 Direct Command Interface", style='Dashboard.TLabel').pack(side='left')

        # Command input
        input_frame = ttk.Frame(cmd_frame, style='Content.TFrame')
        input_frame.pack(fill='x', padx=15, pady=10)

        self.command_entry = ttk.Entry(input_frame, font=('Consolas', 10))
        self.command_entry.pack(side='left', fill='x', expand=True)
        self.command_entry.bind('<Return>', self._send_command)
        self.command_entry.bind('<Up>', self._history_up)
        self.command_entry.bind('<Down>', self._history_down)

        ttk.Button(input_frame, text="Send", command=self._send_command).pack(side='right', padx=(10, 0))

        # Quick commands
        quick_frame = ttk.Frame(cmd_frame, style='Content.TFrame')
        quick_frame.pack(fill='x', padx=15)

        ttk.Label(quick_frame, text="Quick Commands:", style='Info.TLabel',
                  font=('Arial', 9, 'bold')).pack(side='left')

        quick_commands = ['help', 'status', 'ver', 'sysinfo', 'showport']
        for cmd in quick_commands:
            ttk.Button(quick_frame, text=cmd, width=8,
                       command=lambda c=cmd: self._quick_command(c)).pack(side='left', padx=2)

        # Command output
        output_frame = ttk.Frame(cmd_frame, style='Content.TFrame')
        output_frame.pack(fill='both', expand=True, padx=15, pady=(10, 15))

        ttk.Label(output_frame, text="Command Output:", style='Info.TLabel',
                  font=('Arial', 9, 'bold')).pack(anchor='w')

        self.command_output = scrolledtext.ScrolledText(output_frame, height=8, wrap='word',
                                                        bg='#1a1a1a', fg='#00ff00',
                                                        font=('Consolas', 9))
        self.command_output.pack(fill='both', expand=True, pady=(5, 0))

        # Initial welcome message
        welcome_msg = "Advanced Command Interface Ready\n"
        if self.is_demo_mode:
            welcome_msg += "Demo Mode: All commands return simulated responses\n"
        welcome_msg += "Type 'help' for available commands or use Quick Commands above\n"
        welcome_msg += "Use ↑/↓ arrows for command history\n" + "=" * 50 + "\n"

        self.command_output.insert('end', welcome_msg)

    def _create_cache_management_section(self, parent):
        """Create cache management section"""
        cache_frame = ttk.Frame(parent, style='Content.TFrame', relief='solid', borderwidth=1)
        cache_frame.pack(fill='x', pady=10)

        # Header
        header_frame = ttk.Frame(cache_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=15, pady=(15, 10))

        ttk.Label(header_frame, text="💾 Cache Management", style='Dashboard.TLabel').pack(side='left')

        # Content
        content_frame = ttk.Frame(cache_frame, style='Content.TFrame')
        content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        # Cache stats
        stats = self._get_cache_stats()
        cache_info = [
            f"Cache entries: {stats['valid_entries']}",
            f"Cache size: {stats.get('cache_file_size', 0)} bytes",
            f"Hit ratio: {stats.get('hit_ratio', 0.0):.1%}" if 'hit_ratio' in stats else "Hit ratio: N/A"
        ]

        for info in cache_info:
            ttk.Label(content_frame, text=info, style='Info.TLabel').pack(anchor='w', pady=2)

        # Cache controls
        button_frame = ttk.Frame(content_frame, style='Content.TFrame')
        button_frame.pack(fill='x', pady=10)

        ttk.Button(button_frame, text="View Cache Contents",
                   command=self._view_cache_contents).pack(side='left', padx=(0, 10))
        ttk.Button(button_frame, text="Clear Cache",
                   command=self._clear_cache).pack(side='left', padx=(0, 10))
        ttk.Button(button_frame, text="Cache Settings",
                   command=self._open_cache_settings).pack(side='left')

    def _create_response_handler_section(self, parent):
        """Create response handler debug section"""
        handler_frame = ttk.Frame(parent, style='Content.TFrame', relief='solid', borderwidth=1)
        handler_frame.pack(fill='x', pady=10)

        # Header
        header_frame = ttk.Frame(handler_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=15, pady=(15, 10))

        ttk.Label(header_frame, text="🔧 Advanced Response Handler", style='Dashboard.TLabel').pack(side='left')

        # Content
        content_frame = ttk.Frame(handler_frame, style='Content.TFrame')
        content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        # Handler status
        self.handler_status_text = tk.Text(content_frame, height=6, wrap='word',
                                           state='disabled', bg='#f8f8f8',
                                           font=('Consolas', 9))
        self.handler_status_text.pack(fill='x', pady=(0, 10))

        # Control buttons
        button_frame = ttk.Frame(content_frame, style='Content.TFrame')
        button_frame.pack(fill='x')

        ttk.Button(button_frame, text="Refresh Status",
                   command=self._refresh_handler_status).pack(side='left', padx=(0, 10))
        ttk.Button(button_frame, text="Clear Buffers",
                   command=self._clear_handler_buffers).pack(side='left')

        # Initialize handler status
        self._refresh_handler_status()

    def _create_debug_controls_section(self, parent):
        """Create debug controls section"""
        debug_frame = ttk.Frame(parent, style='Content.TFrame', relief='solid', borderwidth=1)
        debug_frame.pack(fill='x', pady=10)

        # Header
        header_frame = ttk.Frame(debug_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=15, pady=(15, 10))

        ttk.Label(header_frame, text="🐛 Debug Controls", style='Dashboard.TLabel').pack(side='left')

        # Content
        content_frame = ttk.Frame(debug_frame, style='Content.TFrame')
        content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        # Debug status
        debug_enabled = self._is_debug_enabled()
        status_text = "🟢 Enabled" if debug_enabled else "🔴 Disabled"
        ttk.Label(content_frame, text=f"Debug Status: {status_text}",
                  style='Info.TLabel', font=('Arial', 10, 'bold')).pack(anchor='w', pady=5)

        # Debug controls
        button_frame = ttk.Frame(content_frame, style='Content.TFrame')
        button_frame.pack(fill='x', pady=5)

        ttk.Button(button_frame, text="Toggle Debug",
                   command=self._toggle_debug).pack(side='left', padx=(0, 10))
        ttk.Button(button_frame, text="View Debug Log",
                   command=self._view_debug_log).pack(side='left', padx=(0, 10))
        ttk.Button(button_frame, text="Export Logs",
                   command=self._export_logs).pack(side='left')

    def _create_system_info_section(self, parent):
        """Create system information section"""
        info_frame = ttk.Frame(parent, style='Content.TFrame', relief='solid', borderwidth=1)
        info_frame.pack(fill='x', pady=10)

        # Header
        header_frame = ttk.Frame(info_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=15, pady=(15, 10))

        ttk.Label(header_frame, text="ℹ️ System Information", style='Dashboard.TLabel').pack(side='left')

        # Content
        content_frame = ttk.Frame(info_frame, style='Content.TFrame')
        content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        # Application info
        app_info = [
            f"CalypsoPy Version: {getattr(self.app, 'version', '1.3.4')}",
            f"Python Version: {self._get_python_version()}",
            f"Operating System: {self._get_os_info()}",
            f"Session Duration: {self._get_session_duration()}",
            f"Memory Usage: {self._get_memory_usage()}"
        ]

        for info in app_info:
            ttk.Label(content_frame, text=info, style='Info.TLabel').pack(anchor='w', pady=2)

    def _create_error_fallback(self, parent, error_msg):
        """Create error fallback content"""
        error_frame = ttk.Frame(parent, style='Content.TFrame')
        error_frame.pack(fill='both', expand=True, padx=20, pady=20)

        ttk.Label(error_frame, text="⚠️ Advanced Dashboard Error",
                  style='Dashboard.TLabel', foreground='#ff0000').pack(anchor='w')
        ttk.Label(error_frame, text=f"Error: {error_msg}",
                  style='Info.TLabel').pack(anchor='w', pady=10)
        ttk.Label(error_frame, text="Some advanced features may not be available.",
                  style='Info.TLabel').pack(anchor='w')

    # Command Interface Methods
    def _send_command(self, event=None):
        """Send command from entry field"""
        command = self.command_entry.get().strip()
        if not command:
            return

        self.command_entry.delete(0, tk.END)
        self.command_history.append(command)
        self.history_index = len(self.command_history)

        # Display command
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.command_output.insert('end', f"[{timestamp}] > {command}\n")

        try:
            if self.is_demo_mode:
                response = self._get_demo_response(command)
            else:
                response = self._send_real_command(command)

            self.command_output.insert('end', f"{response}\n{'=' * 50}\n")
            self.command_count += 1
            self.last_command_time = datetime.now()

            # Update status
            if 'commands_sent' in self.status_vars:
                self.status_vars['commands_sent'].set(str(self.command_count))
            if 'last_activity' in self.status_vars:
                self.status_vars['last_activity'].set(timestamp)

        except Exception as e:
            self.command_output.insert('end', f"ERROR: {e}\n{'=' * 50}\n")

        self.command_output.see('end')

    def _quick_command(self, command):
        """Execute quick command"""
        self.command_entry.delete(0, tk.END)
        self.command_entry.insert(0, command)
        self._send_command()

    def _history_up(self, event):
        """Navigate command history up"""
        if self.command_history and self.history_index > 0:
            self.history_index -= 1
            self.command_entry.delete(0, tk.END)
            self.command_entry.insert(0, self.command_history[self.history_index])

    def _history_down(self, event):
        """Navigate command history down"""
        if self.command_history and self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.command_entry.delete(0, tk.END)
            self.command_entry.insert(0, self.command_history[self.history_index])

    def _get_demo_response(self, command):
        """Generate demo response for command"""
        command = command.lower()

        demo_responses = {
            'help': """Available Commands:
- help          Show available commands
- status        Get device status
- ver           Get detailed version info
- sysinfo       Get complete system information
- showport      Check port status
- reset         Reset device
- lsd           Get system diagnostics""",
            'status': "Device Status: Online | Demo Mode Active | All Systems Operational",
            'ver': "Firmware Version: 1.2.3 Build 456\nHardware Version: Gen6 PCIe Atlas 3\nBootloader: v2.1.0\nDemo Mode: Active",
            'sysinfo': """System Information (Demo Data):
Device: Gen6 PCIe Atlas 3 Host Card
Serial Number: DEMO-12345
Temperature: 45.2°C
Power Status: Normal
Ports: 4x Active
Link Status: All Links Up
Cache: 2.1MB Used""",
            'showport': """Port Status (Demo Data):
Port 1: UP   | Speed: 10Gbps | Link Quality: Excellent
Port 2: UP   | Speed: 10Gbps | Link Quality: Good  
Port 3: UP   | Speed: 5Gbps  | Link Quality: Fair
Port 4: DOWN | Speed: N/A    | Link Quality: N/A""",
            'reset': "Demo Mode: Reset command acknowledged (no actual reset performed)",
            'lsd': "Link Status Diagnostics: All systems nominal (Demo Data)"
        }

        return demo_responses.get(command, f"Demo response for '{command}' - Command executed successfully")

    def _send_real_command(self, command):
        """Send real command to device"""
        if hasattr(self.app, 'cli') and self.app.cli:
            try:
                response = self.app.cli.send_command(command)
                return response if response else "No response received"
            except Exception as e:
                return f"Command failed: {e}"
        else:
            return "No device connection available"

    # Cache Management Methods
    def _get_cache_stats(self):
        """Get cache statistics"""
        if hasattr(self.app, 'cache_manager') and self.app.cache_manager:
            return self.app.cache_manager.get_stats()
        else:
            return {'valid_entries': 0, 'cache_file_size': 0}

    def _view_cache_contents(self):
        """View cache contents in popup window"""
        cache_window = tk.Toplevel(self.app.root)
        cache_window.title("Cache Contents")
        cache_window.geometry("600x400")

        # Create text widget with scrollbar
        text_frame = ttk.Frame(cache_window)
        text_frame.pack(fill='both', expand=True, padx=10, pady=10)

        cache_text = scrolledtext.ScrolledText(text_frame, wrap='word', font=('Consolas', 9))
        cache_text.pack(fill='both', expand=True)

        try:
            if hasattr(self.app, 'cache_manager') and self.app.cache_manager:
                cache_data = self.app.cache_manager.get_all_entries()
                if cache_data:
                    formatted_cache = json.dumps(cache_data, indent=2, default=str)
                    cache_text.insert('1.0', formatted_cache)
                else:
                    cache_text.insert('1.0', "Cache is empty")
            else:
                cache_text.insert('1.0', "No cache manager available")
        except Exception as e:
            cache_text.insert('1.0', f"Error reading cache: {e}")

        cache_text.config(state='disabled')

    def _clear_cache(self):
        """Clear cache with confirmation"""
        if messagebox.askyesno("Clear Cache", "Are you sure you want to clear the cache?"):
            try:
                if hasattr(self.app, 'cache_manager') and self.app.cache_manager:
                    self.app.cache_manager.clear()
                    messagebox.showinfo("Success", "Cache cleared successfully")
                    self._refresh_system_status()
                else:
                    messagebox.showwarning("Warning", "No cache manager available")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear cache: {e}")

    def _open_cache_settings(self):
        """Open cache settings dialog"""
        if hasattr(self.app, 'open_settings'):
            self.app.open_settings()
        else:
            messagebox.showinfo("Settings", "Settings dialog not available")

    # Response Handler Methods
    def _refresh_handler_status(self):
        """Refresh response handler status"""
        self.handler_status_text.config(state='normal')
        self.handler_status_text.delete('1.0', 'end')

        try:
            if hasattr(self.app, 'response_handler') and self.app.response_handler:
                status = self.app.response_handler.get_status()
                status_text = f"""Response Handler Status:
Active Buffers: {status.get('active_buffers', 0)}
Total Commands: {status.get('total_commands', 0)}
Successful Responses: {status.get('successful_responses', 0)}
Timeouts: {status.get('timeouts', 0)}
Handler State: {'Active' if status.get('active_buffers', 0) > 0 else 'Idle'}"""
            else:
                status_text = "Response Handler: Not initialized or not available"

            self.handler_status_text.insert('1.0', status_text)
        except Exception as e:
            self.handler_status_text.insert('1.0', f"Error getting status: {e}")

        self.handler_status_text.config(state='disabled')

    def _clear_handler_buffers(self):
        """Clear response handler buffers"""
        try:
            if hasattr(self.app, 'response_handler') and self.app.response_handler:
                self.app.response_handler.clear_all_buffers()
                messagebox.showinfo("Success", "Response handler buffers cleared")
                self._refresh_handler_status()
            else:
                messagebox.showwarning("Warning", "Response handler not available")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to clear buffers: {e}")

    # Debug Control Methods
    def _is_debug_enabled(self):
        """Check if debug is enabled"""
        try:
            from Admin.debug_config import is_debug_enabled
            return is_debug_enabled()
        except ImportError:
            return False

    def _toggle_debug(self):
        """Toggle debug mode"""
        try:
            from Admin.debug_config import toggle_debug
            new_state = toggle_debug()
            state_text = "enabled" if new_state else "disabled"
            messagebox.showinfo("Debug Mode", f"Debug mode {state_text}")
            self._refresh_system_status()
        except ImportError:
            messagebox.showerror("Error", "Debug config not available")

    def _view_debug_log(self):
        """View debug log in popup window"""
        log_window = tk.Toplevel(self.app.root)
        log_window.title("Debug Log")
        log_window.geometry("800x600")

        # Create text widget with scrollbar
        text_frame = ttk.Frame(log_window)
        text_frame.pack(fill='both', expand=True, padx=10, pady=10)

        log_text = scrolledtext.ScrolledText(text_frame, wrap='word', font=('Consolas', 9))
        log_text.pack(fill='both', expand=True)

        # Show recent log entries
        if hasattr(self.app, 'log_data'):
            log_entries = self.app.log_data[-100:]  # Last 100 entries
            log_text.insert('1.0', '\n'.join(log_entries))
        else:
            log_text.insert('1.0', "No log data available")

        log_text.config(state='disabled')

    def _export_logs(self):
        """Export logs to file"""
        try:
            from tkinter import filedialog

            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Export Logs"
            )

            if filename:
                with open(filename, 'w') as f:
                    f.write(f"CalypsoPy Debug Log Export\n")
                    f.write(f"Exported: {datetime.now()}\n")
                    f.write(f"Session: {'Demo Mode' if self.is_demo_mode else 'Real Device'}\n")
                    f.write("=" * 50 + "\n\n")

                    if hasattr(self.app, 'log_data'):
                        for entry in self.app.log_data:
                            f.write(f"{entry}\n")

                messagebox.showinfo("Success", f"Logs exported to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export logs: {e}")

    # System Information Methods
    def _get_python_version(self):
        """Get Python version"""
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    def _get_os_info(self):
        """Get OS information"""
        import platform
        return f"{platform.system()} {platform.release()}"

    def _get_session_duration(self):
        """Get session duration"""
        if hasattr(self.app, 'session_start_time'):
            duration = time.time() - self.app.session_start_time
            hours, remainder = divmod(int(duration), 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return "Unknown"

    def _get_memory_usage(self):
        """Get memory usage"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return f"{memory_info.rss / 1024 / 1024:.1f} MB"
        except ImportError:
            return "Unknown (psutil not available)"

    # Status Update Methods
    def _refresh_system_status(self):
        """Refresh system status display"""
        try:
            # Update connection status
            if 'connection_status' in self.status_vars:
                status = "🟠 Demo Mode" if self.is_demo_mode else "🟢 Connected"
                self.status_vars['connection_status'].set(status)

            # Update cache entries
            if 'cache_entries' in self.status_vars:
                cache_stats = self._get_cache_stats()
                self.status_vars['cache_entries'].set(str(cache_stats['valid_entries']))

            # Update debug mode
            if 'debug_mode' in self.status_vars:
                debug_status = "Enabled" if self._is_debug_enabled() else "Disabled"
                self.status_vars['debug_mode'].set(debug_status)

            # Update last activity
            if 'last_activity' in self.status_vars and self.last_command_time:
                last_activity = self.last_command_time.strftime('%H:%M:%S')
                self.status_vars['last_activity'].set(last_activity)

        except Exception as e:
            print(f"ERROR: Failed to refresh system status: {e}")

    def update_command_count(self, count):
        """Update command count from external source"""
        self.command_count = count
        if 'commands_sent' in self.status_vars:
            self.status_vars['commands_sent'].set(str(count))


# Standalone test functionality
if __name__ == "__main__":
    print("Advanced Dashboard Module Test")
    print("This module should be imported by main.py")
    print("File location: Dashboards/advanced_dashboard.py")

    # Basic test of the class
    print("\nTesting class instantiation...")
    try:
        # Mock parent app for testing
        class MockApp:
            def __init__(self):
                self.is_demo_mode = True
                self.port = "DEMO"
                self.root = None
                self.log_data = ["Test log entry 1", "Test log entry 2"]


        mock_app = MockApp()
        dashboard = AdvancedDashboard(mock_app)
        print(f"✅ AdvancedDashboard created: Demo Mode = {dashboard.is_demo_mode}")
        print("✅ Module test completed successfully!")
        print("Ready for import in main.py")

    except Exception as e:
        print(f"❌ Module test failed: {e}")
        import traceback

        traceback.print_exc()