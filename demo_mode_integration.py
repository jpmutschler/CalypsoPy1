import random
import time
import threading
import queue
from datetime import datetime
import os


class UnifiedDemoSerialCLI:
    """
    FIXED VERSION: Unified Demo CLI with enhanced debugging and proper threading
    """

    def __init__(self, port="DEMO"):
        self.port = port
        self.baudrate = 115200
        self.serial_connection = None
        self.is_running = False
        self.command_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.log_queue = queue.Queue()

        # Load demo sysinfo file at initialization
        self.demo_sysinfo_content = self._load_demo_sysinfo_file()

        print(f"DEBUG: UnifiedDemoSerialCLI initialized for {port}")
        if self.demo_sysinfo_content:
            print(f"DEBUG: Demo content loaded: {len(self.demo_sysinfo_content)} chars")
        else:
            print("DEBUG: No demo content loaded")

    def _load_demo_sysinfo_file(self):
        """Load sysinfo.txt from multiple possible locations with enhanced debugging"""
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
                    else:
                        print("DEBUG: ⚠ Content missing expected sections")

                    return content
                except Exception as e:
                    print(f"DEBUG: ✗ Error loading {path}: {e}")
                    continue
            else:
                print(f"DEBUG: ✗ Path does not exist: {abs_path}")

        print("DEBUG: No sysinfo file found - creating fallback data")
        return self._create_fallback_sysinfo()

    def _create_fallback_sysinfo(self):
        """Create fallback sysinfo data if file not found"""
        fallback_content = """================================================================================
ver
================================================================================

S/N      : DEMO12345678
Company  : SerialCables,Inc
Model    : DEMO-DEVICE-MODEL
Version  : 1.0.0    Date : Aug 09 2025 12:00:00
SBR Version : 0 34 160 28

================================================================================
lsd
================================================================================

Thermal:
        Board Temperature : 45 degree

Fans Speed:
        Switch Fan : 5500 rpm

Voltage Sensors:
Board    0.8V  Voltage : 850 mV
Board   0.89V  Voltage : 920 mV
Board    1.2V  Voltage : 1250 mV
Board    1.5v  Voltage : 1480 mV

Current Status:
Current : 9500 mA

Error Status:
Voltage    0.8V  error : 0
Voltage   0.89V  error : 0
Voltage    1.2V  error : 0
Voltage    1.5v  error : 0

================================================================================
showport
================================================================================
Port Slot------------------------------------------------------------------------------

Port80 : speed 01, width 00, max_speed06, max_width16
Port112: speed 01, width 00, max_speed06, max_width16
Port128: speed 01, width 00, max_speed06, max_width16
Port Upstream------------------------------------------------------------------------------

Golden finger: speed 01, width 00, max_width = 16"""

        print("DEBUG: Created fallback sysinfo data")
        return fallback_content

    def connect(self):
        """Simulate connection establishment"""
        self.log_queue.put("DEMO: Initializing unified demo mode...")
        time.sleep(0.1)

        if self.demo_sysinfo_content:
            content_preview = self.demo_sysinfo_content[:100].replace('\n', ' ')
            self.log_queue.put(f"DEMO: sysinfo data loaded - {content_preview}...")
        else:
            self.log_queue.put("DEMO: WARNING - sysinfo data not available")

        self.log_queue.put("DEMO: Connection established successfully")
        self.is_running = True

        print("DEBUG: UnifiedDemoSerialCLI connected successfully")
        return True

    def disconnect(self):
        """Simulate disconnection"""
        self.is_running = False
        self.log_queue.put("DEMO: Unified demo connection closed")
        print("DEBUG: UnifiedDemoSerialCLI disconnected")

    def send_command(self, command):
        """Simulate sending command to device"""
        if self.is_running:
            # Put command in queue for background processing
            self.command_queue.put(command)
            self.log_queue.put(f"DEMO SENT: {command}")
            print(f"DEBUG: Demo command queued: {command}")
            return True
        else:
            print("DEBUG: Cannot send command - not running")
            return False

    def read_response(self):
        """Simulate reading response from device"""
        if self.is_running:
            try:
                response = self.response_queue.get_nowait()
                self.log_queue.put(f"DEMO RECV: {response[:100]}...")  # Limit log size
                print(f"DEBUG: Demo response read: {len(response)} chars")
                return response
            except queue.Empty:
                print("DEBUG: No response in queue")
                return None
        return None

    def run_background(self):
        """
        FIXED: Background thread that processes commands with enhanced debugging
        This method was missing and causing the 'run_background' error.
        """
        print("DEBUG: UnifiedDemoSerialCLI background thread started")

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

                        # Simulate realistic delay
                        delay = self._get_command_delay(command)
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

            except Exception as e:
                print(f"DEBUG: Background thread error: {e}")
                import traceback
                traceback.print_exc()

            # Small delay to prevent CPU spinning
            time.sleep(0.05)

        print("DEBUG: Background thread ending")

    def _handle_unified_command(self, command):
        """
        FIXED: Handle commands with better debugging
        """
        command_lower = command.lower().strip()
        print(f"DEBUG: Processing command: '{command}' -> '{command_lower}'")

        if 'sysinfo' in command_lower:
            print("DEBUG: Handling sysinfo command")

            if self.demo_sysinfo_content:
                print(f"DEBUG: Returning sysinfo content ({len(self.demo_sysinfo_content)} chars)")

                # Verify content before returning
                if len(self.demo_sysinfo_content) > 100:
                    print("DEBUG: Content size verification passed")

                    # Format response like real device
                    formatted_response = f"Cmd>sysinfo\n\n{self.demo_sysinfo_content}\n\nCmd>[]"
                    return formatted_response
                else:
                    print("DEBUG: ⚠ Content seems too small")
                    return "ERROR: Demo sysinfo data too small"

            else:
                print("DEBUG: No sysinfo content available")
                return "ERROR: Demo sysinfo data not available"

        elif 'help' in command_lower:
            print("DEBUG: Handling help command")
            return self._get_help_response()

        elif 'status' in command_lower:
            print("DEBUG: Handling status command")
            return self._get_status_response()

        elif 'version' in command_lower or 'ver' in command_lower:
            print("DEBUG: Handling version command")
            return self._get_version_response()

        else:
            print(f"DEBUG: Unknown command: {command}")
            return f"ERROR: Unknown command '{command}'\nType 'help' for available commands."

    def _get_command_delay(self, command):
        """Get realistic delay for command response"""
        command_lower = command.lower()

        if 'sysinfo' in command_lower:
            return 0.3  # Reduced delay for testing
        elif any(cmd in command_lower for cmd in ['help', 'status', 'version']):
            return 0.05  # Quick response for simple commands
        else:
            return 0.1  # Default delay

    def _get_help_response(self):
        """Generate help command response"""
        return """Available commands:
help      - Show this help
sysinfo   - Get complete system information (ver + lsd + showport)
status    - Get device status
version   - Get firmware version

Demo Mode: All responses use actual device data from sysinfo.txt"""

    def _get_status_response(self):
        """Generate status command response"""
        return """Device Status: ONLINE (DEMO MODE)
Power: GOOD
Temperature: 45°C
Link: ACTIVE
Uptime: 1h 23m
Errors: 0

Note: Demo mode using unified workflow with file data"""

    def _get_version_response(self):
        """Generate version command response"""
        return """Firmware Version: 1.0.0 (DEMO)
Hardware Rev: Rev C
Serial Number: DEMO12345678
Build Date: Aug 09 2025 12:00:00
Bootloader: v1.0.5

Note: Demo mode - data from sysinfo.txt file"""


# Test function - only runs when this file is executed directly
if __name__ == "__main__":
    print("Testing Fixed UnifiedDemoSerialCLI...")

    demo = UnifiedDemoSerialCLI()
    demo.connect()

    # Start background thread
    bg_thread = threading.Thread(target=demo.run_background, daemon=True)
    bg_thread.start()

    # Test sysinfo command
    print("\nTesting sysinfo command:")
    demo.command_queue.put("sysinfo")
    time.sleep(1.0)  # Give time for response

    try:
        response = demo.response_queue.get_nowait()
        print(f"Response received ({len(response)} chars):")
        print(response[:200] + "..." if len(response) > 200 else response)
    except:
        print("No response received")

    demo.disconnect()
    print("\nFixed demo test complete!")