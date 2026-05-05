# MediCheck Thesis Repository

โครงสร้าง Git repository สำหรับปริญญานิพนธ์เรื่อง  
**การจำแนกใบสั่งยาแบบหลายป้ายกำกับด้วย Knowledge Base Generative AI**  
**Prescription Multi-label Classification with Knowledge Base Generative AI**

> **หมายเหตุ:** ไม่ควร commit ข้อมูลผู้ป่วยจริง, API key, HN, VN, order number หรือไฟล์ที่ระบุตัวตนผู้ป่วยได้ลง Git

---

## Project goals

1. พัฒนาระบบ Knowledge-Based Generative AI สำหรับจำแนกความคลาดเคลื่อนของใบสั่งยาแบบหลายป้ายกำกับ
2. ประเมินประสิทธิภาพของระบบด้วย Precision, Recall, F1-score และ Cohen's Kappa
3. เปรียบเทียบผลลัพธ์ของระบบ AI กับการประเมินของเภสัชกรวิชาชีพ

---

## Repository structure

```text
KBAI-thesis/
├─ knowledge_base/       ไฟล์ฐานความรู้สำหรับ vector store
├─ src/medicheck/        Python package หลัก (config, knowledge, inference, evaluation)
├─ scripts/              CLI scripts (build_knowledge, run_inference, evaluate)
├─ notebooks/            KBAI.ipynb — Colab notebook สำหรับรัน experiment
├─ prompts/              system_prompt.md และ response_schema.json
├─ data/                 raw/ processed/ samples/
├─ database/             schema.sql และ data_dictionary.md
├─ docs/                 เอกสารวิทยานิพนธ์และ architecture
└─ outputs/              ผลลัพธ์การรัน (ไม่ commit ข้อมูลจริง)
```

---

## Knowledge base files

ไฟล์ทั้งหมดใน `knowledge_base/` ที่ใช้สร้าง vector store:

| File | Content |
|---|---|
| `medication_error_kb_chunked.jsonl` | NCC MERP taxonomy (12 error types + subcategories), severity A–I, psychological classification, definitions |
| `allergy_rules.jsonl` | 14 allergy cross-reactivity rules matched to BKN formulary drug classes |
| `BKN_Med_List.jsonl` | Hospital formulary — 1,001 drugs with dosage, indications, contraindications, allergens |
| `index-color-2021-draft-change-10-2022.pdf` | Updated 2022 NCC MERP severity index |
| `MedFacts - Pocket Guide of Drug Interaction.pdf` | Drug interaction pocket reference |
| `DrugInteractionsChapter.pdf` | Drug interactions chapter reference |
| `คู่มือการใช้ยาที่มีความเสี่ยงสูง High Alert Drug 2564.pdf` | Thai high-alert drug guide (HAD) |
| `การจัดการยาความเสี่ยงสูง.pdf` | Thai high-risk drug management guide |

> PDF files and large JSONL files are not committed to Git. Place them in `knowledge_base/` locally and in Google Drive before building.

---

## Setup (local)

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
copy .env.example .env
```

ตั้งค่า `.env`:

```env
OPENAI_API_KEY=your_api_key_here
VECTOR_STORE_NAME=medicheck_knowledge_base
VECTOR_STORE_ID=                        # filled automatically after first build
MODEL=gpt-4.1-mini
```

---

## Build knowledge base (ทำครั้งเดียว)

```bash
python scripts/build_knowledge.py ^
  --knowledge_files ^
    knowledge_base/medication_error_kb_chunked.jsonl ^
    knowledge_base/allergy_rules.jsonl ^
    knowledge_base/BKN_Med_List.jsonl ^
    "knowledge_base/index-color-2021-draft-change-10-2022.pdf" ^
    "knowledge_base/MedFacts - Pocket Guide of Drug Interaction.pdf" ^
    knowledge_base/DrugInteractionsChapter.pdf ^
    "knowledge_base/คู่มือการใช้ยาที่มีความเสี่ยงสูง High Alert Drug ปรับปรุง 2564 HAD_2109.pdf" ^
    "knowledge_base/การจัดการยาความเสี่ยงสูง.pdf" ^
  --cache_path outputs/knowledge_cache.json
```

หลัง build สำเร็จ `VECTOR_STORE_ID` จะถูกบันทึกอัตโนมัติใน `.env`  
**ครั้งต่อไปไม่ต้อง build ใหม่** — inference จะอ่าน ID จาก `.env` โดยตรง

หากต้องการ rebuild ทั้งหมด (เมื่อไฟล์ KB เปลี่ยน):

```bash
python scripts/build_knowledge.py ... --force_new_vector_store
```

---

## Run inference (local)

```bash
python scripts/run_inference.py ^
  --input data/samples/prescriptions_sample.csv ^
  --output outputs/predictions.jsonl
```

---

## Evaluate

```bash
python scripts/evaluate.py ^
  --prediction outputs/predictions.jsonl ^
  --reference data/samples/pharmacist_reference_sample.csv ^
  --output outputs/evaluation_report.json
```

---

## Colab workflow (primary experiment environment)

### Google Drive folder structure

```text
MyDrive/thesis/
├─ KB/
│   ├─ medication_error_kb_chunked.jsonl
│   ├─ allergy_rules.jsonl
│   ├─ BKN_Med_List.jsonl
│   ├─ index-color-2021-draft-change-10-2022.pdf
│   ├─ MedFacts - Pocket Guide of Drug Interaction.pdf
│   ├─ DrugInteractionsChapter.pdf
│   ├─ คู่มือการใช้ยาที่มีความเสี่ยงสูง High Alert Drug ปรับปรุง 2564 HAD_2109.pdf
│   └─ การจัดการยาความเสี่ยงสูง.pdf
├─ Result/
│   ├─ medicheck_cache/
│   │   ├─ knowledge_cache.json      ← vector store cache
│   │   └─ vector_store_id.txt       ← persistent ID (auto-saved after build)
│   └─ thesismedicheck_output/
│       ├─ medicheck_results.json
│       ├─ partial_results.json
│       └─ failed_cases.json
└─ RT_COMMON_904_test_clean_blinded_first_sheet.json   ← input data
```

### Session flow

```
Every session:
  1. Run "Config" cell
       → loads VECTOR_STORE_ID from vector_store_id.txt on Drive automatically
       → prints ✅ Loaded VECTOR_STORE_ID: vs_xxx

  2. IF ✅ loaded → skip build, go straight to inference
     IF ⚠️ not found → run "Build knowledge base" cell ONCE

  3. Run "Run Inference" cell
```

### Build (first time or after KB changes)

In the notebook build cell, `force_new_vector_store` controls rebuild behaviour:

```python
force_new_vector_store=False   # reuse existing — use this every time after first build
force_new_vector_store=True    # full rebuild — use only when KB files have changed
```

### Colab secrets required

| Secret name | Value |
|---|---|
| `GPTKEY` | OpenAI API key |

---

## Output schema

Each classified case returns:

```json
{
  "order_id": "string",
  "has_medication_error": true,
  "error_categories": ["Prescribing Error"],
  "error_details": ["Allergy Prescribing Error — amoxicillin prescribed despite documented penicillin allergy"],
  "implicated_drugs": ["amoxicillin"],
  "ncc_merp_severity_category": "C",
  "overall_recommendation": "string",
  "evidence_quotes": ["string"]
}
```

Error categories follow the **NCC MERP Taxonomy (2001)** 12-type classification:
`Prescribing Error` · `Omission Error` · `Wrong Time Error` · `Unauthorized Drug Error` · `Improper Dose/Quantity Error` · `Wrong Dosage Form Error` · `Wrong Drug Preparation Error` · `Wrong Administration Technique Error` · `Deteriorated Drug Error` · `Monitoring Error` · `Compliance Error` · `Other`

---

## Research safety and PDPA

- ใช้ข้อมูลที่ผ่านการปกปิดตัวตนแล้วเท่านั้น
- แทน HN, VN, order number ด้วยรหัสนิรนาม
- ไม่เก็บชื่อ นามสกุล เลขบัตรประชาชน เบอร์โทรศัพท์ หรือข้อมูลที่ระบุตัวตนได้
- ใช้ผลลัพธ์ AI เป็น decision support เท่านั้น ไม่ใช่การตัดสินใจแทนเภสัชกร
