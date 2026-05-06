# MediCheck App — Organized Structure

Your app is now organized in a professional, clean directory structure. Here's what's where:

## 📁 Directory Structure

```
KBAI-thesis/
│
├── 🚀 ROOT LEVEL (For Users)
│   ├── run.bat                      ← Windows launcher (double-click)
│   ├── run.sh                       ← Mac/Linux launcher
│   ├── launch.py                    ← Universal Python launcher
│   ├── requirements.txt             ← Python dependencies
│   ├── README.md                    ← Original project README
│   └── pyproject.toml               ← Project config
│
├── 📖 docs/ (Documentation & Guides)
│   ├── README.md                    ← Overview & quick start
│   ├── QUICKSTART.md                ← User guide (how to use)
│   ├── PACKAGE.md                   ← What's included
│   └── DISTRIBUTION.md              ← How to distribute & customize
│
├── 🔧 tools/ (Utilities & Scripts)
│   ├── verify_app.py                ← Verify everything works
│   ├── test_package.bat             ← Test Windows package
│   ├── test_package.sh              ← Test Mac/Linux package
│   ├── create_package.bat           ← Create Windows ZIP
│   └── create_package.sh            ← Create Mac/Linux ZIP
│
├── 💾 pharmacist_app/ (The Application)
│   └── app.py                       ← Main Streamlit web app
│
├── 📁 data/ (Data Directory)
│   ├── sample_prescriptions.json    ← Demo data for testing
│   ├── raw/                         ← Input prescriptions go here
│   ├── processed/                   ← Processed data storage
│   └── samples/                     ← Sample datasets
│
├── 📤 outputs/ (Results)
│   └── [classification results saved here]
│
├── ⚙️ .streamlit/ (Configuration)
│   └── config.toml                  ← Streamlit settings
│
├── 📚 src/ (Original source code)
├── 🧪 tests/ (Original tests)
├── 📓 notebooks/ (Original notebooks)
├── database/ (Original database info)
└── prompts/ (Original prompts)
```

---

## 🎯 Who Uses What

### 👥 End Users
**Files they need:**
- `run.bat` (Windows) or `run.sh` (Mac/Linux)
- `requirements.txt` (auto-installed)
- `docs/QUICKSTART.md` (how-to guide)

**Getting started:**
```bash
bash run.sh                 # Mac/Linux
# or
python3 launch.py          # Any OS
```

### 👨‍💼 Organizers/Distributors
**Files to check/customize:**
- `pharmacist_app/app.py` — Brand the app
- `data/sample_prescriptions.json` — Add test data
- `docs/QUICKSTART.md` — Update instructions
- `docs/DISTRIBUTION.md` — Distribution guide

**Tools to use:**
```bash
python3 tools/verify_app.py         # Verify setup
bash tools/create_package.sh        # Create ZIP
bash tools/test_package.sh          # Test package
```

---

## ✅ Quick Reference

### Start the App
```bash
python3 launch.py
```

### Verify Everything Works
```bash
python3 tools/verify_app.py
```

### Create Distribution Package
```bash
bash tools/create_package.sh        # Mac/Linux
# or
tools\create_package.bat            # Windows
```

### Share with Users
1. Run: `bash tools/create_package.sh`
2. Share the `medicheck-app.zip` file
3. Users extract and run `run.bat` or `bash run.sh`

---

## 📚 Documentation Map

| Document | Purpose | Audience |
|----------|---------|----------|
| [docs/README.md](docs/README.md) | Overview & summary | Everyone |
| [docs/QUICKSTART.md](docs/QUICKSTART.md) | How to install & use | End users |
| [docs/PACKAGE.md](docs/PACKAGE.md) | What's included | Distributors |
| [docs/DISTRIBUTION.md](docs/DISTRIBUTION.md) | Customization & hosting | Organizers |

---

## 🛠️ Tools Reference

| Script | Purpose | Run with |
|--------|---------|----------|
| `tools/verify_app.py` | Pre-flight checks | `python3 tools/verify_app.py` |
| `tools/test_package.bat` | Test Windows package | Double-click or `cmd` |
| `tools/test_package.sh` | Test Mac/Linux package | `bash tools/test_package.sh` |
| `tools/create_package.bat` | Package for Windows | Double-click or `cmd` |
| `tools/create_package.sh` | Package for Mac/Linux | `bash tools/create_package.sh` |

---

## 🎁 For Distribution

When sharing with users, they only need:
- `run.bat` or `run.sh`
- `launch.py`
- `requirements.txt`
- `pharmacist_app/`
- `docs/QUICKSTART.md`
- `data/sample_prescriptions.json`
- `.streamlit/config.toml`

**Everything else (tools/, notebooks/, tests/, etc.) is excluded** when you run `create_package.sh`

---

## 📝 Next Steps

1. ✅ **Verify**: `python3 tools/verify_app.py`
2. ✅ **Test**: `bash tools/test_package.sh`
3. ✅ **Customize** (optional):
   - Edit `pharmacist_app/app.py` for branding
   - Update `docs/QUICKSTART.md` for your instructions
   - Replace `data/sample_prescriptions.json` with your data
4. ✅ **Create Package**: `bash tools/create_package.sh`
5. ✅ **Share**: Send `medicheck-app.zip` to users

---

## 📌 File Organization Benefits

✅ **Clean & Professional** — Everything in its place  
✅ **Easy to Maintain** — Utilities separate from app  
✅ **User-Friendly** — Launchers in root for easy access  
✅ **Well-Documented** — Comprehensive guides in `docs/`  
✅ **Script Organized** — All tools in `tools/` folder  
✅ **Distribution-Ready** — Packaging scripts automated  

---

**Status:** ✅ Fully Organized  
**Ready to:** Distribute or customize  
**Next:** Run `python3 tools/verify_app.py`

