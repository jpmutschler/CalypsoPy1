#!/usr/bin/env python3
"""
resets_dashboard.py

Resets Dashboard module for CalypsoPy application.
Provides reset functionality for different system components.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Callable, Optional


class ResetsDashboard:
    """
    Resets Dashboard for system reset operations
    """

    def __init__(self, parent_app):
        """
        Initialize Resets Dashboard

        Args:
            parent_app: Reference to main dashboard application
        """
        self.app = parent_app
        self.reset_commands = {
            'msrst': {
                'name': 'x16 Straddle Mount Reset',
                'icon': '🔧',
                'description': 'Reset the x16 Straddle Mount component',
                'command': 'msrst',
                'warning_level': 'medium'
            },
            'swreset': {
                'name': 'Atlas 3 Switch Reset',
                'icon': '🔀',
                'description': 'Reset the Atlas 3 Switch component',
                'command': 'swreset',
                'warning_level': 'medium'
            },
            'reset': {
                'name': 'Full System Reset',
                'icon': '🔴',
                'description': 'Perform a complete system reset (will disconnect)',
                'command': 'reset',
                'warning_level': 'high'
            }
        }

    def create_resets_dashboard(self, parent_frame):
        """
        Create the complete resets dashboard

        Args:
            parent_frame: Parent frame to contain the dashboard
        """
        # Clear existing content
        for widget in parent_frame.winfo_children():
            widget.destroy()

        # Main container with centered content
        main_container = ttk.Frame(parent_frame, style='Content.TFrame')
        main_container.pack(fill='both', expand=True)

        # Center frame for all reset options
        center_frame = ttk.Frame(main_container, style='Content.TFrame')
        center_frame.place(relx=0.5, rely=0.5, anchor='center')

        # Dashboard title
        title_frame = ttk.Frame(center_frame, style='Content.TFrame')
        title_frame.pack(pady=(0, 30))

        title_label = ttk.Label(title_frame,
                                text="🔄 System Reset Options",
                                style='Dashboard.TLabel',
                                font=('Arial', 18, 'bold'))
        title_label.pack()

        subtitle_label = ttk.Label(title_frame,
                                   text="Select a reset operation to perform",
                                   style='Info.TLabel',
                                   font=('Arial', 11))
        subtitle_label.pack(pady=(5, 0))

        # Create reset option cards
        for reset_id, reset_info in self.reset_commands.items():
            self._create_reset_card(center_frame, reset_id, reset_info)

        # Warning message
        warning_frame = ttk.Frame(center_frame, style='Content.TFrame')
        warning_frame.pack(pady=(30, 0))

        warning_label = ttk.Label(warning_frame,
                                  text="⚠️ Warning: Reset operations may cause temporary disconnection",
                                  style='Info.TLabel',
                                  font=('Arial', 10, 'italic'))
        warning_label.pack()

    def _create_reset_card(self, parent, reset_id: str, reset_info: dict):
        """
        Create a styled card for each reset option

        Args:
            parent: Parent frame
            reset_id: Reset command identifier
            reset_info: Reset information dictionary
        """
        # Card frame with border
        card_frame = ttk.Frame(parent, style='Content.TFrame',
                               relief='solid', borderwidth=1)
        card_frame.pack(fill='x', pady=10, padx=50)

        # Card content
        content_frame = ttk.Frame(card_frame, style='Content.TFrame')
        content_frame.pack(fill='both', expand=True, padx=20, pady=15)

        # Header with icon and name
        header_frame = ttk.Frame(content_frame, style='Content.TFrame')
        header_frame.pack(fill='x', pady=(0, 10))

        # Icon and title
        icon_title_frame = ttk.Frame(header_frame, style='Content.TFrame')
        icon_title_frame.pack(side='left')

        icon_label = ttk.Label(icon_title_frame,
                               text=reset_info['icon'],
                               style='Dashboard.TLabel',
                               font=('Arial', 16))
        icon_label.pack(side='left', padx=(0, 10))

        title_label = ttk.Label(icon_title_frame,
                                text=reset_info['name'],
                                style='Dashboard.TLabel',
                                font=('Arial', 12, 'bold'))
        title_label.pack(side='left')

        # Warning indicator based on severity
        if reset_info['warning_level'] == 'high':
            warning_color = '#ff4444'
            warning_text = 'HIGH RISK'
        elif reset_info['warning_level'] == 'medium':
            warning_color = '#ff9500'
            warning_text = 'CAUTION'
        else:
            warning_color = '#ffdd44'
            warning_text = 'LOW RISK'

        # Create warning label style
        warning_style_name = f"Warning_{reset_id}.TLabel"
        style = ttk.Style()
        style.configure(warning_style_name,
                        background='#1e1e1e',
                        foreground=warning_color,
                        font=('Arial', 8, 'bold'))

        warning_label = ttk.Label(header_frame,
                                  text=warning_text,
                                  style=warning_style_name)
        warning_label.pack(side='right')

        # Description
        desc_label = ttk.Label(content_frame,
                               text=reset_info['description'],
                               style='Info.TLabel',
                               font=('Arial', 10))
        desc_label.pack(anchor='w', pady=(0, 15))

        # Command display
        command_frame = ttk.Frame(content_frame, style='Content.TFrame')
        command_frame.pack(fill='x', pady=(0, 15))

        ttk.Label(command_frame,
                  text=f"Command: {reset_info['command']}",
                  style='Info.TLabel',
                  font=('Consolas', 9, 'bold')).pack(anchor='w')

        # Execute button
        button_frame = ttk.Frame(content_frame, style='Content.TFrame')
        button_frame.pack(fill='x')

        # Create button style based on warning level
        button_style_name = f"Reset_{reset_id}.TButton"
        if reset_info['warning_level'] == 'high':
            button_text = f"🔴 Execute {reset_info['name']}"
        elif reset_info['warning_level'] == 'medium':
            button_text = f"🟡 Execute {reset_info['name']}"
        else:
            button_text = f"🟢 Execute {reset_info['name']}"

        execute_btn = ttk.Button(button_frame,
                                 text=button_text,
                                 command=lambda: self._execute_reset(reset_id, reset_info))
        execute_btn.pack(anchor='w')

    def _execute_reset(self, reset_id: str, reset_info: dict):
        """
        Execute the selected reset operation

        Args:
            reset_id: Reset command identifier
            reset_info: Reset information dictionary
        """
        # Create confirmation message based on reset type
        if reset_id == 'reset':
            # Full system reset - special handling
            self._execute_full_system_reset(reset_info)
        else:
            # Standard reset operations
            self._execute_standard_reset(reset_id, reset_info)

    def _execute_standard_reset(self, reset_id: str, reset_info: dict):
        """
        Execute standard reset operations (msrst, swreset)

        Args:
            reset_id: Reset command identifier
            reset_info: Reset information dictionary
        """
        # Confirmation dialog
        confirm_message = (
            f"Are you sure you want to execute {reset_info['name']}?\n\n"
            f"Command: {reset_info['command']}\n"
            f"Description: {reset_info['description']}\n\n"
            "This operation may cause temporary system disruption."
        )

        if messagebox.askyesno("Confirm Reset Operation", confirm_message):
            try:
                # Send the reset command
                if hasattr(self.app, 'send_command'):
                    self.app.send_command(reset_info['command'])

                    # Log the operation
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    log_message = f"[{timestamp}] Executed {reset_info['name']} ({reset_info['command']})"
                    self.app.log_data.append(log_message)

                    # Show success message
                    messagebox.showinfo(
                        "Reset Initiated",
                        f"{reset_info['name']} has been initiated.\n\n"
                        f"Command '{reset_info['command']}' sent successfully."
                    )

                    # Clear cache if cache manager exists
                    if hasattr(self.app, 'cache_manager') and self.app.cache_manager:
                        # Invalidate relevant cache entries
                        self.app.cache_manager.invalidate_pattern('system')
                        self.app.cache_manager.invalidate_pattern('status')

                        # Update cache status
                        if hasattr(self.app, 'update_cache_status'):
                            self.app.update_cache_status("Cache cleared after reset")

                else:
                    messagebox.showerror(
                        "Command Error",
                        "Unable to send reset command. No active connection."
                    )

            except Exception as e:
                messagebox.showerror(
                    "Reset Error",
                    f"Failed to execute {reset_info['name']}:\n{str(e)}"
                )

    def _execute_full_system_reset(self, reset_info: dict):
        """
        Execute full system reset with reconnection options

        Args:
            reset_info: Reset information dictionary
        """
        # Special confirmation for full system reset
        confirm_message = (
            f"⚠️ FULL SYSTEM RESET ⚠️\n\n"
            f"This will perform a complete system reset and will disconnect the device.\n\n"
            f"Command: {reset_info['command']}\n"
            f"Risk Level: HIGH\n\n"
            "Are you absolutely sure you want to continue?"
        )

        if messagebox.askyesno("⚠️ Confirm Full System Reset", confirm_message):
            try:
                # Send the reset command
                if hasattr(self.app, 'send_command'):
                    self.app.send_command(reset_info['command'])

                    # Log the operation
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    log_message = f"[{timestamp}] Executed FULL SYSTEM RESET ({reset_info['command']})"
                    self.app.log_data.append(log_message)

                    # Clear all cache data
                    if hasattr(self.app, 'cache_manager') and self.app.cache_manager:
                        self.app.cache_manager.clear()
                        if hasattr(self.app, 'update_cache_status'):
                            self.app.update_cache_status("All cache cleared after full reset")

                    # Ask about reconnection
                    self._handle_post_reset_reconnection()

                else:
                    messagebox.showerror(
                        "Command Error",
                        "Unable to send reset command. No active connection."
                    )

            except Exception as e:
                messagebox.showerror(
                    "Reset Error",
                    f"Failed to execute full system reset:\n{str(e)}"
                )

    def _handle_post_reset_reconnection(self):
        """
        Handle reconnection options after full system reset
        """
        # Wait a moment for the reset to take effect
        self.app.root.after(2000, self._show_reconnection_dialog)

    def _show_reconnection_dialog(self):
        """
        Show reconnection dialog after full system reset
        """
        reconnect_message = (
            "Full system reset has been initiated.\n\n"
            "The device connection will be lost. Would you like to:\n\n"
            "• YES - Attempt to reconnect automatically\n"
            "• NO - Close the application"
        )

        try:
            # Ask user preference
            reconnect = messagebox.askyesno(
                "Reconnection Options",
                reconnect_message
            )

            if reconnect:
                self._attempt_reconnection()
            else:
                self._close_application()

        except Exception as e:
            print(f"Error in reconnection dialog: {e}")
            # Fallback to closing application
            self._close_application()

    def _attempt_reconnection(self):
        """
        Attempt to reconnect to the original device
        """
        try:
            # Get original connection details
            original_port = getattr(self.app, 'port', None)
            is_demo_mode = getattr(self.app, 'is_demo_mode', False)

            if not original_port:
                messagebox.showerror(
                    "Reconnection Error",
                    "Original connection details not available.\nPlease restart the application."
                )
                self._close_application()
                return

            # Show reconnection attempt message
            reconnect_dialog = self._create_reconnection_progress_dialog()

            # Disconnect current connection
            if hasattr(self.app, 'cli') and self.app.cli:
                self.app.cli.disconnect()

            # Wait for device to reset (longer delay)
            self.app.root.after(5000, lambda: self._perform_reconnection(
                original_port, is_demo_mode, reconnect_dialog
            ))

        except Exception as e:
            messagebox.showerror(
                "Reconnection Error",
                f"Failed to initiate reconnection:\n{str(e)}"
            )
            self._close_application()

    def _create_reconnection_progress_dialog(self):
        """
        Create a progress dialog for reconnection attempt

        Returns:
            Progress dialog window
        """
        progress_dialog = tk.Toplevel(self.app.root)
        progress_dialog.title("Reconnecting...")
        progress_dialog.geometry("400x150")
        progress_dialog.transient(self.app.root)
        progress_dialog.grab_set()

        # Center the dialog
        progress_dialog.update_idletasks()
        x = (progress_dialog.winfo_screenwidth() - 400) // 2
        y = (progress_dialog.winfo_screenheight() - 150) // 2
        progress_dialog.geometry(f"+{x}+{y}")

        # Content
        content_frame = ttk.Frame(progress_dialog, padding=20)
        content_frame.pack(fill='both', expand=True)

        ttk.Label(content_frame,
                  text="🔄 Attempting to reconnect...",
                  font=('Arial', 12, 'bold')).pack(pady=(0, 10))

        ttk.Label(content_frame,
                  text="Please wait while the device completes its reset cycle.",
                  font=('Arial', 10)).pack(pady=(0, 15))

        # Progress bar
        progress_bar = ttk.Progressbar(content_frame, mode='indeterminate')
        progress_bar.pack(fill='x', pady=(0, 10))
        progress_bar.start()

        return progress_dialog

    def _perform_reconnection(self, original_port: str, is_demo_mode: bool, progress_dialog):
        """
        Perform the actual reconnection attempt

        Args:
            original_port: Original port to reconnect to
            is_demo_mode: Whether original connection was demo mode
            progress_dialog: Progress dialog to close
        """
        try:
            # Close progress dialog
            progress_dialog.destroy()

            # Attempt to create new connection
            if is_demo_mode:
                from demo_mode_integration import UnifiedDemoSerialCLI
                new_cli = UnifiedDemoSerialCLI(original_port)
            else:
                from main import SerialCLI  # Import from main module
                cache_manager = getattr(self.app, 'cache_manager', None)
                new_cli = SerialCLI(original_port, cache_manager=cache_manager)

            # Try to connect
            if new_cli.connect():
                # Success - update app's CLI
                self.app.cli = new_cli

                # Restart background threads if not demo mode
                if not is_demo_mode and hasattr(self.app, 'start_background_threads'):
                    self.app.start_background_threads()

                # Update connection status
                if hasattr(self.app, 'connection_label'):
                    status_color = '#ff9500' if is_demo_mode else '#00ff00'
                    status_text = "🎭 DEMO MODE" if is_demo_mode else f"🔌 {original_port}"
                    self.app.connection_label.config(foreground=status_color, text=status_text)

                # Log successful reconnection
                timestamp = datetime.now().strftime('%H:%M:%S')
                self.app.log_data.append(f"[{timestamp}] Successfully reconnected after full reset")

                # Show success message
                messagebox.showinfo(
                    "Reconnection Successful",
                    f"Successfully reconnected to {original_port}.\n\n"
                    "The system is ready for use."
                )

                # Refresh current dashboard
                if hasattr(self.app, 'update_content_area'):
                    self.app.update_content_area()

            else:
                # Connection failed
                self._handle_reconnection_failure(original_port)

        except Exception as e:
            # Reconnection error
            self._handle_reconnection_failure(original_port, str(e))

    def _handle_reconnection_failure(self, original_port: str, error_msg: str = None):
        """
        Handle failed reconnection attempt

        Args:
            original_port: Port that failed to reconnect
            error_msg: Optional error message
        """
        failure_message = (
            f"Failed to reconnect to {original_port}.\n\n"
        )

        if error_msg:
            failure_message += f"Error: {error_msg}\n\n"

        failure_message += (
            "This can happen if:\n"
            "• The device is still resetting\n"
            "• The device was disconnected\n"
            "• The COM port changed\n\n"
            "Please restart the application to reconnect manually."
        )

        messagebox.showerror("Reconnection Failed", failure_message)
        self._close_application()

    def _close_application(self):
        """
        Safely close the application
        """
        try:
            # Log application closure
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.app.log_data.append(f"[{timestamp}] Application closing after full system reset")

            # Call the app's close handler if it exists
            if hasattr(self.app, 'on_closing'):
                self.app.on_closing()
            else:
                # Direct close
                self.app.root.destroy()

        except Exception as e:
            print(f"Error during application closure: {e}")
            # Force close as last resort
            import sys
            sys.exit(0)

    def get_dashboard_info(self) -> dict:
        """
        Get information about this dashboard for the main app

        Returns:
            Dictionary with dashboard metadata
        """
        return {
            'name': 'Resets Dashboard',
            'icon': '🔄',
            'description': 'System reset operations',
            'commands_available': list(self.reset_commands.keys()),
            'risk_level': 'HIGH'
        }


# Testing function
if __name__ == "__main__":
    print("Testing Resets Dashboard...")


    # Mock app for testing
    class MockApp:
        def __init__(self):
            self.port = "COM3"
            self.is_demo_mode = False
            self.log_data = []

        def send_command(self, command):
            print(f"Mock: Sending command '{command}'")
            return True

        def update_cache_status(self, message):
            print(f"Mock: Cache status: {message}")


    # Test dashboard info
    mock_app = MockApp()
    dashboard = ResetsDashboard(mock_app)

    info = dashboard.get_dashboard_info()
    print(f"Dashboard info: {info}")

    # Test reset commands
    print(f"Available reset commands: {list(dashboard.reset_commands.keys())}")

    for reset_id, reset_info in dashboard.reset_commands.items():
        print(f"  {reset_id}: {reset_info['name']} ({reset_info['warning_level']})")

    print("Resets Dashboard test completed!")