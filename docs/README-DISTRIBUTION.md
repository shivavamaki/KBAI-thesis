# MediCheck Pharmacist App — Distribution Ready!

Your Pharmacist Review Web App is now ready for download and use without installers or EXE files.

## Quick Summary

✅ **No installer needed**  
✅ **No admin privileges required**  
✅ **Works on Windows, Mac, Linux**  
✅ **Users extract ZIP → Double-click launcher → Done!**  
✅ **All dependencies managed automatically**  

---

## Files You've Been Given

| File | Purpose |
|------|---------|
| **run.bat** | Windows launcher (double-click to start) |
| **run.sh** | Mac/Linux launcher (bash run.sh) |
| **launch.py** | Universal Python launcher (works everywhere) |
| **QUICKSTART.md** | ← **Read this first** — User guide with troubleshooting |
| **PACKAGE.md** | What's in the box, folder structure |
| **DISTRIBUTION.md** | How to brand and redistribute the app |
| requirements.txt | Python dependencies (auto-installed) |
| pharmacist_app/ | The actual Streamlit web application |
| data/ | Sample data and data directory |
| .streamlit/ | Streamlit configuration |

---

## For Your Users — Quick Start

### Windows
1. Extract the ZIP file
2. Double-click `run.bat`
3. Wait 2-3 minutes (first time only)
4. Browser opens automatically

### Mac/Linux
1. Extract the ZIP file
2. Open Terminal → Navigate to folder
3. Run: `bash run.sh` or `python3 launch.py`
4. Wait 2-3 minutes (first time only)
5. Browser opens automatically

**That's it!** Users don't need to know about Python, virtual environments, or pip.

---

## Creating a Download Package

### To Create a ZIP File for Distribution:

**On Windows:**
```batch
create_package.bat
```

**On Mac/Linux:**
```bash
bash create_package.sh
```

This creates: `medicheck-app.zip` (~30-50 MB)

Share this single file with users!

---

## Before Distributing — Verify Everything Works

Run the test script to check all files are present and valid:

**Windows:**
```batch
test_package.bat
```

**Mac/Linux:**
```bash
bash test_package.sh
```

You should see:
```
✓ All checks passed! Package is ready for distribution.
```

---

## What Happens When Users Launch

### First Launch (2-3 minutes)
```
User extracts medicheck-app.zip
     ↓
User runs run.bat (or bash run.sh)
     ↓
Script checks: Python 3.10+ installed?
     ↓
Script creates local environment: venv/
     ↓
Script downloads dependencies (~150 MB)
     ↓
Browser opens to http://localhost:8501
```

### Subsequent Launches (1-2 seconds)
Everything already installed, instant startup.

---

## Key Points for Distribution

### ✓ What Makes This Portable

- **No installer** — Just extract and run
- **No admin needed** — Everything in one folder
- **Bundled dependencies** — Auto-downloaded on first run
- **No system changes** — Entirely isolated folder
- **Easy uninstall** — Just delete the folder

### ✓ System Requirements

Users need:
- Python 3.10+ installed (free from python.org)
- 500 MB disk space
- 2 GB RAM minimum
- Any OS: Windows 7+, macOS 10.14+, Modern Linux

### ✓ First-Time Setup Includes

- Python virtual environment
- Streamlit web framework
- Pandas data processing
- OpenAI library
- All dependencies (auto-downloaded from pip)

**Total download:** ~150 MB (one time only)

---

## Customization Options

**Before creating your distribution package, you may want to:**

1. **Brand the App** — Change title in `pharmacist_app/app.py` line 36:
   ```python
   page_title="[Your Hospital] — Pharmacist Review",
   ```

2. **Update Sample Data** — Replace `data/sample_prescriptions.json` with your data

3. **Customize Instructions** — Edit `QUICKSTART.md` with your details

4. **Add License** — Include `LICENSE` file with terms

See `DISTRIBUTION.md` for detailed instructions.

---

## Hosting & Sharing

### Option 1: GitHub Releases (Easiest)
Create a GitHub release and attach `medicheck-app.zip`

### Option 2: Direct Download
Host on your website/server, share download link

### Option 3: Cloud Storage
Share via Google Drive, Dropbox, OneDrive with public link

### Option 4: Email
Attach ZIP directly to email (~30-50 MB)

---

## User Support Resources

Provide these with your distribution:

- **QUICKSTART.md** — How to use the app
- **PACKAGE.md** — What's included
- **Support email** — For help requests

Common issues are covered in QUICKSTART.md Troubleshooting section.

---

## What's Not Included

The distribution package excludes:
- `venv/` — Users create their own
- `notebooks/` — Development only
- `tests/` — Development only
- `.git/` — Version control
- Large raw data files
- Build artifacts

This keeps the package size small (~30-50 MB).

---

## Version Updates

To release version 0.2.0:

1. Update version number in files
2. Update QUICKSTART.md with changes
3. Run: `create_package.bat` or `create_package.sh`
4. Name it: `medicheck-app-v0.2.0.zip` (include version)
5. Update release notes

---

## Troubleshooting

**"Python not found"**
→ User needs to install Python from python.org

**"Port 8501 already in use"**
→ Streamlit automatically tries 8502, 8503, etc

**"First launch very slow"**
→ Normal (downloading dependencies). Only happens once.

**"I want to move the folder"**
→ Users can copy/move the entire folder anywhere. Venv moves with it.

See QUICKSTART.md for more troubleshooting.

---

## Next Steps

1. ✅ Review the files created
2. ✅ Test locally: `run.bat` or `bash run.sh`
3. ✅ Run verification: `test_package.bat` or `bash test_package.sh`
4. ✅ Customize (if needed) — see DISTRIBUTION.md
5. ✅ Create package: `create_package.bat` or `bash create_package.sh`
6. ✅ Share `medicheck-app.zip` with users

---

## Support

- **User Guide:** See QUICKSTART.md
- **Distribution Guide:** See DISTRIBUTION.md
- **Package Contents:** See PACKAGE.md

---

**Version:** 0.1.0  
**Status:** ✅ Ready for Distribution  
**Framework:** Streamlit  
**Python:** 3.10+  
**Last Updated:** May 2026
