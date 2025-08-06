#!/usr/bin/env python3
"""
Test runner script for the FastAPI application.
This script provides convenient ways to run different types of tests.
"""

import subprocess
import sys
import argparse
from pathlib import Path


def run_tests(test_type=None, verbose=False, coverage=False):
    """Run tests with the specified options."""
    cmd = ["uv", "run", "pytest"]

    if verbose:
        cmd.append("-v")

    if coverage:
        cmd.extend(["--cov=.", "--cov-report=html", "--cov-report=term"])

    if test_type:
        if test_type == "crud":
            cmd.append("-m crud")
        elif test_type == "llm":
            cmd.append("-m llm")
        elif test_type == "auth":
            cmd.append("-m auth")
        elif test_type == "unit":
            cmd.append("-m unit")
        elif test_type == "integration":
            cmd.append("-m integration")
        elif test_type == "slow":
            cmd.append("-m slow")
        else:
            print(f"Unknown test type: {test_type}")
            return False

    # Add the tests directory
    cmd.append("tests/")

    print(f"Running command: {' '.join(cmd)}")

    # Clean up any existing test database before running tests
    test_db_path = Path(__file__).parent.parent / "test.db"
    if test_db_path.exists():
        try:
            test_db_path.unlink()
            print(f"🧹 Cleaned up existing test database: {test_db_path}")
        except OSError as e:
            print(
                f"⚠️  Warning: Could not delete existing test database {test_db_path}: {e}"
            )

    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)

    # Clean up test database after tests complete
    # Wait a moment for any remaining connections to close
    import time

    time.sleep(0.1)

    if test_db_path.exists():
        try:
            test_db_path.unlink()
            print(f"🧹 Cleaned up test database: {test_db_path}")
        except OSError as e:
            print(f"⚠️  Warning: Could not delete test database {test_db_path}: {e}")
            # Try again after a longer delay
            time.sleep(1)
            try:
                test_db_path.unlink()
                print(f"🧹 Cleaned up test database (retry): {test_db_path}")
            except OSError as e2:
                print(f"❌ Failed to delete test database {test_db_path}: {e2}")

    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Run FastAPI application tests")
    parser.add_argument(
        "--type",
        choices=["crud", "llm", "auth", "unit", "integration", "slow"],
        help="Type of tests to run",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--coverage", action="store_true", help="Run with coverage report"
    )
    parser.add_argument("--all", action="store_true", help="Run all tests")

    args = parser.parse_args()

    if args.all:
        print("Running all tests...")
        success = run_tests(verbose=args.verbose, coverage=args.coverage)
    else:
        success = run_tests(
            test_type=args.type, verbose=args.verbose, coverage=args.coverage
        )

    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
