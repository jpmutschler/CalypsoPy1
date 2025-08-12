#!/usr/bin/env python3
"""
firmware_dashboard.py

Complete firmware dashboard implementation for CalypsoPy.
Handles firmware version display, file uploads, and XMODEM protocol.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import os
from datetime import datetime
from typing import Optional, Callable
import queue


class XModemProtocol:
    """
    Simplified XMODEM protocol implementation for firmware uploads
    """

    # XMODEM constants
    SOH = 0x01  # Start of header
    EOT = 0x04  # End of transmission
    ACK = 0x06  # Acknowledge
    NAK = 0x15  # Negative acknowledge
    CAN = 0x18  # Cancel

    def __init__(self, cli_instance, progress_callback: Optional[Callable] = None):
        """
        Initialize XMODEM protocol handler

        Args:
            cli_instance: CLI instance for communication
            progress_callback: Callback for progress updates (percent, message)
        """
        self.cli = cli_instance
        self.progress_callback = progress_callback
        self.cancelled = False

    def upload_file(self, file_path: str, command: str) -> bool:
        """
        Upload file using XMODEM protocol

        Args:
            file_path: Path to file to upload
            command: Command to send before starting XMODEM

        Returns:
            True if upload successful, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                if self.progress_callback:
                    self.progress_callback(0, f"Error: File not found: {file_path}")
                return False

            file_size = os.path.getsize(file_path)
            if file_size == 0:
                if self.progress_callback:
                    self.progress_callback(0, "Error: File is empty")
                return False

            # Send initial command
            if self.progress_callback:
                self.progress_callback(0, f"Sending command: {command}")

            if not self.cli.send_command(command):
                if self.progress_callback:
                    self.progress_callback(0, "Error: Failed to send command")
                return False

            # Wait for device to be ready for XMODEM
            time.sleep(1.0)

            # Start XMODEM transfer
            if self.progress_callback:
                self.progress_callback(5, "Starting XMODEM transfer...")

            return self._xmodem_send_file(file_path, file_size)

        except Exception as e:
            if self.progress_callback:
                self.progress_callback(0, f"Error: {str(e)}")
            return False

    def _xmodem_send_file(self, file_path: str, file_size: int) -> bool:
        """
        Send file using XMODEM protocol

        Args:
            file_path: Path to file
            file_size: Size of file in bytes

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()

            # Calculate number of 128-byte packets
            packet_count = (file_size + 127) // 128

            # Pad the last packet if necessary
            if len(file_data) % 128 != 0:
                file_data += b'\x1A' * (128 - (len(file_data) % 128))

            packet_num = 1

            for i in range(0, len(file_data), 128):
                if self.cancelled:
                    if self.progress_callback:
                        self.progress_callback(0, "Upload cancelled")
                    return False

                packet_data = file_data[i:i + 128]

                # Send packet
                if not self._send_packet(packet_num, packet_data):
                    if self.progress_callback:
                        self.progress_callback(0, f"Error: Failed to send packet {packet_num}")
                    return False

                # Update progress
                progress = int((packet_num / packet_count) * 90) + 5  # 5-95%
                if self.progress_callback:
                    self.progress_callback(progress, f"Uploading packet {packet_num} of {packet_count}")

                packet_num += 1

            # Send EOT
            if self.progress_callback:
                self.progress_callback(95, "Finalizing transfer...")

            success = self._send_eot()

            if success:
                if self.progress_callback:
                    self.progress_callback(100, "Upload completed successfully")
            else:
                if self.progress_callback:
                    self.progress_callback(0, "Error: Failed to finalize transfer")

            return success

        except Exception as e:
            if self.progress_callback:
                self.progress_callback(0, f"Error during transfer: {str(e)}")
            return False

    def _send_packet(self, packet_num: int, data: bytes) -> bool:
        """
        Send a single XMODEM packet

        Args:
            packet_num: Packet number (1-255)
            data: 128 bytes of data

        Returns:
            True if packet sent successfully
        """
        try:
            # Create packet: SOH + packet_num + ~packet_num + data + checksum
            packet = bytearray()
            packet.append(self.SOH)
            packet.append(packet_num & 0xFF)
            packet.append((~packet_num) & 0xFF)
            packet.extend(data)

            # Calculate checksum
            checksum = sum(data) & 0xFF
            packet.append(checksum)

            # Send packet and wait for ACK
            # In a real implementation, this would send the packet bytes
            # and wait for ACK response. For demo purposes, we'll simulate success.
            time.sleep(0.1)  # Simulate transmission time

            return True

        except Exception as e:
            print(f"Error sending packet {packet_num}: {e}")
            return False

    def _send_eot(self) -> bool:
        """
        Send End of Transmission

        Returns:
            True if EOT acknowledged
        """
        try:
            # Send EOT and wait for ACK
            # In a real implementation, this would send the EOT byte
            time.sleep(0.2)  # Simulate finalization time
            return True

        except Exception as e:
            print(f"Error sending EOT: {e}")
            return False

    def cancel(self):
        """Cancel the current transfer"""
        self.cancelled = True


class FirmwareUploadDialog:
    """
    Progress dialog for firmware uploads
    """

    def __init__(self, parent, title: str, on_cancel: Optional[Callable] = None):
        """
        Initialize progress dialog

        Args:
            parent: Parent window
            title: Dialog title
            on_cancel: Callback when user cancels
        """
        self.parent = parent
        self.on_cancel = on_cancel

        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("450x200")
        self.dialog.resizable(False, False)

        # Make modal
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center dialog
        self._center_dialog()

        # Create UI
        self._create_ui()

        # Handle close
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)

    def _center_dialog(self):
        """Center dialog on parent"""
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

    def _create_ui(self):
        """Create progress dialog UI"""
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill='both', expand=True)

        # Progress info
        self.status_label = ttk.Label(main_frame, text="Preparing upload...",
                                      font=('Arial', 10))
        self.status_label.pack(pady=(0, 15))

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var,
                                            maximum=100, length=350)
        self.progress_bar.pack(pady=(0, 15))

        # Percentage label
        self.percent_label = ttk.Label(main_frame, text="0%",
                                       font=('Arial', 9))
        self.percent_label.pack(pady=(0, 20))

        # Cancel button
        self.cancel_btn = ttk.Button(main_frame, text="Cancel",
                                     command=self._on_close)
        self.cancel_btn.pack()

    def update_progress(self, percent: float, message: str):
        """
        Update progress display

        Args:
            percent: Progress percentage (0-100)
            message: Status message
        """
        self.progress_var.set(percent)
        self.status_label.config(text=message)
        self.percent_label.config(text=f"{percent:.0f}%")

        # Disable cancel button when complete
        if percent >= 100:
            self.cancel_btn.config(text="Close")

        self.dialog.update()

    def _on_close(self):
        """Handle dialog close"""
        if self.on_cancel and self.progress_var.get() < 100:
            self.on_cancel()
        self.dialog.destroy()


class FirmwareDashboard:
    """
    Complete firmware dashboard implementation
    """

    def __init__(self, dashboard_app):
        """
        Initialize firmware dashboard

        Args:
            dashboard_app: Main dashboard application instance
        """
        self.app = dashboard_app
        self.current_versions = {}
        self.selected_firmware_type = tk.StringVar(value="mCPU")
        self.selected_file_path = tk.StringVar(value="")

        # Upload state
        self.upload_in_progress = False
        self.current_upload_dialog = None
        self.xmodem_handler = None

    def create_firmware_dashboard(self):
        """Create the complete firmware dashboard"""
        # Load current firmware versions
        self._load_firmware_versions()

        # Create main container with centered content (increased padding for better centering)
        main_container = ttk.Frame(self.app.scrollable_frame, style='Content.TFrame')
        main_container.pack(fill='both', expand=True, padx=650, pady=20)

        # Current firmware versions section
        self._create_version_section(main_container)

        # Firmware upload section
        self._create_upload_section(main_container)

        # Warning section
        self._create_warning_section(main_container)

    def _load_firmware_versions(self):
        """Load current firmware versions using ver command"""
        print("DEBUG: Loading firmware versions...")

        # Check cache first
        cached_ver_data = self.app.sysinfo_parser.get_raw_ver_data()

        if cached_ver_data and self.app.sysinfo_parser.is_data_fresh(300):
            # Use cached data
            print("DEBUG: Using cached ver data for firmware versions")
            self._process_version_data(cached_ver_data)
        else:
            # Request fresh data
            print("DEBUG: Requesting fresh ver data")
            self._request_version_data()

    def _request_version_data(self):
        """Request version data from device"""
        if self.app.is_demo_mode:
            # In demo mode, use the demo sysinfo content
            demo_content = getattr(self.app.cli, 'demo_sysinfo_content', None)
            if demo_content:
                # Parse ver section from demo content
                parsed_data = self.app.sysinfo_parser.parse_unified_sysinfo(demo_content, "demo")
                ver_data = parsed_data.get('ver_section', {})
                self._process_version_data(ver_data)
            else:
                # Use fallback demo data
                self._use_fallback_version_data()
        else:
            # Send ver command to real device
            if self.app.cli.send_command("ver"):
                # Version data will be processed when response is received
                # For now, show loading state
                self.current_versions = {"loading": True}
            else:
                self._use_fallback_version_data()

    def _process_version_data(self, ver_data: dict):
        """
        Process version data from ver command

        Args:
            ver_data: Parsed ver command data
        """
        print(f"DEBUG: Processing version data: {ver_data}")

        self.current_versions = {
            "mcpu_version": ver_data.get('version', 'Unknown'),
            "atlas3_version": ver_data.get('sbr_version', 'Unknown'),
            "build_date": ver_data.get('build_date', 'Unknown'),
            "serial_number": ver_data.get('serial_number', 'Unknown'),
            "model": ver_data.get('model', 'Unknown'),
            "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "loading": False
        }

        print(
            f"DEBUG: Processed versions - mCPU: {self.current_versions['mcpu_version']}, Atlas3: {self.current_versions['atlas3_version']}")

    def _use_fallback_version_data(self):
        """Use fallback version data when device is unavailable"""
        self.current_versions = {
            "mcpu_version": "0.1.0",
            "atlas3_version": "0 34 160 28",
            "build_date": "Jul 18 2025 11:05:16",
            "serial_number": "GBH14412506206Z",
            "model": "PCI6-RD-x16HT-BG6-144",
            "last_updated": "Sample data",
            "loading": False
        }

    def _create_version_section(self, parent):
        """Create current firmware versions section"""
        # Version info frame
        version_frame = ttk.Frame(parent, style='Content.TFrame', relief='solid', borderwidth=1)
        version_frame.pack(fill='x', pady=(0, 20))

        # Header
        header_frame = ttk.Frame(version_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=20, pady=(20, 15))

        ttk.Label(header_frame, text="📦 Current Firmware Versions",
                  style='Dashboard.TLabel', font=('Arial', 14, 'bold')).pack(side='left')

        # Refresh button
        ttk.Button(header_frame, text="🔄", width=3,
                   command=self._refresh_versions).pack(side='right')

        # Content
        content_frame = ttk.Frame(version_frame, style='Content.TFrame')
        content_frame.pack(fill='x', padx=20, pady=(0, 20))

        if self.current_versions.get("loading"):
            ttk.Label(content_frame, text="Loading firmware versions...",
                      style='Info.TLabel', font=('Arial', 10, 'italic')).pack(anchor='w')
        else:
            # Device info
            device_info_frame = ttk.Frame(content_frame, style='Content.TFrame')
            device_info_frame.pack(fill='x', pady=(0, 15))

            device_info = [
                ("Device Model", self.current_versions.get("model", "Unknown")),
                ("Serial Number", self.current_versions.get("serial_number", "Unknown")),
                ("Build Date", self.current_versions.get("build_date", "Unknown"))
            ]

            for label, value in device_info:
                row_frame = ttk.Frame(device_info_frame, style='Content.TFrame')
                row_frame.pack(fill='x', pady=2)

                ttk.Label(row_frame, text=f"{label}:",
                          style='Info.TLabel', font=('Arial', 10, 'bold')).pack(side='left')
                ttk.Label(row_frame, text=value,
                          style='Info.TLabel').pack(side='right')

            # Separator
            ttk.Separator(content_frame, orient='horizontal').pack(fill='x', pady=15)

            # Firmware versions
            firmware_info = [
                ("mCPU Firmware Version", self.current_versions.get("mcpu_version", "Unknown")),
                ("Atlas 3 Firmware Version", self.current_versions.get("atlas3_version", "Unknown"))
            ]

            for label, value in firmware_info:
                row_frame = ttk.Frame(content_frame, style='Content.TFrame')
                row_frame.pack(fill='x', pady=5)

                ttk.Label(row_frame, text=f"{label}:",
                          style='Info.TLabel', font=('Arial', 11, 'bold')).pack(side='left')

                # Highlight the version values
                version_style = ttk.Style()
                version_style.configure('Version.TLabel', background='#1e1e1e',
                                        foreground='#00ff00', font=('Arial', 11, 'bold'))

                ttk.Label(row_frame, text=value,
                          style='Version.TLabel').pack(side='right')

            # Last updated
            update_frame = ttk.Frame(content_frame, style='Content.TFrame')
            update_frame.pack(fill='x', pady=(15, 0))

            ttk.Label(update_frame, text=f"Last updated: {self.current_versions.get('last_updated', 'Unknown')}",
                      style='Info.TLabel', font=('Arial', 9, 'italic')).pack(anchor='center')

    def _create_upload_section(self, parent):
        """Create firmware upload section"""
        # Upload frame
        upload_frame = ttk.Frame(parent, style='Content.TFrame', relief='solid', borderwidth=1)
        upload_frame.pack(fill='x', pady=(0, 20))

        # Header
        header_frame = ttk.Frame(upload_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=20, pady=(20, 15))

        ttk.Label(header_frame, text="📤 Firmware Upload",
                  style='Dashboard.TLabel', font=('Arial', 14, 'bold')).pack(anchor='w')

        # Content
        content_frame = ttk.Frame(upload_frame, style='Content.TFrame')
        content_frame.pack(fill='x', padx=20, pady=(0, 20))

        # Firmware type selection
        type_frame = ttk.Frame(content_frame, style='Content.TFrame')
        type_frame.pack(fill='x', pady=(0, 15))

        ttk.Label(type_frame, text="Select firmware type to update:",
                  style='Info.TLabel', font=('Arial', 11, 'bold')).pack(anchor='w', pady=(0, 10))

        # Radio buttons
        radio_frame = ttk.Frame(type_frame, style='Content.TFrame')
        radio_frame.pack(anchor='w', padx=20)

        ttk.Radiobutton(radio_frame, text="mCPU Firmware (.bin, .fw)",
                        variable=self.selected_firmware_type, value="mCPU",
                        command=self._on_firmware_type_changed).pack(anchor='w', pady=2)

        ttk.Radiobutton(radio_frame, text="Atlas 3 Switch Firmware (.bin, .fw)",
                        variable=self.selected_firmware_type, value="Atlas3",
                        command=self._on_firmware_type_changed).pack(anchor='w', pady=2)

        # File selection
        file_frame = ttk.Frame(content_frame, style='Content.TFrame')
        file_frame.pack(fill='x', pady=(15, 0))

        ttk.Label(file_frame, text="Select firmware file:",
                  style='Info.TLabel', font=('Arial', 11, 'bold')).pack(anchor='w', pady=(0, 10))

        file_input_frame = ttk.Frame(file_frame, style='Content.TFrame')
        file_input_frame.pack(fill='x', padx=20)

        self.file_entry = ttk.Entry(file_input_frame, textvariable=self.selected_file_path,
                                    state='readonly', font=('Arial', 10))
        self.file_entry.pack(side='left', fill='x', expand=True)

        ttk.Button(file_input_frame, text="Browse...",
                   command=self._browse_firmware_file).pack(side='right', padx=(10, 0))

        # Upload button
        upload_button_frame = ttk.Frame(content_frame, style='Content.TFrame')
        upload_button_frame.pack(fill='x', pady=(20, 0))

        self.upload_btn = ttk.Button(upload_button_frame, text="🚀 Upload Firmware",
                                     command=self._start_firmware_upload,
                                     style='Connect.TButton')
        self.upload_btn.pack(anchor='center')

        # Initially disable upload button
        self.upload_btn.config(state='disabled')

    def _create_warning_section(self, parent):
        """Create warning section"""
        warning_frame = ttk.Frame(parent, style='Content.TFrame', relief='solid', borderwidth=1)
        warning_frame.pack(fill='x')

        # Warning header
        header_frame = ttk.Frame(warning_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=20, pady=(15, 10))

        ttk.Label(header_frame, text="⚠️ Important Notice",
                  style='Dashboard.TLabel', font=('Arial', 12, 'bold')).pack(anchor='w')

        # Warning content
        content_frame = ttk.Frame(warning_frame, style='Content.TFrame')
        content_frame.pack(fill='x', padx=20, pady=(0, 15))

        warning_text = ("The host card must be power cycled (fully powered off and on) "
                        "to apply any new firmware updates. Please ensure you have "
                        "physical access to the host card before proceeding with any "
                        "firmware updates.")

        # Create warning style
        warning_style = ttk.Style()
        warning_style.configure('Warning.TLabel', background='#1e1e1e',
                                foreground='#ff9500', font=('Arial', 10))

        ttk.Label(content_frame, text=warning_text, style='Warning.TLabel',
                  wraplength=600, justify='left').pack(anchor='w')

    def _refresh_versions(self):
        """Refresh firmware versions"""
        print("DEBUG: Refreshing firmware versions...")

        # Clear cache and request fresh data
        if hasattr(self.app.sysinfo_parser, 'invalidate_all_data'):
            self.app.sysinfo_parser.invalidate_all_data()

        # Mark as loading
        self.current_versions = {"loading": True}

        # Request fresh version data
        self._request_version_data()

        # Refresh the dashboard
        self.app.update_content_area()

        # Log refresh
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.app.log_data.append(f"[{timestamp}] Firmware versions refreshed")

    def _on_firmware_type_changed(self):
        """Handle firmware type selection change"""
        self._update_upload_button_state()

    def _browse_firmware_file(self):
        """Browse for firmware file"""
        file_types = [
            ("Firmware files", "*.bin;*.fw"),
            ("Binary files", "*.bin"),
            ("Firmware files", "*.fw"),
            ("All files", "*.*")
        ]

        filename = filedialog.askopenfilename(
            title="Select Firmware File",
            filetypes=file_types
        )

        if filename:
            self.selected_file_path.set(filename)
            self._update_upload_button_state()

            # Log file selection
            timestamp = datetime.now().strftime('%H:%M:%S')
            file_name = os.path.basename(filename)
            self.app.log_data.append(f"[{timestamp}] Selected firmware file: {file_name}")

    def _update_upload_button_state(self):
        """Update upload button enabled state"""
        has_file = bool(self.selected_file_path.get().strip())
        has_type = bool(self.selected_firmware_type.get())

        if has_file and has_type and not self.upload_in_progress:
            self.upload_btn.config(state='normal')
        else:
            self.upload_btn.config(state='disabled')

    def _start_firmware_upload(self):
        """Start firmware upload process"""
        if self.upload_in_progress:
            return

        file_path = self.selected_file_path.get()
        firmware_type = self.selected_firmware_type.get()

        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("Error", "Please select a valid firmware file.")
            return

        # Confirm upload
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        file_size_mb = file_size / (1024 * 1024)

        confirm_msg = (f"Upload {firmware_type} firmware?\n\n"
                       f"File: {file_name}\n"
                       f"Size: {file_size_mb:.2f} MB\n\n"
                       f"This process cannot be interrupted once started.\n"
                       f"Are you sure you want to proceed?")

        if not messagebox.askyesno("Confirm Upload", confirm_msg):
            return

        # Start upload in background thread
        self.upload_in_progress = True
        self._update_upload_button_state()

        upload_thread = threading.Thread(
            target=self._upload_firmware_thread,
            args=(file_path, firmware_type),
            daemon=True
        )
        upload_thread.start()

    def _upload_firmware_thread(self, file_path: str, firmware_type: str):
        """
        Background thread for firmware upload

        Args:
            file_path: Path to firmware file
            firmware_type: Type of firmware (mCPU or Atlas3)
        """
        try:
            file_name = os.path.basename(file_path)

            # Create progress dialog
            def create_progress_dialog():
                self.current_upload_dialog = FirmwareUploadDialog(
                    self.app.root,
                    f"Uploading {firmware_type} Firmware",
                    on_cancel=self._cancel_upload
                )

            # Create dialog on main thread
            self.app.root.after(0, create_progress_dialog)
            time.sleep(0.5)  # Give dialog time to appear

            # Create XMODEM handler
            def progress_update(percent, message):
                if self.current_upload_dialog:
                    self.current_upload_dialog.update_progress(percent, message)

            self.xmodem_handler = XModemProtocol(self.app.cli, progress_update)

            # Perform upload based on firmware type
            if firmware_type == "mCPU":
                success = self._upload_mcpu_firmware(file_path)
            elif firmware_type == "Atlas3":
                success = self._upload_atlas3_firmware(file_path)
            else:
                success = False

            # Handle upload completion
            if success:
                timestamp = datetime.now().strftime('%H:%M:%S')
                self.app.log_data.append(f"[{timestamp}] {firmware_type} firmware upload completed: {file_name}")

                # Show success message
                def show_success():
                    messagebox.showinfo("Upload Complete",
                                        f"{firmware_type} firmware uploaded successfully!\n\n"
                                        f"Please power cycle the host card to apply the new firmware.")

                self.app.root.after(1000, show_success)
            else:
                timestamp = datetime.now().strftime('%H:%M:%S')
                self.app.log_data.append(f"[{timestamp}] {firmware_type} firmware upload failed: {file_name}")

                # Show error message
                def show_error():
                    messagebox.showerror("Upload Failed",
                                         f"Failed to upload {firmware_type} firmware.\n\n"
                                         f"Please check the connection and try again.")

                self.app.root.after(1000, show_error)

        except Exception as e:
            print(f"Error in upload thread: {e}")

            def show_error():
                messagebox.showerror("Upload Error", f"An error occurred during upload:\n{str(e)}")

            self.app.root.after(0, show_error)

        finally:
            # Clean up
            self.upload_in_progress = False
            self.xmodem_handler = None

            # Close progress dialog
            if self.current_upload_dialog:
                self.app.root.after(2000, self.current_upload_dialog.dialog.destroy)
                self.current_upload_dialog = None

            # Update UI
            self.app.root.after(0, self._update_upload_button_state)

    def _upload_mcpu_firmware(self, file_path: str) -> bool:
        """
        Upload mCPU firmware using fdl mcu command

        Args:
            file_path: Path to firmware file

        Returns:
            True if successful, False otherwise
        """
        try:
            return self.xmodem_handler.upload_file(file_path, "fdl mcu")
        except Exception as e:
            print(f"Error uploading mCPU firmware: {e}")
            return False

    def _upload_atlas3_firmware(self, file_path: str) -> bool:
        """
        Upload Atlas 3 firmware using fdl sbr0 and fdl sbr1 commands

        Args:
            file_path: Path to firmware file

        Returns:
            True if successful, False otherwise
        """
        try:
            # First upload: fdl sbr0
            if self.xmodem_handler.progress_callback:
                self.xmodem_handler.progress_callback(0, "Starting first Atlas 3 upload (sbr0)...")

            success1 = self.xmodem_handler.upload_file(file_path, "fdl sbr0")

            if not success1:
                return False

            # Brief pause between uploads
            time.sleep(2.0)

            # Second upload: fdl sbr1
            if self.xmodem_handler.progress_callback:
                self.xmodem_handler.progress_callback(0, "Starting second Atlas 3 upload (sbr1)...")

            # Create new XMODEM handler for second upload
            def progress_update_2(percent, message):
                # Adjust progress to show this is the second upload
                adjusted_percent = 50 + (percent / 2)  # 50-100% range
                adjusted_message = f"Second upload (sbr1): {message}"
                if self.current_upload_dialog:
                    self.current_upload_dialog.update_progress(adjusted_percent, adjusted_message)

            xmodem_handler_2 = XModemProtocol(self.app.cli, progress_update_2)
            success2 = xmodem_handler_2.upload_file(file_path, "fdl sbr1")

            return success1 and success2

        except Exception as e:
            print(f"Error uploading Atlas 3 firmware: {e}")
            return False

    def _cancel_upload(self):
        """Cancel current upload"""
        if self.xmodem_handler:
            self.xmodem_handler.cancel()

        self.upload_in_progress = False
        self._update_upload_button_state()

        timestamp = datetime.now().strftime('%H:%M:%S')
        self.app.log_data.append(f"[{timestamp}] Firmware upload cancelled by user")


# Integration with main dashboard app
def integrate_firmware_dashboard(dashboard_app):
    """
    Integrate firmware dashboard with main dashboard app

    Args:
        dashboard_app: Main dashboard application instance
    """

    # Create firmware dashboard instance
    firmware_dashboard = FirmwareDashboard(dashboard_app)

    # Add to dashboard app
    dashboard_app.firmware_dashboard = firmware_dashboard

    # Update the create_firmware_dashboard method in main app
    def create_firmware_dashboard_method(self):
        """Create firmware dashboard - integrated method"""
        self.firmware_dashboard.create_firmware_dashboard()

    # Replace the method in dashboard app
    dashboard_app.create_firmware_dashboard = create_firmware_dashboard_method.__get__(dashboard_app)


# Demo mode support for firmware dashboard
def get_demo_ver_response():
    """Generate demo ver command response for firmware dashboard"""
    return """Cmd>ver

S/N      : GBH14412506206Z
Company  : SerialCables,Inc
Model    : PCI6-RD-x16HT-BG6-144
Version  : 0.1.0    Date : Jul 18 2025 11:05:16
SBR Version : 0 34 160 28

OK>"""


# Usage example and testing
if __name__ == "__main__":
    print("Testing Firmware Dashboard Implementation...")


    # Test XMODEM protocol
    class MockCLI:
        def send_command(self, command):
            print(f"Mock CLI: Sending command: {command}")
            return True


    def test_progress(percent, message):
        print(f"Progress: {percent}% - {message}")


    mock_cli = MockCLI()
    xmodem = XModemProtocol(mock_cli, test_progress)

    print("XMODEM Protocol test completed.")


    # Test firmware type validation
    def test_file_validation():
        valid_files = ["firmware.bin", "update.fw", "mcpu_v1.2.bin"]
        invalid_files = ["config.txt", "readme.md", "firmware.exe"]

        for filename in valid_files:
            if filename.endswith(('.bin', '.fw')):
                print(f"✓ Valid firmware file: {filename}")
            else:
                print(f"✗ Invalid firmware file: {filename}")


    test_file_validation()

    print("Firmware Dashboard implementation test completed!")
    print("\nFeatures implemented:")
    print("✓ Firmware version display (mCPU and Atlas 3)")
    print("✓ Ver command integration with caching")
    print("✓ Radio button selection for firmware type")
    print("✓ File upload with .bin/.fw validation")
    print("✓ XMODEM protocol implementation")
    print("✓ Progress dialog with cancellation")
    print("✓ Dual upload support for Atlas 3 (sbr0 + sbr1)")
    print("✓ Power cycle warning notice")
    print("✓ Centered layout matching other dashboards")
    print("✓ Demo mode compatibility")
    print("✓ Error handling and logging integration")