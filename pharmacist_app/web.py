#!/usr/bin/env python3
"""
MediCheck Pharmacist Review — Standalone Web App
No pip install required. Uses only Python standard library.

Usage:
    python pharmacist_app/web.py
    python pharmacist_app/web.py --input data/raw/data.json --output outputs/ref.json --port 8501
"""

import argparse
import http.server
import json
import os
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# ── NCC MERP constants ─────────────────────────────────────────────────────────
ERROR_CATEGORIES = [
    "Prescribing Error",
    "Omission Error",
    "Wrong Time Error",
    "Unauthorized Drug Error",
    "Improper Dose/Quantity Error",
    "Wrong Dosage Form Error",
    "Wrong Drug Preparation Error",
    "Wrong Administration Technique Error",
    "Deteriorated Drug Error",
    "Monitoring Error",
    "Compliance Error",
    "Other",
]

SEVERITY = {
    "A": "A — Potential error only",
    "B": "B — Did not reach patient",
    "C": "C — Reached patient, no harm",
    "D": "D — Reached patient, monitoring required",
    "E": "E — Temporary harm, intervention required",
    "F": "F — Temporary harm, hospitalization",
    "G": "G — Permanent harm",
    "H": "H — Life-sustaining intervention required",
    "I": "I — Patient death",
}

# ── Global state ───────────────────────────────────────────────────────────────
STATE = {
    "cases": [],       # [{"id": str, "rows": [...], "drugs": [...]}]
    "results": {},     # order_id -> classification dict
    "output_path": "outputs/pharmacist_reference.json",
}


def group_data(data):
    """Group a list of records into cases by ID column."""
    groups, order = {}, []
    id_col = None
    for record in data:
        if id_col is None:
            for col in ("ID", "case_id", "order_id"):
                if col in record:
                    id_col = col
                    break
            if id_col is None:
                id_col = list(record.keys())[0]
        gid = str(record.get(id_col, "UNKNOWN")).strip()
        if gid not in groups:
            groups[gid] = []
            order.append(gid)
        groups[gid].append(record)

    cases = []
    for gid in order:
        rows = groups[gid]
        drugs, seen = [], set()
        for row in rows:
            for col in ("Drug", "drug_name", "drug", "Medication"):
                val = str(row.get(col, "")).strip()
                if val and val not in ("", "-", "None", "nan") and val not in seen:
                    seen.add(val)
                    drugs.append(val)
                    break
        cases.append({"id": gid, "rows": rows, "drugs": drugs})
    return cases


def load_cases(path):
    path = path.strip().strip('"').strip("'")  # strip accidental quotes
    with open(path, "r", encoding="utf-8") as f:
        return group_data(json.load(f))


def load_results(path):
    p = Path(path)
    if not p.exists():
        return {}
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {r["order_id"]: r for r in data if "order_id" in r}
    return data if isinstance(data, dict) else {}


def save_results(path, results):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(list(results.values()), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ── HTML page (single-file SPA) ────────────────────────────────────────────────
def build_html():
    cat_json = json.dumps(ERROR_CATEGORIES)
    sev_options = "\n".join(
        f'<option value="{k}">{v}</option>' for k, v in SEVERITY.items()
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MediCheck — Pharmacist Review</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#f0f3fa;color:#2c3a5c;height:100vh;display:flex;flex-direction:column;overflow:hidden}}

/* ── Top bar ── */
.topbar{{background:#fff;border-bottom:1px solid #dce3f0;padding:0 16px;display:flex;align-items:center;gap:12px;flex-shrink:0;height:44px;box-shadow:0 1px 4px rgba(80,100,160,.07)}}
.topbar-logo{{font-size:15px;font-weight:700;color:#5272c8;letter-spacing:-.3px}}
.topbar-sub{{font-size:11px;color:#a0aec8}}
.prog-wrap{{margin-left:auto;display:flex;align-items:center;gap:10px}}
.prog-bg{{width:130px;height:5px;background:#dce3f0;border-radius:3px}}
.prog-fill{{height:5px;background:#60b88a;border-radius:3px;transition:width .3s}}
.prog-txt{{font-size:11px;color:#8090b0}}

/* ── Workspace ── */
.workspace{{display:flex;flex:1;overflow:hidden}}

/* ── Sidebar ── */
.sidebar{{width:190px;background:#e8ecf5;border-right:1px solid #dce3f0;overflow-y:auto;flex-shrink:0;padding:10px 8px}}
.sb-hdr{{font-size:10px;color:#90a0bc;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;padding:0 4px}}
.ci{{display:flex;align-items:center;gap:6px;padding:5px 8px;border-radius:5px;cursor:pointer;font-size:12px;margin-bottom:1px;overflow:hidden;color:#3a4a6a}}
.ci:hover{{background:#d8e0f0}}
.ci.active{{background:#c8d8f8;color:#304898}}
.ci-label{{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}}
.dot{{width:6px;height:6px;border-radius:50%;flex-shrink:0}}
.dot-ok{{background:#60b88a}}
.dot-no{{background:#c8d0e0}}

/* ── Load screen ── */
.load-wrap{{max-width:440px;margin:50px auto;padding:20px;width:100%}}
.load-title{{font-size:19px;font-weight:700;color:#5272c8;margin-bottom:16px}}
.lcard{{background:#fff;border:1px solid #dce3f0;border-radius:10px;padding:22px;box-shadow:0 2px 8px rgba(80,100,160,.08)}}
.fg{{margin-bottom:13px}}
label.lbl{{display:block;font-size:11px;color:#7080a0;margin-bottom:6px;font-weight:600;text-transform:uppercase;letter-spacing:.4px}}
input[type=text]{{width:100%;padding:8px 10px;border-radius:6px;border:1px solid #dce3f0;background:#f8f9fd;color:#2c3a5c;font-size:13px}}
input[type=text]:focus{{outline:none;border-color:#7090d8;box-shadow:0 0 0 2px rgba(112,144,216,.15)}}
.err{{color:#c04040;font-size:11px;margin-top:6px}}

/* ── RX panel (left) ── */
.rx-panel{{flex:1;overflow-y:auto;padding:14px 16px;min-width:0;background:#f5f7fc}}

/* ── Form panel (right) ── */
.form-panel{{width:370px;flex-shrink:0;overflow-y:auto;padding:14px 16px;background:#eef1f9;border-left:1px solid #dce3f0}}

/* ── Case header ── */
.case-hdr{{display:flex;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap}}
.case-id{{font-size:17px;font-weight:700;color:#2c3a5c}}
.case-num{{font-size:11px;color:#90a0bc}}
.badge{{padding:2px 8px;border-radius:8px;font-size:11px;font-weight:600}}
.b-done{{background:#d8f0e4;color:#1e7048;border:1px solid #a8dcc0}}
.b-pend{{background:#e8ecf5;color:#7080a0;border:1px solid #c8d0e0}}

/* ── Rx section labels ── */
.rx-section{{margin-bottom:14px}}
.rx-section-title{{font-size:10px;font-weight:700;color:#90a0bc;text-transform:uppercase;letter-spacing:.8px;margin-bottom:6px;padding-left:2px}}

/* ── Patient info card ── */
.info-card{{background:#e8f0ff;border:1px solid #b8ccf0;border-radius:8px;padding:11px 14px;font-size:12px;color:#304070;line-height:1.65}}

/* ── Drug entry card ── */
.drug-entry{{background:#fff;border:1px solid #e8ddb8;border-left:4px solid #e0a030;border-radius:0 8px 8px 0;padding:10px 13px;margin-bottom:6px;box-shadow:0 1px 3px rgba(180,140,40,.07)}}
.drug-code-badge{{font-size:9px;color:#a8b0c0;margin-bottom:3px;font-family:monospace;letter-spacing:.3px}}
.drug-name-tag{{font-size:13px;font-weight:700;color:#9a5010;margin-bottom:4px}}
.drug-instructions{{font-size:11px;color:#607088;line-height:1.6;white-space:pre-wrap}}
.rx-fallback{{background:#f0f4ff;border:1px solid #d0d8f0;border-radius:7px;padding:9px 12px;margin-bottom:5px;font-size:12px;color:#8090b0}}

/* ── Clean table ── */
.rx-table-wrap{{background:#fff;border:1px solid #dce3f0;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(80,100,160,.06)}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{text-align:left;color:#8090b0;font-weight:600;padding:7px 10px;border-bottom:1px solid #dce3f0;font-size:10px;text-transform:uppercase;background:#f5f7fc}}
td{{padding:7px 10px;border-bottom:1px solid #eef1f8;vertical-align:top;color:#2c3a5c}}
tr:last-child td{{border-bottom:none}}
td.td-long{{font-size:11px;color:#6878a0;max-width:250px;word-break:break-word;line-height:1.4}}

/* ── Form elements ── */
.form-sect{{margin-bottom:14px}}
.sect-title{{font-size:10px;color:#8090b0;text-transform:uppercase;letter-spacing:.6px;margin-bottom:7px;font-weight:700}}
.radio-row{{display:flex;gap:6px}}
.ropt{{flex:1;display:flex;align-items:center;justify-content:center;gap:5px;cursor:pointer;padding:7px 8px;border-radius:6px;border:1px solid #dce3f0;background:#fff;font-size:11px;font-weight:600;transition:all .15s;user-select:none;text-align:center;line-height:1.3;color:#5a6a8a}}
.ropt.sel-yes{{border-color:#e09090;background:#fde8e8;color:#a03030}}
.ropt.sel-no{{border-color:#80c898;background:#e4f5ec;color:#1e6840}}
.allergy-grid{{display:grid;grid-template-columns:1fr 1fr;gap:5px;margin-bottom:6px}}
.aopt{{display:flex;flex-direction:column;align-items:center;cursor:pointer;padding:7px 5px;border-radius:6px;border:1px solid #dce3f0;background:#fff;font-size:10.5px;font-weight:600;transition:all .15s;user-select:none;text-align:center;line-height:1.3;color:#5a6a8a}}
.aopt.sel-nkda{{border-color:#80c898;background:#e4f5ec;color:#1e6840}}
.aopt.sel-present{{border-color:#e09090;background:#fde8e8;color:#a03030}}
.aopt.sel-unknown{{border-color:#e0c060;background:#fdf6e4;color:#7a5010}}
.aopt.sel-notrec{{border-color:#b0b8c8;background:#f0f2f6;color:#4a5a78}}
.allergy-input{{width:100%;box-sizing:border-box;padding:6px 9px;border-radius:6px;border:1px solid #e09090;background:#fff8f8;color:#2c3a5c;font-size:12px;font-family:inherit;line-height:1.5}}
.allergy-input:focus{{outline:none;border-color:#c06060}}
.allergy-row{{display:flex;align-items:flex-start;gap:8px;padding:7px 10px;border-radius:7px;margin-top:6px;margin-bottom:2px;font-size:11.5px;line-height:1.4}}
.allergy-nkda{{background:#e4f5ec;border:1px solid #80c898;color:#1e6840}}
.allergy-present{{background:#fde8e8;border:1px solid #e09090;color:#a03030}}
.allergy-unknown{{background:#fdf6e4;border:1px solid #e0c060;color:#7a5010}}
.allergy-notrec{{background:#f0f2f6;border:1px solid #b0b8c8;color:#4a5a78}}
.diag-section{{margin-top:8px;display:flex;flex-direction:column;gap:3px}}
.diag-item{{display:flex;justify-content:space-between;align-items:flex-start;padding:4px 9px;border-radius:5px;font-size:11.5px;gap:8px;line-height:1.4}}
.diag-primary{{background:#e8ecff;border-left:3px solid #6070d8;color:#2a3090}}
.diag-comorbid{{background:#f0f2f8;border-left:3px solid #a0a8c8;color:#4a5a78}}
.diag-operative{{background:#fdf6e8;border-left:3px solid #c0a060;color:#6a4010}}
.diag-role{{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;white-space:nowrap;opacity:.65;flex-shrink:0;margin-top:2px}}
.diag-more{{font-size:10px;color:#7090b0;padding:2px 6px;font-style:italic}}
.modal-overlay{{display:none;position:fixed;inset:0;background:rgba(44,58,92,.45);z-index:1000;align-items:center;justify-content:center}}
.modal-box{{background:#fff;border-radius:12px;padding:26px 24px 20px;max-width:360px;width:90%;box-shadow:0 8px 32px rgba(44,58,92,.18)}}
.modal-title{{font-size:14px;font-weight:700;color:#2c3a5c;margin-bottom:7px}}
.modal-body{{font-size:12px;color:#5a6a8a;margin-bottom:16px;line-height:1.5}}
.modal-actions{{display:flex;gap:7px;justify-content:flex-end;flex-wrap:wrap}}
.collapse-hdr{{cursor:pointer;display:flex;align-items:center;user-select:none;gap:4px}}
.collapse-hdr:hover{{color:#4060c0}}
.collapse-arrow{{font-size:9px;margin-left:auto;transition:transform .18s;color:#8090b0}}
.collapse-arrow.open{{transform:rotate(180deg)}}
.collapse-badge{{font-size:9px;font-weight:700;background:#dce8ff;color:#3050a0;border-radius:8px;padding:1px 7px;flex-shrink:0}}
.cat-list{{display:flex;flex-direction:column;gap:3px;margin-top:7px}}
.cat-item{{display:flex;align-items:center;gap:7px;cursor:pointer;padding:6px 9px;border-radius:5px;border:1px solid #dce3f0;background:#fff;font-size:11.5px;user-select:none;transition:background .1s,border-color .1s;color:#3a4a6a}}
.cat-item:hover{{background:#eef2ff}}
.cat-item.ck{{border-color:#90a8e8;background:#eef2ff;color:#304090}}
.cat-item.dis{{opacity:.35;pointer-events:none}}
.cat-item input{{accent-color:#7090d8;width:12px;height:12px;pointer-events:none;flex-shrink:0}}
.dchip-wrap{{display:flex;flex-wrap:wrap;gap:5px}}
.dchip{{padding:4px 10px;border-radius:10px;border:1px solid #dce3f0;background:#fff;font-size:11px;cursor:pointer;user-select:none;transition:all .15s;color:#7080a0}}
.dchip:hover{{background:#eef2ff;color:#304080}}
.dchip.ck{{border-color:#e0a030;background:#fff4d8;color:#8a5010}}
.dchip.dis{{opacity:.3;pointer-events:none}}
select{{width:100%;padding:7px 9px;border-radius:6px;border:1px solid #dce3f0;background:#fff;color:#2c3a5c;font-size:12px}}
select:disabled{{opacity:.4;background:#f0f3fa}}
select:focus{{outline:none;border-color:#7090d8}}
textarea{{width:100%;padding:7px 9px;border-radius:6px;border:1px solid #dce3f0;background:#fff;color:#2c3a5c;font-size:12px;resize:vertical;font-family:inherit;line-height:1.5}}
textarea:focus{{outline:none;border-color:#7090d8}}

/* ── Buttons ── */
.btn{{padding:7px 13px;border-radius:6px;border:none;cursor:pointer;font-size:12px;font-weight:600;transition:all .15s}}
.btn-p{{background:#6080d8;color:#fff}}
.btn-p:hover{{background:#4a68c8}}
.btn-s{{background:#fff;color:#5a6a8a;border:1px solid #dce3f0}}
.btn-s:hover{{background:#eef1f8}}
.btn:disabled{{opacity:.4;cursor:not-allowed}}
.nav{{display:flex;gap:5px;margin-top:8px}}
.nav .btn{{flex:1;font-size:11px;padding:7px 6px}}

/* ── Toast ── */
.toast{{position:fixed;bottom:14px;right:14px;background:#d8f0e4;color:#1e7048;border:1px solid #90d0b0;padding:7px 14px;border-radius:6px;font-size:12px;font-weight:600;opacity:0;transition:opacity .3s;pointer-events:none;z-index:999}}
.toast.show{{opacity:1}}

/* ── Patient info tags ── */
.ptag-wrap{{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:8px}}
.ptag{{display:inline-block;padding:3px 10px;border-radius:10px;font-size:11px;font-weight:600;border:1px solid transparent}}
.ptag-blue{{background:#dce8ff;color:#2050a0;border-color:#b0c8f0}}
.ptag-green{{background:#d8f5e8;color:#1a6040;border-color:#88ccaa}}
.ptag-amber{{background:#fff4d8;color:#8a5010;border-color:#e0c070}}
.ptag-red{{background:#ffe8e8;color:#a03030;border-color:#f0b0b0}}
.ptag-gray{{background:#e8ecf5;color:#4a5a7a;border-color:#c8d0e0}}
.info-raw{{font-size:11px;color:#5a7090;line-height:1.65;margin-top:6px;word-break:break-word}}

/* ── Vital signs ── */
.vitals-card{{background:#f0f8ff;border:1px solid #b8d4f0;border-radius:8px;padding:12px 13px;margin-top:6px}}
.vitals-row{{display:grid;gap:6px;margin-bottom:6px}}
.vitals-row:last-child{{margin-bottom:0}}
.v4{{grid-template-columns:repeat(4,1fr)}}
.v3{{grid-template-columns:repeat(3,1fr)}}
.vital-cell{{background:#fff;border:1px solid #d0e4f8;border-radius:6px;padding:7px 5px;text-align:center}}
.vital-cell.warn{{border-color:#f0c080;background:#fffbf0}}
.vital-cell.alrt{{border-color:#f09090;background:#fff0f0}}
.vital-lbl{{font-size:9px;color:#7090b0;text-transform:uppercase;letter-spacing:.5px;margin-bottom:3px}}
.vital-val{{font-size:15px;font-weight:700;color:#1a3a80;line-height:1}}
.vital-cell.warn .vital-val{{color:#a06010}}
.vital-cell.alrt .vital-val{{color:#c02020}}
.vital-unit{{font-size:9px;color:#90a8c0;margin-left:1px}}

::-webkit-scrollbar{{width:4px}}
::-webkit-scrollbar-thumb{{background:#c8d0e0;border-radius:2px}}
</style>
</head>
<body>

<div class="topbar">
  <span class="topbar-logo">&#128138; MediCheck</span>
  <span class="topbar-sub">Pharmacist Review</span>
  <div class="prog-wrap" id="topProg" style="display:none">
    <div class="prog-bg"><div class="prog-fill" id="pFill" style="width:0%"></div></div>
    <span class="prog-txt" id="pTxt"></span>
    <button class="btn btn-s" style="padding:4px 10px;font-size:11px;margin-left:4px" onclick="exportJSON()">&#8595; Export JSON</button>
    <button class="btn btn-s" style="padding:4px 10px;font-size:11px;margin-left:4px;border-color:#9090c8;color:#4050a0" onclick="openNewFile()">&#128196; New File</button>
  </div>
</div>

<div class="modal-overlay" id="confirmModal">
  <div class="modal-box">
    <div class="modal-title">&#9888;&#65039; Load New File?</div>
    <div class="modal-body">You have <b id="modalCount"></b> saved result(s).<br>Export first to avoid losing your review work.</div>
    <div class="modal-actions">
      <button class="btn btn-s" onclick="closeModal()">Cancel</button>
      <button class="btn btn-s" style="border-color:#6080d8;color:#4060c0" onclick="exportJSON();closeModal();resetToLoad()">Export &amp; Load New</button>
      <button class="btn btn-s" style="border-color:#e09090;color:#a03030" onclick="closeModal();resetToLoad()">Load Without Saving</button>
    </div>
  </div>
</div>

<div class="workspace">
  <!-- ── Sidebar ── -->
  <div class="sidebar">
    <div class="sb-hdr">Cases</div>
    <div id="caseList"></div>
  </div>

  <!-- ── Load screen ── -->
  <div id="loadScreen" style="flex:1;overflow-y:auto">
    <div class="load-wrap">
      <div class="load-title">Load Prescriptions</div>
      <div class="lcard">
        <div class="fg">
          <label class="lbl">Input JSON file</label>
          <div style="display:flex;gap:6px;align-items:center">
            <input type="text" id="inPath" placeholder="Type path or click Browse..." style="flex:1">
            <label for="filePick" class="btn btn-s" style="white-space:nowrap;flex-shrink:0;font-size:11px;padding:8px 11px;cursor:pointer;display:inline-block">Browse...</label>
            <input type="file" id="filePick" accept=".json" style="display:none">
          </div>
          <div id="fileStatus" style="font-size:11px;color:#4caf6e;margin-top:4px;display:none"></div>
          <div style="font-size:10px;color:#3d4460;margin-top:4px">หรือพิมพ์ path โดยตรง (ไม่ต้องใส่เครื่องหมายคำพูด)</div>
        </div>
        <div class="fg">
          <label class="lbl">Output path (where results save)</label>
          <input type="text" id="outPath" value="outputs/pharmacist_reference.json">
        </div>
        <button class="btn btn-p" style="width:100%;padding:10px;font-size:13px" onclick="loadFile()">Load File</button>
        <div class="err" id="loadErr"></div>
      </div>
    </div>
  </div>

  <!-- ── Rx panel (left, scrollable) ── -->
  <div class="rx-panel" id="rxPanel" style="display:none">
    <div class="case-hdr">
      <span class="case-num" id="cNum"></span>
      <span class="case-id" id="cId"></span>
      <span class="badge" id="cBadge"></span>
    </div>
    <div id="rxContent"></div>
  </div>

  <!-- ── Form panel (right, always visible) ── -->
  <div class="form-panel" id="formPanel" style="display:none">

    <div class="form-sect">
      <div class="sect-title">Medication Error?</div>
      <div class="radio-row">
        <div class="ropt" id="optY" onclick="setErr(true)">Yes<br><span style="font-size:10px;font-weight:400;opacity:.8">มีความคลาดเคลื่อน</span></div>
        <div class="ropt" id="optN" onclick="setErr(false)">No<br><span style="font-size:10px;font-weight:400;opacity:.8">ไม่มี</span></div>
      </div>
    </div>

    <div class="form-sect">
      <div class="sect-title collapse-hdr" onclick="toggleCats()">
        Error Categories — NCC MERP
        <span class="collapse-badge" id="catBadge" style="display:none"></span>
        <span class="collapse-arrow" id="catArrow">&#9660;</span>
      </div>
      <div class="cat-list" id="catGrid" style="display:none"></div>
    </div>

    <div class="form-sect">
      <div class="sect-title">Severity — NCC MERP</div>
      <select id="sev">{sev_options}</select>
    </div>

    <div class="form-sect">
      <div class="sect-title">Implicated Drugs <span style="font-weight:400;color:#3d4460">(tap to select)</span></div>
      <div class="dchip-wrap" id="drugChips"></div>
    </div>

    <div class="form-sect">
      <div class="sect-title">Drug Allergy History</div>
      <div class="allergy-grid">
        <div class="aopt" id="aoptNKDA"    onclick="setAllergy('nkda')">NKDA<br><span style="font-size:9px;font-weight:400">ไม่แพ้ยา</span></div>
        <div class="aopt" id="aoptPresent" onclick="setAllergy('present')">Has Allergy<br><span style="font-size:9px;font-weight:400">มีประวัติแพ้ยา</span></div>
        <div class="aopt" id="aoptUnknown" onclick="setAllergy('unknown')">Unknown<br><span style="font-size:9px;font-weight:400">ไม่ทราบ</span></div>
        <div class="aopt" id="aoptNotRec"  onclick="setAllergy('not_recorded')">Not Recorded<br><span style="font-size:9px;font-weight:400">ไม่มีข้อมูล</span></div>
      </div>
      <input type="text" id="allergyDrugs" class="allergy-input" placeholder="e.g. Penicillin, Sulfonamides, NSAIDs…" style="display:none">
    </div>

    <div class="form-sect">
      <div class="sect-title">Notes / Rationale</div>
      <textarea id="notes" rows="3" placeholder="บันทึกเหตุผลหรือข้อสังเกตของเภสัชกร..."></textarea>
    </div>

    <div class="nav">
      <button class="btn btn-s" id="bPrev" onclick="go(-1)">&#8592; Prev</button>
      <button class="btn btn-s" onclick="save(false)">Save</button>
      <button class="btn btn-p" onclick="save(true)">Save &amp; Next &#8594;</button>
      <button class="btn btn-s" id="bNext" onclick="go(1)">Skip &#8594;</button>
    </div>

  </div>
</div>

<div class="toast" id="toast"></div>

<script>
const CATS = {cat_json};
let cases = [], results = {{}}, idx = 0, hasErr = false;
let currentDrugs = [];
let allergyStatus = 'not_recorded';
let catOpen = false;

function toggleCats() {{
  catOpen = !catOpen;
  document.getElementById('catGrid').style.display = catOpen ? '' : 'none';
  document.getElementById('catArrow').className = 'collapse-arrow' + (catOpen ? ' open' : '');
  updateCatBadge();
}}

function setCatOpen(open) {{
  catOpen = open;
  document.getElementById('catGrid').style.display = open ? '' : 'none';
  document.getElementById('catArrow').className = 'collapse-arrow' + (open ? ' open' : '');
  updateCatBadge();
}}

function updateCatBadge() {{
  const n = document.querySelectorAll('#catGrid input:checked').length;
  const badge = document.getElementById('catBadge');
  if (n > 0) {{ badge.textContent = n + ' selected'; badge.style.display = ''; }}
  else {{ badge.style.display = 'none'; }}
}}
let fileReadPromise = null;  // resolves with file text content

const ALLERGY_IDS = {{nkda:'aoptNKDA', present:'aoptPresent', unknown:'aoptUnknown', not_recorded:'aoptNotRec'}};
const ALLERGY_CLS = {{nkda:'sel-nkda', present:'sel-present', unknown:'sel-unknown', not_recorded:'sel-notrec'}};

function setAllergy(status) {{
  allergyStatus = status;
  Object.keys(ALLERGY_IDS).forEach(s => {{
    const el = document.getElementById(ALLERGY_IDS[s]);
    if (el) el.className = 'aopt' + (s === status ? ' ' + ALLERGY_CLS[s] : '');
  }});
  const inp = document.getElementById('allergyDrugs');
  if (inp) inp.style.display = status === 'present' ? '' : 'none';
}}

// ── File picker ──────────────────────────────────────────────────────────────
document.getElementById('filePick').addEventListener('change', function() {{
  const file = this.files[0];
  if (!file) return;
  document.getElementById('inPath').value = file.name;
  document.getElementById('loadErr').textContent = '';
  const statusEl = document.getElementById('fileStatus');
  statusEl.textContent = 'File selected: ' + file.name + ' (' + Math.round(file.size/1024) + ' KB)';
  statusEl.style.display = '';
  // Wrap FileReader in a Promise so loadFile() can await it
  fileReadPromise = new Promise((resolve, reject) => {{
    const reader = new FileReader();
    reader.onload = e => resolve(e.target.result);
    reader.onerror = () => reject(new Error('Could not read file'));
    reader.readAsText(file, 'utf-8');
  }});
}});

// ── Load ─────────────────────────────────────────────────────────────────────
async function loadFile() {{
  const op = document.getElementById('outPath').value.trim();
  const errEl = document.getElementById('loadErr');
  const btn = document.querySelector('.lcard .btn-p');
  btn.textContent = 'Loading...'; btn.disabled = true;
  errEl.textContent = '';
  try {{
    let body;
    if (fileReadPromise) {{
      // Wait for FileReader to finish (handles race condition)
      const content = await fileReadPromise;
      body = JSON.stringify({{content: content, output: op}});
    }} else {{
      const ip = document.getElementById('inPath').value.trim().replace(/^['"]+|['"]+$/g, '');
      if (!ip) {{ errEl.textContent = 'Please select a file or enter a path.'; return; }}
      body = JSON.stringify({{input: ip, output: op}});
    }}
    const r = await fetch('/api/load', {{method: 'POST', headers: {{'Content-Type': 'application/json'}}, body}});
    const d = await r.json();
    if (!r.ok) {{ errEl.textContent = d.error || 'Server error'; return; }}
    if (!d.cases || d.cases.length === 0) {{ errEl.textContent = 'No cases found in file. Check JSON format (must be array of records).'; return; }}
    cases = d.cases;
    results = d.results;
    document.getElementById('loadScreen').style.display = 'none';
    document.getElementById('rxPanel').style.display = '';
    document.getElementById('formPanel').style.display = '';
    document.getElementById('topProg').style.display = 'flex';
    buildSidebar();
    const first = cases.findIndex(c => !results[c.id]);
    goTo(first >= 0 ? first : 0);
  }} catch (e) {{
    errEl.textContent = 'Error: ' + e.message;
  }} finally {{
    btn.textContent = 'Load File'; btn.disabled = false;
  }}
}}

// ── Sidebar ──────────────────────────────────────────────────────────────────
function buildSidebar() {{
  document.getElementById('caseList').innerHTML = cases.map((c, i) =>
    `<div class="ci" id="ci${{i}}" onclick="goTo(${{i}})" title="${{c.id}}">
      <div class="dot ${{results[c.id] ? 'dot-ok' : 'dot-no'}}"></div>
      <span class="ci-label">${{c.id.length > 17 ? c.id.slice(0, 16) + '…' : c.id}}</span>
    </div>`
  ).join('');
  updateProg();
}}

// ── Drug parsing from DETAIL text ────────────────────────────────────────────
function parseDrugs(text) {{
  if (!text) return [];
  const drugs = [], re = /(\\d{{10,}})\\s+([\\s\\S]+?)(?=\\s*\\d{{10,}}|\\s*Bed\\s+Details?|$)/g;
  let m;
  while ((m = re.exec(text)) !== null) {{
    const info = m[2].replace(/\\s+$/, '').trim();
    if (info) drugs.push({{code: m[1], info}});
  }}
  return drugs;
}}

function splitDrugInfo(info) {{
  // Split first segment (name) from rest (instructions)
  const parts = info.split(/  +|\\r?\\n/);
  const name = parts[0].trim().slice(0, 100);
  const rest = parts.slice(1).join('\\n').trim();
  return {{name, rest}};
}}

// ── Diagnosis parsing ────────────────────────────────────────────────────────
function parseDiagnoses(text) {{
  if (!text) return [];
  const EMOJI_RE = /[💉🌐✨🏷️⚠️]/g;
  const diagnoses = [], seen = new Set();

  // Find section: from after the last score counter to 🌐 (or end)
  const ctrAll = [];
  const ctrRe = /\\d+\\/\\d+/g;
  let ctrM;
  while ((ctrM = ctrRe.exec(text)) !== null) ctrAll.push(ctrM);
  const gStart = ctrAll.length ? ctrAll[ctrAll.length - 1].index + ctrAll[ctrAll.length - 1][0].length : 0;
  const gEnd   = text.indexOf('🌐');
  const section = (gEnd > gStart ? text.slice(gStart, gEnd) : text.slice(gStart))
                    .replace(EMOJI_RE, ' ').replace(/\\s+/g, ' ').trim();

  // Split by role keywords; capturing group keeps the role in the parts array
  const SPLIT_RE = /(Primary Diagnosis|Comorbidity|Pre-operative|Post-operative)/gi;
  const parts = section.split(SPLIT_RE);

  for (let i = 0; i + 1 < parts.length; i += 2) {{
    let name = parts[i].trim();
    const role = parts[i + 1].trim();
    if (!name || name.length < 3) continue;

    // Remove allergy context: take text after the last "[drug] Allergy [reaction]"
    if (/\\bAllergy\\b/i.test(name)) {{
      const lastAllergyPos = name.lastIndexOf(' Allergy ');
      if (lastAllergyPos === -1) continue;
      const after = name.slice(lastAllergyPos + 9); // 9 = length(' Allergy ')
      const capIdx = after.search(/[A-Z]/);
      if (capIdx === -1) continue;
      name = after.slice(capIdx).trim();
    }}

    // Strip leading punctuation/separators
    name = name.replace(/^[,;.\\- ]+/, '').replace(/[,;. ]+$/, '').trim();

    if (name.length > 3 && name.length < 200 && !seen.has(name)) {{
      seen.add(name);
      diagnoses.push({{ name, role }});
    }}
  }}
  return diagnoses;
}}

// ── Patient info tag parsing ─────────────────────────────────────────────────
// ── Allergy parsing ───────────────────────────────────────────────────────────
function parseAllergy(text) {{
  if (!text) return {{ status: 'not_recorded', drugs: [], label: '' }};

  // NKDA
  if (/No Known Drug Allerg/i.test(text)) {{
    return {{ status: 'nkda', drugs: [], label: 'No Known Drug Allergies' }};
  }}

  // Structured "[drug/allergen] Allergy" keyword (drug allergies)
  // Regex: (.{{2,60}}?) matches 2–60 chars lazily, followed by whitespace + "Allergy" word
  const EMOJI_RE = /[💉🌐✨🏷️⚠️]/g;
  const structured = [];
  const reA = /(.{{2,60}}?)\\s+Allergy\\b/gi;
  let m;
  while ((m = reA.exec(text)) !== null) {{
    const d = m[1].replace(EMOJI_RE, '').replace(/\\s+/g,' ').trim();
    if (d.length > 1 && !/Primary|Diagnos|Comorbidit|Pre-op|Post-op|Order\\s+Detail|e-Notes/i.test(d)
        && !structured.includes(d)) {{
      structured.push(d);
    }}
  }}
  if (structured.length > 0) {{
    return {{ status: 'present', drugs: structured, label: structured.join(', ') }};
  }}

  // Extract alert section: text after ⚠️ until counter (digits/digits) or 🌐 or end
  const alertM = text.match(/⚠️\\s*([\\s\\S]*?)(?=\\s*\\d+\\s*\\/\\s*\\d+|\\s*🌐|$)/);
  const alertRaw = alertM ? alertM[1].replace(EMOJI_RE,'').replace(/\\s+/g,' ').trim() : '';

  // Empty or only e-Notes → not recorded
  if (!alertRaw || /^e-Notes\\s*$/i.test(alertRaw)) {{
    return {{ status: 'not_recorded', drugs: [], label: '' }};
  }}

  // Food allergens / comma-separated list: split by comma, keep short items
  const parts = alertRaw.split(',').map(s => s.trim()).filter(s => {{
    if (!s || s.length > 50) return false;
    // reject if it looks like an English disease description (3+ lowercase words)
    if (/[A-Z][a-z]+ [a-z]+ [a-z]+/.test(s)) return false;
    return true;
  }});
  if (parts.length > 0) {{
    return {{ status: 'present', drugs: parts, label: parts.join(', ') }};
  }}

  // Fallback: raw alert text
  if (alertRaw) {{
    return {{ status: 'present', drugs: [], label: alertRaw.slice(0, 120) }};
  }}
  return {{ status: 'unknown', drugs: [], label: '' }};
}}

function parseSummaryTags(summary, rowtype) {{
  const tags = [];
  if (rowtype) {{
    const rt = rowtype.toLowerCase();
    if (rt.includes('daily'))   tags.push({{text:'Daily Order',      cls:'ptag-blue'}});
    else if (rt.includes('con')) tags.push({{text:'Continuous Order', cls:'ptag-blue'}});
    else if (rt.includes('dis')) tags.push({{text:'Discharge Meds',   cls:'ptag-amber'}});
    else                         tags.push({{text:rowtype,            cls:'ptag-gray'}});
  }}
  if (/InPatient/i.test(summary))       tags.push({{text:'InPatient',  cls:'ptag-green'}});
  else if (/OutPatient/i.test(summary)) tags.push({{text:'OutPatient', cls:'ptag-gray'}});
  const sm = summary.match(/\\b(Dispensed|Allocated|Ordered)\\b/i);
  if (sm) tags.push({{text:sm[1], cls:/Dispensed/i.test(sm[1])?'ptag-green':'ptag-amber'}});
  if (/\\bStat\\b/i.test(summary)) tags.push({{text:'STAT', cls:'ptag-red'}});
  return tags;
}}

// ── Vital signs parsing ───────────────────────────────────────────────────────
// [key, label, unit, warnLo, warnHi, alertLo, alertHi]
const VITALS_DEF = [
  ['WT',  'Weight', 'kg',   null, null, null, null ],
  ['HT',  'Height', 'cm',   null, null, null, null ],
  ['BMI', 'BMI',    '',     18.5, 24.9, 15,   35   ],
  ['BSA', 'BSA',    'm²', null, null, null, null ],
  ['T',   'Temp',   '°C', 36.0, 37.5, 35.0, 38.5],
  ['PR',  'Pulse',  '/min', 60,   100,  50,   130  ],
  ['RR',  'Resp',   '/min', 12,   20,   8,    30   ],
  ['SBP', 'SBP',    'mmHg', 90,   139,  80,   180  ],
  ['DBP', 'DBP',    'mmHg', 60,   89,   50,   110  ],
  ['MAP', 'MAP',    'mmHg', 70,   100,  60,   110  ],
  ['O2',  'SpO2',   '%',    95,   100,  90,   100  ],
];

function parseVitals(text) {{
  if (!text) return {{}};
  const result = {{}};
  const get = (re) => {{ const m = text.match(re); return m ? parseFloat(m[1]) : undefined; }};
  result.WT  = get(/\\bWT\\s*:\\s*([\\d.]+)/i);
  result.HT  = get(/\\bHT\\s*:\\s*([\\d.]+)/i);
  result.BMI = get(/\\bBMI\\s*:\\s*([\\d.]+)/i);
  result.BSA = get(/\\bBSA\\s*:\\s*([\\d.]+)/i);
  result.T   = get(/\\bT\\s*:\\s*([\\d.]+)/);
  result.PR  = get(/\\bPR\\s*:\\s*(\\d+)/);
  result.RR  = get(/\\bRR\\s*:\\s*(\\d+)/);
  result.SBP = get(/\\bSBP\\s*:\\s*(\\d+)/);
  result.DBP = get(/\\bDBP\\s*:\\s*(\\d+)/);
  result.MAP = get(/\\bMAP\\s*:\\s*(\\d+)/);
  result.O2  = get(/\\bO2\\s*:\\s*(\\d+)/);
  const eg = text.match(/\\beGFR\\s*:\\s*([^\\s,]+)/i);
  if (eg) result.eGFR = eg[1];
  Object.keys(result).forEach(k => {{ if (result[k] === undefined) delete result[k]; }});
  return result;
}}

function vitalCls(key, val) {{
  const n = parseFloat(val);
  if (isNaN(n)) return '';
  for (const [k,,, wL, wH, aL, aH] of VITALS_DEF) {{
    if (k !== key) continue;
    if ((aL !== null && n < aL) || (aH !== null && n > aH)) return 'alrt';
    if ((wL !== null && n < wL) || (wH !== null && n > wH)) return 'warn';
    return '';
  }}
  return '';
}}

function renderVitalsHtml(vitals) {{
  const present = (keys) => keys.filter(k => vitals[k] !== undefined);
  const rows = [
    [present(['WT','HT','BMI','BSA']), 'v4'],
    [present(['T','PR','RR','O2']),    'v4'],
    [present(['SBP','DBP','MAP']),     'v3'],
  ].filter(([keys]) => keys.length);
  if (!rows.length && !vitals.eGFR) return '';

  function cell(key) {{
    const def = VITALS_DEF.find(d => d[0] === key) || [key, key, ''];
    const [,label, unit] = def;
    const val = vitals[key];
    const cls = vitalCls(key, val);
    return `<div class="vital-cell ${{cls}}">
      <div class="vital-lbl">${{esc(label)}}</div>
      <div class="vital-val">${{esc(String(val))}}<span class="vital-unit">${{esc(unit)}}</span></div>
    </div>`;
  }}

  let h = '<div class="vitals-card">';
  for (const [keys, cls] of rows) {{
    h += `<div class="vitals-row ${{cls}}">${{keys.map(cell).join('')}}</div>`;
  }}
  if (vitals.eGFR !== undefined) {{
    h += `<div style="margin-top:6px;font-size:11px;color:#4a6a8a">eGFR : <strong>${{esc(String(vitals.eGFR))}}</strong></div>`;
  }}
  h += '</div>';
  return h;
}}

// ── Prescription renderer ────────────────────────────────────────────────────
function renderRx(c) {{
  if (!c.rows || !c.rows.length) {{
    document.getElementById('rxContent').innerHTML =
      '<div class="rx-fallback">No prescription data</div>';
    return;
  }}
  const cols = Object.keys(c.rows[0]);
  const upper = cols.map(k => k.toUpperCase());
  const hasScraped = upper.some(k => ['SUMMARY', 'DETAIL', 'ROWTYPE'].includes(k));
  hasScraped ? renderScraped(c, cols, upper) : renderTable(c, cols);
}}

function renderScraped(c, cols, upper) {{
  const colOf    = name => cols[upper.indexOf(name)] || null;
  const SUM_COL  = colOf('SUMMARY');
  const DET_COL  = colOf('DETAIL');
  const RT_COL   = colOf('ROWTYPE');

  let patientSummary = '', rowtypeVal = '', vitalsText = '', fullDetail = '';
  const drugCards = [];

  for (const row of c.rows) {{
    const summary = SUM_COL ? String(row[SUM_COL] || '').trim() : '';
    const detail  = DET_COL ? String(row[DET_COL] || '').trim() : '';
    const rowtype = RT_COL  ? String(row[RT_COL]  || '').trim() : '';

    if (summary)  patientSummary = summary;   // last non-empty wins
    if (rowtype)  rowtypeVal     = rowtype;
    if (detail)   fullDetail     = detail;

    const hasCodes = /\\d{{10,}}/.test(detail);
    if (hasCodes) {{
      // Extract vitals prefix (everything before first 10-digit code)
      const pfx = detail.match(/^([\\s\\S]*?)(?=\\d{{10,}})/);
      if (pfx && pfx[1].trim()) vitalsText = pfx[1].trim();
      // Parse drug entries
      const drugs = parseDrugs(detail);
      for (const d of drugs) {{
        const {{name, rest}} = splitDrugInfo(d.info);
        drugCards.push({{code: d.code, name, rest}});
      }}
      if (!drugs.length && detail) {{
        drugCards.push({{code:'', name: detail.slice(0,80), rest: detail.slice(80)}});
      }}
    }} else if (!summary && detail) {{
      patientSummary = detail;   // pure info row
    }}
  }}

  const vitals      = parseVitals(vitalsText);
  const tags        = parseSummaryTags(patientSummary, rowtypeVal);
  const allergyInfo = parseAllergy(fullDetail);
  const diagList    = parseDiagnoses(fullDetail);
  let html = '';

  // ── Section 1 : Patient / Order Info ─────────────────────────────────────
  html += '<div class="rx-section">';
  html += '<div class="rx-section-title">&#128100; Patient / Order Info</div>';
  html += '<div class="info-card">';
  if (tags.length) {{
    html += `<div class="ptag-wrap">${{tags.map(t=>`<span class="ptag ${{t.cls}}">${{esc(t.text)}}</span>`).join('')}}</div>`;
  }}
  if (patientSummary) {{
    html += `<div class="info-raw">${{esc(patientSummary)}}</div>`;
  }}
  // Allergy row
  const _aCls = {{nkda:'allergy-nkda', present:'allergy-present', unknown:'allergy-unknown', not_recorded:'allergy-notrec'}};
  const _aIco = {{nkda:'&#9989;', present:'&#9888;&#65039;', unknown:'&#10067;', not_recorded:'&#128203;'}};
  const _aLbl = {{nkda:'No Known Drug Allergies', unknown:'Allergy Unknown — not confirmed by patient', not_recorded:'Allergy Not Recorded'}};
  const _aCl  = _aCls[allergyInfo.status] || 'allergy-notrec';
  const _aIc  = _aIco[allergyInfo.status] || '&#128203;';
  let _aTxt;
  if (allergyInfo.status === 'present') {{
    _aTxt = '<b>Drug Allergy:</b> ' + esc(allergyInfo.label);
  }} else {{
    _aTxt = _aLbl[allergyInfo.status] || 'Allergy Not Recorded';
  }}
  html += `<div class="allergy-row ${{_aCl}}"><span style="flex-shrink:0">${{_aIc}}</span><span>${{_aTxt}}</span></div>`;

  // Diagnosis list
  if (diagList.length) {{
    const roleCls = (r) => /Primary/i.test(r) ? 'diag-primary' : /Comorbid/i.test(r) ? 'diag-comorbid' : 'diag-operative';
    const roleShort = (r) => /Primary/i.test(r) ? 'Primary Dx' : /Comorbid/i.test(r) ? 'Comorbidity' : r.replace(/-/g,' ');
    const MAX_SHOW = 5;
    const shown = diagList.slice(0, MAX_SHOW);
    const extra = diagList.length - MAX_SHOW;
    html += '<div class="diag-section">';
    for (const d of shown) {{
      html += `<div class="diag-item ${{roleCls(d.role)}}"><span>${{esc(d.name)}}</span><span class="diag-role">${{esc(roleShort(d.role))}}</span></div>`;
    }}
    if (extra > 0) {{
      html += `<div class="diag-more">+ ${{extra}} more diagnosis/comorbidity</div>`;
    }}
    html += '</div>';
  }}
  html += '</div></div>';

  // ── Section 2 : Vital Signs ───────────────────────────────────────────────
  const vitalsHtml = renderVitalsHtml(vitals);
  if (vitalsHtml) {{
    html += '<div class="rx-section">';
    html += '<div class="rx-section-title">&#129658; Vital Signs</div>';
    html += vitalsHtml;
    html += '</div>';
  }}

  // ── Section 3 : Medicines ─────────────────────────────────────────────────
  if (drugCards.length) {{
    html += `<div class="rx-section"><div class="rx-section-title">&#128138; Medicines (${{drugCards.length}} item${{drugCards.length!==1?'s':''}})</div>`;
    for (const d of drugCards) {{
      html += `<div class="drug-entry">
        ${{d.code ? `<div class="drug-code-badge"># ${{esc(d.code)}}</div>` : ''}}
        <div class="drug-name-tag">${{esc(d.name)}}</div>
        ${{d.rest ? `<div class="drug-instructions">${{esc(d.rest)}}</div>` : ''}}
      </div>`;
    }}
    html += '</div>';
  }}

  document.getElementById('rxContent').innerHTML = html ||
    '<div class="rx-fallback">No prescription entries found</div>';
}}

function renderTable(c, cols) {{
  const skip = new Set(['ID', 'case_id', 'order_id', 'id']);
  const show = cols.filter(k => !skip.has(k));
  const isLong = v => String(v).length > 45;
  let html = '<div class="rx-table-wrap"><table><thead><tr>' +
    show.map(k => `<th>${{esc(k)}}</th>`).join('') +
    '</tr></thead><tbody>';
  for (const row of c.rows) {{
    html += '<tr>' + show.map(k => {{
      const v = String(row[k] ?? '');
      return `<td class="${{isLong(v) ? 'td-long' : ''}}">${{esc(v)}}</td>`;
    }}).join('') + '</tr>';
  }}
  html += '</tbody></table></div>';
  document.getElementById('rxContent').innerHTML = html;
}}

// ── Extract drug chips from case ─────────────────────────────────────────────
function getCaseDrugs(c) {{
  // Priority 1: extracted from DETAIL 10-digit codes
  const cols = c.rows.length ? Object.keys(c.rows[0]) : [];
  const upper = cols.map(k => k.toUpperCase());
  const DETAIL = cols[upper.indexOf('DETAIL')] || null;
  if (DETAIL) {{
    const drugs = [], seen = new Set();
    for (const row of c.rows) {{
      for (const d of parseDrugs(String(row[DETAIL] || ''))) {{
        const name = splitDrugInfo(d.info).name;
        if (name && !seen.has(name)) {{ seen.add(name); drugs.push(name); }}
      }}
    }}
    if (drugs.length) return drugs;
  }}
  // Priority 2: explicit drug column
  return c.drugs || [];
}}

// ── Go to case ───────────────────────────────────────────────────────────────
function goTo(i) {{
  idx = i;
  const c = cases[i];

  // Sidebar
  document.querySelectorAll('.ci').forEach(el => el.classList.remove('active'));
  const el = document.getElementById('ci' + i);
  if (el) {{ el.classList.add('active'); el.scrollIntoView({{block: 'nearest'}}); }}

  // Header
  document.getElementById('cNum').textContent = `Case ${{i + 1}} / ${{cases.length}}`;
  document.getElementById('cId').textContent = c.id;
  const done = !!results[c.id];
  document.getElementById('cBadge').textContent = done ? '✓ Classified' : '○ Pending';
  document.getElementById('cBadge').className = 'badge ' + (done ? 'b-done' : 'b-pend');

  // Prescription
  renderRx(c);
  document.getElementById('rxPanel').scrollTop = 0;

  // Drug chips
  currentDrugs = getCaseDrugs(c);
  document.getElementById('drugChips').innerHTML = currentDrugs.map((d, j) =>
    `<div class="dchip dis" data-idx="${{j}}" onclick="toggleDrug(this)">${{esc(d)}}</div>`
  ).join('') || '<span style="font-size:11px;color:#3d4460">No drugs detected</span>';

  // Pre-fill or reset form
  const sv = results[c.id];
  if (sv) {{
    setErr(sv.has_medication_error);
    CATS.forEach(cat => {{
      const cb = document.querySelector(`#catGrid input[value="${{esc(cat)}}"]`);
      if (cb) {{ cb.checked = sv.error_categories.includes(cat); ckStyle(cb.parentElement); }}
    }});
    document.getElementById('sev').value = sv.ncc_merp_severity_category || 'C';
    currentDrugs.forEach((d, j) => {{
      const chip = document.querySelector(`#drugChips [data-idx="${{j}}"]`);
      if (chip) chip.classList.toggle('ck', sv.implicated_drugs.includes(d));
    }});
    document.getElementById('notes').value = sv.overall_recommendation || '';
    setAllergy(sv.drug_allergy_status || 'not_recorded');
    document.getElementById('allergyDrugs').value = (sv.drug_allergies || []).join(', ');
    // Open category panel if categories were saved; refresh badge
    const hasCats = sv.error_categories && sv.error_categories.length > 0;
    if (hasCats && !catOpen) setCatOpen(true);
    updateCatBadge();
  }} else {{
    setErr(false);
    document.querySelectorAll('#catGrid input').forEach(cb => {{ cb.checked = false; ckStyle(cb.parentElement); }});
    document.getElementById('sev').value = 'C';
    document.getElementById('notes').value = '';
    // Auto-populate allergy from parsed DETAIL text
    const _cols2 = c.rows.length ? Object.keys(c.rows[0]) : [];
    const _detKey = _cols2[_cols2.map(k => k.toUpperCase()).indexOf('DETAIL')] || null;
    let _detVal = '';
    if (_detKey) {{ for (const _r of c.rows) {{ const _d = String(_r[_detKey] || '').trim(); if (_d) {{ _detVal = _d; break; }} }} }}
    const _pa = parseAllergy(_detVal);
    setAllergy(_pa.status);
    document.getElementById('allergyDrugs').value = _pa.label || '';
  }}

  document.getElementById('bPrev').disabled = i === 0;
  document.getElementById('bNext').disabled = i >= cases.length - 1;
}}

// ── Form interactions ─────────────────────────────────────────────────────────
function setErr(v) {{
  hasErr = v;
  document.getElementById('optY').className = 'ropt' + (v ? ' sel-yes' : '');
  document.getElementById('optN').className = 'ropt' + (!v ? ' sel-no' : '');
  document.querySelectorAll('#catGrid .cat-item').forEach(el => el.classList.toggle('dis', !v));
  document.querySelectorAll('#catGrid input').forEach(cb => cb.disabled = !v);
  document.getElementById('sev').disabled = !v;
  document.querySelectorAll('#drugChips .dchip').forEach(el => el.classList.toggle('dis', !v));
  // Auto-open when Yes, auto-close when No
  if (v && !catOpen) setCatOpen(true);
  if (!v && catOpen) setCatOpen(false);
}}

function ckStyle(el) {{
  el.classList.toggle('ck', el.querySelector('input').checked);
  updateCatBadge();
}}

function toggleDrug(el) {{
  if (el.classList.contains('dis')) return;
  el.classList.toggle('ck');
}}

// ── Save ─────────────────────────────────────────────────────────────────────
async function save(advance) {{
  const c = cases[idx];
  const cats = [...document.querySelectorAll('#catGrid input:checked')].map(cb => cb.value);
  const drugs = [...document.querySelectorAll('#drugChips .dchip.ck')]
    .map(el => currentDrugs[parseInt(el.dataset.idx)]).filter(Boolean);
  const result = {{
    order_id: c.id,
    has_medication_error: hasErr,
    error_categories: hasErr ? cats : [],
    error_details: hasErr ? cats.map(cat => ({{
      category: cat,
      implicated_drugs: drugs,
      rationale: document.getElementById('notes').value
    }})) : [],
    implicated_drugs: hasErr ? drugs : [],
    ncc_merp_severity_category: hasErr ? document.getElementById('sev').value : 'A',
    overall_recommendation: document.getElementById('notes').value,
    drug_allergy_status: allergyStatus,
    drug_allergies: allergyStatus === 'present'
      ? document.getElementById('allergyDrugs').value.split(',').map(s => s.trim()).filter(Boolean)
      : [],
    reviewed_at: new Date().toISOString()
  }};
  const r = await fetch('/api/save', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify(result)
  }});
  if (r.ok) {{
    results[c.id] = result;
    buildSidebar();
    toast('Saved ✓');
    if (advance && idx + 1 < cases.length) goTo(idx + 1);
    else {{ document.getElementById('cBadge').textContent = '✓ Classified'; document.getElementById('cBadge').className = 'badge b-done'; }}
  }}
}}

function go(d) {{ goTo(idx + d); }}
function exportJSON() {{ window.location.href = '/api/export'; }}

function openNewFile() {{
  const n = Object.keys(results).length;
  if (n > 0) {{
    document.getElementById('modalCount').textContent = n;
    document.getElementById('confirmModal').style.display = 'flex';
  }} else {{
    resetToLoad();
  }}
}}

function closeModal() {{
  document.getElementById('confirmModal').style.display = 'none';
}}

function resetToLoad() {{
  cases = []; results = {{}}; idx = 0; hasErr = false;
  currentDrugs = []; allergyStatus = 'not_recorded'; fileReadPromise = null;
  document.getElementById('loadScreen').style.display = '';
  document.getElementById('rxPanel').style.display = 'none';
  document.getElementById('formPanel').style.display = 'none';
  document.getElementById('topProg').style.display = 'none';
  document.getElementById('caseList').innerHTML = '';
  document.getElementById('inPath').value = '';
  document.getElementById('fileStatus').style.display = 'none';
  document.getElementById('fileStatus').textContent = '';
  document.getElementById('loadErr').textContent = '';
  document.getElementById('filePick').value = '';
}}

function updateProg() {{
  const done = Object.keys(results).length, total = cases.length;
  document.getElementById('pFill').style.width = (total ? Math.round(done / total * 100) : 0) + '%';
  document.getElementById('pTxt').textContent = done + ' / ' + total;
}}

function toast(msg) {{
  const t = document.getElementById('toast');
  t.textContent = msg; t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2000);
}}

function esc(s) {{
  return String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}}

// Init category checkboxes
document.getElementById('catGrid').innerHTML = CATS.map(cat =>
  `<label class="cat-item dis">
    <input type="checkbox" value="${{esc(cat)}}" onchange="ckStyle(this.parentElement)">
    ${{esc(cat)}}
  </label>`
).join('');
</script>
</body>
</html>"""


# ── HTTP server ────────────────────────────────────────────────────────────────
class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, *args):
        pass  # suppress request logs

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length))

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/":
            self.send_html(build_html())

        elif path == "/api/export":
            data = json.dumps(
                list(STATE["results"].values()), ensure_ascii=False, indent=2
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="pharmacist_reference.json"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/api/load":
            try:
                body = self.read_body()
                output_path = body.get("output", "outputs/pharmacist_reference.json")
                if "content" in body:
                    cases = group_data(json.loads(body["content"]))
                else:
                    cases = load_cases(body.get("input", ""))
                results = load_results(output_path)
                STATE["cases"] = cases
                STATE["results"] = results
                STATE["output_path"] = output_path
                self.send_json({"cases": cases, "results": results})
            except FileNotFoundError as e:
                self.send_json({"error": f"File not found: {e}"}, status=400)
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)

        elif path == "/api/save":
            try:
                result = self.read_body()
                STATE["results"][result["order_id"]] = result
                save_results(STATE["output_path"], STATE["results"])
                self.send_json({"ok": True})
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)

        else:
            self.send_response(404)
            self.end_headers()


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="MediCheck Pharmacist Review")
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--input", default="")
    parser.add_argument("--output", default="outputs/pharmacist_reference.json")
    args = parser.parse_args()

    if args.input:
        STATE["output_path"] = args.output

    os.makedirs("outputs", exist_ok=True)
    os.makedirs("data/raw", exist_ok=True)

    server = http.server.HTTPServer(("localhost", args.port), Handler)
    url = f"http://localhost:{args.port}"
    print(f"\nMediCheck running at {url}")
    print("Press Ctrl+C to stop\n")

    threading.Thread(
        target=lambda: (
            __import__("time").sleep(0.8),
            webbrowser.open(url),
        ),
        daemon=True,
    ).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
