#!/usr/bin/env python3
"""
debug_file_structure_check.py

Quick diagnostic script to check your CalypsoPy file structure
and debug import issues.

Run this in your CalypsoPy directory to diagnose the problem.
"""

import os
import sys


def check_file_structure():
    """Check CalypsoPy file structure"""
    print("=" * 60)
    print("CalypsoPy File Structure Check")
    print("=" * 60)

    current_dir = os.getcwd()
    print(f"Current directory: {current_dir}")
    print()

    # Check main files
    main_files = ['main.py', 'requirements.txt']
    for file in main_files:
        exists = os.path.exists(file)
        print(f"{'✓' if exists else '✗'} {file}: {'EXISTS' if exists else 'MISSING'}")

    print()

    # Check Admin directory
    admin_dir = 'Admin'
    admin_exists = os.path.exists(admin_dir)
    print(f"{'✓' if admin_exists else '✗'} Admin directory: {'EXISTS' if admin_exists else 'MISSING'}")

    if admin_exists:
        admin_files = [
            '__init__.py',
            'debug_config.py',
            'cache_manager.py',
            'enhanced_sysinfo_parser.py',
            'settings_manager.py'
        ]

        for file in admin_files:
            file_path = os.path.join(admin_dir, file)
            exists = os.path.exists(file_path)
            print(f"  {'✓' if exists else '✗'} Admin/{file}: {'EXISTS' if exists else 'MISSING'}")

    print()

    # Check Dashboards directory
    dashboard_dir = 'Dashboards'
    dashboard_exists = os.path.exists(dashboard_dir)
    print(f"{'✓' if dashboard_exists else '✗'} Dashboards directory: {'EXISTS' if dashboard_exists else 'MISSING'}")

    if dashboard_exists:
        dashboard_files = [
            '__init__.py',
            'demo_mode_integration.py',
            'host_card_info.py'
        ]

        for file in dashboard_files:
            file_path = os.path.join(dashboard_dir, file)
            exists = os.path.exists(file_path)
            print(f"  {'✓' if exists else '✗'} Dashboards/{file}: {'EXISTS' if exists else 'MISSING'}")

    print()

    # Check DemoData directory
    demo_dir = 'DemoData'
    demo_exists = os.path.exists(demo_dir)
    print(f"{'✓' if demo_exists else '✗'} DemoData directory: {'EXISTS' if demo_exists else 'MISSING'}")

    if demo_exists:
        demo_files = ['sysinfo.txt']
        for file in demo_files:
            file_path = os.path.join(demo_dir, file)
            exists = os.path.exists(file_path)
            print(f"  {'✓' if exists else '✗'} DemoData/{file}: {'EXISTS' if exists else 'MISSING'}")


def test_admin_import():
    """Test importing from Admin module"""
    print("\n" + "=" * 60)
    print("Admin Module Import Test")
    print("=" * 60)

    # Add current directory to path
    current_dir = os.getcwd()
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
        print(f"Added to Python path: {current_dir}")

    # Test 1: Basic Admin import
    print("\n1. Testing basic Admin import...")
    try:
        import Admin
        print("✓ import Admin - SUCCESS")
        print(f"  Admin module location: {Admin.__file__}")
        print(f"  Admin module contents: {[item for item in dir(Admin) if not item.startswith('_')]}")
    except ImportError as e:
        print(f"✗ import Admin - FAILED: {e}")
        return False

    # Test 2: debug_config import
    print("\n2. Testing debug_config import...")
    try:
        from Admin import debug_config
        print("✓ from Admin import debug_config - SUCCESS")
        print(f"  debug_config location: {debug_config.__file__}")
    except ImportError as e:
        print(f"✗ from Admin import debug_config - FAILED: {e}")
        return False

    # Test 3: Check if debug functions exist
    print("\n3. Checking debug functions...")
    debug_functions = ['debug_print', 'debug_error', 'debug_info', 'debug_warning']

    for func_name in debug_functions:
        if hasattr(debug_config, func_name):
            print(f"✓ {func_name} - EXISTS")
        else:
            print(f"✗ {func_name} - MISSING")

    # Test 4: Direct function import
    print("\n4. Testing direct function import...")
    try:
        from Admin.debug_config import debug_info
        print("✓ from Admin.debug_config import debug_info - SUCCESS")

        # Test the function
        debug_info("Test message", "TEST")
        print("✓ debug_info function call - SUCCESS")

    except ImportError as e:
        print(f"✗ from Admin.debug_config import debug_info - FAILED: {e}")
        return False
    except Exception as e:
        print(f"✗ debug_info function call - FAILED: {e}")
        return False

    return True


def check_python_environment():
    """Check Python environment"""
    print("\n" + "=" * 60)
    print("Python Environment Check")
    print("=" * 60)

    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path (first 5 entries):")
    for i, path in enumerate(sys.path[:5]):
        print(f"  {i + 1}. {path}")

    if len(sys.path) > 5:
        print(f"  ... and {len(sys.path) - 5} more entries")


def create_missing_files():
    """Create missing critical files"""
    print("\n" + "=" * 60)
    print("Creating Missing Files")
    print("=" * 60)

    # Create Admin/__init__.py if missing
    admin_init = os.path.join('Admin', '__init__.py')
    if not os.path.exists(admin_init):
        try:
            os.makedirs('Admin', exist_ok=True)
            with open(admin_init, 'w') as f:
                f.write('# Admin module initialization\n')
            print(f"✓ Created {admin_init}")
        except Exception as e:
            print(f"✗ Failed to create {admin_init}: {e}")
    else:
        print(f"✓ {admin_init} already exists")

    # Create Dashboards/__init__.py if missing
    dashboard_init = os.path.join('Dashboards', '__init__.py')
    if not os.path.exists(dashboard_init):
        try:
            os.makedirs('Dashboards', exist_ok=True)
            with open(dashboard_init, 'w') as f:
                f.write('# Dashboards module initialization\n')
            print(f"✓ Created {dashboard_init}")
        except Exception as e:
            print(f"✗ Failed to create {dashboard_init}: {e}")
    else:
        print(f"✓ {dashboard_init} already exists")


def main():
    """Run all diagnostic checks"""
    print("CalypsoPy Debug Import Diagnostic Tool")
    print("This will help identify why debug_info import is failing\n")

    # Run all checks
    check_python_environment()
    check_file_structure()
    create_missing_files()

    # Test imports
    import_success = test_admin_import()

    print("\n" + "=" * 60)
    print("DIAGNOSIS SUMMARY")
    print("=" * 60)

    if import_success:
        print("✓ Admin module imports are working correctly")
        print("  The issue may be elsewhere in your main.py")
        print("  Try running your application again")
    else:
        print("✗ Admin module imports are failing")
        print("  Possible solutions:")
        print("  1. Check that Admin/debug_config.py contains the debug_info function")
        print("  2. Verify Admin/__init__.py exists (created above if missing)")
        print("  3. Make sure you're running from the CalypsoPy root directory")
        print("  4. Try restarting your Python environment/IDE")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()