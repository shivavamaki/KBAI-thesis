#!/usr/bin/env python3
"""
MediCheck Pharmacist Review App - Launcher
Automatically handles Python environment setup and launches the Streamlit app.
Works on Windows, Mac, and Linux without manual virtual environment setup.
"""

import os
import sys
import subprocess
import platform
import venv
from pathlib import Path


def print_header(text):
    print("\n" + "="*50)
    print(f"  {text}")
    print("="*50 + "\n")


def print_status(status, message):
    symbols = {"✓": "✓", "→": "→", "✗": "✗"}
    print(f"[{symbols.get(status, '?')}] {message}")


def check_python_version():
    """Verify Python 3.10+ is available."""
    if sys.version_info < (3, 10):
        print_status("✗", f"Python 3.10+ required, but found {sys.version_info.major}.{sys.version_info.minor}")
        sys.exit(1)
    print_status("✓", f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} found")


def create_virtualenv():
    """Create virtual environment if it doesn't exist."""
    venv_path = Path("venv")
    
    if venv_path.exists():
        print_status("✓", "Virtual environment already exists")
        return
    
    print_status("→", "Creating Python virtual environment...")
    try:
        venv.create(venv_path, with_pip=True, clear=False)
        print_status("✓", "Virtual environment created")
    except Exception as e:
        print_status("✗", f"Failed to create virtual environment: {e}")
        sys.exit(1)


def get_venv_python():
    """Get the Python executable path in the virtual environment."""
    system = platform.system()
    
    if system == "Windows":
        return Path("venv") / "Scripts" / "python.exe"
    else:
        return Path("venv") / "bin" / "python"


def install_dependencies():
    """Install required packages."""
    venv_python = get_venv_python()
    
    print_status("→", "Installing dependencies (this may take a minute)...")
    
    # Upgrade pip first
    try:
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "--quiet", "--upgrade", "pip", "setuptools"],
            check=True,
            capture_output=True
        )
    except subprocess.CalledProcessError as e:
        print_status("✗", f"Failed to upgrade pip: {e}")
        sys.exit(1)
    
    # Install requirements
    try:
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "--quiet", "-r", "requirements.txt"],
            check=True,
            capture_output=True
        )
        print_status("✓", "All dependencies installed")
    except subprocess.CalledProcessError as e:
        print_status("✗", f"Failed to install dependencies: {e}")
        sys.exit(1)


def setup_directories():
    """Create necessary data and output directories."""
    datadir = Path("data")
    datadir.mkdir(exist_ok=True)
    
    outdir = Path("outputs")
    outdir.mkdir(exist_ok=True)
    
    print_status("✓", "Data directories ready")


def launch_app():
    """Launch the Streamlit application."""
    venv_python = get_venv_python()
    
    print_header("Launching MediCheck...")
    
    print("The app will open in your browser at:")
    print("  http://localhost:8501\n")
    print("Press Ctrl+C to stop the server\n")
    
    try:
        subprocess.run(
            [str(venv_python), "-m", "streamlit", "run", "pharmacist_app/app.py", "--logger.level=warning"],
            check=False
        )
    except KeyboardInterrupt:
        print_status("✓", "Server stopped")
        sys.exit(0)
    except Exception as e:
        print_status("✗", f"Failed to launch app: {e}")
        sys.exit(1)


def main():
    """Main launcher flow."""
    print_header("MediCheck Pharmacist Review App")
    
    # Verify Python version
    check_python_version()
    
    # Setup virtual environment
    print()
    create_virtualenv()
    
    # Install dependencies
    print()
    install_dependencies()
    
    # Create directories
    print()
    setup_directories()
    
    # Launch app
    launch_app()


if __name__ == "__main__":
    main()
