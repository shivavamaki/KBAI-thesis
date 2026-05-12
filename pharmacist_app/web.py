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
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#0d0f18;color:#dde1f0;height:100vh;display:flex;flex-direction:column;overflow:hidden}}

/* ── Top bar ── */
.topbar{{background:#141720;border-bottom:1px solid #252a3d;padding:0 16px;display:flex;align-items:center;gap:12px;flex-shrink:0;height:44px}}
.topbar-logo{{font-size:15px;font-weight:700;color:#7c9cf8;letter-spacing:-.3px}}
.topbar-sub{{font-size:11px;color:#3d4460}}
.prog-wrap{{margin-left:auto;display:flex;align-items:center;gap:10px}}
.prog-bg{{width:130px;height:5px;background:#252a3d;border-radius:3px}}
.prog-fill{{height:5px;background:#4caf6e;border-radius:3px;transition:width .3s}}
.prog-txt{{font-size:11px;color:#7a8a9a}}

/* ── Workspace ── */
.workspace{{display:flex;flex:1;overflow:hidden}}

/* ── Sidebar ── */
.sidebar{{width:190px;background:#0f111a;border-right:1px solid #1e2235;overflow-y:auto;flex-shrink:0;padding:10px 8px}}
.sb-hdr{{font-size:10px;color:#3d4460;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;padding:0 4px}}
.ci{{display:flex;align-items:center;gap:6px;padding:5px 8px;border-radius:5px;cursor:pointer;font-size:12px;margin-bottom:1px;overflow:hidden}}
.ci:hover{{background:#1a1e2e}}
.ci.active{{background:#1a2d50;color:#82b4ff}}
.ci-label{{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}}
.dot{{width:6px;height:6px;border-radius:50%;flex-shrink:0}}
.dot-ok{{background:#4caf6e}}
.dot-no{{background:#2a2e40}}

/* ── Load screen ── */
.load-wrap{{max-width:440px;margin:50px auto;padding:20px;width:100%}}
.load-title{{font-size:19px;font-weight:700;color:#7c9cf8;margin-bottom:16px}}
.lcard{{background:#141720;border:1px solid #252a3d;border-radius:10px;padding:22px}}
.fg{{margin-bottom:13px}}
label.lbl{{display:block;font-size:11px;color:#8090a0;margin-bottom:6px;font-weight:600;text-transform:uppercase;letter-spacing:.4px}}
input[type=text]{{width:100%;padding:8px 10px;border-radius:6px;border:1px solid #252a3d;background:#0d0f18;color:#dde1f0;font-size:13px}}
input[type=text]:focus{{outline:none;border-color:#4c6ef5}}
.err{{color:#e05252;font-size:11px;margin-top:6px}}

/* ── RX panel (left) ── */
.rx-panel{{flex:1;overflow-y:auto;padding:14px 16px;min-width:0}}

/* ── Form panel (right) ── */
.form-panel{{width:370px;flex-shrink:0;overflow-y:auto;padding:14px 16px;background:#0f111a;border-left:1px solid #1e2235}}

/* ── Case header ── */
.case-hdr{{display:flex;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap}}
.case-id{{font-size:17px;font-weight:700;color:#fff}}
.case-num{{font-size:11px;color:#3d4460}}
.badge{{padding:2px 8px;border-radius:8px;font-size:11px;font-weight:600}}
.b-done{{background:#0e2d1c;color:#4caf6e;border:1px solid #1a4a2e}}
.b-pend{{background:#1e2030;color:#5a6070;border:1px solid #252a3d}}

/* ── Rx display — scraped cards ── */
.rx-section{{margin-bottom:8px}}
.info-card{{background:#141720;border:1px solid #252a3d;border-radius:7px;padding:10px 12px;margin-bottom:6px}}
.info-label{{font-size:10px;color:#3d4460;text-transform:uppercase;letter-spacing:.5px;margin-bottom:3px}}
.info-text{{font-size:12px;color:#a0b0c8;line-height:1.5}}
.drug-entry{{background:#161a28;border:1px solid #252a3d;border-left:3px solid #4c6ef5;border-radius:0 7px 7px 0;padding:9px 12px;margin-bottom:5px}}
.drug-code-badge{{font-size:9px;color:#3d4460;margin-bottom:3px;font-family:monospace}}
.drug-name-tag{{display:inline-block;background:#2d2600;color:#ffd766;font-size:12px;font-weight:700;padding:1px 7px;border-radius:3px;margin-bottom:5px;border:1px solid #5c4d00}}
.drug-instructions{{font-size:11px;color:#7a9ab8;line-height:1.55;white-space:pre-wrap}}
.rx-fallback{{background:#161a28;border:1px solid #252a3d;border-radius:7px;padding:9px 12px;margin-bottom:5px;font-size:12px;color:#8090a8}}

/* ── Rx display — clean table ── */
.rx-table-wrap{{background:#141720;border:1px solid #252a3d;border-radius:7px;overflow:hidden}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{text-align:left;color:#5a6a7a;font-weight:600;padding:7px 10px;border-bottom:1px solid #1e2235;font-size:10px;text-transform:uppercase;background:#0f111a}}
td{{padding:7px 10px;border-bottom:1px solid #1a1e2e;vertical-align:top}}
tr:last-child td{{border-bottom:none}}
td.td-long{{font-size:11px;color:#8090a8;max-width:250px;word-break:break-word;line-height:1.4}}

/* ── Form elements ── */
.form-sect{{margin-bottom:14px}}
.sect-title{{font-size:10px;color:#3d4460;text-transform:uppercase;letter-spacing:.6px;margin-bottom:7px;font-weight:700}}
.radio-row{{display:flex;gap:6px}}
.ropt{{flex:1;display:flex;align-items:center;justify-content:center;gap:5px;cursor:pointer;padding:7px 8px;border-radius:6px;border:1px solid #252a3d;background:#141720;font-size:11px;font-weight:600;transition:all .15s;user-select:none;text-align:center;line-height:1.3}}
.ropt.sel-yes{{border-color:#c04040;background:#270f0f;color:#ff8888}}
.ropt.sel-no{{border-color:#3a8a50;background:#0e2018;color:#60c878}}
.cat-list{{display:flex;flex-direction:column;gap:3px}}
.cat-item{{display:flex;align-items:center;gap:7px;cursor:pointer;padding:6px 9px;border-radius:5px;border:1px solid #1e2235;background:#141720;font-size:11.5px;user-select:none;transition:background .1s,border-color .1s}}
.cat-item:hover{{background:#1a1e2e}}
.cat-item.ck{{border-color:#4c6ef5;background:#141c38}}
.cat-item.dis{{opacity:.28;pointer-events:none}}
.cat-item input{{accent-color:#4c6ef5;width:12px;height:12px;pointer-events:none;flex-shrink:0}}
.dchip-wrap{{display:flex;flex-wrap:wrap;gap:5px}}
.dchip{{padding:4px 10px;border-radius:10px;border:1px solid #252a3d;background:#141720;font-size:11px;cursor:pointer;user-select:none;transition:all .15s;color:#8090a8}}
.dchip:hover{{background:#1a1e2e;color:#aab8cc}}
.dchip.ck{{border-color:#ffd766;background:#2d2400;color:#ffd766}}
.dchip.dis{{opacity:.25;pointer-events:none}}
select{{width:100%;padding:7px 9px;border-radius:6px;border:1px solid #252a3d;background:#141720;color:#dde1f0;font-size:12px}}
select:disabled{{opacity:.35}}
select:focus{{outline:none;border-color:#4c6ef5}}
textarea{{width:100%;padding:7px 9px;border-radius:6px;border:1px solid #252a3d;background:#141720;color:#dde1f0;font-size:12px;resize:vertical;font-family:inherit;line-height:1.5}}
textarea:focus{{outline:none;border-color:#4c6ef5}}

/* ── Buttons ── */
.btn{{padding:7px 13px;border-radius:6px;border:none;cursor:pointer;font-size:12px;font-weight:600;transition:all .15s}}
.btn-p{{background:#3b5bdb;color:#fff}}
.btn-p:hover{{background:#4c6ef5}}
.btn-s{{background:#1e2235;color:#aab;border:1px solid #252a3d}}
.btn-s:hover{{background:#252a3d}}
.btn:disabled{{opacity:.35;cursor:not-allowed}}
.nav{{display:flex;gap:5px;margin-top:8px}}
.nav .btn{{flex:1;font-size:11px;padding:7px 6px}}

/* ── Toast ── */
.toast{{position:fixed;bottom:14px;right:14px;background:#1a4a2e;color:#6fcf8a;border:1px solid #2a6a42;padding:7px 14px;border-radius:6px;font-size:12px;font-weight:600;opacity:0;transition:opacity .3s;pointer-events:none;z-index:999}}
.toast.show{{opacity:1}}

::-webkit-scrollbar{{width:4px}}
::-webkit-scrollbar-thumb{{background:#252a3d;border-radius:2px}}
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
            <button class="btn btn-s" onclick="document.getElementById('filePick').click()" style="white-space:nowrap;flex-shrink:0;font-size:11px;padding:8px 11px">Browse...</button>
            <input type="file" id="filePick" accept=".json" style="display:none" onchange="onFilePick(this)">
          </div>
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
let cases = [], results = {{}}, idx = 0, hasErr = false, pickedContent = null;
let currentDrugs = [];  // drug list for current case

// ── File picker ──────────────────────────────────────────────────────────────
function onFilePick(input) {{
  const file = input.files[0];
  if (!file) return;
  document.getElementById('inPath').value = file.name + ' (selected via Browse)';
  const reader = new FileReader();
  reader.onload = e => {{ pickedContent = e.target.result; }};
  reader.readAsText(file, 'utf-8');
}}

// ── Load ─────────────────────────────────────────────────────────────────────
async function loadFile() {{
  const op = document.getElementById('outPath').value.trim();
  document.getElementById('loadErr').textContent = 'Loading...';
  try {{
    let body;
    if (pickedContent) {{
      body = JSON.stringify({{content: pickedContent, output: op}});
    }} else {{
      const ip = document.getElementById('inPath').value.trim().replace(/^['"]+|['"]+$/g, '');
      if (!ip) {{ document.getElementById('loadErr').textContent = 'Please select a file or enter a path.'; return; }}
      body = JSON.stringify({{input: ip, output: op}});
    }}
    const r = await fetch('/api/load', {{method: 'POST', headers: {{'Content-Type': 'application/json'}}, body}});
    const d = await r.json();
    if (!r.ok) {{ document.getElementById('loadErr').textContent = d.error || 'Failed'; return; }}
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
    document.getElementById('loadErr').textContent = 'Error: ' + e.message;
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
  const drugs = [], re = /(\d{{10,}})\s+([\s\S]+?)(?=\s*\d{{10,}}|\s*Bed\s+Details?|$)/g;
  let m;
  while ((m = re.exec(text)) !== null) {{
    const info = m[2].replace(/\s+$/, '').trim();
    if (info) drugs.push({{code: m[1], info}});
  }}
  return drugs;
}}

function splitDrugInfo(info) {{
  // Split first segment (name) from rest (instructions)
  const parts = info.split(/  +|\r?\n/);
  const name = parts[0].trim().slice(0, 100);
  const rest = parts.slice(1).join('\n').trim();
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

  let html = '';
  for (const row of c.rows) {{
    const summary = SUMMARY ? String(row[SUMMARY] || '').trim() : '';
    const detail  = DETAIL  ? String(row[DETAIL]  || '').trim() : '';
    const hasCodes = /\d{{10,}}/.test(detail);

    if (!hasCodes) {{
      // Patient info / header row
      const text = summary || detail;
      if (text) {{
        html += `<div class="info-card">
          <div class="info-label">&#128100; Patient / Order Info</div>
          <div class="info-text">${{esc(text)}}</div>
        </div>`;
      }}
    }} else {{
      // Drug row: parse 10-digit codes
      const drugs = parseDrugs(detail);
      if (drugs.length) {{
        for (const d of drugs) {{
          const {{name, rest}} = splitDrugInfo(d.info);
          html += `<div class="drug-entry">
            <div class="drug-code-badge"># ${{esc(d.code)}}</div>
            <div class="drug-name-tag">${{esc(name)}}</div>
            ${{rest ? `<div class="drug-instructions">${{esc(rest)}}</div>` : ''}}
          </div>`;
        }}
      }} else {{
        // Fallback: show raw text
        const text = detail || summary;
        if (text) html += `<div class="rx-fallback">${{esc(text)}}</div>`;
      }}
    }}
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
