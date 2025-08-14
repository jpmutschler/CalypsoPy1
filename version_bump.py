#!/usr/bin/env python3
"""
version_bump.py - Simplified and Fixed Version Management for CalypsoPy

Usage:
    python version_bump.py --show              # Show current version
    python version_bump.py --check             # Check version consistency
    python version_bump.py 1.2.0               # Set specific version
    python version_bump.py --patch             # Increment patch (1.1.0 -> 1.1.1)
    python version_bump.py --minor             # Increment minor (1.1.0 -> 1.2.0)
    python version_bump.py --major             # Increment major (1.1.0 -> 2.0.0)
"""

import re
import sys
import os
import argparse
from datetime import datetime
import urllib.parse


class VersionManager:
    """Enhanced version manager that handles URL encoding"""

    def __init__(self):
        self.project_root = os.path.dirname(os.path.abspath(__file__))

        # Files that contain version information
        self.version_files = {
            'main.py': {
                'pattern': r'APP_VERSION\s*=\s*["\']([^"\']+)["\']',
                'replacement': 'APP_VERSION = "{version}"',
                'description': 'Main application version'
            },
            'README.md': {
                'pattern': r'version-([^-\)]+)-',
                'replacement': 'version-{encoded_version}-',
                'description': 'README badge version',
                'url_encode': True  # Special flag for URL encoding
            },
            'Admin/__init__.py': {
                'pattern': r'__version__\s*=\s*["\']([^"\']+)["\']',
                'replacement': '__version__ = "{version}"',
                'description': 'Admin module version'
            },
            'Dashboards/__init__.py': {
                'pattern': r'__version__\s*=\s*["\']([^"\']+)["\']',
                'replacement': '__version__ = "{version}"',
                'description': 'Dashboard module version'
            }
        }

        # Optional files
        self.optional_files = {
            'setup.py': {
                'pattern': r'version\s*=\s*["\']([^"\']+)["\']',
                'replacement': 'version="{version}"',
                'description': 'Setup.py version'
            }
        }

    def url_encode_version(self, version):
        """URL encode version for README badges"""
        return urllib.parse.quote(version, safe='')

    def url_decode_version(self, encoded_version):
        """URL decode version from README badges"""
        return urllib.parse.unquote(encoded_version)

    def get_current_version(self):
        """Get current version from main.py"""
        main_py_path = os.path.join(self.project_root, 'main.py')

        try:
            with open(main_py_path, 'r', encoding='utf-8') as f:
                content = f.read()

            match = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return match.group(1)

        except Exception as e:
            print(f"Error reading version from main.py: {e}")

        return None

    def parse_version(self, version_str):
        """Parse version string into components"""
        # Handle URL decoding first
        clean_version = self.url_decode_version(version_str)

        # Handle prefixes
        prefix = ""
        numeric_version = clean_version

        for prefix_candidate in ["Beta ", "Alpha ", "Release ", "RC "]:
            if clean_version.startswith(prefix_candidate):
                prefix = prefix_candidate
                numeric_version = clean_version[len(prefix_candidate):]
                break

        # Parse major.minor.patch
        parts = numeric_version.split('.')

        try:
            major = int(parts[0]) if len(parts) > 0 else 1
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0

            return major, minor, patch, prefix

        except ValueError:
            print(f"Invalid version format: {version_str}")
            return 1, 0, 0, ""

    def format_version(self, major, minor, patch, prefix=""):
        """Format version components back to string"""
        return f"{prefix}{major}.{minor}.{patch}".strip()

    def increment_version(self, version_type):
        """Increment version by type"""
        current = self.get_current_version()
        if not current:
            print("Could not get current version")
            return None

        major, minor, patch, prefix = self.parse_version(current)

        if version_type == 'major':
            major += 1
            minor = 0
            patch = 0
        elif version_type == 'minor':
            minor += 1
            patch = 0
        elif version_type == 'patch':
            patch += 1
        else:
            print(f"Invalid version type: {version_type}")
            return None

        return self.format_version(major, minor, patch, prefix)

    def update_file_version(self, filepath, pattern_info, new_version):
        """Update version in a specific file with URL encoding support"""
        full_path = os.path.join(self.project_root, filepath)

        if not os.path.exists(full_path):
            return False

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            pattern = pattern_info['pattern']
            description = pattern_info['description']

            # Handle URL encoding for README.md
            if pattern_info.get('url_encode', False):
                encoded_version = self.url_encode_version(new_version)
                replacement = pattern_info['replacement'].format(
                    version=new_version,
                    encoded_version=encoded_version
                )
            else:
                replacement = pattern_info['replacement'].format(version=new_version)

            if re.search(pattern, content):
                new_content = re.sub(pattern, replacement, content)

                if new_content != content:
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)

                    print(f"✅ Updated {filepath}")
                    print(f"   └─ {description}")
                    return True
            else:
                print(f"⚠️  No version pattern found in {filepath}")
                return False

        except Exception as e:
            print(f"❌ Error updating {filepath}: {e}")
            return False

    def update_all_versions(self, new_version):
        """Update version in all project files"""
        print(f"🔄 Updating version to {new_version}")
        print("=" * 50)

        updated_count = 0

        # Update required files
        for filepath, pattern_info in self.version_files.items():
            if self.update_file_version(filepath, pattern_info, new_version):
                updated_count += 1

        # Update optional files
        for filepath, pattern_info in self.optional_files.items():
            full_path = os.path.join(self.project_root, filepath)
            if os.path.exists(full_path):
                if self.update_file_version(filepath, pattern_info, new_version):
                    updated_count += 1
            else:
                print(f"⏭️  Skipping {filepath} (file not found)")

        return updated_count

    def check_version_consistency(self):
        """Check version consistency with URL decoding"""
        print("🔍 Checking version consistency")
        print("=" * 30)

        found_versions = {}

        # Check all files
        all_files = {**self.version_files, **self.optional_files}

        for filepath, pattern_info in all_files.items():
            full_path = os.path.join(self.project_root, filepath)

            if not os.path.exists(full_path):
                print(f"⏭️  Skipping {filepath} (not found)")
                continue

            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                pattern = pattern_info['pattern']
                description = pattern_info['description']

                match = re.search(pattern, content)
                if match:
                    raw_version = match.group(1)

                    # Decode URL encoding if needed
                    if pattern_info.get('url_encode', False):
                        decoded_version = self.url_decode_version(raw_version)
                        found_versions[filepath] = decoded_version
                        print(f"📄 {filepath}: {decoded_version} (raw: {raw_version})")
                    else:
                        found_versions[filepath] = raw_version
                        print(f"📄 {filepath}: {raw_version}")

                    print(f"   └─ {description}")
                else:
                    print(f"⚠️  No version found in {filepath}")

            except Exception as e:
                print(f"❌ Error reading {filepath}: {e}")

        # Check for inconsistencies
        if found_versions:
            unique_versions = set(found_versions.values())
            if len(unique_versions) > 1:
                print("\n⚠️  Version inconsistencies found:")
                for version in unique_versions:
                    files_with_version = [f for f, v in found_versions.items() if v == version]
                    print(f"   {version}: {', '.join(files_with_version)}")
                print(f"\n💡 To fix, run: python version_bump.py \"{list(unique_versions)[0]}\"")
            else:
                print(f"\n✅ All versions consistent: {list(unique_versions)[0]}")

        return found_versions

    def suggest_git_commands(self, new_version):
        """Suggest git commands"""
        print("\n" + "=" * 50)
        print("📝 SUGGESTED NEXT STEPS:")
        print("=" * 50)
        print("1. Review changes:")
        print("   git diff")
        print()
        print(f"2. Update CHANGELOG in README.md for {new_version}")
        print()
        print("3. Commit changes:")
        print("   git add .")
        print(f"   git commit -m 'Bump version to {new_version}'")
        print()
        print("4. Create version tag:")
        print(f"   git tag v{new_version.replace(' ', '_')}")
        print()
        print("5. Push changes:")
        print("   git push && git push --tags")
        print("=" * 50)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='CalypsoPy Version Management')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('version', nargs='?', help='New version number (e.g., "Beta 1.3.3")')
    group.add_argument('--patch', action='store_true', help='Increment patch version')
    group.add_argument('--minor', action='store_true', help='Increment minor version')
    group.add_argument('--major', action='store_true', help='Increment major version')
    group.add_argument('--show', action='store_true', help='Show current version')
    group.add_argument('--check', action='store_true', help='Check version consistency')

    args = parser.parse_args()

    # Initialize version manager
    vm = VersionManager()

    # Handle commands
    if args.show:
        current = vm.get_current_version()
        if current:
            print(f"📊 Current version: {current}")
        else:
            print("❌ Could not determine current version")
        return

    if args.check:
        vm.check_version_consistency()
        return

    # Determine new version
    new_version = None

    if args.version:
        new_version = args.version
    elif args.patch:
        new_version = vm.increment_version('patch')
    elif args.minor:
        new_version = vm.increment_version('minor')
    elif args.major:
        new_version = vm.increment_version('major')

    if not new_version:
        print("❌ Could not determine new version")
        return

    # Show current version first
    current = vm.get_current_version()
    if current:
        print(f"📊 Current version: {current}")
        print(f"🎯 New version: {new_version}")
        print()

    # Update versions
    updated_count = vm.update_all_versions(new_version)

    # Summary
    print()
    print("=" * 50)
    print("✅ Version update complete!")
    print(f"📊 Updated {updated_count} files")

    if updated_count > 0:
        vm.suggest_git_commands(new_version)


if __name__ == "__main__":
    main()