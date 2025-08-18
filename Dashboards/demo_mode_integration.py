#!/usr/bin/env python3
"""
demo_mode_integration.py - FIXED VERSION

Complete demo mode integration that works with:
- EnhancedSystemInfoParser
- DeviceDataCache
- HostCardInfoManager
- All existing dashboard modules

This provides a realistic simulation environment for training and testing.
"""

import random
import time
import threading
import queue
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List


class UnifiedDemoSerialCLI:
    """
    FIXED: Unified Demo CLI with proper integration to all existing modules
    """

    def __init__(self, port="DEMO"):
        self.port = port
        self.baudrate = 115200
        self.serial_connection = None
        self.is_running = False

        # Proper queue initialization
        self.command_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.log_queue = queue.Queue()

        # Device state for dynamic responses
        self.device_state = self._initialize_device_state()

        # Load demo sysinfo content
        self.demo_sysinfo_content = self._load_demo_sysinfo_file()

        # Background thread reference
        self._background_thread = None

        print(f"DEBUG: UnifiedDemoSerialCLI initialized for {port}")
        if self.demo_sysinfo_content:
            print(f"DEBUG: Demo content loaded: {len(self.demo_sysinfo_content)} chars")
        else:
            print("WARNING: No demo content loaded - using fallback data")

    def _initialize_device_state(self) -> Dict[str, Any]:
        """Initialize dynamic device state for realistic simulation"""
        return {
            'serial_number': 'GBH14412506206Z',
            'company': 'SerialCables,Inc',
            'model': 'PCI6-RD-x16HT-BG6-144',
            'firmware_version': '0.1.0',
            'build_date': 'Jul 18 2025 11:05:16',
            'sbr_version': '0 34 160 28',
            'board_temperature': 55,
            'fan_speed': 6310,
            'voltage_0_8v': 890,
            'voltage_0_89v': 991,
            'voltage_1_2v': 1304,
            'voltage_1_5v': 1512,
            'current_draw': 10240,
            'port_states': {
                '80': {'speed': '06', 'width': '04', 'active': True},
                '112': {'speed': '01', 'width': '00', 'active': True},
                '128': {'speed': '01', 'width': '00', 'active': True}
            },
            'golden_finger': {'speed': '05', 'width': '16', 'active': True},
            'error_counts': {
                '0_8v': 0,
                '0_89v': 0,
                '1_2v': 0,
                '1_5v': 0
            },
            'uptime_hours': 1,
            'last_update': time.time()
        }

    def _load_demo_sysinfo_file(self) -> Optional[str]:
        """Load sysinfo.txt from multiple possible locations"""
        demo_paths = [
            "sysinfo.txt",  # Current directory
            "DemoData/sysinfo.txt",
            "./DemoData/sysinfo.txt",
            "../DemoData/sysinfo.txt",
            os.path.join(os.path.dirname(__file__), "sysinfo.txt"),
            os.path.join(os.path.dirname(__file__), "DemoData", "sysinfo.txt"),
            os.path.join(os.getcwd(), "sysinfo.txt"),
            os.path.join(os.getcwd(), "DemoData", "sysinfo.txt")
        ]

        print("DEBUG: Searching for demo sysinfo file...")
        for i, path in enumerate(demo_paths):
            abs_path = os.path.abspath(path)
            print(f"DEBUG: Checking path {i + 1}: {abs_path}")

            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    print(f"DEBUG: ✓ Loaded demo sysinfo from {path} ({len(content)} chars)")

                    # Verify content has expected sections
                    if 'ver' in content and 'lsd' in content and 'showport' in content:
                        print("DEBUG: ✓ Content verification passed")
                        return content
                    else:
                        print("DEBUG: ⚠ Content missing expected sections")

                except Exception as e:
                    print(f"DEBUG: ✗ Error loading {path}: {e}")
                    continue
            else:
                print(f"DEBUG: ✗ Path does not exist: {abs_path}")

        print("DEBUG: No sysinfo file found - creating fallback data")
        return self._create_fallback_sysinfo()

    def _create_fallback_sysinfo(self) -> str:
        """Create comprehensive fallback sysinfo data"""
        return """================================================================================
ver
================================================================================

S/N      : GBH14412506206Z
Company  : SerialCables,Inc
Model    : PCI6-RD-x16HT-BG6-144
Version  : 0.1.0    Date : Jul 18 2025 11:05:16
SBR Version : 0 34 160 28

================================================================================
lsd
================================================================================

Thermal:
        Board Temperature : 55 degree

Fans Speed:
        Switch Fan : 6310 rpm

Voltage Sensors:
Board    0.8V  Voltage : 890 mV
Board   0.89V  Voltage : 991 mV
Board    1.2V  Voltage : 1304 mV
Board    1.5v  Voltage : 1512 mV

Current Status:
Current : 10240 mA

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

    def connect(self) -> bool:
        """Simulate connection establishment"""
        try:
            self.log_queue.put("DEMO: Initializing unified demo mode...")
            time.sleep(0.1)

            if self.demo_sysinfo_content:
                content_preview = self.demo_sysinfo_content[:100].replace('\n', ' ')
                self.log_queue.put(f"DEMO: sysinfo data loaded - {content_preview}...")
            else:
                self.log_queue.put("DEMO: WARNING - using fallback sysinfo data")

            self.log_queue.put("DEMO: Connection established successfully")
            self.is_running = True

            print("DEBUG: UnifiedDemoSerialCLI connected successfully")
            return True

        except Exception as e:
            print(f"ERROR: Demo connection failed: {e}")
            return False

    def disconnect(self):
        """Simulate disconnection"""
        self.is_running = False

        # Stop background thread gracefully
        if self._background_thread and self._background_thread.is_alive():
            self._background_thread.join(timeout=1.0)

        self.log_queue.put("DEMO: Unified demo connection closed")
        print("DEBUG: UnifiedDemoSerialCLI disconnected")

    def send_command(self, command: str) -> bool:
        """Simulate sending command to device"""
        if self.is_running:
            self.command_queue.put(command)
            self.log_queue.put(f"DEMO SENT: {command}")
            print(f"DEBUG: Demo command queued: {command}")
            return True
        else:
            print("DEBUG: Cannot send command - not running")
            return False

    def read_response(self) -> Optional[str]:
        """Simulate reading response from device"""
        if self.is_running:
            try:
                response = self.response_queue.get_nowait()
                self.log_queue.put(f"DEMO RECV: {response[:100]}...")  # Limit log size
                print(f"DEBUG: Demo response read: {len(response)} chars")
                return response
            except queue.Empty:
                return None
        return None

    def run_background(self):
        """
        FIXED: Background thread that processes commands with enhanced functionality
        """
        print("DEBUG: UnifiedDemoSerialCLI background thread started")
        self._background_thread = threading.current_thread()

        while self.is_running:
            try:
                # Check for commands with timeout
                try:
                    command = self.command_queue.get(timeout=0.1)
                    print(f"DEBUG: Background thread processing command: {command}")

                    # Process the command
                    response = self._handle_unified_command(command)

                    if response:
                        print(f"DEBUG: Generated response ({len(response)} chars)")

                        # Simulate realistic delay based on command
                        delay = self._get_command_delay(command)
                        if delay > 0:
                            print(f"DEBUG: Waiting {delay} seconds before sending response")
                            time.sleep(delay)

                        # Put response in queue
                        self.response_queue.put(response)
                        print(f"DEBUG: Response queued successfully")
                    else:
                        print(f"DEBUG: No response generated for command: {command}")

                except queue.Empty:
                    # No command to process, continue loop
                    pass

                # Update device state periodically
                self._update_device_state()

            except Exception as e:
                print(f"DEBUG: Background thread error: {e}")
                import traceback
                traceback.print_exc()

            # Small delay to prevent CPU spinning
            time.sleep(0.05)

        print("DEBUG: Background thread ending")

    def _handle_unified_command(self, command: str) -> Optional[str]:
        """
        FIXED: Handle commands with comprehensive response generation
        """
        command_lower = command.lower().strip()
        print(f"DEBUG: Processing command: '{command}' -> '{command_lower}'")

        # Handle sysinfo command (main command)
        if 'sysinfo' in command_lower:
            return self._handle_sysinfo_command()

        # Handle individual commands
        elif 'ver' in command_lower or 'version' in command_lower:
            return self._handle_ver_command()

        elif 'lsd' in command_lower:
            return self._handle_lsd_command()

        elif 'showport' in command_lower:
            return self._handle_showport_command()

        elif 'help' in command_lower:
            return self._handle_help_command()

        elif 'status' in command_lower:
            return self._handle_status_command()

        elif 'reset' in command_lower:
            return self._handle_reset_command(command)

        elif 'read_reg' in command_lower:
            return self._handle_read_register_command(command)

        elif 'write_reg' in command_lower:
            return self._handle_write_register_command(command)

        else:
            print(f"DEBUG: Unknown command: {command}")
            return f"ERROR: Unknown command '{command}'\nType 'help' for available commands.\n\nCmd>[]"

    def _handle_sysinfo_command(self) -> str:
        """Handle sysinfo command with dynamic data"""
        print("DEBUG: Handling sysinfo command")

        if self.demo_sysinfo_content:
            # Use file content as base but with dynamic updates
            base_content = self.demo_sysinfo_content

            # Apply dynamic updates to the content
            dynamic_content = self._apply_dynamic_updates(base_content)

            print(f"DEBUG: Returning dynamic sysinfo content ({len(dynamic_content)} chars)")
            return f"Cmd>sysinfo\n\n{dynamic_content}\n\nCmd>[]"
        else:
            print("DEBUG: No sysinfo content available")
            return "ERROR: Demo sysinfo data not available\n\nCmd>[]"

    def _apply_dynamic_updates(self, base_content: str) -> str:
        """Apply dynamic updates to base sysinfo content"""
        content = base_content

        # Update temperature (simulate slight variations)
        temp_variation = random.randint(-3, 3)
        new_temp = max(45, min(65, self.device_state['board_temperature'] + temp_variation))
        content = content.replace(
            f"Board Temperature : {self.device_state['board_temperature']} degree",
            f"Board Temperature : {new_temp} degree"
        )
        self.device_state['board_temperature'] = new_temp

        # Update fan speed (simulate slight variations)
        fan_variation = random.randint(-100, 100)
        new_fan_speed = max(5000, min(7000, self.device_state['fan_speed'] + fan_variation))
        content = content.replace(
            f"Switch Fan : {self.device_state['fan_speed']} rpm",
            f"Switch Fan : {new_fan_speed} rpm"
        )
        self.device_state['fan_speed'] = new_fan_speed

        # Update voltage slightly (simulate normal fluctuation)
        for voltage_key, base_value in [
            ('voltage_0_8v', 890),
            ('voltage_0_89v', 991),
            ('voltage_1_2v', 1304),
            ('voltage_1_5v', 1512)
        ]:
            variation = random.randint(-5, 5)
            new_value = base_value + variation
            self.device_state[voltage_key] = new_value

            # Update in content
            if voltage_key == 'voltage_0_8v':
                content = content.replace(
                    f"Board    0.8V  Voltage : {base_value} mV",
                    f"Board    0.8V  Voltage : {new_value} mV"
                )
            elif voltage_key == 'voltage_0_89v':
                content = content.replace(
                    f"Board   0.89V  Voltage : {base_value} mV",
                    f"Board   0.89V  Voltage : {new_value} mV"
                )
            elif voltage_key == 'voltage_1_2v':
                content = content.replace(
                    f"Board    1.2V  Voltage : {base_value} mV",
                    f"Board    1.2V  Voltage : {new_value} mV"
                )
            elif voltage_key == 'voltage_1_5v':
                content = content.replace(
                    f"Board    1.5v  Voltage : {base_value} mV",
                    f"Board    1.5v  Voltage : {new_value} mV"
                )

        # Update current draw
        current_variation = random.randint(-200, 200)
        new_current = max(9000, min(12000, self.device_state['current_draw'] + current_variation))
        content = content.replace(
            f"Current : {self.device_state['current_draw']} mA",
            f"Current : {new_current} mA"
        )
        self.device_state['current_draw'] = new_current

        return content

    def _handle_ver_command(self) -> str:
        """Handle ver command"""
        print("DEBUG: Handling ver command")
        return f"""Cmd>ver

S/N      : {self.device_state['serial_number']}
Company  : {self.device_state['company']}
Model    : {self.device_state['model']}
Version  : {self.device_state['firmware_version']}    Date : {self.device_state['build_date']}
SBR Version : {self.device_state['sbr_version']}

Cmd>[]"""

    def _handle_lsd_command(self) -> str:
        """Handle lsd command"""
        print("DEBUG: Handling lsd command")
        return f"""Cmd>lsd

Thermal:
        Board Temperature : {self.device_state['board_temperature']} degree

Fans Speed:
        Switch Fan : {self.device_state['fan_speed']} rpm

Voltage Sensors:
Board    0.8V  Voltage : {self.device_state['voltage_0_8v']} mV
Board   0.89V  Voltage : {self.device_state['voltage_0_89v']} mV
Board    1.2V  Voltage : {self.device_state['voltage_1_2v']} mV
Board    1.5v  Voltage : {self.device_state['voltage_1_5v']} mV

Current Status:
Current : {self.device_state['current_draw']} mA

Error Status:
Voltage    0.8V  error : {self.device_state['error_counts']['0_8v']}
Voltage   0.89V  error : {self.device_state['error_counts']['0_89v']}
Voltage    1.2V  error : {self.device_state['error_counts']['1_2v']}
Voltage    1.5v  error : {self.device_state['error_counts']['1_5v']}

Cmd>[]"""

    def _handle_showport_command(self) -> str:
        """Handle showport command"""
        print("DEBUG: Handling showport command")

        port_lines = []
        for port_num, port_data in self.device_state['port_states'].items():
            port_lines.append(
                f"Port{port_num}: speed {port_data['speed']}, width {port_data['width']}, max_speed06, max_width16")

        golden = self.device_state['golden_finger']

        return f"""Cmd>showport
Port Slot------------------------------------------------------------------------------

{chr(10).join(port_lines)}
Port Upstream------------------------------------------------------------------------------

Golden finger: speed {golden['speed']}, width {golden['width']}, max_width = 16

Cmd>[]"""

    def _handle_help_command(self) -> str:
        """Handle help command"""
        print("DEBUG: Handling help command")
        return """Cmd>help

Available commands:
help       - Show this help
sysinfo    - Get complete system information (ver + lsd + showport)
ver        - Get device version information
lsd        - Get system diagnostics and sensors  
showport   - Get port status information
status     - Get device status
reset      - Reset device (soft_reset, hard_reset, etc.)
read_reg   - Read register value
write_reg  - Write register value

Demo Mode: All responses use realistic simulated data

Cmd>[]"""

    def _handle_status_command(self) -> str:
        """Handle status command"""
        print("DEBUG: Handling status command")
        return f"""Cmd>status

Device Status: ONLINE (DEMO MODE)
Serial Number: {self.device_state['serial_number']}
Power Status: GOOD
Temperature: {self.device_state['board_temperature']}°C
Fan Speed: {self.device_state['fan_speed']} rpm
Link Status: ACTIVE
Uptime: {self.device_state['uptime_hours']}h {random.randint(10, 59)}m
Total Errors: {sum(self.device_state['error_counts'].values())}

Note: Demo mode using realistic simulation

Cmd>[]"""

    def _handle_reset_command(self, command: str) -> str:
        """Handle reset commands"""
        print(f"DEBUG: Handling reset command: {command}")

        if 'soft' in command.lower():
            reset_type = "Soft Reset"
        elif 'hard' in command.lower():
            reset_type = "Hard Reset"
        elif 'factory' in command.lower():
            reset_type = "Factory Reset"
        elif 'link' in command.lower():
            reset_type = "Link Reset"
        else:
            reset_type = "System Reset"

        # Simulate reset by updating device state
        self._simulate_reset()

        return f"""Cmd>{command}

{reset_type} initiated...
Device resetting... Please wait.

{reset_type} completed successfully.
Device is now online.

Cmd>[]"""

    def _handle_read_register_command(self, command: str) -> str:
        """Handle read register command"""
        print(f"DEBUG: Handling read register command: {command}")

        # Extract register address from command
        parts = command.split()
        if len(parts) >= 2:
            reg_addr = parts[1]
            # Simulate register value
            reg_value = f"0x{random.randint(0x1000, 0xFFFF):04X}"
            return f"""Cmd>{command}

Register {reg_addr}: {reg_value}

Cmd>[]"""
        else:
            return f"""Cmd>{command}

ERROR: Register address required
Usage: read_reg <address>

Cmd>[]"""

    def _handle_write_register_command(self, command: str) -> str:
        """Handle write register command"""
        print(f"DEBUG: Handling write register command: {command}")

        parts = command.split()
        if len(parts) >= 3:
            reg_addr = parts[1]
            reg_value = parts[2]
            return f"""Cmd>{command}

Register {reg_addr} written with value {reg_value}
Write operation completed successfully.

Cmd>[]"""
        else:
            return f"""Cmd>{command}

ERROR: Register address and value required
Usage: write_reg <address> <value>

Cmd>[]"""

    def _simulate_reset(self):
        """Simulate device reset by updating state"""
        # Reset error counts
        for key in self.device_state['error_counts']:
            self.device_state['error_counts'][key] = 0

        # Reset uptime
        self.device_state['uptime_hours'] = 0

        # Reset some values to defaults
        self.device_state['board_temperature'] = 45  # Lower after reset
        self.device_state['fan_speed'] = 5500  # Reset to default

        print("DEBUG: Device state reset simulated")

    def _update_device_state(self):
        """Periodically update device state for realism"""
        current_time = time.time()

        # Update every 30 seconds
        if current_time - self.device_state['last_update'] > 30:
            # Increment uptime
            self.device_state['uptime_hours'] += 1 / 120  # 30 seconds = 1/120 hour

            # Occasionally introduce minor errors (very rarely)
            if random.random() < 0.001:  # 0.1% chance
                error_key = random.choice(list(self.device_state['error_counts'].keys()))
                self.device_state['error_counts'][error_key] += 1
                print(f"DEBUG: Simulated error in {error_key}")

            self.device_state['last_update'] = current_time

    def _get_command_delay(self, command: str) -> float:
        """Get realistic delay for command response"""
        command_lower = command.lower()

        if 'sysinfo' in command_lower:
            return 0.5  # sysinfo takes longer
        elif 'lsd' in command_lower:
            return 0.3  # diagnostics take some time
        elif 'showport' in command_lower:
            return 0.2  # port info takes moderate time
        elif 'reset' in command_lower:
            return 1.0  # reset operations take longer
        elif any(cmd in command_lower for cmd in ['help', 'status', 'ver']):
            return 0.1  # Quick response for simple commands
        else:
            return 0.1  # Default delay


class DemoDeviceStateManager:
    """
    Manages demo device state and provides integration points for other modules
    """

    def __init__(self, demo_cli: UnifiedDemoSerialCLI):
        self.demo_cli = demo_cli
        self._state_lock = threading.Lock()

    def get_current_state(self) -> Dict[str, Any]:
        """Get current device state for external modules"""
        with self._state_lock:
            return self.demo_cli.device_state.copy()

    def update_state(self, updates: Dict[str, Any]):
        """Update device state from external modules"""
        with self._state_lock:
            self.demo_cli.device_state.update(updates)

    def simulate_event(self, event_type: str, **kwargs):
        """Simulate specific events for testing"""
        with self._state_lock:
            if event_type == "temperature_spike":
                self.demo_cli.device_state['board_temperature'] += kwargs.get('increase', 10)
            elif event_type == "voltage_error":
                rail = kwargs.get('rail', '0_8v')
                if rail in self.demo_cli.device_state['error_counts']:
                    self.demo_cli.device_state['error_counts'][rail] += 1
            elif event_type == "fan_failure":
                self.demo_cli.device_state['fan_speed'] = kwargs.get('new_speed', 0)

        print(f"DEBUG: Simulated event: {event_type} with {kwargs}")


# Integration helpers for existing modules
def create_demo_host_card_manager(demo_cli):
    """Create a HostCardInfoManager configured for demo mode"""
    from host_card_info import HostCardInfoManager
    return HostCardInfoManager(demo_cli)


def create_demo_cache_manager():
    """Create a DeviceDataCache configured for demo mode"""
    from cache_manager import DeviceDataCache
    return DeviceDataCache(default_ttl=300)  # 5 minute TTL for demo


def create_demo_parser(cache_manager):
    """Create an EnhancedSystemInfoParser configured for demo mode"""
    from enhanced_sysinfo_parser import EnhancedSystemInfoParser
    return EnhancedSystemInfoParser(cache_manager)


# Test function
if __name__ == "__main__":
    print("Testing FIXED UnifiedDemoSerialCLI...")

    # Test basic functionality
    demo = UnifiedDemoSerialCLI()

    if demo.connect():
        print("✓ Demo CLI connected successfully")

        # Start background thread
        bg_thread = threading.Thread(target=demo.run_background, daemon=True)
        bg_thread.start()
        print("✓ Background thread started")

        # Test various commands
        test_commands = ['sysinfo', 'ver', 'lsd', 'showport', 'help', 'status']

        for cmd in test_commands:
            print(f"\n--- Testing command: {cmd} ---")
            demo.send_command(cmd)
            time.sleep(1.0)  # Wait for response

            try:
                response = demo.response_queue.get_nowait()
                print(f"Response received ({len(response)} chars):")
                print(response[:200] + "..." if len(response) > 200 else response)
            except queue.Empty:
                print("No response received")

        # Test integration components
        print("\n--- Testing Integration Components ---")

        # Test state manager
        state_mgr = DemoDeviceStateManager(demo)
        current_state = state_mgr.get_current_state()
        print(f"✓ State manager works - current temp: {current_state['board_temperature']}°C")

        # Test event simulation
        state_mgr.simulate_event("temperature_spike", increase=5)
        new_state = state_mgr.get_current_state()
        print(f"✓ Event simulation works - new temp: {new_state['board_temperature']}°C")

        demo.disconnect()
        print("✓ Demo CLI disconnected")

    else:
        print("✗ Demo CLI connection failed")

    print("\nFixed demo integration test completed!")