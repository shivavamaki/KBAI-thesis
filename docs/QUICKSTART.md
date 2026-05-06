# MediCheck Pharmacist Review App — Quick Start

A web-based application for pharmacist prescription error classification using NCC MERP categories.

## Download & Installation

### Prerequisites
- **Python 3.10 or higher** (free download from [python.org](https://www.python.org/downloads/))
- That's it! No additional installation required.

### Getting Started

#### On Windows
1. Extract the downloaded folder
2. Double-click `run.bat`
3. The app opens automatically in your browser at `http://localhost:8501`

#### On Mac or Linux
1. Extract the downloaded folder
2. Open Terminal and navigate to the folder:
   ```bash
   cd /path/to/MediCheck
   ```
3. Run the launcher:
   ```bash
   bash run.sh
   ```
   Or use Python directly:
   ```bash
   python3 launch.py
   ```
4. The app opens in your browser at `http://localhost:8501`

#### Alternative: Python Launcher (All Platforms)
If the batch/bash scripts don't work, you can always use Python:
```bash
python3 launch.py
```

---

## How to Use

### 1. Prepare Your Data
- Create a JSON file with prescription records (array format)
- Required fields: `ID`, `case_id`, or `order_id` (for grouping)
- Optional fields: `Drug`, `Dose`, `Frequency`, `Route`, `Duration`, `Status`

**Example JSON format:**
```json
[
  {
    "order_id": "RX001",
    "Drug": "Metformin",
    "Dose": "500mg",
    "Frequency": "BID",
    "Route": "Oral",
    "Duration": "30 days"
  },
  {
    "order_id": "RX002",
    "Drug": "Lisinopril",
    "Dose": "10mg",
    "Frequency": "OD",
    "Route": "Oral",
    "Duration": "90 days"
  }
]
```

### 2. Load Your Data
1. In the left sidebar, enter your input JSON file path
2. Enter the output JSON file path (where results will be saved)
3. Click **Load File**

### 3. Review & Classify
For each prescription:

- **Has Error?** → Select "Yes" or "No"
- **If Yes:**
  - Select error categories (NCC MERP)
  - Choose severity level (A-I)
  - Select implicated drugs
  - Add notes/rationale
- **If No:** Leave fields blank, click Save
- Click **Save & Next** to continue

### 4. Download Results
- Results auto-save after each classification
- Click **⬇ Download results (JSON)** in the sidebar
- Use in your analysis pipeline

---

## Features

✅ **NCC MERP Classification System**
- 12 error categories
- Severity levels A-I
- Implicated drug tracking

✅ **Progress Tracking**
- Visual progress bar
- Jump to specific cases
- Previous/Next navigation

✅ **Auto-Save**
- Results saved instantly
- Resume from where you left off
- JSON export ready

✅ **Bilingual Interface**
- English & Thai labels
- Support for Unicode text

✅ **No Installation Needed**
- Pure Python + Streamlit
- Works offline (after first setup)
- No admin privileges required

---

## Troubleshooting

### "Python not found"
- **Install Python** from https://www.python.org/downloads/
- **Windows:** Check "Add Python to PATH" during installation
- **Mac/Linux:** Install via `brew install python3` or `apt-get install python3`

### First run is slow
- The app downloads and installs dependencies (~2-3 minutes first time)
- Subsequent runs are instant

### Port 8501 already in use
- Streamlit will automatically try port 8502, 8503, etc.
- Or stop the other application using port 8501

### Data file not found
- Check that the file path is correct
- Use absolute paths if relative paths don't work
- Make sure the JSON file exists in the specified location

### Virtual environment issues (Windows)
If `run.bat` fails, try using Python directly:
```bash
python3 launch.py
```

---

## File Structure

```
MediCheck/
├── run.bat              ← Click to start on Windows
├── run.sh               ← Run in Terminal on Mac/Linux
├── launch.py            ← Alternative launcher for all platforms
├── requirements.txt     ← Python dependencies
├── pharmacist_app/
│   └── app.py          ← Main Streamlit application
├── data/
│   ├── raw/            ← Your input JSON files
│   ├── processed/      ← Processed data
│   └── samples/        ← Sample data for testing
└── outputs/            ← Where results are saved
```

---

## Requirements Version Targets
- Python 3.10+
- Streamlit 1.35.0+
- Pandas 2.2.0+
- OpenAI 1.0.0+
- Pydantic 2.0.0+

---

## Support

For issues or feature requests, please check:
1. The troubleshooting section above
2. Ensure Python 3.10+ is installed
3. Verify your JSON data format is correct
4. Try regenerating the virtual environment (delete `venv/` folder and rerun)

---

**Version:** 0.1.0  
**Last Updated:** May 2026
