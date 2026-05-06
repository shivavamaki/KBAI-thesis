# MediCheck Distribution Package

This package contains everything needed to run the MediCheck Pharmacist Review App.

## Package Contents

```
medicheck-app/
│
├── run.bat                      # Windows launcher (double-click to start)
├── run.sh                       # Mac/Linux launcher (bash run.sh)
├── launch.py                    # Universal Python launcher
│
├── QUICKSTART.md                # User guide (read first!)
├── requirements.txt             # Python dependencies
├── README.md                    # Technical documentation
│
├── pharmacist_app/
│   └── app.py                   # Streamlit application
│
├── data/
│   ├── sample_prescriptions.json # Demo data for testing
│   ├── raw/                     # Place your input data here
│   ├── processed/              # Processing results
│   └── samples/                # Sample datasets
│
├── outputs/                     # Where classifications are saved
│
└── .streamlit/
    └── config.toml             # Streamlit configuration
```

## Quick Start

### Windows
1. Extract the package
2. Double-click `run.bat`
3. Wait 2-3 minutes (first time setup)
4. Browser opens automatically to http://localhost:8501

### Mac/Linux
1. Extract the package
2. Open Terminal
3. Navigate to the package: `cd path/to/medicheck-app`
4. Run: `bash run.sh` or `python3 launch.py`
5. Browser opens automatically to http://localhost:8501

## System Requirements

- **Operating System:** Windows 7+, macOS 10.14+, Ubuntu 16.04+, or any Linux with Python 3.10+
- **Disk Space:** ~500MB (for Python + dependencies)
- **RAM:** 2GB minimum, 4GB recommended
- **Internet:** Required for first download of dependencies

## What Gets Downloaded?

After first launch, the app downloads and installs:
- Python virtual environment (local, no admin needed)
- Streamlit 1.35.0+
- Pandas 2.2.0+
- OpenAI API client
- Pydantic validation
- Supporting libraries

**Total size:** ~150-200 MB

Everything is isolated in a `venv/` folder. Uninstall by simply deleting the app folder.

## Default Paths

When you first load the app:
- **Input file:** `data/raw/RT_COMMON_904_test_clean_blinded_first_sheet.json`
- **Output file:** `outputs/pharmacist_reference.json`

You can change these in the app's sidebar.

## Support

See **QUICKSTART.md** for troubleshooting and detailed instructions.

---

**Version:** 0.1.0  
**Framework:** Streamlit  
**Python:** 3.10+  
**License:** See LICENSE file (if included)
