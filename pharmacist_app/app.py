import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

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
    "A": "A — Potential error only (no error occurred)",
    "B": "B — Error occurred, did not reach patient",
    "C": "C — Error reached patient, no harm",
    "D": "D — Error reached patient, required monitoring, no harm",
    "E": "E — Temporary harm, intervention required",
    "F": "F — Temporary harm, hospitalization required",
    "G": "G — Permanent patient harm",
    "H": "H — Life-sustaining intervention required",
    "I": "I — Patient death",
}

YES_LABEL = "Yes — มีความคลาดเคลื่อน"
NO_LABEL  = "No  — ไม่มีความคลาดเคลื่อน"


# ── Helpers ────────────────────────────────────────────────────────────────────
def load_cases(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    col = next((c for c in ("ID", "case_id", "order_id") if c in df.columns), df.columns[0])
    return [(str(gid), gdf.reset_index(drop=True)) for gid, gdf in df.groupby(col, dropna=False)]


def load_results(path: str) -> dict:
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def save_results(path: str, results: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(list(results.values()), ensure_ascii=False, indent=2), encoding="utf-8")


def get_drugs(case_df: pd.DataFrame) -> list:
    for col in ("Drug", "drug_name", "drug", "Medication", "medication"):
        if col in case_df.columns:
            return [
                str(v).strip()
                for v in case_df[col]
                if str(v).strip() not in ("", "-", "None", "nan")
            ]
    return []


def build_result(order_id, has_error, categories, implicated_drugs, severity, notes) -> dict:
    return {
        "order_id": order_id,
        "has_medication_error": has_error,
        "error_categories": categories if has_error else [],
        "error_details": [
            {"category": c, "implicated_drugs": implicated_drugs, "rationale": notes}
            for c in (categories if has_error else [])
        ],
        "implicated_drugs": implicated_drugs if has_error else [],
        "ncc_merp_severity_category": severity if has_error else "A",
        "overall_recommendation": notes,
        "reviewed_at": datetime.now().isoformat(),
    }


def init_case_state(order_id: str, existing: dict, drug_list: list) -> None:
    """Seed widget session_state from a saved result (runs only on first visit)."""
    if f"he_{order_id}" not in st.session_state:
        st.session_state[f"he_{order_id}"] = (
            YES_LABEL if existing.get("has_medication_error") else NO_LABEL
        )
    if f"cat_{order_id}" not in st.session_state:
        st.session_state[f"cat_{order_id}"] = [
            c for c in existing.get("error_categories", []) if c in ERROR_CATEGORIES
        ]
    if f"sev_{order_id}" not in st.session_state:
        sv = existing.get("ncc_merp_severity_category", "C")
        st.session_state[f"sev_{order_id}"] = sv if sv in SEVERITY else "C"
    if f"drugs_{order_id}" not in st.session_state:
        st.session_state[f"drugs_{order_id}"] = [
            d for d in existing.get("implicated_drugs", []) if d in drug_list
        ]
    if f"notes_{order_id}" not in st.session_state:
        st.session_state[f"notes_{order_id}"] = existing.get("overall_recommendation", "")


def do_save(order_id, has_error, advance=False) -> None:
    result = build_result(
        order_id, has_error,
        st.session_state.get(f"cat_{order_id}", []),
        st.session_state.get(f"drugs_{order_id}", []),
        st.session_state.get(f"sev_{order_id}", "C"),
        st.session_state.get(f"notes_{order_id}", ""),
    )
    st.session_state.results[order_id] = result
    save_results(st.session_state.output_path, st.session_state.results)
    if advance:
        total = len(st.session_state.cases)
        if st.session_state.idx + 1 < total:
            st.session_state.idx += 1


# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MediCheck — Pharmacist Review",
    page_icon="💊",
    layout="wide",
)

# ── Session state defaults ─────────────────────────────────────────────────────
for key, default in [
    ("cases", []),
    ("results", {}),
    ("idx", 0),
    ("output_path", ""),
    ("loaded", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("💊 MediCheck")
    st.caption("Pharmacist Prescription Review")
    st.divider()

    input_path = st.text_input(
        "Input JSON",
        value="data/raw/RT_COMMON_904_test_clean_blinded_first_sheet.json",
        help="Path to prescription JSON file (array of records)",
    )
    output_path_input = st.text_input(
        "Output JSON",
        value="outputs/pharmacist_reference.json",
        help="Where pharmacist classifications are saved",
    )

    if st.button("Load File", type="primary", use_container_width=True):
        try:
            cases = load_cases(input_path)
            results_raw = load_results(output_path_input)
            # Normalize: support both list and dict formats
            if isinstance(results_raw, list):
                results = {r["order_id"]: r for r in results_raw if "order_id" in r}
            else:
                results = results_raw
            st.session_state.cases = cases
            st.session_state.results = results
            st.session_state.output_path = output_path_input
            st.session_state.loaded = True
            # Jump to first unclassified case
            st.session_state.idx = next(
                (i for i, (oid, _) in enumerate(cases) if oid not in results), 0
            )
            st.success(f"Loaded {len(cases)} cases · {len(results)} already classified")
            st.rerun()
        except FileNotFoundError:
            st.error(f"File not found: {input_path}")
        except Exception as e:
            st.error(f"Error loading file: {e}")

    if st.session_state.loaded:
        total = len(st.session_state.cases)
        done  = len(st.session_state.results)
        st.divider()
        pct = done / total if total else 0
        st.progress(pct, text=f"**{done} / {total}** cases classified ({pct:.0%})")

        st.divider()
        jump = st.number_input("Jump to case #", 1, max(total, 1), st.session_state.idx + 1)
        if st.button("Go", use_container_width=True):
            st.session_state.idx = int(jump) - 1
            st.rerun()

        st.divider()
        if st.session_state.results:
            st.download_button(
                "⬇ Download results (JSON)",
                data=json.dumps(list(st.session_state.results.values()), ensure_ascii=False, indent=2),
                file_name="pharmacist_reference.json",
                mime="application/json",
                use_container_width=True,
            )

# ── Guard: not loaded ──────────────────────────────────────────────────────────
if not st.session_state.loaded:
    st.title("MediCheck — Pharmacist Prescription Review")
    st.markdown("""
    ### วิธีใช้ / How to use

    1. ตรวจสอบ path ของไฟล์ข้อมูลใน sidebar ด้านซ้าย
    2. กด **Load File**
    3. ระบบจะแสดงใบสั่งยาทีละรายการ — เลือกประเภทความคลาดเคลื่อนแล้วกด **Save & Next**
    4. ผลลัพธ์จะถูกบันทึกอัตโนมัติทุกครั้งที่กด Save
    """)
    st.stop()

# ── Current case ───────────────────────────────────────────────────────────────
cases  = st.session_state.cases
total  = len(cases)
idx    = max(0, min(st.session_state.idx, total - 1))
order_id, case_df = cases[idx]

existing  = st.session_state.results.get(order_id, {})
drug_list = get_drugs(case_df)
init_case_state(order_id, existing, drug_list)

# ── Case header ────────────────────────────────────────────────────────────────
done = len(st.session_state.results)
h1, h2, h3, h4 = st.columns([3, 2, 2, 2])
h1.markdown(f"## Case {idx + 1} / {total}")
h2.metric("Order ID", order_id)
h3.metric("Classified", f"{done} / {total}")
h4.metric("Status", "✅ Done" if order_id in st.session_state.results else "⬜ Pending")

# ── Prescription table ─────────────────────────────────────────────────────────
st.subheader("Prescription Details")
show_cols = [c for c in ["Drug", "Dose", "Frequency", "Route", "Duration", "Status"] if c in case_df.columns]
st.dataframe(
    case_df[show_cols] if show_cols else case_df,
    use_container_width=True,
    hide_index=True,
)

st.divider()

# ── Classification widgets ─────────────────────────────────────────────────────
st.subheader("Pharmacist Classification")

has_error_str = st.radio(
    "มีความคลาดเคลื่อนทางยาหรือไม่? / Medication error present?",
    [YES_LABEL, NO_LABEL],
    key=f"he_{order_id}",
    horizontal=True,
)
has_error = has_error_str == YES_LABEL

col_left, col_right = st.columns(2)

col_left.multiselect(
    "Error categories — NCC MERP (เลือกได้หลายประเภท)",
    ERROR_CATEGORIES,
    key=f"cat_{order_id}",
    disabled=not has_error,
    placeholder="Select all that apply...",
)

col_right.selectbox(
    "NCC MERP Severity Category",
    list(SEVERITY.keys()),
    format_func=lambda k: SEVERITY[k],
    key=f"sev_{order_id}",
    disabled=not has_error,
)

st.multiselect(
    "Implicated drugs (ยาที่เกี่ยวข้อง)",
    drug_list,
    key=f"drugs_{order_id}",
    disabled=not has_error,
    placeholder="Select drugs involved in the error...",
)

st.text_area(
    "Notes / Rationale (เหตุผลประกอบ)",
    key=f"notes_{order_id}",
    height=110,
    placeholder="บันทึกเหตุผลหรือข้อสังเกตของเภสัชกร...",
)

# ── Navigation & Save ──────────────────────────────────────────────────────────
st.divider()
b1, b2, b3, b4 = st.columns(4)

if b1.button("← Prev", disabled=(idx == 0), use_container_width=True):
    st.session_state.idx = idx - 1
    st.rerun()

if b2.button("Save", use_container_width=True, help="Save without advancing"):
    do_save(order_id, has_error, advance=False)
    st.toast("Saved!", icon="✅")
    st.rerun()

if b3.button("Save & Next →", type="primary", use_container_width=True):
    do_save(order_id, has_error, advance=True)
    st.rerun()

if b4.button("Skip →", disabled=(idx >= total - 1), use_container_width=True, help="Next without saving"):
    st.session_state.idx = idx + 1
    st.rerun()
