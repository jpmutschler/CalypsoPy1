#!/usr/bin/env python3
"""
Dashboards/demo_mode_integration.py

Enhanced Demo Mode Integration for CalypsoPy
Integrates with Admin components for proper sysinfo command handling

This enhanced version adds:
- Integration with Admin cache manager, parser, debug, and settings
- Proper sysinfo command execution with ver, lsd, and showport parsing
- Dashboard data preparation for Host Card and Link Status
- Unified command processing with enhanced error handling

Author: Serial Cables Development Team
"""

import random
import time
import threading
import queue
from datetime import datetime
import os
import re
from typing import Dict, Any, Optional

# Import Admin components for integration
try:
    from Admin.cache_manager import DeviceDataCache
    from Admin.enhanced_sysinfo_parser import EnhancedSystemInfoParser
    from Admin.debug_config import debug_print, debug_error, debug_info, debug_warning
    from Admin.settings_manager import SettingsManager

    ADMIN_COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Admin components not available: {e}")
    ADMIN_COMPONENTS_AVAILABLE = False


class EnhancedUnifiedDemoSerialCLI:
    """
    Enhanced Unified Demo CLI with Admin components integration

    This enhanced version provides:
    - Proper sysinfo command handling with Admin integration
    - Cache management for parsed demo data
    - Debug logging throughout command execution
    - Settings-based demo behavior configuration
    """

    def __init__(self, port="DEMO", cache_manager=None, settings_manager=None):
        """
        Initialize Enhanced Demo CLI

        Args:
            port: Demo port identifier
            cache_manager: DeviceDataCache instance for caching
            settings_manager: SettingsManager instance for configuration
        """
        self.port = port
        self.baudrate = 115200
        self.serial_connection = None
        self.is_running = False
        self.command_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.log_queue = queue.Queue()

        # Admin components integration
        self.cache_manager = cache_manager
        self.settings_manager = settings_manager
        self.parser = None

        # Initialize parser if cache manager available
        if ADMIN_COMPONENTS_AVAILABLE and self.cache_manager:
            self.parser = EnhancedSystemInfoParser(self.cache_manager)
            debug_info("Enhanced parser initialized with cache manager", "DEMO_PARSER_INIT")
        elif ADMIN_COMPONENTS_AVAILABLE:
            self.parser = EnhancedSystemInfoParser()
            debug_info("Enhanced parser initialized without cache manager", "DEMO_PARSER_INIT")

        # Demo device state with enhanced properties
        self.demo_device_state = {
            'current_mode': 0,  # Default SBR mode
            'temperature': 45.5,
            'serial_number': 'DEMO12345678',
            'firmware_version': 'RC28',
            'company': 'SerialCables,Inc',
            'model': 'DEMO-PCI6-RD-x16HT-BG6-144',
            'version': '1.0.0',
            'build_date': 'Aug 19 2025 12:00:00',
            'sbr_version': '0 34 160 28'
        }

        # Load demo content from files
        self.demo_sysinfo_content = self._load_demo_sysinfo_file()
        self.demo_showport_content = self._load_demo_showport_file()

        # Parse demo content on initialization if available
        self._parse_initial_demo_content()

        debug_info(f"Enhanced UnifiedDemoSerialCLI initialized for {port}", "DEMO_CLI_INIT")
        self._log_initialization_status()

    def _log_initialization_status(self):
        """Log initialization status with debug info"""
        if self.demo_sysinfo_content:
            debug_info(f"Demo sysinfo content loaded: {len(self.demo_sysinfo_content)} chars", "DEMO_SYSINFO_LOADED")
        else:
            debug_warning("No demo sysinfo content loaded", "DEMO_SYSINFO_MISSING")

        if self.demo_showport_content:
            debug_info(f"Demo showport content loaded: {len(self.demo_showport_content)} chars", "DEMO_SHOWPORT_LOADED")
        else:
            debug_warning("No demo showport content loaded", "DEMO_SHOWPORT_MISSING")

        if self.parser:
            debug_info("Enhanced parser available for demo parsing", "DEMO_PARSER_AVAILABLE")
        else:
            debug_warning("Enhanced parser not available", "DEMO_PARSER_MISSING")

    def _parse_initial_demo_content(self):
        """Parse initial demo content and cache it"""
        if not self.parser or not self.demo_sysinfo_content:
            debug_warning("Cannot parse initial demo content - parser or content missing", "DEMO_PARSE_SKIP")
            return

        try:
            debug_info("Parsing initial demo content", "DEMO_PARSE_START")

            # Parse the unified sysinfo content
            parsed_data = self.parser.parse_unified_sysinfo(
                self.demo_sysinfo_content,
                "demo"
            )

            if parsed_data:
                debug_info("Initial demo content parsed successfully", "DEMO_PARSE_SUCCESS")

                # Cache the parsed data if cache manager available
                if self.cache_manager:
                    cache_key = "demo_sysinfo_initial"
                    self.cache_manager.store(cache_key, parsed_data, "sysinfo")
                    debug_info(f"Initial demo data cached with key: {cache_key}", "DEMO_CACHE_STORED")
            else:
                debug_error("Initial demo content parsing failed", "DEMO_PARSE_FAILED")

        except Exception as e:
            debug_error(f"Initial demo content parsing exception: {e}", "DEMO_PARSE_EXCEPTION")

    def _load_demo_sysinfo_file(self):
        """Load sysinfo.txt from multiple possible locations with enhanced debugging"""
        demo_paths = [
            "DemoData/sysinfo.txt",
            "./DemoData/sysinfo.txt",
            "../DemoData/sysinfo.txt",
            os.path.join(os.path.dirname(__file__), "DemoData", "sysinfo.txt"),
            os.path.join(os.path.dirname(__file__), "..", "DemoData", "sysinfo.txt"),
            os.path.join(os.getcwd(), "DemoData", "sysinfo.txt"),
            "sysinfo.txt",  # Current directory fallback
        ]

        debug_info("Searching for demo sysinfo file", "DEMO_FILE_SEARCH")

        for i, path in enumerate(demo_paths):
            abs_path = os.path.abspath(path)
            debug_print(f"Checking sysinfo path {i + 1}: {abs_path}", "FILE_CHECK")

            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    debug_info(f"Loaded demo sysinfo from {path} ({len(content)} chars)", "FILE_LOADED")

                    # Verify content has expected sections
                    if self._verify_sysinfo_content(content):
                        debug_info("Sysinfo content verification passed", "CONTENT_VERIFIED")
                        return content
                    else:
                        debug_warning(f"Sysinfo content verification failed for {path}", "CONTENT_VERIFY_FAILED")
                        continue

                except Exception as e:
                    debug_error(f"Error loading sysinfo {path}: {e}", "FILE_READ_ERROR")
                    continue
            else:
                debug_print(f"Sysinfo path does not exist: {abs_path}", "FILE_NOT_FOUND")

        debug_warning("No sysinfo file found - creating fallback data", "SYSINFO_FALLBACK")
        return self._create_fallback_sysinfo()

    def _verify_sysinfo_content(self, content: str) -> bool:
        """Verify sysinfo content has expected sections"""
        required_sections = ['ver', 'lsd', 'showport']
        missing_sections = []

        content_lower = content.lower()
        for section in required_sections:
            if section not in content_lower:
                missing_sections.append(section)

        if missing_sections:
            debug_error(f"Missing required sections: {missing_sections}", "CONTENT_MISSING_SECTIONS")
            return False

        return True

    def _create_fallback_sysinfo(self):
        """Create fallback sysinfo data if file not found"""
        current_time = datetime.now().strftime('%b %d %Y %H:%M:%S')

        fallback_content = f"""================================================================================
ver
================================================================================

S/N      : {self.demo_device_state['serial_number']}
Company  : {self.demo_device_state['company']}
Model    : {self.demo_device_state['model']}
Version  : {self.demo_device_state['version']}    Date : {current_time}
SBR Version : {self.demo_device_state['sbr_version']}

================================================================================
lsd
================================================================================

Thermal:
        Board Temperature : {int(self.demo_device_state['temperature'])} degree

Fans Speed:
        Switch Fan : {random.randint(5000, 7000)} rpm

Voltage Sensors:
Board    0.8V  Voltage : {random.randint(840, 860)} mV
Board   0.89V  Voltage : {random.randint(910, 930)} mV
Board    1.2V  Voltage : {random.randint(1240, 1260)} mV
Board    1.5v  Voltage : {random.randint(1470, 1490)} mV

Current Status:
Current : {random.randint(9000, 10000)} mA

Error Status:
Voltage    0.8V  error : 0
Voltage   0.89V  error : 0
Voltage    1.2V  error : 0
Voltage    1.5v  error : 0

================================================================================
showport
================================================================================
Port Slot------------------------------------------------------------------------------

Port80 : speed 06, width 04, max_speed06, max_width16
Port112: speed 01, width 00, max_speed06, max_width16
Port128: speed 01, width 00, max_speed06, max_width16
Port Upstream------------------------------------------------------------------------------

Golden finger: speed 05, width 16, max_width = 16"""

        debug_info("Created fallback sysinfo data", "FALLBACK_CREATED")
        return fallback_content

    def _load_demo_showport_file(self):
        """Load showport.txt from DemoData directory"""
        showport_paths = [
            "DemoData/showport.txt",
            "./DemoData/showport.txt",
            "../DemoData/showport.txt",
            os.path.join(os.path.dirname(__file__), "DemoData", "showport.txt"),
            os.path.join(os.path.dirname(__file__), "..", "DemoData", "showport.txt"),
            os.path.join(os.getcwd(), "DemoData", "showport.txt")
        ]

        debug_info("Searching for demo showport.txt file", "SHOWPORT_SEARCH")

        for i, path in enumerate(showport_paths):
            abs_path = os.path.abspath(path)
            debug_print(f"Checking showport path {i + 1}: {abs_path}", "SHOWPORT_CHECK")

            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    debug_info(f"Loaded demo showport from {path} ({len(content)} chars)", "SHOWPORT_LOADED")
                    return content
                except Exception as e:
                    debug_error(f"Error loading showport {path}: {e}", "SHOWPORT_READ_ERROR")
                    continue
            else:
                debug_print(f"Showport path does not exist: {abs_path}", "SHOWPORT_NOT_FOUND")

        debug_warning("No showport.txt file found - creating fallback data", "SHOWPORT_FALLBACK")
        return self._create_fallback_showport()

    def _create_fallback_showport(self):
        """Create fallback showport data if file not found"""
        fallback_content = """Port Slot------------------------------------------------------------------------------

Port80 : speed 06, width 04, max_speed06, max_width16
Port112: speed 01, width 00, max_speed06, max_width16
Port128: speed 05, width 16, max_speed06, max_width16

Port Upstream------------------------------------------------------------------------------

Golden finger: speed 06, width 16, max_width = 16"""

        debug_info("Created fallback showport data", "SHOWPORT_FALLBACK_CREATED")
        return fallback_content

    def connect(self):
        """Simulate connection with enhanced debugging"""
        debug_info("Initializing enhanced unified demo mode", "DEMO_CONNECT_START")

        # Simulate connection delay if enabled
        if self.settings_manager and self.settings_manager.get('demo', 'simulate_delays', True):
            delay = 0.1
            debug_info(f"Simulating connection delay: {delay}s", "DEMO_CONNECT_DELAY")
            time.sleep(delay)

        # Log demo content status
        if self.demo_sysinfo_content:
            content_preview = self.demo_sysinfo_content[:100].replace('\n', ' ')
            self.log_queue.put(f"DEMO: sysinfo data loaded - {content_preview}...")
            debug_info("Sysinfo data available for demo mode", "DEMO_SYSINFO_READY")
        else:
            self.log_queue.put("DEMO: WARNING - sysinfo data not available")
            debug_warning("Sysinfo data not available", "DEMO_SYSINFO_NOT_READY")

        # Log parser status
        if self.parser:
            debug_info("Enhanced parser ready for demo parsing", "DEMO_PARSER_READY")
        else:
            debug_warning("Enhanced parser not available", "DEMO_PARSER_NOT_READY")

        self.log_queue.put("DEMO: Enhanced connection established successfully")
        self.is_running = True

        debug_info("Enhanced UnifiedDemoSerialCLI connected successfully", "DEMO_CONNECT_SUCCESS")
        return True

    def disconnect(self):
        """Simulate disconnection with enhanced debugging"""
        debug_info("Disconnecting enhanced demo mode", "DEMO_DISCONNECT")
        self.is_running = False
        self.log_queue.put("DEMO: Enhanced unified demo connection closed")
        debug_info("Enhanced UnifiedDemoSerialCLI disconnected", "DEMO_DISCONNECT_SUCCESS")

    def send_command(self, command, timeout=5):
        """
        Enhanced command sending with better timeout handling

        Args:
            command: Command to send
            timeout: Timeout in seconds

        Returns:
            Response string or None if timeout/error
        """
        if not self.is_running:
            debug_error("Cannot send command - not running", "DEMO_SEND_NOT_RUNNING")
            return None

        debug_info(f"Sending enhanced demo command: {command}", "DEMO_SEND_CMD")

        try:
            # Put command in queue for background processing
            self.command_queue.put(command)
            self.log_queue.put(f"DEMO SENT: {command}")

            # Wait for response with timeout
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    response = self.response_queue.get_nowait()
                    debug_info(f"Enhanced demo response received ({len(response)} chars)", "DEMO_RECV_SUCCESS")
                    return response
                except queue.Empty:
                    time.sleep(0.1)  # Small delay before checking again

            debug_error(f"Enhanced demo command timeout after {timeout}s", "DEMO_TIMEOUT")
            return None

        except Exception as e:
            debug_error(f"Enhanced demo command failed: {e}", "DEMO_SEND_ERROR")
            return None

    def read_response(self):
        """Simulate reading response from device"""
        if self.is_running:
            try:
                response = self.response_queue.get_nowait()
                self.log_queue.put(f"DEMO RECV: {response[:100]}...")  # Limit log size
                debug_info(f"Demo response read: {len(response)} chars", "DEMO_READ_SUCCESS")
                return response
            except queue.Empty:
                debug_print("No response in queue", "DEMO_READ_EMPTY")
                return None
        debug_warning("Cannot read response - not running", "DEMO_READ_NOT_RUNNING")
        return None

    def run_background(self):
        """Enhanced background thread that processes commands with Admin integration"""
        debug_info("Enhanced UnifiedDemoSerialCLI background thread started", "DEMO_BG_START")

        while self.is_running:
            try:
                # Check for commands with timeout
                try:
                    command = self.command_queue.get(timeout=0.1)
                    debug_info(f"Background thread processing command: {command}", "DEMO_BG_PROCESS")

                    # Process the command with enhanced handling
                    response = self._handle_enhanced_command(command)

                    if response:
                        debug_info(f"Generated response ({len(response)} chars)", "DEMO_BG_RESPONSE")

                        # Simulate realistic delay based on settings
                        delay = self._get_command_delay(command)
                        if delay > 0:
                            debug_info(f"Simulating command delay: {delay}s", "DEMO_BG_DELAY")
                            time.sleep(delay)

                        # Put response in queue
                        self.response_queue.put(response)
                        debug_info("Response queued successfully", "DEMO_BG_QUEUED")
                    else:
                        debug_warning(f"No response generated for command: {command}", "DEMO_BG_NO_RESPONSE")

                except queue.Empty:
                    # No command to process, continue loop
                    pass

            except Exception as e:
                debug_error(f"Background thread error: {e}", "DEMO_BG_ERROR")
                import traceback
                traceback.print_exc()

            # Small delay to prevent CPU spinning
            time.sleep(0.05)

        debug_info("Enhanced background thread ending", "DEMO_BG_END")

    def _handle_enhanced_command(self, command):
        """
        Enhanced command handling with Admin components integration

        Args:
            command: Command to process

        Returns:
            Response string or None
        """
        command_lower = command.lower().strip()
        debug_info(f"Processing enhanced command: '{command}' -> '{command_lower}'", "DEMO_CMD_PROCESS")

        if 'sysinfo' in command_lower:
            return self._handle_sysinfo_command()
        elif 'ver' in command_lower and 'sysinfo' not in command_lower:
            return self._handle_ver_command()
        elif 'lsd' in command_lower:
            return self._handle_lsd_command()
        elif 'showport' in command_lower:
            return self._handle_showport_command()
        elif command_lower in ['help', '?']:
            return self._get_help_response()
        elif 'status' in command_lower:
            return self._get_status_response()
        elif 'version' in command_lower:
            return self._get_version_response()
        elif any(reset_cmd in command_lower for reset_cmd in ['reset', 'msrst', 'swreset']):
            return self._handle_reset_command(command_lower)
        else:
            debug_warning(f"Unknown command: {command}", "DEMO_CMD_UNKNOWN")
            return f"Unknown command: {command}\nType 'help' for available commands."

    def _handle_sysinfo_command(self):
        """Handle sysinfo command with enhanced parsing and caching"""
        debug_info("Handling enhanced sysinfo command", "DEMO_SYSINFO_HANDLE")

        if not self.demo_sysinfo_content:
            debug_error("No sysinfo content available", "DEMO_SYSINFO_NO_CONTENT")
            return "Error: Demo sysinfo data not available"

        try:
            # Parse the content using enhanced parser if available
            if self.parser:
                debug_info("Using enhanced parser for sysinfo", "DEMO_SYSINFO_PARSE")

                parsed_data = self.parser.parse_unified_sysinfo(
                    self.demo_sysinfo_content,
                    "demo"
                )

                if parsed_data:
                    debug_info("Sysinfo parsing successful", "DEMO_SYSINFO_PARSE_SUCCESS")

                    # Cache the parsed data
                    if self.cache_manager:
                        cache_key = f"demo_sysinfo_{int(time.time())}"
                        self.cache_manager.store(cache_key, parsed_data, "sysinfo")
                        debug_info(f"Sysinfo data cached with key: {cache_key}", "DEMO_SYSINFO_CACHED")
                else:
                    debug_warning("Sysinfo parsing returned no data", "DEMO_SYSINFO_PARSE_EMPTY")

            # Return the raw sysinfo content for command response
            debug_info(f"Returning sysinfo content ({len(self.demo_sysinfo_content)} chars)", "DEMO_SYSINFO_RETURN")
            return self.demo_sysinfo_content

        except Exception as e:
            debug_error(f"Sysinfo command handling failed: {e}", "DEMO_SYSINFO_ERROR")
            return f"Error processing sysinfo command: {e}"

    def _handle_ver_command(self):
        """Handle ver command separately"""
        debug_info("Handling ver command", "DEMO_VER_HANDLE")

        # Extract ver section from sysinfo content
        if self.demo_sysinfo_content:
            ver_match = re.search(r'ver\s*=+\s*(.*?)\s*=+', self.demo_sysinfo_content, re.DOTALL | re.IGNORECASE)
            if ver_match:
                ver_content = ver_match.group(1).strip()
                debug_info("Ver section extracted successfully", "DEMO_VER_EXTRACTED")
                return f"Cmd>ver\n\n{ver_content}\n\nOK>"

        # Fallback ver response
        debug_warning("Using fallback ver response", "DEMO_VER_FALLBACK")
        return f"""Cmd>ver

S/N      : {self.demo_device_state['serial_number']}
Company  : {self.demo_device_state['company']}
Model    : {self.demo_device_state['model']}
Version  : {self.demo_device_state['version']}    Date : {self.demo_device_state['build_date']}
SBR Version : {self.demo_device_state['sbr_version']}

OK>"""

    def _handle_lsd_command(self):
        """Handle lsd command separately"""
        debug_info("Handling lsd command", "DEMO_LSD_HANDLE")

        # Extract lsd section from sysinfo content
        if self.demo_sysinfo_content:
            lsd_match = re.search(r'lsd\s*=+\s*(.*?)\s*=+', self.demo_sysinfo_content, re.DOTALL | re.IGNORECASE)
            if lsd_match:
                lsd_content = lsd_match.group(1).strip()
                debug_info("LSD section extracted successfully", "DEMO_LSD_EXTRACTED")
                return f"Cmd>lsd\n\n{lsd_content}\n\nOK>"

        # Fallback lsd response with random values
        debug_warning("Using fallback lsd response", "DEMO_LSD_FALLBACK")
        temp = int(self.demo_device_state['temperature']) + random.randint(-2, 2)
        return f"""Cmd>lsd

Thermal:
        Board Temperature : {temp} degree

Fans Speed:
        Switch Fan : {random.randint(5500, 6500)} rpm

Voltage Sensors:
Board    0.8V  Voltage : {random.randint(840, 860)} mV
Board   0.89V  Voltage : {random.randint(910, 930)} mV
Board    1.2V  Voltage : {random.randint(1240, 1260)} mV
Board    1.5v  Voltage : {random.randint(1470, 1490)} mV

Current Status:
Current : {random.randint(9500, 10500)} mA

Error Status:
Voltage    0.8V  error : 0
Voltage   0.89V  error : 0
Voltage    1.2V  error : 0
Voltage    1.5v  error : 0

OK>"""

    def _handle_showport_command(self):
        """Handle showport command separately"""
        debug_info("Handling showport command", "DEMO_SHOWPORT_HANDLE")

        if self.demo_showport_content:
            debug_info("Using demo showport content", "DEMO_SHOWPORT_CONTENT")
            return f"Cmd>showport\n\n{self.demo_showport_content}\n\nOK>"
        elif self.demo_sysinfo_content:
            # Extract showport section from sysinfo content
            showport_match = re.search(r'showport\s*=+\s*(.*?)(?:\s*=+|$)', self.demo_sysinfo_content,
                                       re.DOTALL | re.IGNORECASE)
            if showport_match:
                showport_content = showport_match.group(1).strip()
                debug_info("Showport section extracted from sysinfo", "DEMO_SHOWPORT_EXTRACTED")
                return f"Cmd>showport\n\n{showport_content}\n\nOK>"

        # Fallback showport response
        debug_warning("Using fallback showport response", "DEMO_SHOWPORT_FALLBACK")
        return f"""Cmd>showport

Port Slot------------------------------------------------------------------------------

Port80 : speed 06, width 04, max_speed06, max_width16
Port112: speed 01, width 00, max_speed06, max_width16
Port128: speed 01, width 00, max_speed06, max_width16
Port Upstream------------------------------------------------------------------------------

Golden finger: speed 05, width 16, max_width = 16

OK>"""

    def _handle_reset_command(self, command_lower):
        """Handle reset commands"""
        debug_info(f"Handling reset command: {command_lower}", "DEMO_RESET_HANDLE")

        if 'msrst' in command_lower:
            return "Cmd>msrst\n\nResetting x16 Straddle Mount component...\nReset complete.\n\nOK>"
        elif 'swreset' in command_lower:
            return "Cmd>swreset\n\nResetting Atlas 3 Switch component...\nReset complete.\n\nOK>"
        elif 'reset' in command_lower:
            # Full system reset - will disconnect
            self.is_running = False
            return "Cmd>reset\n\nPerforming full system reset...\nSystem reset complete.\nConnection terminated."
        else:
            return f"Unknown reset command: {command_lower}"

    def _get_command_delay(self, command):
        """Get realistic delay for command response based on settings"""
        if not self.settings_manager or not self.settings_manager.get('demo', 'simulate_delays', True):
            return 0

        command_lower = command.lower()

        if 'sysinfo' in command_lower:
            return 0.3  # Longer delay for comprehensive command
        elif any(cmd in command_lower for cmd in ['lsd', 'showport']):
            return 0.2  # Medium delay for diagnostic commands
        elif any(cmd in command_lower for cmd in ['help', 'status', 'version', 'ver']):
            return 0.05  # Quick response for simple commands
        else:
            return 0.1  # Default delay

    def _get_help_response(self):
        """Generate help command response"""
        return """Available commands:
    help      - Show this help
    sysinfo   - Get complete system information (ver + lsd + showport)
    ver       - Get device version information
    lsd       - Get system diagnostics (temperature, voltages, etc.)
    showport  - Get port status information
    status    - Get device status
    version   - Get firmware version

    Reset Commands:
    msrst     - Reset x16 Straddle Mount component
    swreset   - Reset Atlas 3 Switch component  
    reset     - Full system reset (will disconnect)

    Demo Mode: All responses use simulated device behavior with Admin integration"""

    def _get_status_response(self):
        """Generate status command response"""
        return f"""Device Status:
    Mode: Demo Mode (Enhanced)
    Serial: {self.demo_device_state['serial_number']}
    Temperature: {self.demo_device_state['temperature']}°C
    Connection: Active
    Parser: {'Available' if self.parser else 'Not Available'}
    Cache: {'Available' if self.cache_manager else 'Not Available'}
    Settings: {'Available' if self.settings_manager else 'Not Available'}"""

    def _get_version_response(self):
        """Generate version command response"""
        return f"""Firmware Version: {self.demo_device_state['version']} (DEMO)
Hardware Rev: Rev C
Serial Number: {self.demo_device_state['serial_number']}
Build Date: {self.demo_device_state['build_date']}
Bootloader: v1.0.5

Enhanced Demo Mode with Admin Integration
Parser: {'Available' if self.parser else 'Not Available'}
Cache: {'Available' if self.cache_manager else 'Not Available'}"""

    def get_host_card_data(self):
        """
        Get Host Card dashboard data (ver + lsd sections)

        Returns:
            Parsed host card data or None
        """
        if self.parser:
            return self.parser.get_host_card_json()
        return None

    def get_link_status_data(self):
        """
        Get Link Status dashboard data (showport section)

        Returns:
            Parsed link status data or None
        """
        if self.parser:
            return self.parser.get_link_status_json()
        return None

    def get_complete_sysinfo_data(self):
        """
        Get complete parsed sysinfo data

        Returns:
            Complete parsed data or None
        """
        if self.parser:
            return self.parser.get_complete_sysinfo()
        return None

    def is_data_fresh(self, max_age_seconds=300):
        """
        Check if cached data is fresh

        Args:
            max_age_seconds: Maximum age in seconds

        Returns:
            True if data is fresh, False otherwise
        """
        if self.parser:
            return self.parser.is_data_fresh(max_age_seconds)
        return False

    def force_refresh_data(self):
        """
        Force refresh of demo data

        Returns:
            True if refresh successful, False otherwise
        """
        debug_info("Forcing demo data refresh", "DEMO_FORCE_REFRESH")

        try:
            # Clear cache if available
            if self.cache_manager:
                self.cache_manager.clear()
                debug_info("Cache cleared for refresh", "DEMO_CACHE_CLEARED")

            # Reload demo files
            self.demo_sysinfo_content = self._load_demo_sysinfo_file()
            self.demo_showport_content = self._load_demo_showport_file()

            # Re-parse content
            self._parse_initial_demo_content()

            debug_info("Demo data refresh completed", "DEMO_REFRESH_SUCCESS")
            return True

        except Exception as e:
            debug_error(f"Demo data refresh failed: {e}", "DEMO_REFRESH_ERROR")
            return False

    def get_debug_info(self):
        """
        Get debug information about demo CLI state

        Returns:
            Debug information dictionary
        """
        debug_info_dict = {
            'is_running': self.is_running,
            'port': self.port,
            'sysinfo_content_available': self.demo_sysinfo_content is not None,
            'sysinfo_content_size': len(self.demo_sysinfo_content) if self.demo_sysinfo_content else 0,
            'showport_content_available': self.demo_showport_content is not None,
            'showport_content_size': len(self.demo_showport_content) if self.demo_showport_content else 0,
            'parser_available': self.parser is not None,
            'cache_manager_available': self.cache_manager is not None,
            'settings_manager_available': self.settings_manager is not None,
            'admin_components_available': ADMIN_COMPONENTS_AVAILABLE,
            'command_queue_size': self.command_queue.qsize(),
            'response_queue_size': self.response_queue.qsize()
        }

        if self.cache_manager:
            debug_info_dict['cache_stats'] = self.cache_manager.get_stats()

        if self.parser and self.parser.get_complete_sysinfo():
            complete_data = self.parser.get_complete_sysinfo()
            debug_info_dict['parsed_sections'] = list(complete_data.keys()) if complete_data else []

        return debug_info_dict


# Backwards compatibility - keep original class name as alias
UnifiedDemoSerialCLI = EnhancedUnifiedDemoSerialCLI


# Integration helper functions for main.py
def create_enhanced_demo_cli(port="DEMO", cache_manager=None, settings_manager=None):
    """
    Create enhanced demo CLI with Admin components integration

    Args:
        port: Demo port identifier
        cache_manager: DeviceDataCache instance
        settings_manager: SettingsManager instance

    Returns:
        EnhancedUnifiedDemoSerialCLI instance
    """
    debug_info(f"Creating enhanced demo CLI for port: {port}", "DEMO_CLI_CREATE")

    try:
        cli = EnhancedUnifiedDemoSerialCLI(port, cache_manager, settings_manager)
        debug_info("Enhanced demo CLI created successfully", "DEMO_CLI_CREATE_SUCCESS")
        return cli
    except Exception as e:
        debug_error(f"Enhanced demo CLI creation failed: {e}", "DEMO_CLI_CREATE_ERROR")
        # Fallback to basic version
        return UnifiedDemoSerialCLI(port)


def initialize_demo_mode_with_admin(cache_manager=None, settings_manager=None):
    """
    Initialize demo mode with Admin components

    Args:
        cache_manager: DeviceDataCache instance
        settings_manager: SettingsManager instance

    Returns:
        Tuple of (cli, parser) for demo mode
    """
    debug_info("Initializing demo mode with Admin components", "DEMO_ADMIN_INIT")

    try:
        # Create enhanced demo CLI
        cli = create_enhanced_demo_cli("DEMO", cache_manager, settings_manager)

        # Get parser from CLI
        parser = cli.parser if hasattr(cli, 'parser') else None

        debug_info("Demo mode with Admin components initialized", "DEMO_ADMIN_INIT_SUCCESS")
        return cli, parser

    except Exception as e:
        debug_error(f"Demo mode Admin initialization failed: {e}", "DEMO_ADMIN_INIT_ERROR")
        # Return basic demo CLI as fallback
        return UnifiedDemoSerialCLI("DEMO"), None


# Enhanced demo data access functions
def get_demo_host_card_data(cli):
    """
    Get host card data from enhanced demo CLI

    Args:
        cli: Enhanced demo CLI instance

    Returns:
        Host card data dictionary or None
    """
    if hasattr(cli, 'get_host_card_data'):
        return cli.get_host_card_data()
    return None


def get_demo_link_status_data(cli):
    """
    Get link status data from enhanced demo CLI

    Args:
        cli: Enhanced demo CLI instance

    Returns:
        Link status data dictionary or None
    """
    if hasattr(cli, 'get_link_status_data'):
        return cli.get_link_status_data()
    return None


def get_demo_complete_sysinfo_data(cli):
    """
    Get complete sysinfo data from enhanced demo CLI

    Args:
        cli: Enhanced demo CLI instance

    Returns:
        Complete sysinfo data dictionary or None
    """
    if hasattr(cli, 'get_complete_sysinfo_data'):
        return cli.get_complete_sysinfo_data()
    return None


# Testing and debugging functions
def test_enhanced_demo_integration():
    """Test the enhanced demo integration functionality"""
    print("=" * 60)
    print("Testing Enhanced Demo Mode Integration")
    print("=" * 60)

    # Test 1: Basic CLI creation
    print("\n1. Testing basic CLI creation...")
    try:
        cli = EnhancedUnifiedDemoSerialCLI()
        print("✓ Enhanced demo CLI created successfully")

        # Test connection
        if cli.connect():
            print("✓ Demo CLI connected successfully")
        else:
            print("✗ Demo CLI connection failed")

        cli.disconnect()
        print("✓ Demo CLI disconnected successfully")

    except Exception as e:
        print(f"✗ Basic CLI creation failed: {e}")
        return False

    # Test 2: Admin components integration
    print("\n2. Testing Admin components integration...")
    if ADMIN_COMPONENTS_AVAILABLE:
        print("✓ Admin components are available")

        try:
            # Create with mock cache/settings managers
            cache_mgr = DeviceDataCache() if 'DeviceDataCache' in globals() else None
            settings_mgr = SettingsManager() if 'SettingsManager' in globals() else None

            cli = EnhancedUnifiedDemoSerialCLI("DEMO", cache_mgr, settings_mgr)
            print("✓ Enhanced CLI created with Admin components")

            # Test parser availability
            if cli.parser:
                print("✓ Enhanced parser is available")
            else:
                print("⚠ Enhanced parser not available")

        except Exception as e:
            print(f"✗ Admin integration test failed: {e}")
    else:
        print("⚠ Admin components not available - skipping integration test")

    # Test 3: Command handling
    print("\n3. Testing enhanced command handling...")
    try:
        cli = EnhancedUnifiedDemoSerialCLI()
        cli.connect()

        # Start background thread
        bg_thread = threading.Thread(target=cli.run_background, daemon=True)
        bg_thread.start()

        # Test sysinfo command
        response = cli.send_command("sysinfo", timeout=2)
        if response and len(response) > 100:
            print(f"✓ Sysinfo command successful ({len(response)} chars)")
        else:
            print("✗ Sysinfo command failed or returned insufficient data")

        # Test ver command
        response = cli.send_command("ver", timeout=1)
        if response and "S/N" in response:
            print("✓ Ver command successful")
        else:
            print("✗ Ver command failed")

        # Test lsd command
        response = cli.send_command("lsd", timeout=1)
        if response and "Temperature" in response:
            print("✓ LSD command successful")
        else:
            print("✗ LSD command failed")

        # Test showport command
        response = cli.send_command("showport", timeout=1)
        if response and "Port" in response:
            print("✓ Showport command successful")
        else:
            print("✗ Showport command failed")

        cli.disconnect()

    except Exception as e:
        print(f"✗ Command handling test failed: {e}")

    # Test 4: Data access methods
    print("\n4. Testing data access methods...")
    try:
        cli = EnhancedUnifiedDemoSerialCLI()

        # Test debug info
        debug_info = cli.get_debug_info()
        if debug_info and isinstance(debug_info, dict):
            print(f"✓ Debug info available ({len(debug_info)} keys)")
        else:
            print("✗ Debug info not available")

        # Test data methods (may return None if parser not available)
        host_data = cli.get_host_card_data()
        link_data = cli.get_link_status_data()
        complete_data = cli.get_complete_sysinfo_data()

        print(f"✓ Data access methods tested:")
        print(f"  - Host card data: {'Available' if host_data else 'None'}")
        print(f"  - Link status data: {'Available' if link_data else 'None'}")
        print(f"  - Complete sysinfo data: {'Available' if complete_data else 'None'}")

    except Exception as e:
        print(f"✗ Data access test failed: {e}")

    print("\n" + "=" * 60)
    print("Enhanced Demo Integration test completed!")
    print("=" * 60)

    return True


def demonstrate_integration_usage():
    """Demonstrate how to use the enhanced demo integration"""
    print("\n" + "=" * 60)
    print("Enhanced Demo Integration Usage Example")
    print("=" * 60)

    # Example 1: Basic usage
    print("\n1. Basic Enhanced Demo CLI Usage:")
    print("""
# Create enhanced demo CLI
cli = EnhancedUnifiedDemoSerialCLI()
cli.connect()

# Start background processing
bg_thread = threading.Thread(target=cli.run_background, daemon=True)
bg_thread.start()

# Send commands
sysinfo_response = cli.send_command("sysinfo")
ver_response = cli.send_command("ver")
lsd_response = cli.send_command("lsd")
showport_response = cli.send_command("showport")

cli.disconnect()
""")

    # Example 2: Admin integration usage
    print("\n2. Admin Components Integration Usage:")
    print("""
# Create with Admin components
cache_manager = DeviceDataCache()
settings_manager = SettingsManager()
cli = EnhancedUnifiedDemoSerialCLI("DEMO", cache_manager, settings_manager)

# CLI now has enhanced parsing and caching
host_data = cli.get_host_card_data()  # Returns parsed Host Card data
link_data = cli.get_link_status_data()  # Returns parsed Link Status data
complete_data = cli.get_complete_sysinfo_data()  # Returns all parsed data

# Check if data is fresh
if cli.is_data_fresh(300):  # 5 minutes
    print("Data is fresh")
else:
    cli.force_refresh_data()  # Force refresh if needed
""")

    # Example 3: Integration with main.py
    print("\n3. Integration with main.py DashboardApp:")
    print("""
# In DashboardApp.__init__():
if self.is_demo_mode:
    # Use enhanced demo CLI with Admin components
    self.cli = create_enhanced_demo_cli(
        port="DEMO",
        cache_manager=self.cache_manager,
        settings_manager=self.settings_mgr
    )

    # CLI automatically parses demo data and caches it

# In create_host_dashboard():
if self.is_demo_mode:
    host_data = get_demo_host_card_data(self.cli)
    if host_data:
        # Create dashboard from parsed data
        self._create_host_dashboard_from_data(host_data)

# In create_link_status_dashboard():
if self.is_demo_mode:
    link_data = get_demo_link_status_data(self.cli)
    if link_data:
        # Create dashboard from parsed data
        self._create_link_dashboard_from_data(link_data)
""")

    print("\n" + "=" * 60)
    print("Usage examples completed!")
    print("=" * 60)


# Main execution for testing
if __name__ == "__main__":
    print("Enhanced Demo Mode Integration Module")
    print("=" * 60)

    # Run tests
    if test_enhanced_demo_integration():
        print("\n✓ All tests completed successfully!")
    else:
        print("\n✗ Some tests failed!")

    # Show usage examples
    demonstrate_integration_usage()

    print("\nModule test completed!")