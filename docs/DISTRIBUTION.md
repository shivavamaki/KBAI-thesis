# How to Create & Distribute MediCheck App

A step-by-step guide for preparing the MediCheck Pharmacist Review App for download and distribution.

## Overview

The goal is to create a single, portable archive file that users can extract and run immediately without:
- Installing an EXE
- Running an installer
- System admin privileges
- Manual environment setup

## For Distributors: Creating the Package

### Option 1: Automated Script (Recommended)

#### On Windows
```batch
create_package.bat
```

#### On Mac/Linux
```bash
chmod +x create_package.sh
bash create_package.sh
```

This creates:
- Windows: `medicheck-app.7z` or `medicheck-app.zip`
- Mac/Linux: `medicheck-app.tar.gz` or `medicheck-app.zip`

### Option 2: Manual Packaging

Use your preferred tool to create a ZIP or TAR archive containing these files:

**Required files:**
```
run.bat                    # Windows launcher
run.sh                     # Mac/Linux launcher
launch.py                  # Universal Python launcher

QUICKSTART.md              # User instructions
PACKAGE.md                 # Package documentation
requirements.txt           # Dependencies list

pharmacist_app/            # Application code
  └── app.py
  
data/                      # Data directory
  └── sample_prescriptions.json
  
.streamlit/                # Streamlit config
  └── config.toml
```

**Exclude from archive:**
- `venv/` - virtual environment (users create their own)
- `.git/` - version control
- `__pycache__/` - Python cache
- `*.pyc` - compiled Python
- `.pytest_cache/` - test cache
- `build/`, `dist/` - build artifacts
- `notebooks/` - development notebooks
- `tests/` - unit tests
- Any data files not needed for demo

### Option 3: GitHub Releases

1. Create a git tag:
   ```bash
   git tag -a v0.1.0 -m "MediCheck v0.1 Release"
   git push origin v0.1.0
   ```

2. Create a GitHub Release and attach the archive

3. Share the release link (e.g., `github.com/youruser/repo/releases/tag/v0.1.0`)

---

## For End Users: Installing & Running

**File:** `medicheck-app.zip` (or `.7z` or `.tar.gz`)

### On Windows

1. Right-click the ZIP file → "Extract All"
2. Open the extracted folder
3. Double-click `run.bat`
4. Wait 2-3 minutes on first launch (downloads dependencies)
5. Browser opens to `http://localhost:8501`

### On Mac/Linux

1. Extract: `unzip medicheck-app.zip` or `tar xzf medicheck-app.tar.gz`
2. Open Terminal in the extracted folder
3. Run: `bash run.sh`
4. Wait 2-3 minutes on first launch
5. Browser opens to `http://localhost:8501`

---

## What Happens After User Downloads

### First Launch

```
User extracts medicheck-app.zip
        ↓
User runs run.bat (Windows) or bash run.sh (Mac/Linux)
        ↓
Script checks: Is Python 3.10+ installed?
  ├─ NO → Error message with install link
  └─ YES → Continue
        ↓
Script creates: ./venv/ (virtual environment)
        ↓
Script runs: pip install -r requirements.txt
  (Downloads ~150MB of dependencies)
        ↓
Script launches: streamlit run pharmacist_app/app.py
        ↓
Browser opens to http://localhost:8501
```

### Subsequent Launches

```
Just 1-2 seconds startup time (everything already installed)
```

---

## Customization for Your Distribution

### 1. Update QUICKSTART.md
Add your organization's name and specific instructions:

```markdown
# [Your Organization] MediCheck Review App

Customized for [specific region/hospital/clinic]

...rest of content
```

### 2. Update Sample Data
Replace `data/sample_prescriptions.json` with:
- Your actual sample data (anonymized)
- Realistic examples from your use case

### 3. Brand the App
Modify `pharmacist_app/app.py` line 36-38:
```python
st.set_page_config(
    page_title="[Your Hospital] — Pharmacist Review",  # ← Update this
    page_icon="💊",
    layout="wide",
)
```

### 4. Add Organization Logo
Add an image to the sidebar:
```python
st.image("logo.png", width=200)
```

### 5. Create LICENSE
Add a `LICENSE` file with your terms:
```
MediCheck Pharmacist Review App
Copyright [Year] [Your Organization]

License terms...
```

---

## Distribution Checklist

Before sharing your package, verify:

- [ ] Archive contains all required files
- [ ] Archive size is reasonable (~30-50 MB)
- [ ] Tested extraction on Windows, Mac, and Linux
- [ ] Tested first launch on clean machine
- [ ] `QUICKSTART.md` is clear and accurate
- [ ] Sample data loads without errors
- [ ] App classifies and saves data correctly
- [ ] Download link is clearly accessible

---

## Verification Script

Before distributing, run this to verify the package:

```python
import zipfile
import os

required_files = [
    'run.bat',
    'run.sh', 
    'launch.py',
    'QUICKSTART.md',
    'requirements.txt',
    'pharmacist_app/app.py',
    'data/sample_prescriptions.json',
    '.streamlit/config.toml',
]

with zipfile.ZipFile('medicheck-app.zip', 'r') as z:
    archive_files = z.namelist()
    print(f"Archive contains {len(archive_files)} files")
    
    for required in required_files:
        if any(required in f for f in archive_files):
            print(f"✓ {required}")
        else:
            print(f"✗ MISSING: {required}")
```

---

## Hosting Options

### Option A: GitHub Releases (Free)
- Host on GitHub
- Automated distribution
- Version history
- User feedback through issues

### Option B: Direct Download Link
- Host on your website
- Create download button
- Share via email/QR-code

### Option C: Cloud Storage
- Google Drive
- Dropbox
- OneDrive
- Share link with password if needed

---

## Support Resources

Provide these with your distribution:

1. **QUICKSTART.md** - User guide (included)
2. **PACKAGE.md** - What's in the box (included)
3. **Troubleshooting** - Common issues
4. **Contact email** - For support questions

---

## Version Updates

To release version 0.2.0:

1. Update version in `pyproject.toml` and requirements
2. Update `QUICKSTART.md` with changes
3. Create new archive: `create_package.bat` or `create_package.sh`
4. Name it `medicheck-app-v0.2.0.zip` (include version)
5. Share release notes with archive

---

## Troubleshooting Distribution Issues

### Users report "Python not found"
- Add installation link to QUICKSTART.md
- Provide Windows installer link
- Add `python-installer.md` guide

### Users report port conflicts
- Document how to change port in `launch.py`
- Provide alternative: "Try port 8502, 8503, etc."

### First launch very slow
- Document that first launch downloads ~150MB
- Suggest waiting 2-3 minutes
- Explain it only happens once

### Users want to move the app
- Document that entire folder can be moved/copied
- `venv/` folder moves with it

---

**Version:** 0.1.0  
**Last Updated:** May 2026  
**Questions?** See QUICKSTART.md or PACKAGE.md
