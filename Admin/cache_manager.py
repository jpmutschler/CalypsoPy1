#!/usr/bin/env python3
"""
cache_manager.py

Handles caching of parsed device data to JSON files for performance optimization.
Provides thread-safe access to cached data with automatic expiration.
"""

import json
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import tempfile


@dataclass
class CacheEntry:
    """Represents a single cache entry with metadata"""
    data: Any
    timestamp: float
    command: str
    expires_at: float

    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return time.time() > self.expires_at

    def age_seconds(self) -> float:
        """Get age of cache entry in seconds"""
        return time.time() - self.timestamp


class DeviceDataCache:
    """
    Thread-safe cache manager for device data with JSON persistence
    """

    def __init__(self, cache_dir: Optional[str] = None, default_ttl: int = 300):
        """
        Initialize cache manager

        Args:
            cache_dir: Directory for cache files (uses temp dir if None)
            default_ttl: Default time-to-live for cache entries in seconds
        """
        self.default_ttl = default_ttl
        self._lock = threading.RLock()

        # Setup cache directory
        if cache_dir is None:
            self.cache_dir = os.path.join(tempfile.gettempdir(), "calypsopy_cache")
        else:
            self.cache_dir = cache_dir

        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)

        # In-memory cache for fast access
        self._memory_cache: Dict[str, CacheEntry] = {}

        # Cache file paths
        self.cache_file = os.path.join(self.cache_dir, "device_cache.json")
        self.metadata_file = os.path.join(self.cache_dir, "cache_metadata.json")

        # Load existing cache
        self._load_cache()

        # Start cleanup thread
        self._start_cleanup_thread()

    def _load_cache(self):
        """Load cache from JSON file"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)

                # Reconstruct cache entries
                for key, entry_data in cache_data.items():
                    entry = CacheEntry(
                        data=entry_data['data'],
                        timestamp=entry_data['timestamp'],
                        command=entry_data['command'],
                        expires_at=entry_data['expires_at']
                    )

                    # Only load non-expired entries
                    if not entry.is_expired():
                        self._memory_cache[key] = entry

        except Exception as e:
            print(f"Warning: Could not load cache file: {e}")
            self._memory_cache = {}

    def _save_cache(self):
        """Save cache to JSON file"""
        try:
            # Convert cache entries to serializable format
            cache_data = {}
            for key, entry in self._memory_cache.items():
                if not entry.is_expired():  # Only save non-expired entries
                    cache_data[key] = {
                        'data': entry.data,
                        'timestamp': entry.timestamp,
                        'command': entry.command,
                        'expires_at': entry.expires_at
                    }

            # Write to file atomically
            temp_file = self.cache_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, default=str)

            # Atomic move
            if os.name == 'nt':  # Windows
                if os.path.exists(self.cache_file):
                    os.remove(self.cache_file)
                os.rename(temp_file, self.cache_file)
            else:  # Unix/Linux
                os.rename(temp_file, self.cache_file)

            # Save metadata
            metadata = {
                'last_save': time.time(),
                'entry_count': len(cache_data),
                'cache_size_bytes': os.path.getsize(self.cache_file) if os.path.exists(self.cache_file) else 0
            }

            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)

        except Exception as e:
            print(f"Warning: Could not save cache file: {e}")

    def set(self, key: str, data: Any, command: str = "", ttl: Optional[int] = None) -> None:
        """
        Store data in cache

        Args:
            key: Cache key
            data: Data to cache
            command: Command that generated this data
            ttl: Time-to-live in seconds (uses default if None)
        """
        if ttl is None:
            ttl = self.default_ttl

        expires_at = time.time() + ttl

        with self._lock:
            entry = CacheEntry(
                data=data,
                timestamp=time.time(),
                command=command,
                expires_at=expires_at
            )

            self._memory_cache[key] = entry
            self._save_cache()

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve data from cache

        Args:
            key: Cache key

        Returns:
            Cached data or None if not found/expired
        """
        with self._lock:
            entry = self._memory_cache.get(key)

            if entry is None:
                return None

            if entry.is_expired():
                # Remove expired entry
                del self._memory_cache[key]
                self._save_cache()
                return None

            return entry.data

    def get_with_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve data with metadata from cache

        Returns:
            Dict with 'data', 'timestamp', 'command', 'age_seconds' or None
        """
        with self._lock:
            entry = self._memory_cache.get(key)

            if entry is None:
                return None

            if entry.is_expired():
                del self._memory_cache[key]
                self._save_cache()
                return None

            return {
                'data': entry.data,
                'timestamp': entry.timestamp,
                'command': entry.command,
                'age_seconds': entry.age_seconds(),
                'expires_at': entry.expires_at
            }

    def invalidate(self, key: str) -> bool:
        """
        Remove entry from cache

        Args:
            key: Cache key to remove

        Returns:
            True if entry was removed, False if not found
        """
        with self._lock:
            if key in self._memory_cache:
                del self._memory_cache[key]
                self._save_cache()
                return True
            return False

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Remove all entries matching pattern

        Args:
            pattern: Pattern to match (simple substring match)

        Returns:
            Number of entries removed
        """
        removed_count = 0

        with self._lock:
            keys_to_remove = [key for key in self._memory_cache.keys() if pattern in key]

            for key in keys_to_remove:
                del self._memory_cache[key]
                removed_count += 1

            if removed_count > 0:
                self._save_cache()

        return removed_count

    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._memory_cache.clear()
            self._save_cache()

    def cleanup_expired(self) -> int:
        """
        Remove expired entries

        Returns:
            Number of entries removed
        """
        removed_count = 0

        with self._lock:
            expired_keys = [
                key for key, entry in self._memory_cache.items()
                if entry.is_expired()
            ]

            for key in expired_keys:
                del self._memory_cache[key]
                removed_count += 1

            if removed_count > 0:
                self._save_cache()

        return removed_count

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_entries = len(self._memory_cache)
            expired_entries = sum(1 for entry in self._memory_cache.values() if entry.is_expired())

            # Calculate total size (approximate)
            total_size = 0
            try:
                if os.path.exists(self.cache_file):
                    total_size = os.path.getsize(self.cache_file)
            except:
                pass

            return {
                'total_entries': total_entries,
                'expired_entries': expired_entries,
                'valid_entries': total_entries - expired_entries,
                'cache_file_size': total_size,
                'cache_directory': self.cache_dir,
                'default_ttl': self.default_ttl
            }

    def get_entry_list(self) -> list:
        """Get list of all cache entries with metadata"""
        with self._lock:
            entries = []
            for key, entry in self._memory_cache.items():
                entries.append({
                    'key': key,
                    'command': entry.command,
                    'timestamp': entry.timestamp,
                    'age_seconds': entry.age_seconds(),
                    'expired': entry.is_expired(),
                    'data_type': type(entry.data).__name__,
                    'data_size': len(str(entry.data)) if entry.data else 0
                })

            # Sort by timestamp (newest first)
            entries.sort(key=lambda x: x['timestamp'], reverse=True)
            return entries

    def _start_cleanup_thread(self):
        """Start background thread for periodic cleanup"""

        def cleanup_worker():
            while True:
                try:
                    time.sleep(300)  # Run cleanup every 5 minutes
                    removed = self.cleanup_expired()
                    if removed > 0:
                        print(f"Cache cleanup: removed {removed} expired entries")
                except Exception as e:
                    print(f"Cache cleanup error: {e}")

        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()


class SystemInfoParser:
    """
    Parser for sysinfo command output with caching integration
    """

    def __init__(self, cache_manager: DeviceDataCache):
        self.cache = cache_manager

    def parse_sysinfo(self, sysinfo_output: str) -> Dict[str, Any]:
        """
        Parse sysinfo command output into structured data

        Args:
            sysinfo_output: Raw output from sysinfo command

        Returns:
            Parsed system information dictionary
        """
        parsed_data = {
            'raw_output': sysinfo_output,
            'parsed_at': datetime.now().isoformat(),
            'sections': {}
        }

        # Basic parsing - adapt this to your actual sysinfo format
        lines = sysinfo_output.split('\n')
        current_section = 'general'

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect section headers (lines with === or similar)
            if '===' in line or line.endswith(':'):
                current_section = line.replace('=', '').replace(':', '').strip().lower()
                parsed_data['sections'][current_section] = {}
                continue

            # Parse key-value pairs
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()

                if current_section not in parsed_data['sections']:
                    parsed_data['sections'][current_section] = {}

                parsed_data['sections'][current_section][key] = value

        # Cache the parsed data
        self.cache.set('sysinfo_parsed', parsed_data, 'sysinfo')

        return parsed_data

    def get_cached_sysinfo(self) -> Optional[Dict[str, Any]]:
        """Get cached sysinfo data if available"""
        return self.cache.get('sysinfo_parsed')

    def get_sysinfo_section(self, section_name: str) -> Optional[Dict[str, Any]]:
        """Get specific section from cached sysinfo data"""
        cached_data = self.get_cached_sysinfo()
        if cached_data and 'sections' in cached_data:
            return cached_data['sections'].get(section_name.lower())
        return None


# Usage example and testing
if __name__ == "__main__":
    # Test the cache manager
    cache = DeviceDataCache()

    print("Testing DeviceDataCache...")

    # Test basic operations
    cache.set("test_key", {"value": 123, "name": "test"}, "test_command")
    result = cache.get("test_key")
    print(f"Cached data: {result}")

    # Test metadata
    metadata = cache.get_with_metadata("test_key")
    print(f"With metadata: {metadata}")

    # Test stats
    stats = cache.get_stats()
    print(f"Cache stats: {stats}")

    # Test sysinfo parser
    parser = SystemInfoParser(cache)
    sample_sysinfo = """=== System Information ===
Device: Gen6 PCIe Atlas 3 Host Card
Manufacturer: Serial Cables, LLC
Serial Number: SC240808001

=== Hardware ===
PCIe Slot: Slot 1
Bus Speed: PCIe 3.0 x4
Memory: 512MB DDR3
Flash: 64MB"""

    parsed = parser.parse_sysinfo(sample_sysinfo)
    print(f"Parsed sysinfo: {parsed}")

    # Test retrieval
    cached_sysinfo = parser.get_cached_sysinfo()
    print(f"Retrieved from cache: {cached_sysinfo is not None}")

    print("Cache manager test completed!")