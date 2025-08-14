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
        print("DEBUG: ResetsDashboard initialized successfully")

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

    def create_resets_dashboard(self, scrollable_frame):
        """
        FIXED: Create the complete resets dashboard

        Args:
            scrollable_frame: Parent frame to contain the dashboard content
        """
        print("DEBUG: create_resets_dashboard called with scrollable_frame")

        try:
            # Clear existing content first
            for widget in scrollable_frame.winfo_children():
                widget.destroy()
            print("DEBUG: Cleared existing widgets")

            # Create main container that fills the scrollable frame
            main_container = ttk.Frame(scrollable_frame, style='Content.TFrame')
            main_container.pack(fill='both', expand=True, padx=650, pady=20)
            print("DEBUG: Created main container")

            # Dashboard title section
            title_frame = ttk.Frame(main_container, style='Content.TFrame')
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
            print("DEBUG: Created title section")

            # Create reset option cards
            for reset_id, reset_info in self.reset_commands.items():
                print(f"DEBUG: Creating card for {reset_id}")
                self._create_reset_card(main_container, reset_id, reset_info)

            # Warning message at bottom
            warning_frame = ttk.Frame(main_container, style='Content.TFrame')
            warning_frame.pack(pady=(30, 0))

            warning_label = ttk.Label(warning_frame,
                                      text="⚠️ Warning: Reset operations may cause temporary disconnection",
                                      style='Info.TLabel',
                                      font=('Arial', 10, 'italic'))
            warning_label.pack()
            print("DEBUG: Created warning section")

            print("DEBUG: Resets dashboard creation completed successfully")

        except Exception as e:
            print(f"ERROR: Exception in create_resets_dashboard: {e}")
            import traceback
            traceback.print_exc()

            # Create error display
            error_frame = ttk.Frame(scrollable_frame, style='Content.TFrame')
            error_frame.pack(fill='both', expand=True, padx=20, pady=20)

            error_label = ttk.Label(error_frame,
                                    text=f"❌ Error Creating Resets Dashboard: {str(e)}",
                                    style='Dashboard.TLabel',
                                    font=('Arial', 14))
            error_label.pack(pady=50)

    def _create_reset_card(self, parent, reset_id: str, reset_info: dict):
        """
        Create a styled card for each reset option

        Args:
            parent: Parent frame
            reset_id: Reset command identifier
            reset_info: Reset information dictionary
        """
        try:
            print(f"DEBUG: Creating reset card for {reset_id}")

            # Card frame with border and padding
            card_frame = ttk.Frame(parent, style='Content.TFrame',
                                   relief='solid', borderwidth=1)
            card_frame.pack(fill='x', pady=15, padx=40)

            # Card content with internal padding
            content_frame = ttk.Frame(card_frame, style='Content.TFrame')
            content_frame.pack(fill='both', expand=True, padx=25, pady=20)

            # Header with icon and name
            header_frame = ttk.Frame(content_frame, style='Content.TFrame')
            header_frame.pack(fill='x', pady=(0, 10))

            # Icon and title on left side
            left_header_frame = ttk.Frame(header_frame, style='Content.TFrame')
            left_header_frame.pack(side='left')

            icon_label = ttk.Label(left_header_frame,
                                   text=reset_info['icon'],
                                   style='Dashboard.TLabel',
                                   font=('Arial', 16))
            icon_label.pack(side='left', padx=(0, 10))

            title_label = ttk.Label(left_header_frame,
                                    text=reset_info['name'],
                                    style='Dashboard.TLabel',
                                    font=('Arial', 12, 'bold'))
            title_label.pack(side='left')

            # Warning indicator on right side
            warning_color, warning_text = self._get_warning_style(reset_info['warning_level'])

            warning_label = ttk.Label(header_frame,
                                      text=warning_text,
                                      font=('Arial', 8, 'bold'))
            warning_label.pack(side='right')

            # Configure warning label color
            try:
                style = ttk.Style()
                warning_style_name = f"Warning_{reset_id}.TLabel"
                style.configure(warning_style_name,
                                background='#1e1e1e',
                                foreground=warning_color,
                                font=('Arial', 8, 'bold'))
                warning_label.config(style=warning_style_name)
            except:
                pass  # If style configuration fails, just use default

            # Description
            desc_label = ttk.Label(content_frame,
                                   text=reset_info['description'],
                                   style='Info.TLabel',
                                   font=('Arial', 10))
            desc_label.pack(anchor='w', pady=(0, 15))

            # Command display
            command_frame = ttk.Frame(content_frame, style='Content.TFrame')
            command_frame.pack(fill='x', pady=(0, 15))

            command_label = ttk.Label(command_frame,
                                      text=f"Command: {reset_info['command']}",
                                      style='Info.TLabel',
                                      font=('Consolas', 9, 'bold'))
            command_label.pack(anchor='w')

            # Execute button
            button_frame = ttk.Frame(content_frame, style='Content.TFrame')
            button_frame.pack(fill='x')

            button_text = self._get_button_text(reset_info)

            execute_btn = ttk.Button(button_frame,
                                     text=button_text,
                                     command=lambda: self._execute_reset(reset_id, reset_info))
            execute_btn.pack(anchor='w')

            print(f"DEBUG: Successfully created reset card for {reset_id}")

        except Exception as e:
            print(f"ERROR: Failed to create reset card for {reset_id}: {e}")
            # Create a simple fallback
            error_frame = ttk.Frame(parent, style='Content.TFrame')
            error_frame.pack(fill='x', pady=5)
            ttk.Label(error_frame, text=f"Error creating {reset_id} card").pack()

    def _get_warning_style(self, warning_level: str) -> tuple:
        """Get warning color and text based on level"""
        if warning_level == 'high':
            return '#ff4444', 'HIGH RISK'
        elif warning_level == 'medium':
            return '#ff9500', 'CAUTION'
        else:
            return '#ffdd44', 'LOW RISK'

    def _get_button_text(self, reset_info: dict) -> str:
        """Get button text based on warning level"""
        if reset_info['warning_level'] == 'high':
            return f"🔴 Execute {reset_info['name']}"
        elif reset_info['warning_level'] == 'medium':
            return f"🟡 Execute {reset_info['name']}"
        else:
            return f"🟢 Execute {reset_info['name']}"

    def _execute_reset(self, reset_id: str, reset_info: dict):
        """
        Execute the selected reset operation

        Args:
            reset_id: Reset command identifier
            reset_info: Reset information dictionary
        """
        print(f"DEBUG: _execute_reset called for {reset_id}")

        try:
            # Create confirmation message based on reset type
            if reset_id == 'reset':
                # Full system reset - special handling
                self._execute_full_system_reset(reset_info)
            else:
                # Standard reset operations
                self._execute_standard_reset(reset_id, reset_info)

        except Exception as e:
            print(f"ERROR: Failed to execute reset {reset_id}: {e}")
            messagebox.showerror("Reset Error", f"Failed to execute reset: {str(e)}")

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
                # Send the reset command using app's send_command method
                if hasattr(self.app, 'send_command'):
                    self.app.send_command(reset_info['command'])
                    print(f"DEBUG: Sent command: {reset_info['command']}")

                    # Log the operation
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    log_message = f"[{timestamp}] Executed {reset_info['name']} ({reset_info['command']})"

                    if hasattr(self.app, 'log_data'):
                        self.app.log_data.append(log_message)

                    # Show success message
                    messagebox.showinfo(
                        "Reset Initiated",
                        f"{reset_info['name']} has been initiated.\n\n"
                        f"Command '{reset_info['command']}' sent successfully."
                    )

                    # Clear cache if available
                    if hasattr(self.app, 'cache_manager') and self.app.cache_manager:
                        # Invalidate relevant cache entries
                        self.app.cache_manager.invalidate_pattern('system')
                        self.app.cache_manager.invalidate_pattern('status')

                        # Update cache status if method exists
                        if hasattr(self.app, 'update_cache_status'):
                            self.app.update_cache_status("Cache cleared after reset")

                else:
                    print("ERROR: No send_command method found")
                    messagebox.showerror(
                        "Command Error",
                        "Unable to send reset command. No active connection."
                    )

            except Exception as e:
                print(f"ERROR: Exception in _execute_standard_reset: {e}")
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
                    print(f"DEBUG: Sent full reset command: {reset_info['command']}")

                    # Log the operation
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    log_message = f"[{timestamp}] Executed FULL SYSTEM RESET ({reset_info['command']})"

                    if hasattr(self.app, 'log_data'):
                        self.app.log_data.append(log_message)

                    # Clear all cache data
                    if hasattr(self.app, 'cache_manager') and self.app.cache_manager:
                        self.app.cache_manager.clear()
                        if hasattr(self.app, 'update_cache_status'):
                            self.app.update_cache_status("All cache cleared after full reset")

                    # Ask about reconnection
                    self._handle_post_reset_reconnection()

                else:
                    print("ERROR: No send_command method for full reset")
                    messagebox.showerror(
                        "Command Error",
                        "Unable to send reset command. No active connection."
                    )

            except Exception as e:
                print(f"ERROR: Exception in _execute_full_system_reset: {e}")
                messagebox.showerror(
                    "Reset Error",
                    f"Failed to execute full system reset:\n{str(e)}"
                )

    def _handle_post_reset_reconnection(self):
        """Handle reconnection options after full system reset"""
        try:
            # Wait a moment for the reset to take effect, then show dialog
            if hasattr(self.app, 'root'):
                self.app.root.after(2000, self._show_reconnection_dialog)
            else:
                # Fallback if no root reference
                self._show_reconnection_dialog()
        except Exception as e:
            print(f"ERROR: Failed to handle post-reset reconnection: {e}")

    def _show_reconnection_dialog(self):
        """Show reconnection dialog after full system reset"""
        try:
            reconnect_message = (
                "Full system reset has been initiated.\n\n"
                "The device connection will be lost. Would you like to:\n\n"
                "• YES - Attempt to reconnect automatically\n"
                "• NO - Close the application"
            )

            reconnect = messagebox.askyesno("Reconnection Options", reconnect_message)

            if reconnect:
                self._attempt_reconnection()
            else:
                self._close_application()

        except Exception as e:
            print(f"ERROR: Exception in reconnection dialog: {e}")
            self._close_application()

    def _attempt_reconnection(self):
        """Attempt to reconnect to the original device"""
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

            messagebox.showinfo(
                "Reconnection Attempt",
                f"Attempting to reconnect to {original_port}...\n\n"
                "This may take a few seconds."
            )

            # For now, just show a message - full reconnection logic would be complex
            reconnection_success = False  # Placeholder

            if reconnection_success:
                messagebox.showinfo("Reconnection Successful",
                                    f"Successfully reconnected to {original_port}")
            else:
                failure_message = (
                    f"Failed to reconnect to {original_port}.\n\n"
                    "Please restart the application to reconnect manually."
                )
                messagebox.showerror("Reconnection Failed", failure_message)
                self._close_application()

        except Exception as e:
            print(f"ERROR: Exception in reconnection attempt: {e}")
            messagebox.showerror("Reconnection Error", f"Reconnection failed: {str(e)}")
            self._close_application()

    def _close_application(self):
        """Safely close the application"""
        try:
            # Log application closure
            timestamp = datetime.now().strftime('%H:%M:%S')
            if hasattr(self.app, 'log_data'):
                self.app.log_data.append(f"[{timestamp}] Application closing after full system reset")

            # Call the app's close handler if it exists
            if hasattr(self.app, 'on_closing'):
                self.app.on_closing()
            elif hasattr(self.app, 'root'):
                self.app.root.destroy()
            else:
                print("WARNING: No close method available")

        except Exception as e:
            print(f"ERROR: Exception during application closure: {e}")


# Testing function
if __name__ == "__main__":
    print("Testing Fixed Resets Dashboard...")


    # Mock app for testing
    class MockApp:
        def __init__(self):
            self.port = "COM3"
            self.is_demo_mode = False
            self.log_data = []

        def send_command(self, command):
            print(f"Mock: Sending command '{command}'")
            return True


    mock_app = MockApp()
    dashboard = ResetsDashboard(mock_app)

    print(f"Available reset commands: {list(dashboard.reset_commands.keys())}")
    print("Fixed Resets Dashboard test completed!")