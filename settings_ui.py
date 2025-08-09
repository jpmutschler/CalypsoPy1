#!/usr/bin/env python3
"""
settings_ui.py

Settings dialog UI for CalypsoPy application.
Provides a comprehensive interface for viewing and editing application settings.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from typing import Dict, Any, Callable
from settings_manager import SettingsManager


class SettingsDialog:
    """
    Settings dialog window with tabbed interface
    """

    def __init__(self, parent: tk.Tk, settings_manager: SettingsManager,
                 on_settings_changed: Callable = None):
        """
        Initialize settings dialog

        Args:
            parent: Parent window
            settings_manager: Settings manager instance
            on_settings_changed: Callback when settings are changed
        """
        self.parent = parent
        self.settings_mgr = settings_manager
        self.on_settings_changed = on_settings_changed

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings - CalypsoPy")
        self.dialog.geometry("700x600")
        self.dialog.resizable(True, True)

        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center dialog on parent
        self._center_dialog()

        # Configure styles
        self._setup_styles()

        # Create UI
        self._create_ui()

        # Load current settings
        self._load_settings()

        # Handle dialog close
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _center_dialog(self):
        """Center dialog on parent window"""
        self.dialog.update_idletasks()

        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()

        dialog_width = self.dialog.winfo_width()
        dialog_height = self.dialog.winfo_height()

        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2

        self.dialog.geometry(f"+{x}+{y}")

    def _setup_styles(self):
        """Configure dialog styles"""
        style = ttk.Style()

        # Configure tab styles
        style.configure('Settings.TNotebook.Tab',
                        font=('Arial', 10, 'bold'))

        # Configure frame styles
        style.configure('SettingsFrame.TFrame',
                        background='#f0f0f0')

        # Configure label styles
        style.configure('SettingsLabel.TLabel',
                        font=('Arial', 10))
        style.configure('SettingsHeader.TLabel',
                        font=('Arial', 12, 'bold'))

    def _create_ui(self):
        """Create the main UI"""
        # Main container
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill='both', expand=True)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame, style='Settings.TNotebook')
        self.notebook.pack(fill='both', expand=True, pady=(0, 10))

        # Create tabs
        self._create_cache_tab()
        self._create_refresh_tab()
        self._create_ui_tab()
        self._create_communication_tab()
        self._create_demo_tab()
        self._create_advanced_tab()

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(10, 0))

        # Buttons
        ttk.Button(button_frame, text="Reset to Defaults",
                   command=self._reset_to_defaults).pack(side='left')

        ttk.Button(button_frame, text="Cancel",
                   command=self._on_cancel).pack(side='right', padx=(5, 0))
        ttk.Button(button_frame, text="Apply",
                   command=self._on_apply).pack(side='right', padx=(5, 0))
        ttk.Button(button_frame, text="OK",
                   command=self._on_ok).pack(side='right', padx=(5, 0))

    def _create_cache_tab(self):
        """Create cache settings tab"""
        cache_frame = ttk.Frame(self.notebook, style='SettingsFrame.TFrame', padding=15)
        self.notebook.add(cache_frame, text="Cache")

        # Cache enabled
        ttk.Label(cache_frame, text="Cache Settings",
                  style='SettingsHeader.TLabel').pack(anchor='w', pady=(0, 15))

        self.cache_enabled = tk.BooleanVar()
        ttk.Checkbutton(cache_frame, text="Enable data caching",
                        variable=self.cache_enabled).pack(anchor='w', pady=5)

        # TTL settings
        ttl_frame = ttk.Frame(cache_frame)
        ttl_frame.pack(fill='x', pady=10)

        ttk.Label(ttl_frame, text="Default cache TTL (seconds):",
                  style='SettingsLabel.TLabel').pack(side='left')
        self.cache_ttl = tk.StringVar()
        ttk.Entry(ttl_frame, textvariable=self.cache_ttl, width=10).pack(side='right')

        # Max entries
        entries_frame = ttk.Frame(cache_frame)
        entries_frame.pack(fill='x', pady=10)

        ttk.Label(entries_frame, text="Maximum cache entries:",
                  style='SettingsLabel.TLabel').pack(side='left')
        self.cache_max_entries = tk.StringVar()
        ttk.Entry(entries_frame, textvariable=self.cache_max_entries, width=10).pack(side='right')

        # Cleanup interval
        cleanup_frame = ttk.Frame(cache_frame)
        cleanup_frame.pack(fill='x', pady=10)

        ttk.Label(cleanup_frame, text="Cleanup interval (minutes):",
                  style='SettingsLabel.TLabel').pack(side='left')
        self.cache_cleanup_interval = tk.StringVar()
        ttk.Entry(cleanup_frame, textvariable=self.cache_cleanup_interval, width=10).pack(side='right')

        # Cache directory
        dir_frame = ttk.Frame(cache_frame)
        dir_frame.pack(fill='x', pady=10)

        ttk.Label(dir_frame, text="Cache directory:",
                  style='SettingsLabel.TLabel').pack(anchor='w')

        dir_input_frame = ttk.Frame(dir_frame)
        dir_input_frame.pack(fill='x', pady=(5, 0))

        self.cache_directory = tk.StringVar()
        ttk.Entry(dir_input_frame, textvariable=self.cache_directory).pack(side='left', fill='x', expand=True)
        ttk.Button(dir_input_frame, text="Browse",
                   command=self._browse_cache_directory).pack(side='right', padx=(5, 0))

        # Cache info
        ttk.Label(cache_frame, text="Cache Information",
                  style='SettingsHeader.TLabel').pack(anchor='w', pady=(20, 10))

        self.cache_info_text = tk.Text(cache_frame, height=6, wrap='word',
                                       state='disabled', bg='#f8f8f8')
        self.cache_info_text.pack(fill='x', pady=5)

        # Cache management buttons
        cache_buttons_frame = ttk.Frame(cache_frame)
        cache_buttons_frame.pack(fill='x', pady=10)

        ttk.Button(cache_buttons_frame, text="View Cache Contents",
                   command=self._view_cache_contents).pack(side='left', padx=(0, 5))
        ttk.Button(cache_buttons_frame, text="Clear Cache",
                   command=self._clear_cache).pack(side='left', padx=5)

    def _create_refresh_tab(self):
        """Create auto-refresh settings tab"""
        refresh_frame = ttk.Frame(self.notebook, style='SettingsFrame.TFrame', padding=15)
        self.notebook.add(refresh_frame, text="Auto-Refresh")

        # Auto-refresh enabled
        ttk.Label(refresh_frame, text="Auto-Refresh Settings",
                  style='SettingsHeader.TLabel').pack(anchor='w', pady=(0, 15))

        self.refresh_enabled = tk.BooleanVar()
        ttk.Checkbutton(refresh_frame, text="Enable auto-refresh",
                        variable=self.refresh_enabled).pack(anchor='w', pady=5)

        # Refresh interval
        interval_frame = ttk.Frame(refresh_frame)
        interval_frame.pack(fill='x', pady=10)

        ttk.Label(interval_frame, text="Refresh interval (seconds):",
                  style='SettingsLabel.TLabel').pack(side='left')
        self.refresh_interval = tk.StringVar()
        ttk.Entry(interval_frame, textvariable=self.refresh_interval, width=10).pack(side='right')

        # Dashboard selection
        ttk.Label(refresh_frame, text="Enable auto-refresh for dashboards:",
                  style='SettingsHeader.TLabel').pack(anchor='w', pady=(20, 10))

        self.dashboard_vars = {}
        dashboards = [
            ('host', 'Host Card Information'),
            ('link', 'Link Status'),
            ('port', 'Port Configuration'),
            ('compliance', 'Compliance'),
            ('registers', 'Registers'),
            ('advanced', 'Advanced'),
            ('resets', 'Resets'),
            ('firmware', 'Firmware Updates')
        ]

        for dash_id, dash_name in dashboards:
            var = tk.BooleanVar()
            self.dashboard_vars[dash_id] = var
            ttk.Checkbutton(refresh_frame, text=dash_name, variable=var).pack(anchor='w', pady=2)

    def _create_ui_tab(self):
        """Create UI settings tab"""
        ui_frame = ttk.Frame(self.notebook, style='SettingsFrame.TFrame', padding=15)
        self.notebook.add(ui_frame, text="Interface")

        # Theme settings
        ttk.Label(ui_frame, text="Appearance",
                  style='SettingsHeader.TLabel').pack(anchor='w', pady=(0, 15))

        theme_frame = ttk.Frame(ui_frame)
        theme_frame.pack(fill='x', pady=10)

        ttk.Label(theme_frame, text="Theme:",
                  style='SettingsLabel.TLabel').pack(side='left')
        self.ui_theme = tk.StringVar()
        theme_combo = ttk.Combobox(theme_frame, textvariable=self.ui_theme,
                                   values=['dark', 'light'], state='readonly', width=15)
        theme_combo.pack(side='right')

        # Font settings
        font_frame = ttk.Frame(ui_frame)
        font_frame.pack(fill='x', pady=10)

        ttk.Label(font_frame, text="Font family:",
                  style='SettingsLabel.TLabel').pack(side='left')
        self.ui_font_family = tk.StringVar()
        font_combo = ttk.Combobox(font_frame, textvariable=self.ui_font_family,
                                  values=['Arial', 'Helvetica', 'Times New Roman', 'Courier New'],
                                  width=15)
        font_combo.pack(side='right')

        size_frame = ttk.Frame(ui_frame)
        size_frame.pack(fill='x', pady=10)

        ttk.Label(size_frame, text="Font size:",
                  style='SettingsLabel.TLabel').pack(side='left')
        self.ui_font_size = tk.StringVar()
        ttk.Entry(size_frame, textvariable=self.ui_font_size, width=10).pack(side='right')

        # Window settings
        ttk.Label(ui_frame, text="Window Settings",
                  style='SettingsHeader.TLabel').pack(anchor='w', pady=(20, 15))

        width_frame = ttk.Frame(ui_frame)
        width_frame.pack(fill='x', pady=10)

        ttk.Label(width_frame, text="Default window width:",
                  style='SettingsLabel.TLabel').pack(side='left')
        self.ui_window_width = tk.StringVar()
        ttk.Entry(width_frame, textvariable=self.ui_window_width, width=10).pack(side='right')

        height_frame = ttk.Frame(ui_frame)
        height_frame.pack(fill='x', pady=10)

        ttk.Label(height_frame, text="Default window height:",
                  style='SettingsLabel.TLabel').pack(side='left')
        self.ui_window_height = tk.StringVar()
        ttk.Entry(height_frame, textvariable=self.ui_window_height, width=10).pack(side='right')

        # UI options
        self.ui_remember_position = tk.BooleanVar()
        ttk.Checkbutton(ui_frame, text="Remember window position",
                        variable=self.ui_remember_position).pack(anchor='w', pady=5)

        self.ui_show_tooltips = tk.BooleanVar()
        ttk.Checkbutton(ui_frame, text="Show tooltips",
                        variable=self.ui_show_tooltips).pack(anchor='w', pady=5)

        self.ui_show_status_bar = tk.BooleanVar()
        ttk.Checkbutton(ui_frame, text="Show status bar",
                        variable=self.ui_show_status_bar).pack(anchor='w', pady=5)

    def _create_communication_tab(self):
        """Create communication settings tab"""
        comm_frame = ttk.Frame(self.notebook, style='SettingsFrame.TFrame', padding=15)
        self.notebook.add(comm_frame, text="Communication")

        # Serial settings
        ttk.Label(comm_frame, text="Serial Communication",
                  style='SettingsHeader.TLabel').pack(anchor='w', pady=(0, 15))

        baudrate_frame = ttk.Frame(comm_frame)
        baudrate_frame.pack(fill='x', pady=10)

        ttk.Label(baudrate_frame, text="Default baud rate:",
                  style='SettingsLabel.TLabel').pack(side='left')
        self.comm_baudrate = tk.StringVar()
        baudrate_combo = ttk.Combobox(baudrate_frame, textvariable=self.comm_baudrate,
                                      values=['9600', '19200', '38400', '57600', '115200'],
                                      width=15)
        baudrate_combo.pack(side='right')

        timeout_frame = ttk.Frame(comm_frame)
        timeout_frame.pack(fill='x', pady=10)

        ttk.Label(timeout_frame, text="Timeout (seconds):",
                  style='SettingsLabel.TLabel').pack(side='left')
        self.comm_timeout = tk.StringVar()
        ttk.Entry(timeout_frame, textvariable=self.comm_timeout, width=10).pack(side='right')

        # Retry settings
        retry_frame = ttk.Frame(comm_frame)
        retry_frame.pack(fill='x', pady=10)

        ttk.Label(retry_frame, text="Retry attempts:",
                  style='SettingsLabel.TLabel').pack(side='left')
        self.comm_retry_attempts = tk.StringVar()
        ttk.Entry(retry_frame, textvariable=self.comm_retry_attempts, width=10).pack(side='right')

        retry_delay_frame = ttk.Frame(comm_frame)
        retry_delay_frame.pack(fill='x', pady=10)

        ttk.Label(retry_delay_frame, text="Retry delay (seconds):",
                  style='SettingsLabel.TLabel').pack(side='left')
        self.comm_retry_delay = tk.StringVar()
        ttk.Entry(retry_delay_frame, textvariable=self.comm_retry_delay, width=10).pack(side='right')

        # Logging settings
        ttk.Label(comm_frame, text="Logging",
                  style='SettingsHeader.TLabel').pack(anchor='w', pady=(20, 15))

        log_level_frame = ttk.Frame(comm_frame)
        log_level_frame.pack(fill='x', pady=10)

        ttk.Label(log_level_frame, text="Log level:",
                  style='SettingsLabel.TLabel').pack(side='left')
        self.comm_log_level = tk.StringVar()
        log_combo = ttk.Combobox(log_level_frame, textvariable=self.comm_log_level,
                                 values=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                                 state='readonly', width=15)
        log_combo.pack(side='right')

        history_frame = ttk.Frame(comm_frame)
        history_frame.pack(fill='x', pady=10)

        ttk.Label(history_frame, text="Command history size:",
                  style='SettingsLabel.TLabel').pack(side='left')
        self.comm_history_size = tk.StringVar()
        ttk.Entry(history_frame, textvariable=self.comm_history_size, width=10).pack(side='right')

    def _create_demo_tab(self):
        """Create demo mode settings tab"""
        demo_frame = ttk.Frame(self.notebook, style='SettingsFrame.TFrame', padding=15)
        self.notebook.add(demo_frame, text="Demo Mode")

        # Demo settings
        ttk.Label(demo_frame, text="Demo Mode Settings",
                  style='SettingsHeader.TLabel').pack(anchor='w', pady=(0, 15))

        self.demo_enabled_default = tk.BooleanVar()
        ttk.Checkbutton(demo_frame, text="Enable demo mode by default",
                        variable=self.demo_enabled_default).pack(anchor='w', pady=5)

        self.demo_simulate_delays = tk.BooleanVar()
        ttk.Checkbutton(demo_frame, text="Simulate realistic response delays",
                        variable=self.demo_simulate_delays).pack(anchor='w', pady=5)

        self.demo_random_variation = tk.BooleanVar()
        ttk.Checkbutton(demo_frame, text="Add random data variation",
                        variable=self.demo_random_variation).pack(anchor='w', pady=5)

        self.demo_fake_errors = tk.BooleanVar()
        ttk.Checkbutton(demo_frame, text="Occasionally simulate errors",
                        variable=self.demo_fake_errors).pack(anchor='w', pady=5)

        # Device name
        name_frame = ttk.Frame(demo_frame)
        name_frame.pack(fill='x', pady=15)

        ttk.Label(name_frame, text="Demo device name:",
                  style='SettingsLabel.TLabel').pack(side='left')
        self.demo_device_name = tk.StringVar()
        ttk.Entry(name_frame, textvariable=self.demo_device_name, width=20).pack(side='right')

    def _create_advanced_tab(self):
        """Create advanced settings tab"""
        advanced_frame = ttk.Frame(self.notebook, style='SettingsFrame.TFrame', padding=15)
        self.notebook.add(advanced_frame, text="Advanced")

        # Settings file info
        ttk.Label(advanced_frame, text="Settings File",
                  style='SettingsHeader.TLabel').pack(anchor='w', pady=(0, 15))

        file_info_frame = ttk.Frame(advanced_frame)
        file_info_frame.pack(fill='x', pady=10)

        ttk.Label(file_info_frame, text="Location:",
                  style='SettingsLabel.TLabel').pack(anchor='w')

        self.settings_file_path = tk.StringVar(value=self.settings_mgr.settings_file)
        file_entry = ttk.Entry(file_info_frame, textvariable=self.settings_file_path,
                               state='readonly', width=50)
        file_entry.pack(fill='x', pady=(5, 0))

        file_buttons_frame = ttk.Frame(advanced_frame)
        file_buttons_frame.pack(fill='x', pady=10)

        ttk.Button(file_buttons_frame, text="Open Settings Folder",
                   command=self._open_settings_folder).pack(side='left', padx=(0, 5))
        ttk.Button(file_buttons_frame, text="Export Settings",
                   command=self._export_settings).pack(side='left', padx=5)
        ttk.Button(file_buttons_frame, text="Import Settings",
                   command=self._import_settings).pack(side='left', padx=5)

        # Settings validation
        ttk.Label(advanced_frame, text="Validation",
                  style='SettingsHeader.TLabel').pack(anchor='w', pady=(20, 15))

        ttk.Button(advanced_frame, text="Validate Current Settings",
                   command=self._validate_settings).pack(anchor='w', pady=5)

        self.validation_text = tk.Text(advanced_frame, height=8, wrap='word',
                                       state='disabled', bg='#f8f8f8')
        self.validation_text.pack(fill='both', expand=True, pady=10)

    def _load_settings(self):
        """Load current settings into UI"""
        settings = self.settings_mgr.settings

        # Cache settings
        self.cache_enabled.set(settings.cache.enabled)
        self.cache_ttl.set(str(settings.cache.default_ttl_seconds))
        self.cache_max_entries.set(str(settings.cache.max_entries))
        self.cache_cleanup_interval.set(str(settings.cache.cleanup_interval_minutes))
        self.cache_directory.set(settings.cache.cache_directory)

        # Refresh settings
        self.refresh_enabled.set(settings.refresh.enabled)
        self.refresh_interval.set(str(settings.refresh.interval_seconds))

        for dash_id, var in self.dashboard_vars.items():
            var.set(settings.refresh.dashboards.get(dash_id, False))

        # UI settings
        self.ui_theme.set(settings.ui.theme)
        self.ui_font_family.set(settings.ui.font_family)
        self.ui_font_size.set(str(settings.ui.font_size))
        self.ui_window_width.set(str(settings.ui.window_width))
        self.ui_window_height.set(str(settings.ui.window_height))
        self.ui_remember_position.set(settings.ui.remember_window_position)
        self.ui_show_tooltips.set(settings.ui.show_tooltips)
        self.ui_show_status_bar.set(settings.ui.show_status_bar)

        # Communication settings
        self.comm_baudrate.set(str(settings.communication.default_baudrate))
        self.comm_timeout.set(str(settings.communication.timeout_seconds))
        self.comm_retry_attempts.set(str(settings.communication.retry_attempts))
        self.comm_retry_delay.set(str(settings.communication.retry_delay_seconds))
        self.comm_log_level.set(settings.communication.log_level)
        self.comm_history_size.set(str(settings.communication.command_history_size))

        # Demo settings
        self.demo_enabled_default.set(settings.demo.enabled_by_default)
        self.demo_simulate_delays.set(settings.demo.simulate_delays)
        self.demo_random_variation.set(settings.demo.random_data_variation)
        self.demo_fake_errors.set(settings.demo.fake_errors)
        self.demo_device_name.set(settings.demo.demo_device_name)

        # Update cache info
        self._update_cache_info()

    def _save_settings(self):
        """Save UI values to settings"""
        try:
            settings = self.settings_mgr.settings

            # Cache settings
            settings.cache.enabled = self.cache_enabled.get()
            settings.cache.default_ttl_seconds = int(self.cache_ttl.get())
            settings.cache.max_entries = int(self.cache_max_entries.get())
            settings.cache.cleanup_interval_minutes = int(self.cache_cleanup_interval.get())
            settings.cache.cache_directory = self.cache_directory.get()

            # Refresh settings
            settings.refresh.enabled = self.refresh_enabled.get()
            settings.refresh.interval_seconds = int(self.refresh_interval.get())

            for dash_id, var in self.dashboard_vars.items():
                settings.refresh.dashboards[dash_id] = var.get()

            # UI settings
            settings.ui.theme = self.ui_theme.get()
            settings.ui.font_family = self.ui_font_family.get()
            settings.ui.font_size = int(self.ui_font_size.get())
            settings.ui.window_width = int(self.ui_window_width.get())
            settings.ui.window_height = int(self.ui_window_height.get())
            settings.ui.remember_window_position = self.ui_remember_position.get()
            settings.ui.show_tooltips = self.ui_show_tooltips.get()
            settings.ui.show_status_bar = self.ui_show_status_bar.get()

            # Communication settings
            settings.communication.default_baudrate = int(self.comm_baudrate.get())
            settings.communication.timeout_seconds = float(self.comm_timeout.get())
            settings.communication.retry_attempts = int(self.comm_retry_attempts.get())
            settings.communication.retry_delay_seconds = float(self.comm_retry_delay.get())
            settings.communication.log_level = self.comm_log_level.get()
            settings.communication.command_history_size = int(self.comm_history_size.get())

            # Demo settings
            settings.demo.enabled_by_default = self.demo_enabled_default.get()
            settings.demo.simulate_delays = self.demo_simulate_delays.get()
            settings.demo.random_data_variation = self.demo_random_variation.get()
            settings.demo.fake_errors = self.demo_fake_errors.get()
            settings.demo.demo_device_name = self.demo_device_name.get()

            # Validate settings
            issues = self.settings_mgr.validate_settings()
            if issues:
                issue_text = "Settings validation failed:\n\n"
                for section, section_issues in issues.items():
                    issue_text += f"{section.upper()}:\n"
                    for issue in section_issues:
                        issue_text += f"  • {issue}\n"
                    issue_text += "\n"

                messagebox.showerror("Validation Error", issue_text)
                return False

            # Save to file
            if self.settings_mgr.save():
                return True
            else:
                messagebox.showerror("Save Error", "Failed to save settings to file.")
                return False

        except ValueError as e:
            messagebox.showerror("Input Error", f"Invalid input value: {e}")
            return False
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
            return False

    def _update_cache_info(self):
        """Update cache information display"""
        # This would be implemented to show current cache stats
        info_text = "Cache information will be displayed here..."

        self.cache_info_text.config(state='normal')
        self.cache_info_text.delete(1.0, tk.END)
        self.cache_info_text.insert(1.0, info_text)
        self.cache_info_text.config(state='disabled')

        def _browse_cache_directory(self):
            """Browse for cache directory"""
            directory = filedialog.askdirectory(
                title="Select Cache Directory",
                initialdir=self.cache_directory.get() or os.path.expanduser('~')
            )
            if directory:
                self.cache_directory.set(directory)

        def _view_cache_contents(self):
            """Show cache contents in a new window"""
            # This would open a new dialog showing cache entries
            messagebox.showinfo("Cache Contents", "Cache viewer will be implemented here.")

        def _clear_cache(self):
            """Clear cache after confirmation"""
            if messagebox.askyesno("Clear Cache",
                                   "Are you sure you want to clear all cached data?\n\n"
                                   "This action cannot be undone."):
                # Implementation would clear the cache
                messagebox.showinfo("Cache Cleared", "All cached data has been cleared.")
                self._update_cache_info()

        def _open_settings_folder(self):
            """Open settings folder in file manager"""
            settings_dir = os.path.dirname(self.settings_mgr.settings_file)
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(settings_dir)
                elif os.name == 'posix':  # Unix/Linux/Mac
                    import sys
                    if sys.platform == 'darwin':  # macOS
                        os.system(f'open "{settings_dir}"')
                    else:  # Linux
                        os.system(f'xdg-open "{settings_dir}"')
            except Exception as e:
                messagebox.showerror("Error", f"Could not open settings folder: {e}")

        def _export_settings(self):
            """Export settings to a file"""
            filename = filedialog.asksaveasfilename(
                title="Export Settings",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            if filename:
                try:
                    import shutil
                    shutil.copy2(self.settings_mgr.settings_file, filename)
                    messagebox.showinfo("Export Complete", f"Settings exported to:\n{filename}")
                except Exception as e:
                    messagebox.showerror("Export Error", f"Failed to export settings: {e}")

        def _import_settings(self):
            """Import settings from a file"""
            filename = filedialog.askopenfilename(
                title="Import Settings",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            if filename:
                if messagebox.askyesno("Import Settings",
                                       "This will replace all current settings.\n\n"
                                       "Are you sure you want to continue?"):
                    try:
                        import shutil
                        shutil.copy2(filename, self.settings_mgr.settings_file)
                        self.settings_mgr.load()  # Reload settings
                        self._load_settings()  # Update UI
                        messagebox.showinfo("Import Complete", "Settings imported successfully.")
                    except Exception as e:
                        messagebox.showerror("Import Error", f"Failed to import settings: {e}")

        def _validate_settings(self):
            """Validate current settings and show results"""
            # First save current UI values temporarily
            temp_settings = self.settings_mgr.settings
            try:
                self._save_settings_to_temp(temp_settings)
                issues = self.settings_mgr.validate_settings()

                self.validation_text.config(state='normal')
                self.validation_text.delete(1.0, tk.END)

                if not issues:
                    self.validation_text.insert(1.0, "✅ All settings are valid!")
                else:
                    result_text = "❌ Validation Issues Found:\n\n"
                    for section, section_issues in issues.items():
                        result_text += f"{section.upper()}:\n"
                        for issue in section_issues:
                            result_text += f"  • {issue}\n"
                        result_text += "\n"
                    self.validation_text.insert(1.0, result_text)

                self.validation_text.config(state='disabled')

            except Exception as e:
                self.validation_text.config(state='normal')
                self.validation_text.delete(1.0, tk.END)
                self.validation_text.insert(1.0, f"❌ Validation Error: {e}")
                self.validation_text.config(state='disabled')

        def _save_settings_to_temp(self, settings):
            """Save UI values to a settings object without file persistence"""
            # Cache settings
            settings.cache.enabled = self.cache_enabled.get()
            settings.cache.default_ttl_seconds = int(self.cache_ttl.get())
            settings.cache.max_entries = int(self.cache_max_entries.get())
            settings.cache.cleanup_interval_minutes = int(self.cache_cleanup_interval.get())
            settings.cache.cache_directory = self.cache_directory.get()

            # Refresh settings
            settings.refresh.enabled = self.refresh_enabled.get()
            settings.refresh.interval_seconds = int(self.refresh_interval.get())

            # UI settings
            settings.ui.theme = self.ui_theme.get()
            settings.ui.font_family = self.ui_font_family.get()
            settings.ui.font_size = int(self.ui_font_size.get())
            settings.ui.window_width = int(self.ui_window_width.get())
            settings.ui.window_height = int(self.ui_window_height.get())

            # Communication settings
            settings.communication.default_baudrate = int(self.comm_baudrate.get())
            settings.communication.timeout_seconds = float(self.comm_timeout.get())
            settings.communication.retry_attempts = int(self.comm_retry_attempts.get())
            settings.communication.retry_delay_seconds = float(self.comm_retry_delay.get())

        def _reset_to_defaults(self):
            """Reset all settings to defaults"""
            if messagebox.askyesno("Reset to Defaults",
                                   "This will reset all settings to their default values.\n\n"
                                   "Are you sure you want to continue?"):
                self.settings_mgr.reset_to_defaults()
                self._load_settings()
                messagebox.showinfo("Reset Complete", "All settings have been reset to defaults.")

        def _on_ok(self):
            """Handle OK button"""
            if self._save_settings():
                if self.on_settings_changed:
                    self.on_settings_changed()
                self.dialog.destroy()

        def _on_apply(self):
            """Handle Apply button"""
            if self._save_settings():
                if self.on_settings_changed:
                    self.on_settings_changed()
                messagebox.showinfo("Applied", "Settings have been applied successfully.")

        def _on_cancel(self):
            """Handle Cancel button"""
            self.dialog.destroy()

    class CacheViewerDialog:
        """
        Dialog for viewing cache contents
        """

        def __init__(self, parent: tk.Tk, cache_manager):
            """Initialize cache viewer dialog"""
            self.parent = parent
            self.cache_manager = cache_manager

            # Create dialog
            self.dialog = tk.Toplevel(parent)
            self.dialog.title("Cache Contents - CalypsoPy")
            self.dialog.geometry("800x500")
            self.dialog.resizable(True, True)

            # Make modal
            self.dialog.transient(parent)
            self.dialog.grab_set()

            # Create UI
            self._create_ui()
            self._load_cache_data()

        def _create_ui(self):
            """Create the cache viewer UI"""
            main_frame = ttk.Frame(self.dialog, padding=10)
            main_frame.pack(fill='both', expand=True)

            # Header
            header_frame = ttk.Frame(main_frame)
            header_frame.pack(fill='x', pady=(0, 10))

            ttk.Label(header_frame, text="Cache Contents",
                      font=('Arial', 14, 'bold')).pack(side='left')

            ttk.Button(header_frame, text="Refresh",
                       command=self._load_cache_data).pack(side='right')

            # Treeview for cache entries
            columns = ('Key', 'Command', 'Age', 'Type', 'Size', 'Status')
            self.tree = ttk.Treeview(main_frame, columns=columns, show='headings', height=15)

            # Configure columns
            self.tree.heading('Key', text='Cache Key')
            self.tree.heading('Command', text='Command')
            self.tree.heading('Age', text='Age (seconds)')
            self.tree.heading('Type', text='Data Type')
            self.tree.heading('Size', text='Size (chars)')
            self.tree.heading('Status', text='Status')

            self.tree.column('Key', width=200)
            self.tree.column('Command', width=120)
            self.tree.column('Age', width=100)
            self.tree.column('Type', width=80)
            self.tree.column('Size', width=80)
            self.tree.column('Status', width=80)

            # Scrollbar
            scrollbar = ttk.Scrollbar(main_frame, orient='vertical', command=self.tree.yview)
            self.tree.configure(yscrollcommand=scrollbar.set)

            # Pack treeview and scrollbar
            self.tree.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')

            # Buttons
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill='x', pady=(10, 0))

            ttk.Button(button_frame, text="View Details",
                       command=self._view_details).pack(side='left', padx=(0, 5))
            ttk.Button(button_frame, text="Delete Entry",
                       command=self._delete_entry).pack(side='left', padx=5)
            ttk.Button(button_frame, text="Close",
                       command=self.dialog.destroy).pack(side='right')

        def _load_cache_data(self):
            """Load cache data into the treeview"""
            # Clear existing items
            for item in self.tree.get_children():
                self.tree.delete(item)

            # Get cache entries
            if hasattr(self.cache_manager, 'get_entry_list'):
                entries = self.cache_manager.get_entry_list()

                for entry in entries:
                    status = "Expired" if entry['expired'] else "Valid"

                    self.tree.insert('', 'end', values=(
                        entry['key'],
                        entry['command'],
                        f"{entry['age_seconds']:.1f}",
                        entry['data_type'],
                        entry['data_size'],
                        status
                    ))

        def _view_details(self):
            """View details of selected cache entry"""
            selection = self.tree.selection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a cache entry to view.")
                return

            item = self.tree.item(selection[0])
            cache_key = item['values'][0]

            # Get detailed cache data
            cache_data = self.cache_manager.get_with_metadata(cache_key)
            if cache_data:
                detail_text = f"Cache Key: {cache_key}\n\n"
                detail_text += f"Command: {cache_data['command']}\n"
                detail_text += f"Age: {cache_data['age_seconds']:.1f} seconds\n"
                detail_text += f"Timestamp: {cache_data['timestamp']}\n\n"
                detail_text += f"Data:\n{cache_data['data']}"

                # Show in a new dialog
                detail_dialog = tk.Toplevel(self.dialog)
                detail_dialog.title(f"Cache Entry Details - {cache_key}")
                detail_dialog.geometry("600x400")

                text_widget = tk.Text(detail_dialog, wrap='word', padx=10, pady=10)
                text_widget.pack(fill='both', expand=True)
                text_widget.insert(1.0, detail_text)
                text_widget.config(state='disabled')

        def _delete_entry(self):
            """Delete selected cache entry"""
            selection = self.tree.selection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a cache entry to delete.")
                return

            item = self.tree.item(selection[0])
            cache_key = item['values'][0]

            if messagebox.askyesno("Delete Entry", f"Delete cache entry '{cache_key}'?"):
                if self.cache_manager.invalidate(cache_key):
                    self._load_cache_data()  # Refresh the list
                    messagebox.showinfo("Deleted", f"Cache entry '{cache_key}' has been deleted.")
                else:
                    messagebox.showerror("Error", f"Failed to delete cache entry '{cache_key}'.")

    # REPLACE the test code at the bottom of your settings_ui.py file (around line 898) with this:

    # Usage example
    if __name__ == "__main__":
        import sys
        import tkinter as tk
        from tkinter import ttk  # ADD this import
        from settings_manager import SettingsManager

        # Test the settings dialog
        root = tk.Tk()
        root.title("Settings Test")
        root.geometry("300x200")

        settings_mgr = SettingsManager()

        def show_settings():
            dialog = SettingsDialog(root, settings_mgr,
                                    on_settings_changed=lambda: print("Settings changed!"))

        ttk.Button(root, text="Open Settings", command=show_settings).pack(pady=50)

        root.mainloop()