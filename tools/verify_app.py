#!/usr/bin/env python3
"""
MediCheck App - Quick Verification Script
Tests if the app is ready to run and distribute
"""

import os
import sys
import json
import subprocess
from pathlib import Path
import platform


class Colors:
    """ANSI color codes"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


def print_header(text):
    print(f"\n{Colors.BLUE}{'='*50}{Colors.END}")
    print(f"{Colors.BLUE}  {text}{Colors.END}")
    print(f"{Colors.BLUE}{'='*50}{Colors.END}\n")


def print_success(msg):
    print(f"{Colors.GREEN}[✓]{Colors.END} {msg}")


def print_error(msg):
    print(f"{Colors.RED}[✗]{Colors.END} {msg}")


def print_warning(msg):
    print(f"{Colors.YELLOW}[!]{Colors.END} {msg}")


def check_file(path, description=""):
    """Check if a file exists"""
    p = Path(path)
    if p.exists() and p.is_file():
        print_success(f"{path}")
        return True
    else:
        print_error(f"{path} — NOT FOUND")
        return False


def check_directory(path, description=""):
    """Check if a directory exists"""
    p = Path(path)
    if p.exists() and p.is_dir():
        print_success(f"Directory: {path}")
        return True
    else:
        print_error(f"Directory: {path} — NOT FOUND")
        return False


def validate_json(filepath):
    """Validate JSON file syntax"""
    try:
        with open(filepath, 'r') as f:
            json.load(f)
        print_success(f"Valid JSON: {filepath}")
        return True
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON in {filepath}: {e}")
        return False
    except FileNotFoundError:
        print_error(f"JSON file not found: {filepath}")
        return False


def check_python_syntax(filepath):
    """Check Python file syntax"""
    try:
        with open(filepath, 'r') as f:
            compile(f.read(), filepath, 'exec')
        print_success(f"Valid Python syntax: {filepath}")
        return True
    except SyntaxError as e:
        print_error(f"Syntax error in {filepath}: {e}")
        return False
    except FileNotFoundError:
        print_error(f"Python file not found: {filepath}")
        return False


def main():
    print_header("MediCheck App - Verification Check")
    
    results = {
        "files_ok": True,
        "json_ok": True,
        "python_ok": True,
        "dirs_ok": True,
    }
    
    # Test 1: Required files
    print(f"{Colors.BLUE}[TEST 1] Required Files{Colors.END}")
    required_files = [
        "run.bat",
        "run.sh",
        "launch.py",
        "docs/QUICKSTART.md",
        "docs/DISTRIBUTION.md",
        "requirements.txt",
        "pharmacist_app/app.py",
    ]
    
    for f in required_files:
        if not check_file(f):
            results["files_ok"] = False
    
    # Test 2: Python syntax
    print(f"\n{Colors.BLUE}[TEST 2] Python Syntax{Colors.END}")
    python_files = [
        "pharmacist_app/app.py",
        "launch.py",
    ]
    
    for f in python_files:
        if not check_python_syntax(f):
            results["python_ok"] = False
    
    # Test 3: JSON files
    print(f"\n{Colors.BLUE}[TEST 3] JSON Files{Colors.END}")
    json_files = [
        "data/sample_prescriptions.json",
    ]
    
    for f in json_files:
        if not validate_json(f):
            results["json_ok"] = False
    
    # Test 4: Directories
    print(f"\n{Colors.BLUE}[TEST 4] Directories{Colors.END}")
    required_dirs = [
        "data",
        "data/raw",
        "data/processed",
        "outputs",
        "pharmacist_app",
        ".streamlit",
        "docs",
        "tools",
    ]
    
    for d in required_dirs:
        if not check_directory(d):
            results["dirs_ok"] = False
    
    # Test 5: Python version
    print(f"\n{Colors.BLUE}[TEST 5] Python Environment{Colors.END}")
    version_info = sys.version_info
    if version_info >= (3, 10):
        print_success(f"Python {version_info.major}.{version_info.minor}.{version_info.micro}")
    else:
        print_error(f"Python 3.10+ required, found {version_info.major}.{version_info.minor}")
        results["python_ok"] = False
    
    # Test 6: System info
    print(f"\n{Colors.BLUE}[TEST 6] System Information{Colors.END}")
    print_success(f"OS: {platform.system()} {platform.release()}")
    print_success(f"Python: {platform.python_implementation()} {platform.python_version()}")
    print_success(f"Architecture: {platform.architecture()[0]}")
    
    # Summary
    print_header("Summary")
    
    all_ok = all(results.values())
    
    if all_ok:
        print_success("All checks passed!")
        print(f"\n{Colors.GREEN}✓ App is ready for distribution{Colors.END}\n")
        print("Next steps:")
        print("  1. Test the app locally: python3 launch.py")
        print("  2. Run test_package.bat or bash test_package.sh")
        print("  3. Create distribution: create_package.bat or bash create_package.sh")
        print("  4. Share the ZIP file with users")
        return 0
    else:
        print_error("Some checks failed!")
        print(f"\n{Colors.RED}✗ Fix issues above before distributing{Colors.END}\n")
        
        if not results["files_ok"]:
            print_warning("Missing required files")
        if not results["python_ok"]:
            print_warning("Python issues detected")
        if not results["json_ok"]:
            print_warning("Invalid JSON files")
        if not results["dirs_ok"]:
            print_warning("Missing directories")
        
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nVerification cancelled.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
