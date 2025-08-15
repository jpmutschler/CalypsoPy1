#!/usr/bin/env python3
"""
Enhanced SystemInfoParser with proper cache manager integration
All command responses are cached and retrieved through the cache manager
"""

import re
from datetime import datetime
from typing import Dict, Any, Optional, List


class EnhancedSystemInfoParser:
    """
    Enhanced parser with full cache manager integration
    All parsed data is cached and retrieved through cache manager
    """

    def __init__(self, cache_manager):
        self.cache = cache_manager

    def parse_complete_sysinfo(self, sysinfo_output: str) -> Dict[str, Any]:
        """
        Parse complete sysinfo output and cache all sections

        Args:
            sysinfo_output: Raw output from sysinfo command

        Returns:
            Parsed system information with all sections cached
        """
        parsed_data = {
            'raw_output': sysinfo_output,
            'parsed_at': datetime.now().isoformat(),
            'ver_section': {},
            'lsd_section': {},
            'showport_section': {},
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # Parse each section
        parsed_data['ver_section'] = self._parse_ver_section(sysinfo_output)
        parsed_data['lsd_section'] = self._parse_lsd_section(sysinfo_output)
        parsed_data['showport_section'] = self._parse_showport_section(sysinfo_output)

        # Cache everything through cache manager with appropriate TTL
        self._cache_all_sections(parsed_data)

        return parsed_data

    def _cache_all_sections(self, parsed_data: Dict[str, Any]):
        """Cache all parsed sections with appropriate keys and TTL"""
        ttl = 300  # 5 minutes default TTL

        # Cache the complete parsed data
        self.cache.set('complete_sysinfo', parsed_data, 'sysinfo', ttl)

        # Cache individual sections for dashboard access
        self.cache.set('ver_data', parsed_data['ver_section'], 'ver', ttl)
        self.cache.set('lsd_data', parsed_data['lsd_section'], 'lsd', ttl)
        self.cache.set('showport_data', parsed_data['showport_section'], 'showport', ttl)

        # Cache combined host card info (ver + lsd)
        host_info = {**parsed_data['ver_section'], **parsed_data['lsd_section']}
        host_info['last_updated'] = parsed_data['last_updated']
        self.cache.set('host_card_info', host_info, 'sysinfo', ttl)

        # Cache link status info (showport)
        link_info = parsed_data['showport_section']
        link_info['last_updated'] = parsed_data['last_updated']
        self.cache.set('link_status_info', link_info, 'sysinfo', ttl)

        # Cache formatted display data
        self.cache.set('host_display_data', self._format_host_data(host_info), 'sysinfo', ttl)
        self.cache.set('link_display_data', self._format_link_data(link_info), 'sysinfo', ttl)

    def get_cached_data(self, data_key: str, fallback_generator=None) -> Optional[Any]:
        """
        Get cached data with fallback to generator function

        Args:
            data_key: Cache key to retrieve
            fallback_generator: Function to generate default data if cache miss

        Returns:
            Cached data or generated fallback data
        """
        cached = self.cache.get(data_key)

        if cached is not None:
            return cached

        # If no cached data and fallback provided, use fallback
        if fallback_generator:
            fallback_data = fallback_generator()
            # Cache the fallback data briefly
            self.cache.set(data_key, fallback_data, 'fallback', ttl=60)
            return fallback_data

        return None

    def get_host_info_for_display(self) -> Dict[str, Any]:
        """Get formatted host information with cache-first approach"""
        return self.get_cached_data('host_display_data', self._get_default_host_display_data)

    def get_link_info_for_display(self) -> list:
        """Get formatted link information with cache-first approach"""
        return self.get_cached_data('link_display_data', self._get_default_link_display_data)

    def get_raw_ver_data(self) -> Optional[Dict[str, Any]]:
        """Get raw ver section data from cache"""
        return self.cache.get('ver_data')

    def get_raw_lsd_data(self) -> Optional[Dict[str, Any]]:
        """Get raw lsd section data from cache"""
        return self.cache.get('lsd_data')

    def get_raw_showport_data(self) -> Optional[Dict[str, Any]]:
        """Get raw showport section data from cache"""
        return self.cache.get('showport_data')

    def get_complete_sysinfo(self) -> Optional[Dict[str, Any]]:
        """Get complete parsed sysinfo from cache"""
        return self.cache.get('complete_sysinfo')

    def invalidate_all_data(self):
        """Invalidate all cached data"""
        cache_keys = [
            'complete_sysinfo', 'ver_data', 'lsd_data', 'showport_data',
            'host_card_info', 'link_status_info', 'host_display_data', 'link_display_data'
        ]

        for key in cache_keys:
            self.cache.invalidate(key)

    def is_data_fresh(self, max_age_seconds: int = 300) -> bool:
        """Check if cached data is fresh enough"""
        if hasattr(self.cache, 'get_with_metadata'):
            complete_data = self.cache.get_with_metadata('complete_sysinfo')
            if complete_data:
                return complete_data['age_seconds'] < max_age_seconds
        return False

    def force_refresh_needed(self) -> bool:
        """Check if a force refresh is needed (no data or data too old)"""
        return not self.is_data_fresh(300)  # 5 minutes

    # Parsing methods remain the same but with added caching
    def _parse_ver_section(self, output: str) -> Dict[str, Any]:
        """Parse the ver section from sysinfo output"""
        ver_data = {}

        # Extract S/N
        sn_match = re.search(r'S/N\s*:\s*([A-Za-z0-9]+)', output, re.IGNORECASE)
        if sn_match:
            ver_data['serial_number'] = sn_match.group(1)

        # Extract Company
        company_match = re.search(r'Company\s*:\s*(.+?)(?:\n|$)', output, re.IGNORECASE)
        if company_match:
            ver_data['company'] = company_match.group(1).strip()

        # Extract Model
        model_match = re.search(r'Model\s*:\s*(.+?)(?:\n|$)', output, re.IGNORECASE)
        if model_match:
            ver_data['model'] = model_match.group(1).strip()

        # Extract Version and Date
        version_match = re.search(r'Version\s*:\s*([\d\.]+)\s+Date\s*:\s*(.+?)(?:\n|$)', output, re.IGNORECASE)
        if version_match:
            ver_data['version'] = version_match.group(1)
            ver_data['build_date'] = version_match.group(2).strip()

        # Extract SBR Version
        sbr_match = re.search(r'SBR Version\s*:\s*([\d\s]+)', output, re.IGNORECASE)
        if sbr_match:
            ver_data['sbr_version'] = sbr_match.group(1).strip()

        return ver_data

    def _parse_lsd_section(self, output: str) -> Dict[str, Any]:
        """Parse the lsd section from sysinfo output"""
        lsd_data = {}

        # Extract Board Temperature
        temp_match = re.search(r'Board Temperature\s*:\s*(\d+)\s*degree', output, re.IGNORECASE)
        if temp_match:
            lsd_data['board_temperature'] = int(temp_match.group(1))

        # Extract Switch Fan Speed
        fan_match = re.search(r'Switch Fan\s*:\s*(\d+)\s*rpm', output, re.IGNORECASE)
        if fan_match:
            lsd_data['switch_fan_speed'] = int(fan_match.group(1))

        # Extract Voltage Sensors
        voltage_patterns = [
            (r'Board\s+0\.8V\s+Voltage\s*:\s*(\d+)\s*mV', 'voltage_0_8v'),
            (r'Board\s+0\.89V\s+Voltage\s*:\s*(\d+)\s*mV', 'voltage_0_89v'),
            (r'Board\s+1\.2V\s+Voltage\s*:\s*(\d+)\s*mV', 'voltage_1_2v'),
            (r'Board\s+1\.5v\s+Voltage\s*:\s*(\d+)\s*mV', 'voltage_1_5v')
        ]

        for pattern, key in voltage_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                lsd_data[key] = int(match.group(1))

        # Extract Current Status
        current_match = re.search(r'Current\s*:\s*(\d+)\s*mA', output, re.IGNORECASE)
        if current_match:
            lsd_data['current_draw'] = int(current_match.group(1))

        # Extract Error Status
        error_patterns = [
            (r'Voltage\s+0\.8V\s+error\s*:\s*(\d+)', 'voltage_0_8v_errors'),
            (r'Voltage\s+0\.89V\s+error\s*:\s*(\d+)', 'voltage_0_89v_errors'),
            (r'Voltage\s+1\.2V\s+error\s*:\s*(\d+)', 'voltage_1_2v_errors'),
            (r'Voltage\s+1\.5V\s+error\s*:\s*(\d+)', 'voltage_1_5v_errors')
        ]

        for pattern, key in error_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                lsd_data[key] = int(match.group(1))

        return lsd_data

    def _parse_showport_section(self, output: str) -> Dict[str, Any]:
        """Parse the showport section from sysinfo output"""
        showport_data = {
            'ports': {},
            'golden_finger': {}
        }

        # Extract individual port information
        port_pattern = r'Port(\d+)\s*:\s*speed\s+(\w+),\s*width\s+(\w+),\s*max_speed(\w+),\s*max_width(\d+)'
        port_matches = re.findall(port_pattern, output, re.IGNORECASE)

        for match in port_matches:
            port_num, speed, width, max_speed, max_width = match
            showport_data['ports'][f'port_{port_num}'] = {
                'port_number': port_num,
                'speed': speed,
                'width': width,
                'max_speed': max_speed,
                'max_width': max_width,
                'status': 'Active' if speed != '00' else 'Inactive'
            }

        # Extract Golden Finger information
        golden_match = re.search(r'Golden finger:\s*speed\s+(\w+),\s*width\s+(\w+),\s*max_width\s*=\s*(\d+)', output,
                                 re.IGNORECASE)
        if golden_match:
            showport_data['golden_finger'] = {
                'speed': golden_match.group(1),
                'width': golden_match.group(2),
                'max_width': int(golden_match.group(3)),
                'status': 'Active' if golden_match.group(1) != '00' else 'Inactive'
            }

        return showport_data

    def _format_host_data(self, host_info: Dict[str, Any]) -> Dict[str, Any]:
        """Format host information for display"""
        if not host_info:
            return self._get_default_host_display_data()

        display_data = {
            'device_info': {
                'Serial Number': host_info.get('serial_number', 'Unknown'),
                'Company': host_info.get('company', 'Unknown'),
                'Model': host_info.get('model', 'Unknown'),
                'Firmware Version': host_info.get('version', 'Unknown'),
                'Build Date': host_info.get('build_date', 'Unknown'),
                'SBR Version': host_info.get('sbr_version', 'Unknown')
            },
            'thermal_info': {
                'Board Temperature': f"{host_info.get('board_temperature', 0)}°C"
            },
            'fan_info': {
                'Switch Fan Speed': f"{host_info.get('switch_fan_speed', 0)} rpm"
            },
            'power_info': {
                '0.8V Rail': f"{host_info.get('voltage_0_8v', 0)} mV",
                '0.89V Rail': f"{host_info.get('voltage_0_89v', 0)} mV",
                '1.2V Rail': f"{host_info.get('voltage_1_2v', 0)} mV",
                '1.5V Rail': f"{host_info.get('voltage_1_5v', 0)} mV",
                'Current Draw': f"{host_info.get('current_draw', 0)} mA"
            },
            'error_info': {
                '0.8V Rail Errors': str(host_info.get('voltage_0_8v_errors', 0)),
                '0.89V Rail Errors': str(host_info.get('voltage_0_89v_errors', 0)),
                '1.2V Rail Errors': str(host_info.get('voltage_1_2v_errors', 0)),
                '1.5V Rail Errors': str(host_info.get('voltage_1_5v_errors', 0))
            },
            'last_updated': host_info.get('last_updated', 'Never'),
            'data_fresh': True
        }

        return display_data

    def _format_link_data(self, link_info: Dict[str, Any]) -> list:
        """Format link information for display"""
        if not link_info:
            return self._get_default_link_display_data()

        link_data = []

        # Add port information
        for port_key, port_info in link_info.get('ports', {}).items():
            status = "✅ Active" if port_info['status'] == 'Active' else "❌ Inactive"
            link_data.append((f"Port {port_info['port_number']}", status))
            if port_info['status'] == 'Active':
                link_data.append((f"  └─ Speed", f"Level {port_info['speed']}"))
                link_data.append((f"  └─ Width", f"{port_info['width']}"))

        # Add Golden Finger info
        golden = link_info.get('golden_finger', {})
        if golden:
            status = "✅ Active" if golden.get('status') == 'Active' else "❌ Inactive"
            link_data.append(("Golden Finger", status))
            link_data.append(("  └─ Speed", f"Level {golden.get('speed', '00')}"))
            link_data.append(("  └─ Max Width", str(golden.get('max_width', 0))))

        return link_data

    def _get_default_host_display_data(self) -> Dict[str, Any]:
        """Return default host info based on sample data"""
        return {
            'device_info': {
                'Serial Number': 'GBH14412506206Z',
                'Company': 'SerialCables, Inc',
                'Model': 'PCI6-RD-x16HT-BG6-144',
                'Firmware Version': '0.1.0',
                'Build Date': 'Jul 18 2025 11:05:16',
                'SBR Version': '0 34 160 28'
            },
            'thermal_info': {
                'Board Temperature': '55°C'
            },
            'fan_info': {
                'Switch Fan Speed': '6310 rpm'
            },
            'power_info': {
                '0.8V Rail': '890 mV',
                '0.89V Rail': '991 mV',
                '1.2V Rail': '1304 mV',
                '1.5V Rail': '1512 mV',
                'Current Draw': '10240 mA'
            },
            'error_info': {
                '0.8V Rail Errors': '0',
                '0.89V Rail Errors': '0',
                '1.2V Rail Errors': '0',
                '1.5V Rail Errors': '0'
            },
            'last_updated': 'Sample data',
            'data_fresh': False
        }

    def _get_default_link_display_data(self) -> list:
        """Return default link info based on sample data"""
        return [
            ("Port 80", "✅ Active"),
            ("  └─ Speed", "Level 01"),
            ("  └─ Width", "00"),
            ("Port 112", "✅ Active"),
            ("  └─ Speed", "Level 01"),
            ("  └─ Width", "00"),
            ("Port 128", "✅ Active"),
            ("  └─ Speed", "Level 01"),
            ("  └─ Width", "00"),
            ("Golden Finger", "✅ Active"),
            ("  └─ Speed", "Level 01"),
            ("  └─ Max Width", "16")
        ]

    def parse_unified_sysinfo(self, sysinfo_output: str, source="device") -> Dict[str, Any]:
        """
        UNIFIED parsing method - processes both device responses and demo file data

        Args:
            sysinfo_output: Raw sysinfo response (from device or file)
            source: "device" or "file" for tracking data source

        Returns:
            Parsed data dictionary with enhanced caching
        """
        print(f"DEBUG: Unified parser processing {source} data ({len(sysinfo_output)} chars)")

        try:
            # Use your existing parse_complete_sysinfo method as the base
            parsed_data = self.parse_complete_sysinfo(sysinfo_output)

            # Add source tracking and enhanced metadata
            parsed_data['data_source'] = source
            parsed_data['unified_parsing'] = True
            parsed_data['processed_at'] = datetime.now().isoformat()

            print(
                f"DEBUG: Base parsing completed - ver:{len(parsed_data.get('ver_section', {}))}, lsd:{len(parsed_data.get('lsd_section', {}))}, showport:{len(parsed_data.get('showport_section', {}))}")

            # Create and cache JSON objects for dashboards
            self._create_and_cache_json_objects(parsed_data)

            print(f"DEBUG: Unified parsing successful for {source} data")
            return parsed_data

        except Exception as e:
            print(f"ERROR: Unified parsing failed for {source} data: {e}")
            import traceback
            traceback.print_exc()

            # Return minimal data structure on error
            return {
                'data_source': source,
                'unified_parsing': False,
                'error': str(e),
                'processed_at': datetime.now().isoformat(),
                'ver_section': {},
                'lsd_section': {},
                'showport_section': {}
            }

    def _create_and_cache_json_objects(self, parsed_data: Dict[str, Any]):
        """
        Create JSON objects for each dashboard and cache them

        This creates structured JSON objects that dashboards can easily consume
        """
        ttl = 300  # 5 minutes cache TTL

        print("DEBUG: Creating JSON objects for dashboards...")

        try:
            # Create HOST CARD JSON (combines ver + lsd data)
            host_card_json = {
                'dashboard_type': 'host_card_information',
                'data_source': parsed_data.get('data_source', 'unknown'),
                'last_updated': parsed_data.get('last_updated', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                'sections': {
                    'device_info': {
                        'title': 'Device Information',
                        'icon': '💻',
                        'fields': self._extract_device_fields(parsed_data.get('ver_section', {}))
                    },
                    'thermal_info': {
                        'title': 'Thermal Status',
                        'icon': '🌡️',
                        'fields': self._extract_thermal_fields(parsed_data.get('lsd_section', {}))
                    },
                    'fan_info': {
                        'title': 'Fan Status',
                        'icon': '🌀',
                        'fields': self._extract_fan_fields(parsed_data.get('lsd_section', {}))
                    },
                    'power_info': {
                        'title': 'Power Status',
                        'icon': '⚡',
                        'fields': self._extract_power_fields(parsed_data.get('lsd_section', {}))
                    },
                    'error_info': {
                        'title': 'Error Status',
                        'icon': '🚨',
                        'fields': self._extract_error_fields(parsed_data.get('lsd_section', {}))
                    }
                },
                'data_fresh': True
            }

            # Create LINK STATUS JSON (showport data only)
            link_status_json = {
                'dashboard_type': 'link_status',
                'data_source': parsed_data.get('data_source', 'unknown'),
                'last_updated': parsed_data.get('last_updated', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                'sections': {
                    'port_status': {
                        'title': 'Port and Link Status',
                        'icon': '🔗',
                        'items': self._extract_link_items(parsed_data.get('showport_section', {}))
                    }
                },
                'data_fresh': True
            }

            # Cache the JSON objects
            self.cache.set('host_card_json', host_card_json, 'host_card', ttl)
            self.cache.set('link_status_json', link_status_json, 'link_status', ttl)

            print(f"DEBUG: JSON objects created and cached successfully")
            print(f"  Host card sections: {len(host_card_json['sections'])}")
            print(f"  Link status items: {len(link_status_json['sections']['port_status']['items'])}")

            # Also cache individual sections for backwards compatibility
            self.cache.set('host_display_data', host_card_json, 'host_display', ttl)
            self.cache.set('link_display_data', link_status_json, 'link_display', ttl)

        except Exception as e:
            print(f"ERROR: Failed to create JSON objects: {e}")
            import traceback
            traceback.print_exc()

    def _extract_device_fields(self, ver_data: Dict) -> Dict[str, str]:
        """
        Extract device information fields for host card JSON
        """
        fields = {}

        # Extract fields with fallbacks
        if ver_data.get('serial_number'):
            fields['Serial Number'] = ver_data['serial_number']

        if ver_data.get('company'):
            fields['Company'] = ver_data['company']

        if ver_data.get('model'):
            fields['Model'] = ver_data['model']

        if ver_data.get('version'):
            fields['Firmware Version'] = ver_data['version']

        if ver_data.get('build_date'):
            fields['Build Date'] = ver_data['build_date']

        if ver_data.get('sbr_version'):
            fields['SBR Version'] = ver_data['sbr_version']

        print(f"DEBUG: Extracted {len(fields)} device fields")
        return fields

    def _extract_thermal_fields(self, lsd_data: Dict) -> Dict[str, str]:
        """
        Extract thermal fields for host card JSON
        """
        fields = {}

        if lsd_data.get('board_temperature') is not None:
            temp = lsd_data['board_temperature']
            fields['Board Temperature'] = f"{temp}°C"

        print(f"DEBUG: Extracted {len(fields)} thermal fields")
        return fields

    def _extract_fan_fields(self, lsd_data: Dict) -> Dict[str, str]:
        """
        Extract fan fields for host card JSON
        """
        fields = {}

        if lsd_data.get('switch_fan_speed') is not None:
            speed = lsd_data['switch_fan_speed']
            fields['Switch Fan Speed'] = f"{speed} rpm"

        print(f"DEBUG: Extracted {len(fields)} fan fields")
        return fields

    def _extract_power_fields(self, lsd_data: Dict) -> Dict[str, str]:
        """
        Extract power fields for host card JSON
        """
        fields = {}

        # Voltage rails
        voltage_mappings = {
            'voltage_0_8v': '0.8V Rail',
            'voltage_0_89v': '0.89V Rail',
            'voltage_1_2v': '1.2V Rail',
            'voltage_1_5v': '1.5V Rail'
        }

        for field_key, display_name in voltage_mappings.items():
            if lsd_data.get(field_key) is not None:
                voltage = lsd_data[field_key]
                fields[display_name] = f"{voltage} mV"

        # Current draw
        if lsd_data.get('current_draw') is not None:
            current = lsd_data['current_draw']
            fields['Current Draw'] = f"{current} mA"

        print(f"DEBUG: Extracted {len(fields)} power fields")
        return fields

    def _extract_error_fields(self, lsd_data: Dict) -> Dict[str, str]:
        """
        Extract error fields for host card JSON
        """
        fields = {}

        # Error count mappings
        error_mappings = {
            'voltage_0_8v_errors': '0.8V Rail Errors',
            'voltage_0_89v_errors': '0.89V Rail Errors',
            'voltage_1_2v_errors': '1.2V Rail Errors',
            'voltage_1_5v_errors': '1.5V Rail Errors'
        }

        for field_key, display_name in error_mappings.items():
            if lsd_data.get(field_key) is not None:
                error_count = lsd_data[field_key]
                fields[display_name] = str(error_count)

        print(f"DEBUG: Extracted {len(fields)} error fields")
        return fields

    def _extract_link_items(self, showport_data: Dict) -> List[Dict]:
        """
        Extract link items for link status JSON
        """
        items = []

        # Process individual ports
        ports = showport_data.get('ports', {})
        for port_key, port_info in ports.items():
            status_text = "✅ Active" if port_info.get('status') == 'Active' else "❌ Inactive"

            item = {
                'label': f"Port {port_info.get('port_number', '?')}",
                'value': status_text,
                'details': f"Speed: Level {port_info.get('speed', '00')}, Width: {port_info.get('width', '00')}"
            }
            items.append(item)

        # Process golden finger
        golden_finger = showport_data.get('golden_finger', {})
        if golden_finger:
            status_text = "✅ Active" if golden_finger.get('status') == 'Active' else "❌ Inactive"

            item = {
                'label': 'Golden Finger',
                'value': status_text,
                'details': f"Speed: Level {golden_finger.get('speed', '00')}, Max Width: {golden_finger.get('max_width', 0)}"
            }
            items.append(item)

        print(f"DEBUG: Extracted {len(items)} link items")
        return items

    def get_host_card_json(self) -> Optional[Dict[str, Any]]:
        """
        Get JSON object for Host Card Information dashboard

        Returns:
            JSON object with structured host card data or None if not available
        """
        host_json = self.cache.get('host_card_json')
        if host_json:
            print("DEBUG: Retrieved host card JSON from cache")
            return host_json
        else:
            print("DEBUG: No host card JSON in cache")
            return None

    def get_link_status_json(self) -> Optional[Dict[str, Any]]:
        """
        Get JSON object for Link Status dashboard

        Returns:
            JSON object with structured link status data or None if not available
        """
        link_json = self.cache.get('link_status_json')
        if link_json:
            print("DEBUG: Retrieved link status JSON from cache")
            return link_json
        else:
            print("DEBUG: No link status JSON in cache")
            return None

    def is_unified_data_available(self) -> bool:
        """
        Check if unified JSON data is available in cache

        Returns:
            True if both host card and link status JSON objects are cached
        """
        host_available = self.cache.get('host_card_json') is not None
        link_available = self.cache.get('link_status_json') is not None

        print(f"DEBUG: Unified data availability - host:{host_available}, link:{link_available}")
        return host_available and link_available


# Processing function for situations where sysinfo response needs error handling
def process_sysinfo_response(parser, response, source="device"):
    """
    FIXED: Process sysinfo response with error handling
    """
    try:
        # Check if response contains expected keywords
        if any(keyword in response.lower() for keyword in
               ['s/n', 'thermal', 'voltage', '===', 'company', 'port']):

            parsed_data = parser.parse_unified_sysinfo(response, source)

            if parsed_data and not parsed_data.get('error'):
                print(f"DEBUG: Successfully processed {source} sysinfo response")
                return parsed_data
            else:
                print(f"ERROR: Failed to parse {source} response")
                return None
        else:
            print(f"WARNING: Response doesn't contain expected sysinfo keywords")
            return None

    except Exception as e:
        print(f"ERROR: Exception processing {source} response: {e}")
        return None


# Usage example and testing
if __name__ == "__main__":
    print("Testing Enhanced SystemInfo Parser...")


    # Mock cache manager for testing
    class MockCache:
        def __init__(self):
            self.data = {}

        def get(self, key):
            return self.data.get(key)

        def set(self, key, value, category="", ttl=300):
            self.data[key] = value

        def invalidate(self, key):
            if key in self.data:
                del self.data[key]

        def get_with_metadata(self, key):
            if key in self.data:
                return {
                    'data': self.data[key],
                    'age_seconds': 30,
                    'timestamp': 1234567890,
                    'command': 'test'
                }
            return None


    # Test the parser
    mock_cache = MockCache()
    parser = EnhancedSystemInfoParser(mock_cache)

    # Sample sysinfo data from your file
    sample_sysinfo = """================================================================================
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

    # Test parsing
    print("\n--- Testing unified parsing ---")
    parsed_data = parser.parse_unified_sysinfo(sample_sysinfo, "test")

    if parsed_data:
        print(f"✓ Parsing successful")
        print(f"  Ver section keys: {list(parsed_data['ver_section'].keys())}")
        print(f"  LSD section keys: {list(parsed_data['lsd_section'].keys())}")
        print(f"  Showport section keys: {list(parsed_data['showport_section'].keys())}")
    else:
        print("✗ Parsing failed")

    # Test JSON retrieval
    print("\n--- Testing JSON retrieval ---")
    host_json = parser.get_host_card_json()
    if host_json:
        print(f"✓ Host card JSON retrieved")
        print(f"  Sections: {list(host_json['sections'].keys())}")
    else:
        print("✗ No host card JSON available")

    link_json = parser.get_link_status_json()
    if link_json:
        print(f"✓ Link status JSON retrieved")
        print(f"  Items: {len(link_json['sections']['port_status']['items'])}")
    else:
        print("✗ No link status JSON available")

    # Test cache functions
    print("\n--- Testing cache functions ---")
    complete_data = parser.get_complete_sysinfo()
    if complete_data:
        print("✓ Complete sysinfo data cached")
    else:
        print("✗ No complete sysinfo data in cache")

    print(f"Data fresh: {parser.is_data_fresh()}")
    print(f"Force refresh needed: {parser.force_refresh_needed()}")

    print("\nEnhanced SystemInfo Parser test completed!")