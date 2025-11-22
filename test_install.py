#!/usr/bin/env python3
"""
Test script for jumpingjerboa

Run this after installation to verify everything works:
    python test_install.py
"""

import sys
import subprocess


def test_import():
    """Test that the package can be imported"""
    print("Testing import...", end=" ")
    try:
        import jumpingjerboa

        print("✓ Package imports successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import: {e}")
        return False


def test_dependencies():
    """Test that required dependencies are available"""
    print("Testing dependencies...", end=" ")
    try:
        import polars

        print("✓ Dependencies available")
        return True
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print("  Run: pip install polars")
        return False


def test_cli():
    """Test CLI help command"""
    print("Testing CLI...", end=" ")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "jumpingjerboa.main", "--help"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and "jumpingjerboa" in result.stdout:
            print("✓ CLI working")
            return True
        else:
            print("✗ CLI help failed")
            return False
    except Exception as e:
        print(f"✗ CLI test failed: {e}")
        return False


def main():
    print("\n=== jumpingjerboa Installation Test ===\n")

    tests = [test_import, test_dependencies, test_cli]

    results = [test() for test in tests]

    print("\n" + "=" * 40)
    if all(results):
        print("✓ All tests passed! Installation successful.")
        print("\nNext steps:")
        print("  1. Read QUICKSTART.md for usage examples")
        print("  2. Run: python -m jumpingjerboa.main diff /path/to/your.parquet")
    else:
        print("✗ Some tests failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
