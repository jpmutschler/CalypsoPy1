#!/usr/bin/env python3
"""
advanced_response_handler.py

Advanced Fragmented Response Handler for CalypsoPy
Complete robust implementation for handling various device response patterns

Place this file in: Admin/advanced_response_handler.py

Author: Serial Cables Development Team
"""

import time
import re
import threading
import queue
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional, Set
from datetime import datetime


class ResponseState(Enum):
    """Response collection states"""
    IDLE = "idle"
    COLLECTING = "collecting"
    COMPLETE = "complete"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class ResponsePattern:
    """Defines expected response patterns for different commands"""
    command: str
    start_markers: List[str]
    end_markers: List[str]
    required_sections: List[str]
    optional_sections: List[str]
    timeout_seconds: float
    min_lines: int
    max_lines: int


@dataclass
class ResponseBuffer:
    """Manages response collection and state"""
    command: str
    lines: List[str]
    start_time: float
    last_activity: float
    state: ResponseState
    expected_pattern: Optional[ResponsePattern]

    def add_line(self, line: str):
        """Add a line to the buffer"""
        self.lines.append(line)
        self.last_activity = time.time()

    def get_content(self) -> str:
        """Get complete buffer content"""
        return '\n'.join(self.lines)

    def age_seconds(self) -> float:
        """Get buffer age in seconds"""
        return time.time() - self.start_time

    def idle_seconds(self) -> float:
        """Get seconds since last activity"""
        return time.time() - self.last_activity


class AdvancedResponseHandler:
    """
    Advanced handler for fragmented device responses
    Handles multiple response patterns, timeouts, and error recovery
    """

    def __init__(self, dashboard_app):
        """Initialize the response handler"""
        self.app = dashboard_app
        self.lock = threading.RLock()

        # Response management
        self.active_buffers: Dict[str, ResponseBuffer] = {}
        self.response_patterns = self._init_response_patterns()
        self.state = ResponseState.IDLE

        # Configuration
        self.default_timeout = 10.0
        self.idle_timeout = 3.0  # Process buffer after 3s of inactivity
        self.max_buffer_size = 50000  # 50KB max buffer
        self.cleanup_interval = 30.0  # Clean up old buffers every 30s

        # Statistics
        self.stats = {
            'responses_processed': 0,
            'responses_failed': 0,
            'responses_timeout': 0,
            'fragments_collected': 0,
            'average_fragments_per_response': 0
        }

        # Start cleanup timer
        self._start_cleanup_timer()

        print("DEBUG: Advanced Response Handler initialized")

    def _init_response_patterns(self) -> Dict[str, ResponsePattern]:
        """Initialize known response patterns for different commands"""
        patterns = {}

        # SYSINFO command pattern
        patterns['sysinfo'] = ResponsePattern(
            command='sysinfo',
            start_markers=[
                '====', 'ver', 'S/N', 'Company', 'Model',
                'Port Slot', 'Thermal:', 'Voltage Sensors:'
            ],
            end_markers=[
                'Golden finger:', 'max_width', 'Error Status:', 'OK>', 'Cmd>'
            ],
            required_sections=['S/N', 'Port'],  # Must have device info and port info
            optional_sections=['Thermal:', 'Voltage', 'Error'],
            timeout_seconds=15.0,
            min_lines=10,
            max_lines=100
        )

        # VER command pattern
        patterns['ver'] = ResponsePattern(
            command='ver',
            start_markers=['S/N', 'Company', 'Model', 'Version'],
            end_markers=['SBR Version', 'OK>', 'Cmd>'],
            required_sections=['S/N', 'Version'],
            optional_sections=['Company', 'Model'],
            timeout_seconds=5.0,
            min_lines=3,
            max_lines=20
        )

        # LSD command pattern
        patterns['lsd'] = ResponsePattern(
            command='lsd',
            start_markers=['Thermal:', 'Fans Speed:', 'Voltage Sensors:'],
            end_markers=['Error Status:', 'error :', 'OK>', 'Cmd>'],
            required_sections=['Thermal:', 'Voltage'],
            optional_sections=['Fans', 'Current', 'Error'],
            timeout_seconds=8.0,
            min_lines=5,
            max_lines=30
        )

        # SHOWPORT command pattern
        patterns['showport'] = ResponsePattern(
            command='showport',
            start_markers=['Port Slot', 'Port80', 'Port112'],
            end_markers=['Golden finger:', 'max_width', 'OK>', 'Cmd>'],
            required_sections=['Port'],
            optional_sections=['Golden finger', 'Upstream'],
            timeout_seconds=5.0,
            min_lines=3,
            max_lines=25
        )

        return patterns

    def start_response_collection(self, command: str):
        """Start collecting responses for a command"""
        with self.lock:
            command_lower = command.lower()

            # Get expected pattern
            pattern = None
            for pattern_key, pattern_obj in self.response_patterns.items():
                if pattern_key in command_lower or command_lower in pattern_key:
                    pattern = pattern_obj
                    break

            # Create new buffer
            buffer = ResponseBuffer(
                command=command,
                lines=[],
                start_time=time.time(),
                last_activity=time.time(),
                state=ResponseState.COLLECTING,
                expected_pattern=pattern
            )

            self.active_buffers[command_lower] = buffer
            self.state = ResponseState.COLLECTING

            timeout = pattern.timeout_seconds if pattern else self.default_timeout

            print(f"DEBUG: Started response collection for '{command}' (timeout: {timeout}s)")

            # Schedule timeout check
            self.app.root.after(int(timeout * 1000),
                                lambda: self._check_timeout(command_lower))

    def add_response_fragment(self, fragment: str) -> bool:
        """
        Add a response fragment to the appropriate buffer
        Returns True if fragment was handled
        """
        with self.lock:
            if not self.active_buffers:
                return False

            fragment = fragment.strip()
            if not fragment:
                return False

            # Find the best matching buffer for this fragment
            best_buffer = self._find_matching_buffer(fragment)

            if best_buffer:
                best_buffer.add_line(fragment)
                self.stats['fragments_collected'] += 1

                print(f"DEBUG: Added fragment to '{best_buffer.command}' buffer: {fragment[:60]}...")

                # Check if response might be complete
                if self._is_response_potentially_complete(best_buffer):
                    print(f"DEBUG: Response for '{best_buffer.command}' appears complete")
                    self._schedule_processing(best_buffer.command)

                return True

            return False

    def _find_matching_buffer(self, fragment: str) -> Optional[ResponseBuffer]:
        """Find the best matching buffer for a response fragment"""
        fragment_lower = fragment.lower()

        # First, try exact command match
        for command, buffer in self.active_buffers.items():
            if buffer.state == ResponseState.COLLECTING:
                pattern = buffer.expected_pattern

                if pattern:
                    # Check against start markers
                    for marker in pattern.start_markers:
                        if marker.lower() in fragment_lower:
                            return buffer

                    # Check against required sections
                    for section in pattern.required_sections:
                        if section.lower() in fragment_lower:
                            return buffer

        # If no specific match, return the first collecting buffer
        for buffer in self.active_buffers.values():
            if buffer.state == ResponseState.COLLECTING:
                return buffer

        return None

    def _is_response_potentially_complete(self, buffer: ResponseBuffer) -> bool:
        """Check if response might be complete based on patterns"""
        if not buffer.expected_pattern:
            # Use heuristics for unknown patterns
            return (len(buffer.lines) >= 5 and
                    buffer.idle_seconds() > 1.0)

        pattern = buffer.expected_pattern
        content = buffer.get_content().lower()

        # Check minimum requirements
        if len(buffer.lines) < pattern.min_lines:
            return False

        # Check for required sections
        required_found = 0
        for section in pattern.required_sections:
            if section.lower() in content:
                required_found += 1

        if required_found < len(pattern.required_sections):
            return False

        # Check for end markers
        for marker in pattern.end_markers:
            if marker.lower() in content:
                return True

        # Check idle timeout
        if buffer.idle_seconds() > self.idle_timeout:
            return True

        # Check if we have enough content
        return len(buffer.lines) >= pattern.min_lines * 2

    def _schedule_processing(self, command: str):
        """Schedule processing of a complete response"""
        # Add small delay to catch any final fragments
        delay_ms = 500  # 500ms delay
        self.app.root.after(delay_ms, lambda: self._process_buffer(command))

    def _process_buffer(self, command: str):
        """Process a completed response buffer"""
        with self.lock:
            buffer = self.active_buffers.get(command)
            if not buffer or buffer.state != ResponseState.COLLECTING:
                return

            buffer.state = ResponseState.COMPLETE
            content = buffer.get_content()

            print(f"DEBUG: Processing buffer for '{command}' ({len(content)} chars, {len(buffer.lines)} lines)")

            try:
                # Validate response quality
                if not self._validate_response_quality(buffer):
                    raise ValueError("Response quality validation failed")

                # Parse the response
                parsed_data = self.app.sysinfo_parser.parse_unified_sysinfo(
                    content,
                    "demo" if self.app.is_demo_mode else "device"
                )

                print(f"DEBUG: Successfully parsed '{command}' response")

                # Update statistics
                self.stats['responses_processed'] += 1
                fragments = len(buffer.lines)
                total_responses = self.stats['responses_processed']
                self.stats['average_fragments_per_response'] = (
                        (self.stats['average_fragments_per_response'] * (total_responses - 1) + fragments)
                        / total_responses
                )

                # Reset request flags
                if hasattr(self.app, 'sysinfo_requested'):
                    self.app.sysinfo_requested = False

                # Update UI
                self.app.root.after_idle(self.app.update_content_area)
                self.app.update_cache_status("Fresh data loaded")

                # Log success
                timestamp = datetime.now().strftime('%H:%M:%S')
                self.app.log_data.append(
                    f"[{timestamp}] Advanced handler processed '{command}' "
                    f"({fragments} fragments, {len(content)} chars)"
                )

                # Clean up this buffer
                self._cleanup_buffer(command)

            except Exception as e:
                print(f"ERROR: Failed to process '{command}' buffer: {e}")
                import traceback
                traceback.print_exc()

                buffer.state = ResponseState.ERROR
                self.stats['responses_failed'] += 1

                # Reset request flags
                if hasattr(self.app, 'sysinfo_requested'):
                    self.app.sysinfo_requested = False

                # Show error
                self.app.show_loading_message(f"Error processing {command}: {e}")

                # Log error
                timestamp = datetime.now().strftime('%H:%M:%S')
                self.app.log_data.append(f"[{timestamp}] Error processing '{command}': {e}")

                # Clean up failed buffer
                self._cleanup_buffer(command)

    def _validate_response_quality(self, buffer: ResponseBuffer) -> bool:
        """Validate the quality of a response before processing"""
        content = buffer.get_content()

        # Basic checks
        if len(content) < 50:  # Too short
            print(f"DEBUG: Response too short ({len(content)} chars)")
            return False

        if len(content) > self.max_buffer_size:  # Too long
            print(f"DEBUG: Response too long ({len(content)} chars)")
            return False

        # Pattern-specific validation
        if buffer.expected_pattern:
            pattern = buffer.expected_pattern
            content_lower = content.lower()

            # Check line count
            if len(buffer.lines) < pattern.min_lines:
                print(f"DEBUG: Too few lines ({len(buffer.lines)} < {pattern.min_lines})")
                return False

            if len(buffer.lines) > pattern.max_lines:
                print(f"DEBUG: Too many lines ({len(buffer.lines)} > {pattern.max_lines})")
                return False

            # Check for required sections
            for section in pattern.required_sections:
                if section.lower() not in content_lower:
                    print(f"DEBUG: Missing required section: {section}")
                    return False

        # Check for common error patterns
        error_patterns = [
            'error:', 'failed:', 'invalid:', 'unknown command',
            'syntax error', 'not found', 'permission denied'
        ]

        content_lower = content.lower()
        for error_pattern in error_patterns:
            if error_pattern in content_lower:
                print(f"DEBUG: Found error pattern: {error_pattern}")
                return False

        print(f"DEBUG: Response quality validation passed")
        return True

    def _check_timeout(self, command: str):
        """Check if a response collection has timed out"""
        with self.lock:
            buffer = self.active_buffers.get(command)
            if not buffer or buffer.state != ResponseState.COLLECTING:
                return

            age = buffer.age_seconds()
            timeout = (buffer.expected_pattern.timeout_seconds
                       if buffer.expected_pattern
                       else self.default_timeout)

            if age >= timeout:
                print(f"DEBUG: Response collection timed out for '{command}' after {age:.1f}s")

                # Try to process whatever we have
                if len(buffer.lines) > 0:
                    print(f"DEBUG: Attempting to process partial response ({len(buffer.lines)} lines)")
                    self._process_buffer(command)
                else:
                    # Complete timeout with no data
                    buffer.state = ResponseState.TIMEOUT
                    self.stats['responses_timeout'] += 1

                    # Reset request flags
                    if hasattr(self.app, 'sysinfo_requested'):
                        self.app.sysinfo_requested = False

                    # Show timeout message
                    self.app.show_loading_message("Request timed out. Click refresh to try again.")
                    self.app.update_cache_status("Request timed out")

                    # Log timeout
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    self.app.log_data.append(f"[{timestamp}] '{command}' timed out after {age:.1f}s")

                    # Clean up
                    self._cleanup_buffer(command)

    def _cleanup_buffer(self, command: str):
        """Clean up a specific buffer"""
        with self.lock:
            if command in self.active_buffers:
                del self.active_buffers[command]
                print(f"DEBUG: Cleaned up buffer for '{command}'")

            # Update state
            if not self.active_buffers:
                self.state = ResponseState.IDLE

    def _start_cleanup_timer(self):
        """Start periodic cleanup of old buffers"""

        def cleanup():
            try:
                self._periodic_cleanup()
            except Exception as e:
                print(f"ERROR: Cleanup error: {e}")

            # Schedule next cleanup
            self.app.root.after(int(self.cleanup_interval * 1000), cleanup)

        # Start first cleanup
        self.app.root.after(int(self.cleanup_interval * 1000), cleanup)

    def _periodic_cleanup(self):
        """Periodic cleanup of stale buffers"""
        with self.lock:
            stale_commands = []

            for command, buffer in self.active_buffers.items():
                if buffer.age_seconds() > self.cleanup_interval:
                    stale_commands.append(command)

            for command in stale_commands:
                print(f"DEBUG: Cleaning up stale buffer: {command}")
                self._cleanup_buffer(command)

    def get_status(self) -> Dict:
        """Get handler status and statistics"""
        with self.lock:
            return {
                'state': self.state.value,
                'active_buffers': len(self.active_buffers),
                'buffer_details': {
                    cmd: {
                        'lines': len(buf.lines),
                        'age_seconds': buf.age_seconds(),
                        'idle_seconds': buf.idle_seconds(),
                        'state': buf.state.value
                    }
                    for cmd, buf in self.active_buffers.items()
                },
                'statistics': self.stats.copy()
            }

    def force_process_all(self):
        """Force process all active buffers (for debugging)"""
        with self.lock:
            commands = list(self.active_buffers.keys())
            for command in commands:
                print(f"DEBUG: Force processing buffer: {command}")
                self._process_buffer(command)

    def clear_all_buffers(self):
        """Clear all active buffers"""
        with self.lock:
            commands = list(self.active_buffers.keys())
            for command in commands:
                self._cleanup_buffer(command)
            print("DEBUG: All buffers cleared")


# Module test functionality
if __name__ == "__main__":
    print("Advanced Response Handler Module Test")
    print("This module should be imported by main.py")
    print("File location: Admin/advanced_response_handler.py")

    # Basic test of the classes
    print("\nTesting class instantiation...")
    try:
        # Test ResponsePattern
        pattern = ResponsePattern(
            command='test',
            start_markers=['start'],
            end_markers=['end'],
            required_sections=['req'],
            optional_sections=['opt'],
            timeout_seconds=5.0,
            min_lines=1,
            max_lines=10
        )
        print(f"✅ ResponsePattern created: {pattern.command}")

        # Test ResponseBuffer
        buffer = ResponseBuffer(
            command='test',
            lines=[],
            start_time=time.time(),
            last_activity=time.time(),
            state=ResponseState.IDLE,
            expected_pattern=pattern
        )
        print(f"✅ ResponseBuffer created: {buffer.command}")

        print("\n✅ Module test completed successfully!")
        print("Ready for import in main.py")

    except Exception as e:
        print(f"❌ Module test failed: {e}")
        import traceback

        traceback.print_exc()