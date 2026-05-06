# MediCheck Pharmacist Review App — Distribution Ready!

Your Pharmacist Review Web App is now ready for download and use without installers or EXE files.

## Quick Summary

✅ **No installer needed**  
✅ **No admin privileges required**  
✅ **Works on Windows, Mac, Linux**  
✅ **Users extract ZIP → Double-click launcher → Done!**  
✅ **All dependencies managed automatically**  

---

## Getting Started

### For End Users
1. Extract the downloaded ZIP file
2. Run `run.bat` (Windows) or `bash run.sh` (Mac/Linux)
3. Done! App opens in browser at `http://localhost:8501`

**See [QUICKSTART.md](QUICKSTART.md) for detailed instructions**

### For Organizers/Distributors
1. Customize app branding (edit `pharmacist_app/app.py`)
2. Add sample data (`data/sample_prescriptions.json`)
3. Run verification: `python3 tools/verify_app.py`
4. Create package: `bash tools/create_package.sh`
5. Share the ZIP file

**See [DISTRIBUTION.md](DISTRIBUTION.md) for detailed instructions**

---

## Files Overview

### Root Level (For Users)
- `run.bat` — Windows launcher
- `run.sh` — Mac/Linux launcher
- `launch.py` — Universal Python launcher
- `requirements.txt` — Python dependencies

### Documentation (This Folder)
- `QUICKSTART.md` — User guide
- `PACKAGE.md` — Package contents
- `DISTRIBUTION.md` — Distribution guide
- `README.md` — This file

### Tools (For Organizers)
- `tools/verify_app.py` — Verify everything works
- `tools/create_package.bat` — Create Windows package
- `tools/create_package.sh` — Create Mac/Linux package
- `tools/test_package.bat` — Test Windows package
- `tools/test_package.sh` — Test Mac/Linux package

### Application
- `pharmacist_app/app.py` — Main Streamlit app
- `.streamlit/config.toml` — Streamlit settings

### Data
- `data/sample_prescriptions.json` — Demo data
- `data/raw/` — Where user input files go
- `data/processed/` — Processed datasets
- `outputs/` — Where results are saved

---

## Quick Reference

| Task | Command |
|------|---------|
| **Run the app** | `python3 launch.py` or `bash run.sh` |
| **Verify setup** | `python3 tools/verify_app.py` |
| **Create package** | `bash tools/create_package.sh` |
| **Test package** | `bash tools/test_package.sh` |

---

## System Requirements

- **Python:** 3.10 or higher
- **OS:** Windows 7+, macOS 10.14+, Linux (Ubuntu 16.04+)
- **Disk:** ~500 MB
- **RAM:** 2 GB minimum

---

## Key Features

✅ NCC MERP classification system  
✅ Bilingual interface (English/Thai)  
✅ Auto-save classifications  
✅ Progress tracking  
✅ JSON import/export  
✅ Zero configuration needed  

---

## Support Resources

- **User questions:** See [QUICKSTART.md](QUICKSTART.md)
- **Distribution help:** See [DISTRIBUTION.md](DISTRIBUTION.md)
- **Package contents:** See [PACKAGE.md](PACKAGE.md)

---

**Version:** 0.1.0  
**Status:** ✅ Ready for Distribution  
**Last Updated:** May 2026
