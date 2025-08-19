import re
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Optional, Any, List, Tuple

@dataclass
class HostCardInfo:
    """Data class to store parsed host card information from ver and lsd commands"""
    # Device Information (from ver command)
    serial_number: str = "Unknown"
    company: str = "Unknown"
    model: str = "Unknown"
    version: str = "Unknown"
    date: str = "Unknown"
    sbr_version: str = "Unknown"
    
    # Thermal Information (from lsd command)
    board_temperature: str = "Unknown"
    
    # Fan Information (from lsd command)
    switch_fan_speed: str = "Unknown"
    
    # Voltage Information (from lsd command)
    voltage_0_8v: str = "Unknown"
    voltage_0_89v: str = "Unknown"
    voltage_1_2v: str = "Unknown"
    voltage_1_5v: str = "Unknown"
    
    # Current Information (from lsd command)
    current_status: str = "Unknown"
    
    # Error Information (from lsd command)
    voltage_0_8v_error: str = "Unknown"
    voltage_0_89v_error: str = "Unknown"
    voltage_1_2v_error: str = "Unknown"
    voltage_1_5v_error: str = "Unknown"
    
    # Metadata
    last_updated: str = ""
    raw_ver_response: str = ""
    raw_lsd_response: str = ""
    
    def get_display_sections(self) -> List[Tuple[str, str, List[Tuple[str, str]]]]:
        """Get organized display sections with icons, titles, and data"""
        sections = []
        
        # Device Information Section
        device_info = [
            ("Serial Number", self.serial_number),
            ("Company", self.company),
            ("Model", self.model),
            ("Firmware Version", self.version),
            ("Build Date", self.date),
            ("SBR Version", self.sbr_version)
        ]
        sections.append(("💻", "Device Information", device_info))
        
        # Thermal Status Section
        thermal_info = [
            ("Board Temperature", f"{self.board_temperature}°C" if self.board_temperature != "Unknown" else "Unknown")
        ]
        sections.append(("🌡️", "Thermal Status", thermal_info))
        
        # Fan Status Section
        fan_info = [
            ("Switch Fan Speed", f"{self.switch_fan_speed} rpm" if self.switch_fan_speed != "Unknown" else "Unknown")
        ]
        sections.append(("🌀", "Fan Status", fan_info))
        
        # Power Status Section
        power_info = [
            ("0.8V Rail", f"{self.voltage_0_8v} mV" if self.voltage_0_8v != "Unknown" else "Unknown"),
            ("0.89V Rail", f"{self.voltage_0_89v} mV" if self.voltage_0_89v != "Unknown" else "Unknown"),
            ("1.2V Rail", f"{self.voltage_1_2v} mV" if self.voltage_1_2v != "Unknown" else "Unknown"),
            ("1.5V Rail", f"{self.voltage_1_5v} mV" if self.voltage_1_5v != "Unknown" else "Unknown"),
            ("Current Draw", f"{self.current_status} mA" if self.current_status != "Unknown" else "Unknown")
        ]
        sections.append(("⚡", "Power Status", power_info))
        
        # Error Status Section
        error_info = [
            ("0.8V Rail Errors", self.voltage_0_8v_error),
            ("0.89V Rail Errors", self.voltage_0_89v_error),
            ("1.2V Rail Errors", self.voltage_1_2v_error),
            ("1.5V Rail Errors", self.voltage_1_5v_error)
        ]
        sections.append(("🚨", "Error Status", error_info))
        
        return sections

class HostCardInfoParser:
    """Parser for ver and lsd command responses"""
    
    def __init__(self):
        # Patterns for ver command parsing
        self.ver_patterns = {
            'serial_number': [
                r's/n\s*:\s*([A-Za-z0-9]+)',
                r'serial\s*(?:number)?[:\s]+([A-Za-z0-9\-]+)',
                r's/n[:\s]+([A-Za-z0-9]+)'
            ],
            'company': [
                r'company\s*:\s*(.+?)(?:\n|$)',
                r'manufacturer[:\s]+(.+?)(?:\n|$)',
                r'vendor[:\s]+(.+?)(?:\n|$)'
            ],
            'model': [
                r'model\s*:\s*(.+?)(?:\n|$)',
                r'part\s*(?:number)?[:\s]+(.+?)(?:\n|$)'
            ],
            'version': [
                r'version\s*:\s*([\d\.]+)',
                r'fw\s*version[:\s]+([\d\.]+)',
                r'firmware[:\s]+([\d\.]+)'
            ],
            'date': [
                r'date\s*:\s*(.+?)(?:\n|$)',
                r'build\s*date[:\s]+(.+?)(?:\n|$)'
            ],
            'sbr_version': [
                r'sbr\s*version\s*:\s*([\d\s]+)',
                r'sbr[:\s]+([\d\s]+)'
            ]
        }
        
        # Patterns for lsd command parsing
        self.lsd_patterns = {
            'board_temperature': [
                r'board\s*temperature\s*:\s*(\d+)\s*degree',
                r'temperature[:\s]+(\d+)',
                r'temp[:\s]+(\d+)'
            ],
            'switch_fan_speed': [
                r'switch\s*fan\s*:\s*(\d+)\s*rpm',
                r'fan\s*speed[:\s]+(\d+)',
                r'fan[:\s]+(\d+)\s*rpm'
            ],
            'voltage_0_8v': [
                r'board\s*0\.8v\s*voltage\s*:\s*(\d+)\s*mv',
                r'0\.8v[:\s]+(\d+)',
                r'board.*?0\.8.*?(\d+).*?mv'
            ],
            'voltage_0_89v': [
                r'board\s*0\.89v\s*voltage\s*:\s*(\d+)\s*mv',
                r'0\.89v[:\s]+(\d+)',
                r'board.*?0\.89.*?(\d+).*?mv'
            ],
            'voltage_1_2v': [
                r'board\s*1\.2v\s*voltage\s*:\s*(\d+)\s*mv',
                r'1\.2v[:\s]+(\d+)',
                r'board.*?1\.2.*?(\d+).*?mv'
            ],
            'voltage_1_5v': [
                r'board\s*1\.5v\s*voltage\s*:\s*(\d+)\s*mv',
                r'1\.5v[:\s]+(\d+)',
                r'board.*?1\.5.*?(\d+).*?mv'
            ],
            'current_status': [
                r'current\s*:\s*(\d+)\s*ma',
                r'current[:\s]+(\d+)',
                r'draw[:\s]+(\d+)\s*ma'
            ],
            'voltage_0_8v_error': [
                r'voltage\s*0\.8v\s*error\s*:\s*(\d+)',
                r'0\.8v.*?error[:\s]+(\d+)'
            ],
            'voltage_0_89v_error': [
                r'voltage\s*0\.89v\s*error\s*:\s*(\d+)',
                r'0\.89v.*?error[:\s]+(\d+)'
            ],
            'voltage_1_2v_error': [
                r'voltage\s*1\.2v\s*error\s*:\s*(\d+)',
                r'1\.2v.*?error[:\s]+(\d+)'
            ],
            'voltage_1_5v_error': [
                r'voltage\s*1\.5v\s*error\s*:\s*(\d+)',
                r'1\.5v.*?error[:\s]+(\d+)'
            ]
        }
    
    def parse_responses(self, ver_response: str, lsd_response: str) -> HostCardInfo:
        """Parse both ver and lsd command responses"""
        info = HostCardInfo()
        info.raw_ver_response = ver_response
        info.raw_lsd_response = lsd_response
        info.last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Parse ver command response
        ver_lower = ver_response.lower()
        for field_name, patterns in self.ver_patterns.items():
            value = self._extract_field(ver_lower, patterns)
            if value:
                setattr(info, field_name, value.strip())
        
        # Parse lsd command response
        lsd_lower = lsd_response.lower()
        for field_name, patterns in self.lsd_patterns.items():
            value = self._extract_field(lsd_lower, patterns)
            if value:
                setattr(info, field_name, value.strip())
        
        # Post-process extracted data
        self._post_process_info(info)
        
        return info
    
    def _extract_field(self, text: str, patterns: List[str]) -> Optional[str]:
        """Try multiple regex patterns to extract a field value"""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        return None
    
    def _post_process_info(self, info: HostCardInfo) -> None:
        """Post-process and clean up extracted information"""
        # Clean up serial number
        if info.serial_number and info.serial_number != "Unknown":
            info.serial_number = re.sub(r'[^\w\-]', '', info.serial_number)
        
        # Clean up company name
        if info.company and info.company != "Unknown":
            info.company = info.company.replace(',', '').strip()
        
        # Format date if available
        if info.date and info.date != "Unknown":
            try:
                if len(info.date) > 10:
                    info.date = info.date[:19].strip()  # Take date and time
            except:
                pass
        
        # Clean up SBR version
        if info.sbr_version and info.sbr_version != "Unknown":
            info.sbr_version = re.sub(r'\s+', ' ', info.sbr_version).strip()

class HostCardInfoManager:
    """Manager class for handling host card information requests with dual commands"""
    
    def __init__(self, cli_instance):
        """Initialize with CLI instance"""
        self.cli = cli_instance
        self.parser = HostCardInfoParser()
        self.cached_info: Optional[HostCardInfo] = None
        self.last_refresh: Optional[datetime] = None
        self.refresh_interval = 30  # seconds
        self._lock = threading.Lock()
    
    def get_host_card_info(self, force_refresh: bool = False) -> HostCardInfo:
        """Get host card information using both ver and lsd commands"""
        with self._lock:
            needs_refresh = (
                force_refresh or 
                self.cached_info is None or 
                self.last_refresh is None or
                (datetime.now() - self.last_refresh).seconds > self.refresh_interval
            )
            
            if needs_refresh:
                self._refresh_info()
            
            return self.cached_info or HostCardInfo()
    
    def _refresh_info(self) -> None:
        """Send both ver and lsd commands and parse responses"""
        try:
            # Send ver command
            ver_success = self.cli.send_command("ver")
            if not ver_success:
                self.cached_info = self._get_error_info("Failed to send ver command")
                return
            
            # Wait for ver response
            ver_response = self._wait_for_response("ver", timeout=5.0)
            
            # Send lsd command
            lsd_success = self.cli.send_command("lsd")
            if not lsd_success:
                self.cached_info = self._get_error_info("Failed to send lsd command")
                return
            
            # Wait for lsd response
            lsd_response = self._wait_for_response("lsd", timeout=5.0)
            
            if ver_response or lsd_response:
                # Parse both responses
                self.cached_info = self.parser.parse_responses(
                    ver_response or "", 
                    lsd_response or ""
                )
                self.last_refresh = datetime.now()
            else:
                self.cached_info = self._get_error_info("No response received from ver/lsd commands")
                
        except Exception as e:
            self.cached_info = self._get_error_info(f"Error getting host card info: {str(e)}")
    
    def _wait_for_response(self, command: str, timeout: float = 5.0) -> Optional[str]:
        """Wait for command response"""
        start_time = time.time()
        response_parts = []
        
        while (time.time() - start_time) < timeout:
            response = self.cli.read_response()
            if response:
                response_parts.append(response)
                if self._is_response_complete(command, response_parts):
                    return '\n'.join(response_parts)
            time.sleep(0.1)
        
        return '\n'.join(response_parts) if response_parts else None
    
    def _is_response_complete(self, command: str, response_parts: List[str]) -> bool:
        """Check if command response appears complete"""
        if not response_parts:
            return False
        
        full_response = '\n'.join(response_parts).lower()
        
        # Command-specific completion checks
        if command == "ver":
            if "sbr version" in full_response or "date :" in full_response:
                return True
        elif command == "lsd":
            if "error :" in full_response and len(response_parts) > 10:
                return True
        
        # General completion indicators
        completion_indicators = ['ok>', 'cmd>', '# ', 'end>']
        for indicator in completion_indicators:
            if indicator in full_response:
                return True
        
        if len(response_parts) > 5:
            last_line = response_parts[-1].strip().lower()
            if len(last_line) < 10 and ('>' in last_line or '#' in last_line):
                return True
        
        return False
    
    def _get_error_info(self, error_message: str) -> HostCardInfo:
        """Create HostCardInfo object for error conditions"""
        info = HostCardInfo()
        info.serial_number = f"Error: {error_message}"
        info.last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return info

class HostCardDashboardUI:
    """UI components for the Host Card Information dashboard"""
    
    def __init__(self, dashboard_app):
        """Initialize with reference to main dashboard app"""
        self.app = dashboard_app
        self.raw_output_expanded = False
        self.auto_refresh_var = tk.BooleanVar()

    def create_host_dashboard(self):
        """Create the complete host card information dashboard"""
        # Get real host card information from both commands
        host_info = self.app.host_card_manager.get_host_card_info()
        sections = host_info.get_display_sections()

        # Create each section with icons and organized data
        for icon, section_title, section_data in sections:
            self.create_host_info_section(icon, section_title, section_data)

        # Add refresh controls
        self.create_host_refresh_controls(host_info)

        # Add raw command output for debugging (collapsible)
        if self.app.is_demo_mode or (host_info.raw_ver_response or host_info.raw_lsd_response):
            self.create_raw_output_section(host_info)

    def create_host_info_section(self, icon, title, data_items):
        """Create a section with enhanced data validation"""
        # FIX: Use self.app.scrollable_frame instead of self.scrollable_frame
        section_frame = ttk.Frame(self.app.scrollable_frame, style='Content.TFrame',
                                  relief='solid', borderwidth=1)
        section_frame.pack(fill='x', pady=10)

        # Section header with icon
        header_frame = ttk.Frame(section_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=15, pady=(15, 10))

        header_label = ttk.Label(header_frame, text=f"{icon} {title}",
                                 style='Dashboard.TLabel', font=('Arial', 12, 'bold'))
        header_label.pack(anchor='w')

        # Section content
        content_frame = ttk.Frame(section_frame, style='Content.TFrame')
        content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        # Display data items with validation
        if data_items:
            items_displayed = 0
            for field_name, value in data_items:
                # Skip empty or "Unknown" values unless it's sample data
                if value and value != "Unknown":
                    self.create_data_row(content_frame, field_name, value)
                    items_displayed += 1

            # If no valid items were displayed, show a message
            if items_displayed == 0:
                no_data_label = ttk.Label(content_frame, text="No valid data available",
                                        style='Info.TLabel', font=('Arial', 10, 'italic'))
                no_data_label.pack(pady=10)
        else:
            # Show message when no data items
            no_data_label = ttk.Label(content_frame, text="No data available",
                                    style='Info.TLabel', font=('Arial', 10, 'italic'))
            no_data_label.pack(pady=10)

    def debug_cache_status(self):
        """Debug method to check cache status"""
        if self.cache_manager:
            stats = self.cache_manager.get_stats()
            print(f"DEBUG: Cache stats - Entries: {stats['valid_entries']}, Expired: {stats['expired_entries']}")

            entries = self.cache_manager.get_entry_list()
            for entry in entries:
                print(
                    f"DEBUG: Cache entry - Key: {entry['key']}, Age: {entry['age_seconds']:.1f}s, Expired: {entry['expired']}")

        # Check parsed data availability
        complete_data = self.sysinfo_parser.get_complete_sysinfo()
        if complete_data:
            print(f"DEBUG: Complete sysinfo data available with {len(complete_data)} keys")
        else:
            print("DEBUG: No complete sysinfo data in cache")

    def create_data_row(self, parent, field_name, value):
        """Create a data row with field name and value"""
        row_frame = ttk.Frame(parent, style='Content.TFrame')
        row_frame.pack(fill='x', pady=2)

        # Field name label
        field_label = ttk.Label(row_frame, text=f"{field_name}:",
                                style='Info.TLabel', font=('Arial', 10, 'bold'))
        field_label.pack(side='left')

        # Value label with color coding for certain values
        value_color = self._get_value_color(field_name, value)
        value_label = ttk.Label(row_frame, text=str(value),
                                style='Info.TLabel', font=('Arial', 10))
        value_label.pack(side='right')

        # Apply color if needed
        if value_color != '#cccccc':
            value_label.configure(foreground=value_color)

    def _get_value_color(self, field_name, value):
        """Get color for value based on field type and value"""
        # Temperature color coding
        if 'temperature' in field_name.lower():
            try:
                temp = float(re.sub(r'[^\d.]', '', str(value)))
                if temp > 70:
                    return '#ff4444'  # Red for high temp
                elif temp > 60:
                    return '#ff9500'  # Orange for medium temp
                else:
                    return '#00ff00'  # Green for normal temp
            except:
                return '#cccccc'

        # Error count color coding
        if 'error' in field_name.lower():
            try:
                error_count = int(re.sub(r'[^\d]', '', str(value)))
                if error_count > 0:
                    return '#ff4444'  # Red for errors
                else:
                    return '#00ff00'  # Green for no errors
            except:
                return '#cccccc'

        # Current draw color coding
        if 'current' in field_name.lower():
            try:
                current = float(re.sub(r'[^\d.]', '', str(value)))
                if current > 15000:
                    return '#ff9500'
                else:
                    return '#00ff00'
            except:
                return '#cccccc'

        return '#cccccc'  # Default color

    def create_host_refresh_controls(self, host_info):
        """Create refresh controls and status display"""
        controls_frame = ttk.Frame(self.app.scrollable_frame, style='Content.TFrame')
        controls_frame.pack(fill='x', pady=15)

        # Refresh button
        refresh_btn = ttk.Button(controls_frame, text="🔄 Refresh Device Info",
                                 command=self.refresh_host_info)
        refresh_btn.pack(side='left')

        # Auto-refresh toggle
        auto_refresh_check = ttk.Checkbutton(controls_frame,
                                             text="Auto-refresh (30s)",
                                             variable=self.auto_refresh_var)
        auto_refresh_check.pack(side='left', padx=(15, 0))

        # Last update time
        if host_info.last_updated:
            update_label = ttk.Label(controls_frame,
                                     text=f"Last updated: {host_info.last_updated}",
                                     style='Info.TLabel', font=('Arial', 9))
            update_label.pack(side='right')

    def create_raw_output_section(self, host_info):
        """Create collapsible raw output section for debugging"""
        # Create expandable frame
        raw_frame = ttk.Frame(self.app.scrollable_frame, style='Content.TFrame',
                              relief='solid', borderwidth=1)
        raw_frame.pack(fill='x', pady=20)

        # Header with expand/collapse button
        header_frame = ttk.Frame(raw_frame, style='Content.TFrame')
        header_frame.pack(fill='x', padx=15, pady=(15, 10))

        self.expand_btn = ttk.Button(header_frame,
                                     text="▼ Raw Command Output" if self.raw_output_expanded else "▶ Raw Command Output",
                                     command=lambda: self.toggle_raw_output(raw_frame))
        self.expand_btn.pack(side='left')

        # Content frame
        self.raw_content_frame = ttk.Frame(raw_frame, style='Content.TFrame')
        if self.raw_output_expanded:
            self.raw_content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

            # Show raw responses
            if host_info.raw_ver_response:
                self.create_raw_text_display(self.raw_content_frame, "Ver Command Output", host_info.raw_ver_response)

            if host_info.raw_lsd_response:
                self.create_raw_text_display(self.raw_content_frame, "LSD Command Output", host_info.raw_lsd_response)

    def toggle_raw_output(self, raw_frame):
        """Toggle raw output display"""
        self.raw_output_expanded = not self.raw_output_expanded
        self.expand_btn.config(text="▼ Raw Command Output" if self.raw_output_expanded else "▶ Raw Command Output")

        if self.raw_output_expanded:
            self.raw_content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))
        else:
            self.raw_content_frame.pack_forget()

    def create_raw_text_display(self, parent, title, text_content):
        """Create a text display for raw command output"""
        # Title
        title_label = ttk.Label(parent, text=title, style='Dashboard.TLabel', font=('Arial', 10, 'bold'))
        title_label.pack(anchor='w', pady=(10, 5))

        # Text area with scrollbar
        text_frame = ttk.Frame(parent)
        text_frame.pack(fill='both', expand=True, pady=(0, 10))

        text_widget = tk.Text(text_frame, height=8, wrap='word', font=('Consolas', 9))
        scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        text_widget.insert('1.0', text_content)
        text_widget.configure(state='disabled')  # Make read-only

        text_widget.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def populate_raw_content(self, host_info):
        """Populate the raw content frame with command outputs"""
        # Clear existing content
        for widget in self.raw_content_frame.winfo_children():
            widget.destroy()
        
        # Create notebook for tabbed raw output
        notebook = ttk.Notebook(self.raw_content_frame)
        notebook.pack(fill='both', expand=True)
        
        # Ver command tab
        if host_info.raw_ver_response:
            ver_frame = ttk.Frame(notebook, style='Content.TFrame')
            notebook.add(ver_frame, text="ver Command")
            
            ver_text = tk.Text(ver_frame, height=8, wrap='word',
                              bg='#2d2d2d', fg='#ffffff', 
                              font=('Consolas', 9),
                              relief='flat', borderwidth=0)
            
            ver_scrollbar = ttk.Scrollbar(ver_frame, orient='vertical', 
                                         command=ver_text.yview)
            ver_text.configure(yscrollcommand=ver_scrollbar.set)
            
            ver_text.insert('1.0', host_info.raw_ver_response)
            ver_text.config(state='disabled')
            
            ver_text.pack(side='left', fill='both', expand=True)
            ver_scrollbar.pack(side='right', fill='y')
        
        # LSD command tab
        if host_info.raw_lsd_response:
            lsd_frame = ttk.Frame(notebook, style='Content.TFrame')
            notebook.add(lsd_frame, text="lsd Command")
            
            lsd_text = tk.Text(lsd_frame, height=8, wrap='word',
                              bg='#2d2d2d', fg='#ffffff', 
                              font=('Consolas', 9),
                              relief='flat', borderwidth=0)
            
            lsd_scrollbar = ttk.Scrollbar(lsd_frame, orient='vertical', 
                                         command=lsd_text.yview)
            lsd_text.configure(yscrollcommand=lsd_scrollbar.set)
            
            lsd_text.insert('1.0', host_info.raw_lsd_response)
            lsd_text.config(state='disabled')
            
            lsd_text.pack(side='left', fill='both', expand=True)
            lsd_scrollbar.pack(side='right', fill='y')
        
        # If no raw data, show message
        if not host_info.raw_ver_response and not host_info.raw_lsd_response:
            no_data_label = ttk.Label(self.raw_content_frame, 
                                    text="No raw command output available", 
                                    style='Info.TLabel', 
                                    font=('Arial', 10, 'italic'))
            no_data_label.pack(pady=20)
    
    def refresh_host_info(self):
        """Refresh host card information"""
        try:
            # Force refresh
            self.app.host_card_manager.get_host_card_info(force_refresh=True)
            # Refresh the display
            self.app.update_content_area()
        except Exception as e:
            print(f"ERROR: Failed to refresh host info: {e}")

# Demo mode support functions
def get_demo_ver_response(device_state):
    """Generate demo ver command response"""
    return f"""Cmd>ver

S/N      : {device_state['serial_number']}
Company  : Demo Electronics, Inc
Model    : DEMO-SWITCH-PRO-X16HT-8G6-144
Version  : {device_state['firmware_version']}    Date : {datetime.now().strftime('%b %d %Y %H:%M:%S')}
SBR Version : 0 34 160 28

OK>"""


def get_demo_lsd_response(device_state):
    """Generate demo lsd command response"""
    import random
    temp = int(device_state['temperature'])
    return f"""Cmd>lsd

Thermal:
        Board Temperature : {temp} degree

Fans Speed:
        Switch Fan : {random.randint(6000, 7000)} rpm

Voltage Sensors:
Board    0.8V  Voltage : {random.randint(900, 920)} mV
Board   0.89V  Voltage : {random.randint(970, 990)} mV
Board    1.2V  Voltage : {random.randint(1290, 1310)} mV
Board    1.5v  Voltage : {random.randint(1500, 1520)} mV

Current Status:
Current : {random.randint(10000, 11000)} mA

Error Status:
Voltage    0.8V  error : 0
Voltage   0.89V  error : 0
Voltage    1.2V  error : 0
Voltage    1.5v  error : 0

OK>"""


# Testing function
if __name__ == "__main__":
    print("Testing Complete Host Card Info Module...")

    # Test with sample data from your images
    sample_ver = """Cmd>ver

S/N      : GBH14412506206Z
Company  : SerialCables, Inc
Model    : PCT6-RD-x16HT-8G6-144
Version  : 0.1.0    Date : Jul 18 2025 11:05:16
SBR Version : 0 34 160 28

OK>"""

    sample_lsd = """Cmd>lsd

Thermal:
        Board Temperature : 54 degree

Fans Speed:
        Switch Fan : 6566 rpm

Voltage Sensors:
Board    0.8V  Voltage : 902 mV
Board   0.89V  Voltage : 980 mV
Board    1.2V  Voltage : 1292 mV
Board    1.5v  Voltage : 1503 mV

Current Status:
Current : 10880 mA

Error Status:
Voltage    0.8V  error : 0
Voltage   0.89V  error : 0
Voltage    1.2V  error : 0
Voltage    1.5v  error : 0

OK>"""

    # Test parser
    parser = HostCardInfoParser()
    info = parser.parse_responses(sample_ver, sample_lsd)

    print("Parsed Information:")
    sections = info.get_display_sections()

    for icon, title, data in sections:
        print(f"\n{icon} {title}:")
        for field_name, value in data:
            if value != "Unknown":
                print(f"  {field_name}: {value}")

    # Test demo functions
    print("\n" + "=" * 50)
    print("Testing Demo Functions:")

    demo_device_state = {
        'serial_number': 'DEMO-123456',
        'firmware_version': 'RC28',
        'temperature': 45.5
    }

    print("\nDemo ver response:")
    print(get_demo_ver_response(demo_device_state))

    print("\nDemo lsd response:")
    print(get_demo_lsd_response(demo_device_state))

    print("\nModule test completed!")