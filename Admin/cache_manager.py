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
from debug_config import debug, cache_debug, log_info, log_error, log_debug, log_warning

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
        ENHANCED: Initialize cache manager with debug logging
        """
        cache_debug("Initializing DeviceDataCache", "CACHE_INIT")

        # Default settings
        self.default_ttl = default_ttl
        self._lock = threading.RLock()

        # Setup cache directory
        if cache_dir is None:
            self.cache_dir = os.path.join(tempfile.gettempdir(), "calypsopy_cache")
        else:
            self.cache_dir = cache_dir

        cache_debug(f"Cache directory: {self.cache_dir}", "CACHE_DIR")
        cache_debug(f"Default TTL: {default_ttl} seconds", "CACHE_TTL")

        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        cache_debug("Cache directory created/verified", "DIR_READY")

        # In-memory cache for fast access
        self._memory_cache: Dict[str, CacheEntry] = {}

        # Cache file paths
        self.cache_file = os.path.join(self.cache_dir, "device_cache.json")
        self.metadata_file = os.path.join(self.cache_dir, "cache_metadata.json")

        cache_debug(f"Cache file: {self.cache_file}", "CACHE_FILE")
        cache_debug(f"Metadata file: {self.metadata_file}", "META_FILE")

        # Load existing cache
        self._load_cache()

        # Start cleanup thread
        self._start_cleanup_thread()

        cache_debug("DeviceDataCache initialization completed", "INIT_COMPLETE")

    def _load_cache(self):
        """ENHANCED: Load cache from JSON file with debug logging"""
        cache_debug("Loading cache from file", "LOAD_START")

        try:
            if os.path.exists(self.cache_file):
                cache_debug(f"Cache file exists: {self.cache_file}", "FILE_EXISTS")

                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)

                cache_debug(f"Loaded {len(cache_data)} cache entries from file", "ENTRIES_LOADED")

                # Reconstruct cache entries
                loaded_count = 0
                expired_count = 0

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
                        loaded_count += 1
                        cache_debug(f"Loaded cache entry: {key}", "ENTRY_LOADED")
                    else:
                        expired_count += 1
                        cache_debug(f"Skipped expired entry: {key}", "ENTRY_EXPIRED")

                cache_debug(f"Cache load complete: {loaded_count} loaded, {expired_count} expired", "LOAD_COMPLETE")
            else:
                cache_debug("No existing cache file found", "NO_FILE")

        except Exception as e:
            cache_debug(f"Error loading cache: {e}", "LOAD_ERROR")
            log_error(f"Could not load cache file: {e}", "cache_manager")
            self._memory_cache = {}

    def _save_cache(self):
        """ENHANCED: Save cache to JSON file with debug logging"""
        cache_debug("Saving cache to file", "SAVE_START")

        try:
            # Convert cache entries to serializable format
            cache_data = {}
            saved_count = 0
            expired_count = 0

            for key, entry in self._memory_cache.items():
                if not entry.is_expired():  # Only save non-expired entries
                    cache_data[key] = {
                        'data': entry.data,
                        'timestamp': entry.timestamp,
                        'command': entry.command,
                        'expires_at': entry.expires_at
                    }
                    saved_count += 1
                else:
                    expired_count += 1

            cache_debug(f"Preparing to save {saved_count} entries, skipping {expired_count} expired", "SAVE_PREP")

            # Write to file atomically
            temp_file = self.cache_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, default=str)

            cache_debug(f"Written cache data to temp file: {temp_file}", "TEMP_WRITTEN")

            # Atomic move
            if os.name == 'nt':  # Windows
                if os.path.exists(self.cache_file):
                    os.remove(self.cache_file)
                os.rename(temp_file, self.cache_file)
            else:  # Unix/Linux
                os.rename(temp_file, self.cache_file)

            cache_debug(f"Cache file updated: {self.cache_file}", "FILE_UPDATED")

            # Save metadata
            file_size = os.path.getsize(self.cache_file) if os.path.exists(self.cache_file) else 0
            metadata = {
                'last_save': time.time(),
                'entry_count': len(cache_data),
                'cache_size_bytes': file_size
            }

            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)

            cache_debug(f"Cache save complete: {saved_count} entries, {file_size} bytes", "SAVE_COMPLETE")

        except Exception as e:
            cache_debug(f"Error saving cache: {e}", "SAVE_ERROR")
            log_error(f"Could not save cache file: {e}", "cache_manager")

    def set(self, key: str, data: Any, command: str = "", ttl: Optional[int] = None) -> None:
        """
        ENHANCED: Store data in cache with debug logging
        """
        if ttl is None:
            ttl = self.default_ttl

        cache_debug(f"Setting cache entry: {key}", "SET_START")
        cache_debug(f"Command: {command}, TTL: {ttl}s", "SET_PARAMS")

        expires_at = time.time() + ttl

        with self._lock:
            entry = CacheEntry(
                data=data,
                timestamp=time.time(),
                command=command,
                expires_at=expires_at
            )

            # Check if we're updating an existing entry
            is_update = key in self._memory_cache
            self._memory_cache[key] = entry

            cache_debug(f"Cache entry {'updated' if is_update else 'created'}: {key}", "SET_STORED")

            # Save to file
            self._save_cache()

            cache_debug(f"Cache set complete for: {key}", "SET_COMPLETE")

    def get(self, key: str) -> Optional[Any]:
        """
        ENHANCED: Retrieve data from cache with debug logging
        """
        cache_debug(f"Getting cache entry: {key}", "GET_START")

        with self._lock:
            entry = self._memory_cache.get(key)

            if entry is None:
                cache_debug(f"Cache miss: {key}", "CACHE_MISS")
                return None

            if entry.is_expired():
                cache_debug(f"Cache entry expired: {key}", "CACHE_EXPIRED")
                # Remove expired entry
                del self._memory_cache[key]
                self._save_cache()
                return None

            age = entry.age_seconds()
            cache_debug(f"Cache hit: {key} (age: {age:.1f}s)", "CACHE_HIT")
            return entry.data

    def get_with_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """
        ENHANCED: Retrieve data with metadata from cache with debug logging
        """
        cache_debug(f"Getting cache entry with metadata: {key}", "META_GET")

        with self._lock:
            entry = self._memory_cache.get(key)

            if entry is None:
                cache_debug(f"Cache miss (metadata): {key}", "META_MISS")
                return None

            if entry.is_expired():
                cache_debug(f"Cache entry expired (metadata): {key}", "META_EXPIRED")
                del self._memory_cache[key]
                self._save_cache()
                return None

            age = entry.age_seconds()
            cache_debug(f"Cache hit (metadata): {key} (age: {age:.1f}s)", "META_HIT")

            return {
                'data': entry.data,
                'timestamp': entry.timestamp,
                'command': entry.command,
                'age_seconds': age,
                'expires_at': entry.expires_at
            }

    def invalidate(self, key: str) -> bool:
        """
        ENHANCED: Remove entry from cache with debug logging
        """
        cache_debug(f"Invalidating cache entry: {key}", "INVALIDATE")

        with self._lock:
            if key in self._memory_cache:
                del self._memory_cache[key]
                self._save_cache()
                cache_debug(f"Cache entry invalidated: {key}", "INVALIDATED")
                return True
            else:
                cache_debug(f"Cache entry not found for invalidation: {key}", "NOT_FOUND")
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
        """ENHANCED: Clear all cache entries with debug logging"""
        cache_debug("Clearing all cache entries", "CLEAR_START")

        with self._lock:
            entry_count = len(self._memory_cache)
            self._memory_cache.clear()
            self._save_cache()

        cache_debug(f"Cache cleared: {entry_count} entries removed", "CLEAR_COMPLETE")

    def debug_cache_state(self):
        """Debug method to show detailed cache state"""
        cache_debug("=== CACHE STATE DEBUG ===", "STATE_DEBUG")

        with self._lock:
            total_entries = len(self._memory_cache)
            cache_debug(f"Total entries in memory: {total_entries}", "TOTAL_ENTRIES")

            if total_entries == 0:
                cache_debug("Cache is empty", "EMPTY_CACHE")
                return

            # Analyze entries by type and age
            entry_analysis = {}
            age_distribution = {'fresh': 0, 'stale': 0, 'expired': 0}

            for key, entry in self._memory_cache.items():
                # Categorize by key prefix
                key_type = key.split('_')[0] if '_' in key else 'other'
                if key_type not in entry_analysis:
                    entry_analysis[key_type] = 0
                entry_analysis[key_type] += 1

                # Categorize by age
                age = entry.age_seconds()
                if entry.is_expired():
                    age_distribution['expired'] += 1
                elif age > 300:  # Older than 5 minutes
                    age_distribution['stale'] += 1
                else:
                    age_distribution['fresh'] += 1

                cache_debug(f"Entry: {key} | Age: {age:.1f}s | Command: {entry.command}", "ENTRY_DETAIL")

            # Show analysis
            cache_debug("Entry types:", "TYPE_ANALYSIS")
            for entry_type, count in entry_analysis.items():
                cache_debug(f"  {entry_type}: {count} entries", "TYPE_COUNT")

            cache_debug("Age distribution:", "AGE_ANALYSIS")
            for age_type, count in age_distribution.items():
                cache_debug(f"  {age_type}: {count} entries", "AGE_COUNT")

        cache_debug("=== END CACHE STATE DEBUG ===", "STATE_DEBUG")

    def monitor_cache_performance(self) -> Dict[str, Any]:
        """Monitor cache performance metrics"""
        cache_debug("Monitoring cache performance", "PERF_MONITOR")

        with self._lock:
            stats = self.get_stats()

            # Calculate cache efficiency
            total_entries = stats['total_entries']
            valid_entries = stats['valid_entries']
            expired_entries = stats['expired_entries']

            efficiency = (valid_entries / total_entries * 100) if total_entries > 0 else 100

            # File size analysis
            file_size_mb = stats['cache_file_size'] / (1024 * 1024)

            performance_metrics = {
                'efficiency_percent': efficiency,
                'file_size_mb': file_size_mb,
                'memory_entries': total_entries,
                'expired_ratio': (expired_entries / total_entries * 100) if total_entries > 0 else 0
            }

            cache_debug(f"Cache efficiency: {efficiency:.1f}%", "PERF_EFFICIENCY")
            cache_debug(f"File size: {file_size_mb:.2f} MB", "PERF_SIZE")
            cache_debug(f"Expired ratio: {performance_metrics['expired_ratio']:.1f}%", "PERF_EXPIRED")

            return performance_metrics

    def validate_cache_integrity(self) -> bool:
        """Validate cache integrity and consistency"""
        cache_debug("Validating cache integrity", "INTEGRITY_CHECK")

        issues_found = 0

        try:
            with self._lock:
                # Check for corrupted entries
                for key, entry in self._memory_cache.items():
                    if not hasattr(entry, 'data') or not hasattr(entry, 'timestamp'):
                        cache_debug(f"Corrupted entry found: {key}", "CORRUPT_ENTRY")
                        issues_found += 1

                    if entry.timestamp > time.time():
                        cache_debug(f"Future timestamp found: {key}", "FUTURE_TIMESTAMP")
                        issues_found += 1

                    if entry.expires_at < entry.timestamp:
                        cache_debug(f"Invalid expiry time: {key}", "INVALID_EXPIRY")
                        issues_found += 1

            # Check file system consistency
            if os.path.exists(self.cache_file):
                try:
                    with open(self.cache_file, 'r') as f:
                        json.load(f)
                    cache_debug("Cache file JSON is valid", "JSON_VALID")
                except json.JSONDecodeError as e:
                    cache_debug(f"Cache file JSON is corrupted: {e}", "JSON_CORRUPT")
                    issues_found += 1

            if issues_found == 0:
                cache_debug("Cache integrity validation passed", "INTEGRITY_PASS")
                return True
            else:
                cache_debug(f"Cache integrity validation failed: {issues_found} issues", "INTEGRITY_FAIL")
                return False

        except Exception as e:
            cache_debug(f"Error during integrity check: {e}", "INTEGRITY_ERROR")
            log_error(f"Cache integrity check failed: {e}", "cache_manager")
            return False

    def get_cache_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive cache health report"""
        cache_debug("Generating cache health report", "HEALTH_REPORT")

        health_report = {
            'timestamp': datetime.now().isoformat(),
            'overall_health': 'unknown',
            'statistics': self.get_stats(),
            'performance': self.monitor_cache_performance(),
            'integrity': self.validate_cache_integrity(),
            'recommendations': []
        }

        # Determine overall health
        perf = health_report['performance']
        integrity = health_report['integrity']
        stats = health_report['statistics']

        issues = []
        recommendations = []

        # Check efficiency
        if perf['efficiency_percent'] < 70:
            issues.append("Low cache efficiency")
            recommendations.append("Consider clearing expired entries or reducing TTL")

        # Check file size
        if perf['file_size_mb'] > 10:
            issues.append("Large cache file size")
            recommendations.append("Consider implementing cache size limits")

        # Check integrity
        if not integrity:
            issues.append("Cache integrity issues detected")
            recommendations.append("Rebuild cache from scratch")

        # Check expired ratio
        if perf['expired_ratio'] > 30:
            issues.append("High expired entry ratio")
            recommendations.append("Increase cleanup frequency")

        # Determine overall health
        if len(issues) == 0:
            health_report['overall_health'] = 'excellent'
        elif len(issues) <= 2:
            health_report['overall_health'] = 'good'
        elif len(issues) <= 4:
            health_report['overall_health'] = 'fair'
        else:
            health_report['overall_health'] = 'poor'

        health_report['issues'] = issues
        health_report['recommendations'] = recommendations

        cache_debug(f"Health report generated: {health_report['overall_health']}", "HEALTH_COMPLETE")
        return health_report

    def export_cache_debug_info(self, filepath: Optional[str] = None) -> str:
        """Export detailed cache debug information to file"""
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(self.cache_dir, f"cache_debug_{timestamp}.txt")

        cache_debug(f"Exporting cache debug info to: {filepath}", "DEBUG_EXPORT")

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("CalypsoPy Cache Debug Information\n")
                f.write("=" * 50 + "\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n")
                f.write(f"Cache Directory: {self.cache_dir}\n")
                f.write(f"Default TTL: {self.default_ttl} seconds\n\n")

                # Health report
                health = self.get_cache_health_report()
                f.write("HEALTH REPORT\n")
                f.write("-" * 20 + "\n")
                f.write(f"Overall Health: {health['overall_health']}\n")
                f.write(f"Integrity: {'PASS' if health['integrity'] else 'FAIL'}\n")
                f.write(f"Efficiency: {health['performance']['efficiency_percent']:.1f}%\n")
                f.write(f"File Size: {health['performance']['file_size_mb']:.2f} MB\n")

                if health['issues']:
                    f.write("\nISSUES:\n")
                    for issue in health['issues']:
                        f.write(f"  - {issue}\n")

                if health['recommendations']:
                    f.write("\nRECOMMENDATIONS:\n")
                    for rec in health['recommendations']:
                        f.write(f"  - {rec}\n")

                # Detailed statistics
                f.write("\n\nDETAILED STATISTICS\n")
                f.write("-" * 30 + "\n")
                stats = health['statistics']
                for key, value in stats.items():
                    f.write(f"{key}: {value}\n")

                # Entry list
                f.write("\n\nCACHE ENTRIES\n")
                f.write("-" * 20 + "\n")
                entries = self.get_entry_list()
                for entry in entries:
                    status = "EXPIRED" if entry['expired'] else "VALID"
                    f.write(f"{entry['key']:<30} {status:<8} {entry['age_seconds']:.1f}s {entry['command']}\n")

            cache_debug(f"Debug info exported successfully to: {filepath}", "EXPORT_SUCCESS")
            return filepath

        except Exception as e:
            cache_debug(f"Failed to export debug info: {e}", "EXPORT_ERROR")
            log_error(f"Cache debug export failed: {e}", "cache_manager")
            raise

    def cleanup_expired(self) -> int:
        """
        ENHANCED: Remove expired entries with debug logging
        """
        cache_debug("Starting expired entry cleanup", "CLEANUP_START")

        removed_count = 0

        with self._lock:
            expired_keys = [
                key for key, entry in self._memory_cache.items()
                if entry.is_expired()
            ]

            for key in expired_keys:
                del self._memory_cache[key]
                removed_count += 1
                cache_debug(f"Removed expired entry: {key}", "EXPIRED_REMOVED")

            if removed_count > 0:
                self._save_cache()

        cache_debug(f"Cleanup complete: {removed_count} expired entries removed", "CLEANUP_COMPLETE")
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


# ============================================================================
# ENHANCED CLEANUP AND MAINTENANCE
# ============================================================================

def _start_cleanup_thread(self):
    """ENHANCED: Start background thread for periodic cleanup with debug logging"""
    cache_debug("Starting cache cleanup thread", "CLEANUP_THREAD")

    def cleanup_worker():
        cache_debug("Cache cleanup worker thread started", "WORKER_START")

        while True:
            try:
                time.sleep(300)  # Run cleanup every 5 minutes
                cache_debug("Running periodic cache cleanup", "PERIODIC_CLEANUP")

                removed = self.cleanup_expired()
                if removed > 0:
                    cache_debug(f"Periodic cleanup removed {removed} expired entries", "CLEANUP_RESULT")

                # Additional maintenance tasks
                self._perform_maintenance()

            except Exception as e:
                cache_debug(f"Cleanup worker error: {e}", "CLEANUP_ERROR")
                log_error(f"Cache cleanup error: {e}", "cache_manager")

    cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
    cleanup_thread.start()
    cache_debug("Cache cleanup thread started successfully", "THREAD_STARTED")


def _perform_maintenance(self):
    """Perform additional cache maintenance tasks"""
    cache_debug("Performing cache maintenance", "MAINTENANCE")

    try:
        # Check cache health
        health = self.get_cache_health_report()

        # Auto-optimize based on health
        if health['performance']['expired_ratio'] > 50:
            cache_debug("High expired ratio detected, forcing cleanup", "AUTO_CLEANUP")
            self.cleanup_expired()

        if health['performance']['file_size_mb'] > 50:  # 50 MB limit
            cache_debug("Large cache file detected, consider optimization", "SIZE_WARNING")
            log_warning("Cache file is becoming large, consider clearing old data", "cache_manager")

        cache_debug("Cache maintenance completed", "MAINTENANCE_DONE")

    except Exception as e:
        cache_debug(f"Maintenance error: {e}", "MAINTENANCE_ERROR")
        log_error(f"Cache maintenance failed: {e}", "cache_manager")


# ============================================================================
# ENHANCED STATISTICS AND MONITORING
# ============================================================================

def get_stats(self) -> Dict[str, Any]:
    """ENHANCED: Get cache statistics with additional metrics"""
    with self._lock:
        total_entries = len(self._memory_cache)
        expired_entries = sum(1 for entry in self._memory_cache.values() if entry.is_expired())

        # Calculate total data size (approximate)
        total_data_size = 0
        for entry in self._memory_cache.values():
            try:
                # Rough estimation of data size
                total_data_size += len(str(entry.data))
            except:
                pass

        # Get file size
        file_size = 0
        try:
            if os.path.exists(self.cache_file):
                file_size = os.path.getsize(self.cache_file)
        except:
            pass

        # Age analysis
        ages = [entry.age_seconds() for entry in self._memory_cache.values()]
        avg_age = sum(ages) / len(ages) if ages else 0
        max_age = max(ages) if ages else 0
        min_age = min(ages) if ages else 0

        stats = {
            'total_entries': total_entries,
            'expired_entries': expired_entries,
            'valid_entries': total_entries - expired_entries,
            'cache_file_size': file_size,
            'cache_directory': self.cache_dir,
            'default_ttl': self.default_ttl,
            'estimated_data_size_bytes': total_data_size,
            'average_age_seconds': avg_age,
            'max_age_seconds': max_age,
            'min_age_seconds': min_age,
            'cache_efficiency_percent': (
                        (total_entries - expired_entries) / total_entries * 100) if total_entries > 0 else 100
        }

        cache_debug(f"Cache statistics calculated: {stats['valid_entries']}/{stats['total_entries']} valid",
                    "STATS_CALC")
        return stats

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