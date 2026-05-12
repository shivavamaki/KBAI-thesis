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
.cat-list{{display:flex;flex-direction:column;gap:3px}}
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
      <div class="sect-title">Error Categories — NCC MERP</div>
      <div class="cat-list" id="catGrid"></div>
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
let fileReadPromise = null;  // resolves with file text content

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
  const colOf = name => cols[upper.indexOf(name)] || null;
  const SUMMARY = colOf('SUMMARY'), DETAIL = colOf('DETAIL');

  // Collect rows into two buckets
  const patientTexts = [], drugCards = [];

  for (const row of c.rows) {{
    const summary = SUMMARY ? String(row[SUMMARY] || '').trim() : '';
    const detail  = DETAIL  ? String(row[DETAIL]  || '').trim() : '';
    const hasCodes = /\\d{{10,}}/.test(detail);

    if (!hasCodes) {{
      const text = summary || detail;
      if (text) patientTexts.push(text);
    }} else {{
      const drugs = parseDrugs(detail);
      if (drugs.length) {{
        for (const d of drugs) {{
          const {{name, rest}} = splitDrugInfo(d.info);
          drugCards.push({{code: d.code, name, rest}});
        }}
      }} else {{
        const text = detail || summary;
        if (text) drugCards.push({{code: '', name: text.slice(0, 80), rest: text.slice(80)}});
      }}
    }}
  }}

  let html = '';

  // ── Section 1: Patient / order info ──────────────────────────────────────
  if (patientTexts.length) {{
    html += `<div class="rx-section">
      <div class="rx-section-title">&#128100; Patient / Order Info</div>
      <div class="info-card">${{patientTexts.map(t => esc(t)).join('<br>')}}</div>
    </div>`;
  }}

  // ── Section 2: Medicines ──────────────────────────────────────────────────
  if (drugCards.length) {{
    html += `<div class="rx-section">
      <div class="rx-section-title">&#128138; Medicines (${{drugCards.length}} item${{drugCards.length !== 1 ? 's' : ''}})</div>`;
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
  }} else {{
    setErr(false);
    document.querySelectorAll('#catGrid input').forEach(cb => {{ cb.checked = false; ckStyle(cb.parentElement); }});
    document.getElementById('sev').value = 'C';
    document.getElementById('notes').value = '';
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
}}

function ckStyle(el) {{ el.classList.toggle('ck', el.querySelector('input').checked); }}

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
