# MediCheck Thesis Repository

โครงสร้าง Git repository สำหรับปริญญานิพนธ์เรื่อง  
**การจำแนกใบสั่งยาแบบหลายป้ายกำกับด้วย Knowledge Base Generative AI**  
**Prescription Multi-label Classification with Knowledge Base Generative AI**

Repository นี้จัดเตรียมไฟล์สำคัญสำหรับงานวิจัย ได้แก่ เอกสารประกอบวิทยานิพนธ์ ฐานข้อมูลตัวอย่าง โครงสร้างฐานข้อมูล ฐานความรู้ โค้ด Python สำหรับสร้าง knowledge base, inference และ evaluation รวมถึง notebook ต้นฉบับ

> หมายเหตุ: ไม่ควร commit ข้อมูลผู้ป่วยจริง, API key, HN, VN, order number หรือไฟล์ที่ระบุตัวตนผู้ป่วยได้ลง Git

## Project goals

1. พัฒนาระบบ Knowledge-Based Generative AI สำหรับจำแนกความคลาดเคลื่อนของใบสั่งยาแบบหลายป้ายกำกับ
2. ประเมินประสิทธิภาพของระบบด้วย Precision, Recall, F1-score, ROC-AUC และ Cohen’s Kappa
3. เปรียบเทียบผลลัพธ์ของระบบ AI กับการประเมินของเภสัชกรวิชาชีพ

## Repository structure

```text
medicheck-thesis-repo/
├─ docs/                 เอกสารวิทยานิพนธ์และเอกสารระบบ
├─ knowledge_base/       ไฟล์ฐานความรู้ที่ใช้กับ vector store
├─ data/                 raw/ processed/ samples/
├─ database/             schema และ data dictionary
├─ notebooks/            notebook ต้นฉบับ
├─ prompts/              system prompt และ response schema
├─ src/medicheck/        source code หลัก
├─ scripts/              command-line scripts
├─ tests/                unit tests เบื้องต้น
└─ outputs/              ผลลัพธ์การรัน ไม่ควร commit ข้อมูลจริง
```

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
copy .env.example .env
```

ตั้งค่า `.env`

```env
OPENAI_API_KEY=your_api_key_here
VECTOR_STORE_NAME=medicheck_knowledge_base
```

สร้าง knowledge base

```bash
python scripts/build_knowledge.py ^
  --knowledge_files knowledge_base/Medication_errors_definitions.pdf knowledge_base/taxonomy2001-07-31.pdf knowledge_base/BKN_Med_List.json ^
  --cache_path outputs/knowledge_cache.json
```

รัน inference

```bash
python scripts/run_inference.py ^
  --input data/samples/prescriptions_sample.csv ^
  --output outputs/predictions.jsonl ^
  --cache_path outputs/knowledge_cache.json
```

ประเมินผล

```bash
python scripts/evaluate.py ^
  --prediction outputs/predictions.jsonl ^
  --reference data/samples/pharmacist_reference_sample.csv ^
  --output outputs/evaluation_report.json
```

## Research safety and PDPA

- ใช้ข้อมูลที่ผ่านการปกปิดตัวตนแล้วเท่านั้น
- แทน HN, VN, order number ด้วยรหัสนิรนาม
- ไม่เก็บชื่อ นามสกุล เลขบัตรประชาชน เบอร์โทรศัพท์ หรือข้อมูลที่ระบุตัวตนได้
- เก็บ log เฉพาะข้อมูลที่จำเป็นต่อการทำซ้ำและ audit
- ใช้ผลลัพธ์ AI เป็น decision support ไม่ใช่การตัดสินใจแทนเภสัชกร

## Main outputs

- `outputs/predictions.jsonl` ผลการจำแนกของ AI
- `outputs/evaluation_report.json` รายงานตัวชี้วัด
- `outputs/failed_cases.json` เคสที่ inference ไม่สำเร็จ
- `outputs/debug_response.jsonl` log สำหรับตรวจสอบ response ที่ผิดรูปแบบ
