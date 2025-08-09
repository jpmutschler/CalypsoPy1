"""
host_card_info.py

This module handles the Host Card Information subsection of the dashboard.
It runs the 'ver' and 'lsd' commands via the CLI and parses the response for display.


"""

import re
import time
import threading
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Optional, Any


@dataclass
class HostCardInfo:
    """Data class to store parsed host card information"""
    device_type: str = "Unknown"
    vendor_id: str = "Unknown"
    product_id: str = "Unknown"
    serial_number: str = "Unknown"
    firmware_version: str = "Unknown"
    hardware_revision: str = "Unknown"
    max_power: str = "Unknown"
    operating_temperature: str = "Unknown"
    manufacturer: str = "Unknown"
    model_number: str = "Unknown"
    usb_version: str = "Unknown"
    controller_type: str = "Unknown"
    port_count: str = "Unknown"
    last_updated: str = ""
    raw_response: str = ""

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for easy display"""
        return {
            "Device Type": self.device_type,
            "Manufacturer": self.manufacturer,
            "Model Number": self.model_number,
            "Vendor ID": self.vendor_id,
            "Product ID": self.product_id,
            "Serial Number": self.serial_number,
            "Firmware Version": self.firmware_version,
            "Hardware Revision": self.hardware_revision,
            "USB Version": self.usb_version,
            "Controller Type": self.controller_type,
            "Port Count": self.port_count,
            "Max Power": self.max_power,
            "Operating Temperature": self.operating_temperature,
            "Last Updated": self.last_updated
        }


class HostCardInfoParser:
    """Parser for sysinfo command responses"""

    def __init__(self):
        # Common patterns for parsing sysinfo responses
        self.patterns = {
            'device_type': [
                r'device\s*type[:\s]+(.+?)(?:\n|$)',
                r'type[:\s]+(.+?)(?:\n|$)',
                r'device[:\s]+(.+?)(?:\n|$)'
            ],
            'vendor_id': [
                r'vendor\s*id[:\s]+(0x[a-fA-F0-9]+|\d+)',
                r'vid[:\s]+(0x[a-fA-F0-9]+|\d+)',
                r'vendor[:\s]+(0x[a-fA-F0-9]+|\d+)'
            ],
            'product_id': [
                r'product\s*id[:\s]+(0x[a-fA-F0-9]+|\d+)',
                r'pid[:\s]+(0x[a-fA-F0-9]+|\d+)',
                r'product[:\s]+(0x[a-fA-F0-9]+|\d+)'
            ],
            'serial_number': [
                r'serial\s*(?:number|#)?[:\s]+([A-Za-z0-9\-]+)',
                r's/?n[:\s]+([A-Za-z0-9\-]+)',
                r'serial[:\s]+([A-Za-z0-9\-]+)'
            ],
            'firmware_version': [
                r'firmware\s*(?:version)?[:\s]+(v?[\d\.]+[\w\-]*)',
                r'fw\s*(?:version)?[:\s]+(v?[\d\.]+[\w\-]*)',
                r'version[:\s]+(v?[\d\.]+[\w\-]*)'
            ],
            'hardware_revision': [
                r'hardware\s*(?:revision|rev)?[:\s]+([\w\d\.\-\s]+)',
                r'hw\s*(?:revision|rev)?[:\s]+([\w\d\.\-\s]+)',
                r'revision[:\s]+([\w\d\.\-\s]+)'
            ],
            'max_power': [
                r'max\s*power[:\s]+([\d]+\s*ma?)',
                r'power[:\s]+([\d]+\s*ma?)',
                r'current[:\s]+([\d]+\s*ma?)'
            ],
            'operating_temperature': [
                r'operating\s*temp(?:erature)?[:\s]+([\d\-\+°C\s]+)',
                r'temp\s*range[:\s]+([\d\-\+°C\s]+)',
                r'temperature[:\s]+([\d\-\+°C\s]+)'
            ],
            'manufacturer': [
                r'manufacturer[:\s]+(.+?)(?:\n|$)',
                r'mfg[:\s]+(.+?)(?:\n|$)',
                r'vendor[:\s]+([A-Za-z\s]+)(?:\n|$)'
            ],
            'model_number': [
                r'model\s*(?:number)?[:\s]+([A-Za-z0-9\-\s]+)',
                r'model[:\s]+([A-Za-z0-9\-\s]+)',
                r'part\s*(?:number)?[:\s]+([A-Za-z0-9\-\s]+)'
            ],
            'usb_version': [
                r'usb\s*(?:version)?[:\s]+([\d\.]+)',
                r'usb[:\s]+([\d\.]+)',
                r'version\s*usb[:\s]+([\d\.]+)'
            ],
            'controller_type': [
                r'controller\s*(?:type)?[:\s]+(.+?)(?:\n|$)',
                r'host\s*controller[:\s]+(.+?)(?:\n|$)',
                r'type[:\s]+(.*controller.*?)(?:\n|$)'
            ],
            'port_count': [
                r'port\s*count[:\s]+(\d+)',
                r'ports[:\s]+(\d+)',
                r'(\d+)\s*ports?'
            ]
        }

    def parse_sysinfo_response(self, response: str) -> HostCardInfo:
        """
        Parse the sysinfo command response and extract host card information

        Args:
            response: Raw response string from sysinfo command

        Returns:
            HostCardInfo object with parsed data
        """
        info = HostCardInfo()
        info.raw_response = response
        info.last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Convert response to lowercase for case-insensitive matching
        response_lower = response.lower()

        # Parse each field using multiple patterns
        for field_name, patterns in self.patterns.items():
            value = self._extract_field(response_lower, patterns)
            if value:
                setattr(info, field_name, value.strip())

        # Post-process and validate extracted data
        self._post_process_info(info)

        return info

    def _extract_field(self, text: str, patterns: list) -> Optional[str]:
        """
        Try multiple regex patterns to extract a field value

        Args:
            text: Text to search in (should be lowercase)
            patterns: List of regex patterns to try

        Returns:
            Extracted value or None if not found
        """
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        return None

    def _post_process_info(self, info: HostCardInfo) -> None:
        """
        Post-process and clean up extracted information

        Args:
            info: HostCardInfo object to process
        """
        # Clean up and standardize vendor/product IDs
        info.vendor_id = self._standardize_hex_id(info.vendor_id)
        info.product_id = self._standardize_hex_id(info.product_id)

        # Clean up firmware version
        if info.firmware_version and not info.firmware_version.startswith('v'):
            info.firmware_version = f"v{info.firmware_version}"

        # Standardize power consumption format
        if info.max_power and info.max_power.lower() != "unknown":
            info.max_power = self._standardize_power(info.max_power)

        # Clean up temperature range
        if info.operating_temperature and info.operating_temperature.lower() != "unknown":
            info.operating_temperature = self._standardize_temperature(info.operating_temperature)

        # Set default values for common USB controller info if not found
        if info.device_type == "Unknown" and "controller" in info.raw_response.lower():
            info.device_type = "USB Host Controller"

        if info.usb_version == "Unknown":
            # Try to infer USB version from other clues
            if "3.0" in info.raw_response or "superspeed" in info.raw_response.lower():
                info.usb_version = "3.0"
            elif "2.0" in info.raw_response or "high speed" in info.raw_response.lower():
                info.usb_version = "2.0"
            elif "1.1" in info.raw_response or "full speed" in info.raw_response.lower():
                info.usb_version = "1.1"

    def _standardize_hex_id(self, hex_id: str) -> str:
        """Standardize hex ID format"""
        if not hex_id or hex_id.lower() == "unknown":
            return "Unknown"

        # Remove any whitespace
        hex_id = hex_id.strip()

        # Ensure it starts with 0x and is uppercase
        if not hex_id.startswith('0x') and not hex_id.startswith('0X'):
            hex_id = '0x' + hex_id

        return hex_id.upper()

    def _standardize_power(self, power: str) -> str:
        """Standardize power consumption format"""
        if not power:
            return "Unknown"

        # Extract numbers and units
        power_clean = re.sub(r'[^\d\w]', '', power.lower())
        numbers = re.findall(r'\d+', power_clean)

        if numbers:
            # Convert to mA if needed
            power_val = int(numbers[0])
            if 'ma' in power_clean or 'milliamp' in power_clean:
                return f"{power_val}mA"
            elif 'a' in power_clean or 'amp' in power_clean:
                return f"{power_val * 1000}mA"
            else:
                return f"{power_val}mA"  # Assume mA if no unit

        return power

    def _standardize_temperature(self, temp: str) -> str:
        """Standardize temperature range format"""
        if not temp:
            return "Unknown"

        # Extract temperature values
        temp_numbers = re.findall(r'[-+]?\d+', temp)

        if len(temp_numbers) >= 2:
            min_temp, max_temp = temp_numbers[0], temp_numbers[1]
            return f"{min_temp}°C to {max_temp}°C"
        elif len(temp_numbers) == 1:
            return f"Max {temp_numbers[0]}°C"

        return temp


class HostCardInfoManager:
    """Manager class for handling host card information requests and caching"""

    def __init__(self, cli_instance):
        """
        Initialize with CLI instance

        Args:
            cli_instance: Either SerialCLI or DemoSerialCLI instance
        """
        self.cli = cli_instance
        self.parser = HostCardInfoParser()
        self.cached_info: Optional[HostCardInfo] = None
        self.last_refresh: Optional[datetime] = None
        self.refresh_interval = 30  # seconds
        self._lock = threading.Lock()

    def get_host_card_info(self, force_refresh: bool = False) -> HostCardInfo:
        """
        Get host card information, using cache if available and fresh

        Args:
            force_refresh: Force a new sysinfo command even if cache is fresh

        Returns:
            HostCardInfo object with current information
        """
        with self._lock:
            # Check if we need to refresh
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
        """Send sysinfo command and parse the response"""
        try:
            # Send sysinfo command
            success = self.cli.send_command("sysinfo")
            if not success:
                self.cached_info = self._get_error_info("Failed to send sysinfo command")
                return

            # Wait for response with timeout
            response = self._wait_for_sysinfo_response(timeout=5.0)

            if response:
                # Parse the response
                self.cached_info = self.parser.parse_sysinfo_response(response)
                self.last_refresh = datetime.now()
            else:
                self.cached_info = self._get_error_info("No response received from sysinfo command")

        except Exception as e:
            self.cached_info = self._get_error_info(f"Error getting host card info: {str(e)}")

    def _wait_for_sysinfo_response(self, timeout: float = 5.0) -> Optional[str]:
        """
        Wait for sysinfo command response

        Args:
            timeout: Maximum time to wait for response in seconds

        Returns:
            Response string or None if timeout/error
        """
        start_time = time.time()
        response_parts = []

        while (time.time() - start_time) < timeout:
            response = self.cli.read_response()
            if response:
                response_parts.append(response)
                # Check if this looks like the end of a sysinfo response
                if self._is_sysinfo_complete(response_parts):
                    return '\n'.join(response_parts)
            time.sleep(0.1)

        # Return partial response if we have any
        return '\n'.join(response_parts) if response_parts else None

    def _is_sysinfo_complete(self, response_parts: list) -> bool:
        """
        Check if the sysinfo response appears complete

        Args:
            response_parts: List of response lines received so far

        Returns:
            True if response appears complete
        """
        if not response_parts:
            return False

        full_response = '\n'.join(response_parts).lower()

        # Look for indicators that the response is complete
        completion_indicators = [
            'end of sysinfo',
            'sysinfo complete',
            '---end---',
            'ok>',  # Command prompt return
            'cmd>',
            '# '  # Shell prompt
        ]

        for indicator in completion_indicators:
            if indicator in full_response:
                return True

        # If we have multiple lines and the last line looks like a prompt
        if len(response_parts) > 3:
            last_line = response_parts[-1].strip().lower()
            if len(last_line) < 10 and ('>' in last_line or '#' in last_line):
                return True

        return False

    def _get_error_info(self, error_message: str) -> HostCardInfo:
        """
        Create HostCardInfo object for error conditions

        Args:
            error_message: Error description

        Returns:
            HostCardInfo with error information
        """
        info = HostCardInfo()
        info.device_type = f"Error: {error_message}"
        info.last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return info

    def format_for_display(self, info: HostCardInfo) -> list:
        """
        Format host card info for display in the dashboard

        Args:
            info: HostCardInfo object to format

        Returns:
            List of (label, value) tuples for display
        """
        display_data = []
        info_dict = info.to_dict()

        # Define display order and labels
        display_order = [
            ("Device Type", "device_type"),
            ("Manufacturer", "manufacturer"),
            ("Model Number", "model_number"),
            ("Serial Number", "serial_number"),
            ("Firmware Version", "firmware_version"),
            ("Hardware Revision", "hardware_revision"),
            ("USB Version", "usb_version"),
            ("Controller Type", "controller_type"),
            ("Port Count", "port_count"),
            ("Vendor ID", "vendor_id"),
            ("Product ID", "product_id"),
            ("Max Power", "max_power"),
            ("Operating Temperature", "operating_temperature"),
            ("Last Updated", "last_updated")
        ]

        for display_label, field_name in display_order:
            field_key = display_label  # The dict uses display labels as keys
            value = info_dict.get(field_key, "Unknown")

            # Skip unknown values for cleaner display
            if value and value != "Unknown":
                display_data.append((display_label, value))

        return display_data


# Demo data generator for testing
def generate_demo_sysinfo_response() -> str:
    """Generate realistic sysinfo response for demo/testing purposes"""
    demo_responses = [
        """=== SYSTEM INFORMATION ===
Device Type: USB 3.0 Host Controller
Manufacturer: Advanced USB Technologies
Model Number: AUT-HC3000
Vendor ID: 0x1ABC
Product ID: 0x3000
Serial Number: AUT-2024-HC-001234
Firmware Version: v3.2.1
Hardware Revision: Rev D
USB Version: 3.0
Controller Type: xHCI Host Controller
Port Count: 4
Max Power: 900mA
Operating Temperature: 0°C to 70°C
Build Date: 2024-01-15
Compliance: USB-IF Certified
Status: Operational
=== END SYSINFO ===
OK>""",
        """SYSINFO OUTPUT:
TYPE: USB HOST CONTROLLER
VID: 0x2DEF  
PID: 0x4000
S/N: UHC-DEV-789012
FW VERSION: 2.8.5
HW REV: C
USB: 3.0 SUPERSPEED
CONTROLLER: ENHANCED HOST
PORTS: 6
POWER: 1500MA
TEMP RANGE: -10°C TO +85°C
MFG: TechCorp Industries  
MODEL: TC-UHC-6000
STATUS: READY
CMD>""",
        """--- Device Information ---
Device: SuperSpeed USB Hub Controller
Vendor: MegaUSB Corp
Model: MUSB-HUB-PRO
VendorID: 0x3CBA
ProductID: 0x5000  
Serial: MUSB-PRO-555666
Firmware: v4.1.2-beta
Hardware: Revision E
USB Standard: 3.1 Gen 1
Type: Multi-Port Hub Controller
Available Ports: 8
Maximum Current: 2000mA
Operating Range: 5°C to 60°C
Last Update: 2024-02-20
--- End Info ---
#"""
    ]

    import random
    return random.choice(demo_responses)


# Testing function
if __name__ == "__main__":
    print("Testing Host Card Info Parser...")

    # Test with demo data
    parser = HostCardInfoParser()

    for i, demo_response in enumerate([generate_demo_sysinfo_response() for _ in range(3)]):
        print(f"\n=== Test {i + 1} ===")
        print("Raw Response:")
        print(demo_response)
        print("\nParsed Information:")

        info = parser.parse_sysinfo_response(demo_response)


        # Create a mock manager for display formatting
        class MockCLI:
            pass


        manager = HostCardInfoManager(MockCLI())
        display_data = manager.format_for_display(info)

        for label, value in display_data:
            print(f"  {label}: {value}")

    print("\nHost Card Info Parser test completed!")
