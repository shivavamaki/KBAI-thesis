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


def load_cases(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
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
        drugs = []
        seen = set()
        for row in rows:
            for col in ("Drug", "drug_name", "drug", "Medication"):
                val = str(row.get(col, "")).strip()
                if val and val not in ("", "-", "None", "nan") and val not in seen:
                    seen.add(val)
                    drugs.append(val)
                    break
        cases.append({"id": gid, "rows": rows, "drugs": drugs})
    return cases


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
body{{font-family:'Segoe UI',sans-serif;background:#0f1117;color:#e0e0e0;height:100vh;display:flex;flex-direction:column}}
.topbar{{background:#1a1d27;border-bottom:1px solid #2d3148;padding:10px 20px;display:flex;align-items:center;gap:12px;flex-shrink:0}}
.topbar h1{{font-size:17px;color:#7c9cf8}}
.prog-wrap{{margin-left:auto;display:flex;align-items:center;gap:10px}}
.prog-bg{{width:160px;height:7px;background:#2d3148;border-radius:4px}}
.prog-fill{{height:7px;background:#4caf50;border-radius:4px;transition:width .3s}}
.prog-txt{{font-size:13px;color:#9aa}}
.layout{{display:flex;flex:1;overflow:hidden}}
.sidebar{{width:220px;background:#13151e;border-right:1px solid #2d3148;overflow-y:auto;padding:10px;flex-shrink:0}}
.sb-title{{font-size:11px;color:#556;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px}}
.ci{{display:flex;align-items:center;gap:7px;padding:6px 8px;border-radius:6px;cursor:pointer;font-size:12px;margin-bottom:1px;white-space:nowrap;overflow:hidden}}
.ci:hover{{background:#1e2235}}
.ci.active{{background:#1e3a5f;color:#7cb8ff}}
.dot{{width:7px;height:7px;border-radius:50%;flex-shrink:0}}
.dot-ok{{background:#4caf50}}
.dot-no{{background:#3a3a3a}}
.content{{flex:1;overflow-y:auto;padding:22px}}
.card{{background:#1a1d27;border:1px solid #2d3148;border-radius:10px;padding:18px;margin-bottom:14px}}
.card-title{{font-size:12px;font-weight:600;color:#7c9cf8;text-transform:uppercase;letter-spacing:.5px;margin-bottom:12px}}
.case-hdr{{display:flex;align-items:baseline;gap:14px;margin-bottom:14px}}
.case-id{{font-size:20px;font-weight:700;color:#fff}}
.case-num{{font-size:13px;color:#667}}
.badge{{padding:3px 10px;border-radius:10px;font-size:12px;font-weight:600}}
.b-done{{background:#1a3d2b;color:#4caf50}}
.b-pend{{background:#252520;color:#888}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{text-align:left;color:#778;font-weight:500;padding:7px 10px;border-bottom:1px solid #2d3148;font-size:11px;text-transform:uppercase}}
td{{padding:9px 10px;border-bottom:1px solid #1e2133}}
tr:last-child td{{border-bottom:none}}
tr:hover td{{background:#1e2235}}
.row2{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.fg{{margin-bottom:14px}}
label.lbl{{display:block;font-size:12px;color:#9ab;margin-bottom:7px;font-weight:500}}
.radio-row{{display:flex;gap:10px}}
.ropt{{display:flex;align-items:center;gap:8px;cursor:pointer;padding:9px 14px;border-radius:8px;border:1px solid #2d3148;background:#13151e;font-size:13px;transition:all .15s;user-select:none}}
.ropt.sel-yes{{border-color:#e05252;background:#2d1a1a}}
.ropt.sel-no{{border-color:#4caf50;background:#1a2d1e}}
.cbgrid{{display:grid;grid-template-columns:1fr 1fr;gap:6px}}
.cbi{{display:flex;align-items:center;gap:7px;cursor:pointer;padding:7px 9px;border-radius:6px;border:1px solid #2d3148;background:#13151e;font-size:12px;user-select:none;transition:all .15s}}
.cbi:hover{{background:#1e2235}}
.cbi.ck{{border-color:#7c9cf8;background:#1a1e35}}
.cbi.dis{{opacity:.35;pointer-events:none}}
.cbi input{{accent-color:#7c9cf8;width:13px;height:13px;pointer-events:none}}
select{{width:100%;padding:9px 10px;border-radius:7px;border:1px solid #2d3148;background:#13151e;color:#e0e0e0;font-size:13px}}
select:disabled{{opacity:.4}}
textarea{{width:100%;padding:9px 10px;border-radius:7px;border:1px solid #2d3148;background:#13151e;color:#e0e0e0;font-size:13px;resize:vertical;font-family:inherit}}
textarea:focus{{outline:none;border-color:#7c9cf8}}
input[type=text]{{width:100%;padding:9px 10px;border-radius:7px;border:1px solid #2d3148;background:#13151e;color:#e0e0e0;font-size:13px}}
input[type=text]:focus{{outline:none;border-color:#7c9cf8}}
.btn{{padding:9px 18px;border-radius:7px;border:none;cursor:pointer;font-size:13px;font-weight:600;transition:all .15s}}
.btn-p{{background:#3b5bdb;color:#fff}}
.btn-p:hover{{background:#4c6ef5}}
.btn-s{{background:#2d3148;color:#ccc}}
.btn-s:hover{{background:#363a57}}
.btn:disabled{{opacity:.4;cursor:not-allowed}}
.nav{{display:flex;gap:8px;margin-top:6px}}
.nav .btn{{flex:1}}
.toast{{position:fixed;bottom:22px;right:22px;background:#2b7a44;color:#fff;padding:10px 18px;border-radius:7px;font-size:13px;font-weight:600;opacity:0;transition:opacity .3s;pointer-events:none;z-index:999}}
.toast.show{{opacity:1}}
.load-wrap{{max-width:460px;margin:60px auto}}
.load-wrap h2{{color:#7c9cf8;margin-bottom:20px;font-size:20px}}
.err{{color:#e05252;font-size:12px;margin-top:8px}}
::-webkit-scrollbar{{width:5px}}
::-webkit-scrollbar-thumb{{background:#2d3148;border-radius:3px}}
</style>
</head>
<body>
<div class="topbar">
  <h1>&#128138; MediCheck</h1>
  <span style="color:#556;font-size:12px">Pharmacist Review</span>
  <div class="prog-wrap" id="topProg" style="display:none">
    <div class="prog-bg"><div class="prog-fill" id="pFill" style="width:0%"></div></div>
    <span class="prog-txt" id="pTxt"></span>
    <button class="btn btn-s" style="padding:5px 12px;font-size:12px" onclick="exportJSON()">Export JSON</button>
  </div>
</div>
<div class="layout">
  <div class="sidebar">
    <div class="sb-title">Cases</div>
    <div id="caseList"></div>
  </div>
  <div class="content">

    <div class="load-wrap" id="loadScreen">
      <h2>Load Prescriptions</h2>
      <div class="card">
        <div class="fg"><label class="lbl">Input JSON file path</label>
          <input type="text" id="inPath" value="data/raw/RT_COMMON_904_test_clean_blinded_first_sheet.json">
        </div>
        <div class="fg"><label class="lbl">Output JSON file path</label>
          <input type="text" id="outPath" value="outputs/pharmacist_reference.json">
        </div>
        <button class="btn btn-p" style="width:100%" onclick="loadFile()">Load File</button>
        <div class="err" id="loadErr"></div>
      </div>
    </div>

    <div id="reviewScreen" style="display:none">
      <div class="case-hdr">
        <div class="case-num" id="cNum"></div>
        <div class="case-id" id="cId"></div>
        <span class="badge" id="cBadge"></span>
      </div>

      <div class="card">
        <div class="card-title">Prescription Details</div>
        <table><thead id="rxH"></thead><tbody id="rxB"></tbody></table>
      </div>

      <div class="card">
        <div class="card-title">Classification</div>
        <div class="fg">
          <label class="lbl">&#3617;&#3637;&#3588;&#3623;&#3634;&#3617;&#3588;&#3621;&#3634;&#3604;&#3648;&#3588;&#3621;&#3639;&#3657;&#3629;&#3609;&#3607;&#3634;&#3591;&#3618;&#3634;&#3627;&#3619;&#3639;&#3629;&#3652;&#3617;&#3656;? / Medication error present?</label>
          <div class="radio-row">
            <div class="ropt" id="optY" onclick="setErr(true)">Yes &#8212; &#3617;&#3637;&#3588;&#3623;&#3634;&#3617;&#3588;&#3621;&#3634;&#3604;&#3648;&#3588;&#3621;&#3639;&#3657;&#3629;&#3609;</div>
            <div class="ropt" id="optN" onclick="setErr(false)">No &#8212; &#3652;&#3617;&#3656;&#3617;&#3637;&#3588;&#3623;&#3634;&#3617;&#3588;&#3621;&#3634;&#3604;&#3648;&#3588;&#3621;&#3639;&#3657;&#3629;&#3609;</div>
          </div>
        </div>
        <div class="row2">
          <div class="fg">
            <label class="lbl">Error categories &#8212; NCC MERP</label>
            <div class="cbgrid" id="catGrid"></div>
          </div>
          <div>
            <div class="fg">
              <label class="lbl">NCC MERP Severity</label>
              <select id="sev">{sev_options}</select>
            </div>
            <div class="fg">
              <label class="lbl">Implicated drugs</label>
              <div class="cbgrid" id="drugGrid"></div>
            </div>
          </div>
        </div>
        <div class="fg">
          <label class="lbl">Notes / Rationale</label>
          <textarea id="notes" rows="3" placeholder="&#3610;&#3633;&#3609;&#3607;&#3638;&#3585;&#3648;&#3627;&#3605;&#3640;&#3612;&#3621;&#3627;&#3619;&#3639;&#3629;&#3586;&#3657;&#3629;&#3626;&#3633;&#3591;&#3648;&#3585;&#3605;&#3586;&#3629;&#3591;&#3648;&#3616;&#3626;&#3633;&#3594;&#3585;&#3619;..."></textarea>
        </div>
        <div class="nav">
          <button class="btn btn-s" id="bPrev" onclick="go(-1)">&#8592; Prev</button>
          <button class="btn btn-s" onclick="save(false)">Save</button>
          <button class="btn btn-p" onclick="save(true)">Save &amp; Next &#8594;</button>
          <button class="btn btn-s" id="bNext" onclick="go(1)">Skip &#8594;</button>
        </div>
      </div>
    </div>

  </div>
</div>
<div class="toast" id="toast"></div>
<script>
const CATS={cat_json};
let cases=[],results={{}},idx=0,hasErr=false;

async function loadFile(){{
  const ip=document.getElementById('inPath').value.trim();
  const op=document.getElementById('outPath').value.trim();
  document.getElementById('loadErr').textContent='';
  try{{
    const r=await fetch('/api/load',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{input:ip,output:op}})}});
    const d=await r.json();
    if(!r.ok){{document.getElementById('loadErr').textContent=d.error||'Failed';return;}}
    cases=d.cases; results=d.results;
    document.getElementById('loadScreen').style.display='none';
    document.getElementById('reviewScreen').style.display='';
    document.getElementById('topProg').style.display='flex';
    buildSidebar();
    const first=cases.findIndex(c=>!results[c.id]);
    goTo(first>=0?first:0);
  }}catch(e){{document.getElementById('loadErr').textContent='Error: '+e.message;}}
}}

function buildSidebar(){{
  document.getElementById('caseList').innerHTML=cases.map((c,i)=>
    `<div class="ci ${{results[c.id]?'':''}}" id="ci${{i}}" onclick="goTo(${{i}})" title="${{c.id}}">
      <div class="dot ${{results[c.id]?'dot-ok':'dot-no'}}"></div>
      <span>${{c.id.length>16?c.id.slice(0,16)+'...':c.id}}</span></div>`
  ).join('');
  updateProg();
}}

function goTo(i){{
  idx=i;
  const c=cases[i];
  document.querySelectorAll('.ci').forEach(el=>el.classList.remove('active'));
  const el=document.getElementById('ci'+i);
  if(el){{el.classList.add('active');el.scrollIntoView({{block:'nearest'}});}}
  document.getElementById('cNum').textContent=`Case ${{i+1}} of ${{cases.length}}`;
  document.getElementById('cId').textContent=c.id;
  const done=!!results[c.id];
  document.getElementById('cBadge').textContent=done?'✓ Classified':'○ Pending';
  document.getElementById('cBadge').className='badge '+(done?'b-done':'b-pend');
  // Table
  const cols=c.rows.length?Object.keys(c.rows[0]).filter(k=>!['ID','case_id','order_id'].includes(k)):[];
  document.getElementById('rxH').innerHTML='<tr>'+cols.map(k=>`<th>${{k}}</th>`).join('')+'</tr>';
  document.getElementById('rxB').innerHTML=c.rows.map(r=>'<tr>'+cols.map(k=>`<td>${{esc(r[k]??'')}}</td>`).join('')+'</tr>').join('');
  // Drug checkboxes
  document.getElementById('drugGrid').innerHTML=c.drugs.map(d=>
    `<label class="cbi"><input type="checkbox" value="${{esc(d)}}" onchange="ckStyle(this.parentElement)"> ${{esc(d)}}</label>`
  ).join('');
  // Pre-fill
  const sv=results[c.id];
  if(sv){{
    setErr(sv.has_medication_error);
    CATS.forEach(cat=>{{const cb=document.querySelector(`#catGrid input[value="${{cat}}"]`);if(cb){{cb.checked=sv.error_categories.includes(cat);ckStyle(cb.parentElement);}}}});
    document.getElementById('sev').value=sv.ncc_merp_severity_category||'C';
    c.drugs.forEach(d=>{{const cb=document.querySelector(`#drugGrid input[value="${{d}}"]`);if(cb){{cb.checked=sv.implicated_drugs.includes(d);ckStyle(cb.parentElement);}}}});
    document.getElementById('notes').value=sv.overall_recommendation||'';
  }}else{{
    setErr(false);
    document.querySelectorAll('#catGrid input,#drugGrid input').forEach(cb=>{{cb.checked=false;ckStyle(cb.parentElement);}});
    document.getElementById('sev').value='C';
    document.getElementById('notes').value='';
  }}
  document.getElementById('bPrev').disabled=i===0;
  document.getElementById('bNext').disabled=i>=cases.length-1;
}}

function setErr(v){{
  hasErr=v;
  document.getElementById('optY').className='ropt'+(v?' sel-yes':'');
  document.getElementById('optN').className='ropt'+(!v?' sel-no':'');
  document.querySelectorAll('#catGrid .cbi,#drugGrid .cbi').forEach(el=>el.classList.toggle('dis',!v));
  document.querySelectorAll('#catGrid input,#drugGrid input').forEach(cb=>cb.disabled=!v);
  document.getElementById('sev').disabled=!v;
}}

function ckStyle(el){{el.classList.toggle('ck',el.querySelector('input').checked);}}

async function save(advance){{
  const c=cases[idx];
  const cats=[...document.querySelectorAll('#catGrid input:checked')].map(cb=>cb.value);
  const drugs=[...document.querySelectorAll('#drugGrid input:checked')].map(cb=>cb.value);
  const result={{
    order_id:c.id, has_medication_error:hasErr,
    error_categories:hasErr?cats:[],
    error_details:hasErr?cats.map(cat=>{{return{{category:cat,implicated_drugs:drugs,rationale:document.getElementById('notes').value}}}}):[],
    implicated_drugs:hasErr?drugs:[],
    ncc_merp_severity_category:hasErr?document.getElementById('sev').value:'A',
    overall_recommendation:document.getElementById('notes').value,
    reviewed_at:new Date().toISOString()
  }};
  const r=await fetch('/api/save',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(result)}});
  if(r.ok){{
    results[c.id]=result;
    buildSidebar();
    toast('Saved!');
    if(advance&&idx+1<cases.length) goTo(idx+1);
    else{{document.getElementById('cBadge').textContent='✓ Classified';document.getElementById('cBadge').className='badge b-done';}}
  }}
}}

function go(d){{goTo(idx+d);}}
function exportJSON(){{window.location.href='/api/export';}}
function updateProg(){{
  const done=Object.keys(results).length,total=cases.length;
  document.getElementById('pFill').style.width=(total?Math.round(done/total*100):0)+'%';
  document.getElementById('pTxt').textContent=done+' / '+total;
}}
function toast(msg){{const t=document.getElementById('toast');t.textContent=msg;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2000);}}
function esc(s){{return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}}

// Build category checkboxes on load
document.getElementById('catGrid').innerHTML=CATS.map(cat=>
  `<label class="cbi dis"><input type="checkbox" value="${{esc(cat)}}" onchange="ckStyle(this.parentElement)"> ${{esc(cat)}}</label>`
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
                input_path = body.get("input", "")
                output_path = body.get("output", "outputs/pharmacist_reference.json")
                cases = load_cases(input_path)
                results = load_results(output_path)
                STATE["cases"] = cases
                STATE["results"] = results
                STATE["output_path"] = output_path
                self.send_json({
                    "cases": cases,
                    "results": results,
                })
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
