"""
demo_mode_integration.py

This file contains the demo mode classes for the Serial Dashboard Application.
Save this as a separate Python file in the same directory as your main application.

File Structure:
your_project_folder/
├── serial_dashboard_app.py     (your main application file)
├── demo_mode_integration.py    (this file)
└── requirements.txt            (optional)
"""

import random
import time
import threading
import queue
from datetime import datetime


class DemoSerialCLI:
    """
    Demo version of SerialCLI that simulates device responses
    This class provides the same interface as SerialCLI but simulates all responses
    """

    def __init__(self, port="DEMO"):
        self.port = port
        self.baudrate = 115200
        self.serial_connection = None
        self.is_running = False
        self.command_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.log_queue = queue.Queue()

        # Demo device state - simulates a real device's internal state
        self.device_state = {
            'connected': True,
            'temperature': 45.0,
            'power_status': True,
            'link_active': True,
            'link_speed': '5.0 Gbps',
            'uptime_hours': random.randint(1, 999),
            'uptime_minutes': random.randint(1, 59),
            'ports': {
                'port1': {'enabled': True, 'speed': 'High Speed', 'device_connected': True},
                'port2': {'enabled': True, 'speed': 'Super Speed', 'device_connected': False},
                'port3': {'enabled': False, 'speed': 'N/A', 'device_connected': False},
                'port4': {'enabled': True, 'speed': 'High Speed', 'device_connected': True}
            },
            'registers': {
                '0x00': '0x1234',  # Device ID
                '0x04': '0x5678',  # Vendor ID
                '0x08': '0x0001',  # Status Register
                '0x0C': '0x8000',  # Control Register
                '0x10': '0x4321',  # Configuration Register
                '0x14': '0x0000',  # Error Register
                '0x18': '0xFFFF',  # Capability Register
                '0x1C': '0x2024'  # Version Register
            },
            'firmware_version': 'v2.1.3',
            'hardware_revision': 'Rev C',
            'serial_number': 'DEMO-2024-001',
            'packets_tx': random.randint(1000000, 9999999),
            'packets_rx': random.randint(1000000, 9999999),
            'crc_errors': random.randint(0, 10),
            'timeout_errors': random.randint(0, 5),
            'total_errors': 0
        }

        # Calculate total errors
        self.device_state['total_errors'] = (
                self.device_state['crc_errors'] +
                self.device_state['timeout_errors']
        )

        # Command response mappings
        self.command_responses = {
            'help': self._get_help_response,
            'status': self._get_status_response,
            'version': self._get_version_response,
            'info': self._get_device_info_response,
            'link_status': self._get_link_status_response,
            'port_status': self._get_port_status_response,
            'temp': self._get_temperature_response,
            'uptime': self._get_uptime_response,
            'errors': self._get_error_response,
            'reset_errors': self._reset_error_counters,
            'soft_reset': self._handle_soft_reset,
            'hard_reset': self._handle_hard_reset,
            'factory_reset': self._handle_factory_reset,
            'link_reset': self._handle_link_reset,
            'enable_debug': self._enable_debug_mode,
            'disable_debug': self._disable_debug_mode,
            'get_config': self._get_configuration,
            'save_config': self._save_configuration
        }

        # Debug mode state
        self.debug_mode = False

    def connect(self):
        """Simulate connection establishment"""
        self.log_queue.put("DEMO: Initializing connection...")
        time.sleep(0.2)  # Simulate connection delay

        self.log_queue.put("DEMO: Performing handshake...")
        time.sleep(0.3)

        self.log_queue.put("DEMO: Connection established successfully")
        self.is_running = True

        # Log initial connection info
        self.log_queue.put(f"DEMO: Device detected - {self.device_state['firmware_version']}")
        self.log_queue.put(f"DEMO: Serial number - {self.device_state['serial_number']}")

        return True

    def disconnect(self):
        """Simulate disconnection"""
        self.is_running = False
        self.log_queue.put("DEMO: Connection closed gracefully")

    def send_command(self, command):
        """Simulate sending command to device"""
        if self.is_running:
            self.log_queue.put(f"DEMO SENT: {command}")
            return True
        return False

    def read_response(self):
        """Simulate reading response from device"""
        if self.is_running:
            try:
                response = self.response_queue.get_nowait()
                self.log_queue.put(f"DEMO RECV: {response}")
                return response
            except queue.Empty:
                return None
        return None

    def run_background(self):
        """Background thread for handling demo responses"""
        while self.is_running:
            # Handle commands and generate responses
            try:
                command = self.command_queue.get_nowait()
                response = self._generate_response(command)
                if response:
                    # Simulate realistic response delay
                    delay = random.uniform(0.1, 0.4)
                    time.sleep(delay)
                    self.response_queue.put(response)

            except queue.Empty:
                pass

            # Occasionally update dynamic values to simulate real device
            if random.random() < 0.05:  # 5% chance each cycle
                self._update_dynamic_values()

            # Small delay to prevent CPU spinning
            time.sleep(0.02)

    def _generate_response(self, command):
        """Generate appropriate response for command"""
        cmd_parts = command.lower().strip().split()
        if not cmd_parts:
            return "ERROR: Empty command"

        base_cmd = cmd_parts[0]

        # Handle register operations
        if base_cmd.startswith('read_reg') or base_cmd == 'read':
            return self._handle_read_register(cmd_parts)
        elif base_cmd.startswith('write_reg') or base_cmd == 'write':
            return self._handle_write_register(cmd_parts)
        elif base_cmd.startswith('port'):
            return self._handle_port_command(cmd_parts)
        elif base_cmd in self.command_responses:
            return self.command_responses[base_cmd]()
        else:
            # Unknown command - provide helpful suggestion
            suggestions = self._get_command_suggestions(base_cmd)
            return f"ERROR: Unknown command '{command}'\n{suggestions}"

    def _get_command_suggestions(self, unknown_cmd):
        """Provide command suggestions for unknown commands"""
        all_commands = list(self.command_responses.keys()) + ['read_reg', 'write_reg', 'port']

        # Simple fuzzy matching
        suggestions = []
        for cmd in all_commands:
            if unknown_cmd in cmd or cmd in unknown_cmd:
                suggestions.append(cmd)

        if suggestions:
            return f"Did you mean: {', '.join(suggestions[:3])}?\nType 'help' for all commands."
        else:
            return "Type 'help' for available commands."

    def _get_help_response(self):
        """Return comprehensive help information"""
        return """=== DEMO DEVICE COMMAND REFERENCE ===

BASIC COMMANDS:
  help                    - Show this help information
  status                  - Get overall device status  
  version                 - Get firmware version
  info                    - Get detailed device information
  temp                    - Get current temperature
  uptime                  - Get device uptime

LINK COMMANDS:
  link_status             - Check communication link status
  link_reset              - Reset communication link

PORT COMMANDS:
  port_status             - Get all port status information
  port <num> enable       - Enable specific port (1-4)
  port <num> disable      - Disable specific port (1-4)
  port <num> status       - Get specific port status

REGISTER COMMANDS:
  read_reg <addr>         - Read register (e.g., read_reg 0x00)
  write_reg <addr> <val>  - Write register (e.g., write_reg 0x10 0x1234)

ERROR COMMANDS:
  errors                  - Get error statistics
  reset_errors            - Clear all error counters

RESET COMMANDS:
  soft_reset              - Perform software reset
  hard_reset              - Perform hardware reset
  factory_reset           - Reset to factory defaults

CONFIGURATION:
  get_config              - Show current configuration
  save_config             - Save current configuration to flash

DEBUG COMMANDS:
  enable_debug            - Enable debug mode
  disable_debug           - Disable debug mode

All commands are case-insensitive. Use 'Ctrl+C' to cancel operations."""

    def _get_status_response(self):
        """Return comprehensive device status"""
        temp = self.device_state['temperature']
        power = "ACTIVE" if self.device_state['power_status'] else "STANDBY"
        link = "CONNECTED" if self.device_state['link_active'] else "DISCONNECTED"
        debug = "ENABLED" if self.debug_mode else "DISABLED"

        # Calculate error rate
        total_packets = self.device_state['packets_tx'] + self.device_state['packets_rx']
        error_rate = (self.device_state['total_errors'] / max(total_packets, 1)) * 100

        # Count enabled ports
        enabled_ports = sum(1 for port in self.device_state['ports'].values() if port['enabled'])

        return f"""=== DEVICE STATUS ===
Overall Status: OPERATIONAL
Temperature: {temp:.1f}°C (Normal)
Power Status: {power}
Link Status: {link} ({self.device_state['link_speed']})
Enabled Ports: {enabled_ports}/4
Total Errors: {self.device_state['total_errors']} (Rate: {error_rate:.3f}%)
Debug Mode: {debug}
Uptime: {self.device_state['uptime_hours']}h {self.device_state['uptime_minutes']}m

Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

    def _get_version_response(self):
        """Return firmware and hardware version info"""
        return f"""=== VERSION INFORMATION ===
Firmware Version: {self.device_state['firmware_version']}
Hardware Revision: {self.device_state['hardware_revision']}
Serial Number: {self.device_state['serial_number']}
Build Date: 2024-01-15
Build Number: 20240115-001
Bootloader: v1.2.1
Demo Mode: ACTIVE"""

    def _get_device_info_response(self):
        """Return detailed device information"""
        return f"""=== DEVICE INFORMATION ===
Device Type: USB 3.0 Host Controller (Demo)
Manufacturer: Demo Electronics Inc.
Model: DH-3000-DEMO
Serial Number: {self.device_state['serial_number']}
Firmware: {self.device_state['firmware_version']}
Hardware: {self.device_state['hardware_revision']}

SPECIFICATIONS:
• Max Ports: 4
• Max Speed: USB 3.0 SuperSpeed (5 Gbps)
• Power: Bus-powered (900mA max)
• Operating Temperature: 0°C to +70°C
• Certifications: USB-IF, FCC, CE (Simulated)

CURRENT CONFIGURATION:
• Port 1: {"Enabled" if self.device_state['ports']['port1']['enabled'] else "Disabled"}
• Port 2: {"Enabled" if self.device_state['ports']['port2']['enabled'] else "Disabled"}
• Port 3: {"Enabled" if self.device_state['ports']['port3']['enabled'] else "Disabled"}
• Port 4: {"Enabled" if self.device_state['ports']['port4']['enabled'] else "Disabled"}"""

    def _get_link_status_response(self):
        """Return detailed link status"""
        training_status = "COMPLETE" if self.device_state['link_active'] else "FAILED"
        error_rate = (self.device_state['total_errors'] /
                      max(self.device_state['packets_tx'] + self.device_state['packets_rx'], 1)) * 100

        return f"""=== LINK STATUS ===
Link State: {"ACTIVE" if self.device_state['link_active'] else "INACTIVE"}
Link Speed: {self.device_state['link_speed']} (USB 3.0)
Link Training: {training_status}
Signal Quality: GOOD

TRAFFIC STATISTICS:
• Packets Transmitted: {self.device_state['packets_tx']:,}
• Packets Received: {self.device_state['packets_rx']:,}
• CRC Errors: {self.device_state['crc_errors']}
• Timeout Errors: {self.device_state['timeout_errors']}
• Overall Error Rate: {error_rate:.4f}%

LINK PARAMETERS:
• LFPS Detection: ENABLED
• Receiver Termination: 90Ω ±15%
• Transmit Amplitude: 1000mV ±10%
• Last Link Training: {datetime.now().strftime('%H:%M:%S')}"""

    def _get_port_status_response(self):
        """Return status of all ports"""
        status_lines = ["=== PORT STATUS ==="]

        for port_id, port_info in self.device_state['ports'].items():
            port_num = port_id[-1]  # Extract number from 'port1', etc.
            status = "ENABLED" if port_info['enabled'] else "DISABLED"
            speed = port_info['speed']
            device = "DEVICE CONNECTED" if port_info['device_connected'] else "NO DEVICE"

            status_lines.append(f"Port {port_num}: {status} | {speed} | {device}")

        return "\n".join(status_lines)

    def _get_temperature_response(self):
        """Return current temperature reading"""
        temp = self.device_state['temperature']
        status = "NORMAL"
        if temp > 60:
            status = "HIGH"
        elif temp > 70:
            status = "CRITICAL"

        return f"Temperature: {temp:.1f}°C ({status})"

    def _get_uptime_response(self):
        """Return device uptime"""
        return f"Device Uptime: {self.device_state['uptime_hours']}h {self.device_state['uptime_minutes']}m"

    def _get_error_response(self):
        """Return error statistics"""
        return f"""=== ERROR STATISTICS ===
CRC Errors: {self.device_state['crc_errors']}
Timeout Errors: {self.device_state['timeout_errors']}
Total Errors: {self.device_state['total_errors']}
Last Error: {"None" if self.device_state['total_errors'] == 0 else "CRC mismatch (Port 2)"}
Error Log: {"Empty" if self.device_state['total_errors'] == 0 else "3 entries available"}"""

    def _reset_error_counters(self):
        """Reset all error counters"""
        self.device_state['crc_errors'] = 0
        self.device_state['timeout_errors'] = 0
        self.device_state['total_errors'] = 0
        return "All error counters have been reset to zero."

    def _handle_read_register(self, cmd_parts):
        """Handle register read command"""
        if len(cmd_parts) < 2:
            return "ERROR: Missing register address\nUsage: read_reg <address> (e.g., read_reg 0x00)"

        addr = cmd_parts[1].upper()
        # Ensure address starts with 0x
        if not addr.startswith('0X'):
            addr = '0X' + addr.lstrip('0X')

        if addr in self.device_state['registers']:
            reg_value = self.device_state['registers'][addr]
            return f"Register {addr}: {reg_value}"
        else:
            # Generate random value for unknown registers
            random_val = f"0x{random.randint(0, 65535):04X}"
            self.device_state['registers'][addr] = random_val
            return f"Register {addr}: {random_val} (initialized)"

    def _handle_write_register(self, cmd_parts):
        """Handle register write command"""
        if len(cmd_parts) < 3:
            return "ERROR: Missing register address or value\nUsage: write_reg <address> <value> (e.g., write_reg 0x10 0x1234)"

        addr = cmd_parts[1].upper()
        value = cmd_parts[2].upper()

        # Ensure addresses and values start with 0x
        if not addr.startswith('0X'):
            addr = '0X' + addr.lstrip('0X')
        if not value.startswith('0X'):
            value = '0X' + value.lstrip('0X')

        # Simulate write protection for certain registers
        protected_regs = ['0X00', '0X04']  # Device ID and Vendor ID
        if addr in protected_regs:
            return f"ERROR: Register {addr} is write-protected"

        self.device_state['registers'][addr] = value
        return f"Register {addr} written: {value}"

    def _handle_port_command(self, cmd_parts):
        """Handle port-specific commands"""
        if len(cmd_parts) < 2:
            return "ERROR: Missing port command\nUsage: port <number> <action> (e.g., port 1 enable)"

        try:
            port_num = int(cmd_parts[1])
            if port_num < 1 or port_num > 4:
                return "ERROR: Port number must be 1-4"

            port_key = f"port{port_num}"

            if len(cmd_parts) < 3:
                # Just show status for this port
                port_info = self.device_state['ports'][port_key]
                status = "ENABLED" if port_info['enabled'] else "DISABLED"
                device = "DEVICE CONNECTED" if port_info['device_connected'] else "NO DEVICE"
                return f"Port {port_num}: {status} | {port_info['speed']} | {device}"

            action = cmd_parts[2].lower()
            if action == 'enable':
                self.device_state['ports'][port_key]['enabled'] = True
                return f"Port {port_num} enabled"
            elif action == 'disable':
                self.device_state['ports'][port_key]['enabled'] = False
                return f"Port {port_num} disabled"
            elif action == 'status':
                port_info = self.device_state['ports'][port_key]
                status = "ENABLED" if port_info['enabled'] else "DISABLED"
                device = "DEVICE CONNECTED" if port_info['device_connected'] else "NO DEVICE"
                return f"Port {port_num}: {status} | {port_info['speed']} | {device}"
            else:
                return f"ERROR: Unknown port action '{action}'\nValid actions: enable, disable, status"

        except ValueError:
            return "ERROR: Invalid port number. Use 1-4."

    def _handle_soft_reset(self):
        """Handle soft reset command"""
        self.device_state['packets_tx'] = 0
        self.device_state['packets_rx'] = 0
        self.device_state['uptime_hours'] = 0
        self.device_state['uptime_minutes'] = 0
        return "Soft reset completed - statistics cleared, configuration preserved"

    def _handle_hard_reset(self):
        """Handle hard reset command"""
        self.device_state['temperature'] = random.randint(40, 50)
        self.device_state['packets_tx'] = 0
        self.device_state['packets_rx'] = 0
        self.device_state['uptime_hours'] = 0
        self.device_state['uptime_minutes'] = 0
        self.device_state['crc_errors'] = 0
        self.device_state['timeout_errors'] = 0
        self.device_state['total_errors'] = 0
        return "Hard reset completed - full hardware reinitialize"

    def _handle_factory_reset(self):
        """Handle factory reset command"""
        # Reset to factory defaults
        self.device_state.update({
            'temperature': 25.0,
            'packets_tx': 0,
            'packets_rx': 0,
            'crc_errors': 0,
            'timeout_errors': 0,
            'total_errors': 0,
            'uptime_hours': 0,
            'uptime_minutes': 0,
            'ports': {
                'port1': {'enabled': True, 'speed': 'High Speed', 'device_connected': False},
                'port2': {'enabled': True, 'speed': 'Super Speed', 'device_connected': False},
                'port3': {'enabled': False, 'speed': 'N/A', 'device_connected': False},
                'port4': {'enabled': True, 'speed': 'High Speed', 'device_connected': False}
            },
            'registers': {
                '0x00': '0x1234',
                '0x04': '0x5678',
                '0x08': '0x0001',
                '0x0C': '0x8000',
                '0x10': '0x4321',
                '0x14': '0x0000',
                '0x18': '0xFFFF',
                '0x1C': '0x2024'
            }
        })
        self.debug_mode = False
        return "Factory reset completed - all settings restored to factory defaults"

    def _handle_link_reset(self):
        """Handle link reset command"""
        self.device_state['link_active'] = False
        self.device_state['packets_tx'] = 0
        self.device_state['packets_rx'] = 0

        # Simulate link reestablishment after delay
        def reestablish_link():
            time.sleep(2.0)
            self.device_state['link_active'] = True
            self.log_queue.put("DEMO: Link reestablished automatically")

        threading.Thread(target=reestablish_link, daemon=True).start()
        return "Link reset initiated - reestablishing connection..."

    def _enable_debug_mode(self):
        """Enable debug mode"""
        self.debug_mode = True
        return "Debug mode ENABLED - verbose logging active"

    def _disable_debug_mode(self):
        """Disable debug mode"""
        self.debug_mode = False
        return "Debug mode DISABLED - normal logging active"

    def _get_configuration(self):
        """Get current device configuration"""
        enabled_ports = [p for p, info in self.device_state['ports'].items() if info['enabled']]
        return f"""=== CURRENT CONFIGURATION ===
Enabled Ports: {len(enabled_ports)} ({', '.join([p[-1] for p in enabled_ports])})
Debug Mode: {"ENABLED" if self.debug_mode else "DISABLED"}
Temperature Monitoring: ENABLED
Error Logging: ENABLED
Auto-recovery: ENABLED
Configuration Source: {"Factory Defaults" if self.device_state['total_errors'] == 0 else "User Modified"}"""

    def _save_configuration(self):
        """Save current configuration"""
        return "Configuration saved to flash memory (simulated)"

    def _update_dynamic_values(self):
        """Update dynamic values to simulate a real device"""
        # Slight temperature fluctuation
        temp_change = random.uniform(-0.5, 0.5)
        self.device_state['temperature'] += temp_change
        self.device_state['temperature'] = max(20, min(80, self.device_state['temperature']))

        # Increment packet counters if link is active
        if self.device_state['link_active']:
            self.device_state['packets_tx'] += random.randint(1, 50)
            self.device_state['packets_rx'] += random.randint(1, 50)

        # Occasionally introduce errors (very rarely)
        if random.random() < 0.01:  # 1% chance
            error_type = random.choice(['crc', 'timeout'])
            if error_type == 'crc':
                self.device_state['crc_errors'] += 1
            else:
                self.device_state['timeout_errors'] += 1
            self.device_state['total_errors'] = (
                    self.device_state['crc_errors'] +
                    self.device_state['timeout_errors']
            )

        # Update uptime occasionally
        if random.random() < 0.1:  # 10% chance
            self.device_state['uptime_minutes'] += 1
            if self.device_state['uptime_minutes'] >= 60:
                self.device_state['uptime_minutes'] = 0
                self.device_state['uptime_hours'] += 1

        # Simulate device connections/disconnections on ports
        for port_info in self.device_state['ports'].values():
            if port_info['enabled'] and random.random() < 0.02:  # 2% chance
                port_info['device_connected'] = not port_info['device_connected']


# Test function - only runs when this file is executed directly
if __name__ == "__main__":
    print("Testing DemoSerialCLI...")

    demo = DemoSerialCLI()
    demo.connect()

    # Start background thread
    bg_thread = threading.Thread(target=demo.run_background, daemon=True)
    bg_thread.start()

    # Test commands
    test_commands = [
        "help",
        "status",
        "version",
        "link_status",
        "read_reg 0x00",
        "write_reg 0x20 0xDEAD",
        "port 1 status",
        "port 2 disable",
        "errors",
        "unknown_command"
    ]

    print("\nTesting commands:")
    for cmd in test_commands:
        print(f"\n> {cmd}")
        demo.command_queue.put(cmd)
        time.sleep(0.5)

        try:
            response = demo.response_queue.get_nowait()
            print(response)
        except:
            print("No response")

    demo.disconnect()
    print("\nDemo test complete!")