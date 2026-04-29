CREATE TABLE prescriptions (
    case_id TEXT PRIMARY KEY,
    order_id_hash TEXT UNIQUE NOT NULL,
    patient_age INTEGER,
    weight_kg REAL,
    height_cm REAL,
    bmi REAL,
    bsa REAL,
    sbp INTEGER,
    dbp INTEGER,
    allergy_text TEXT,
    diagnosis_icd TEXT,
    created_at TEXT
);

CREATE TABLE prescription_items (
    item_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    drug_name TEXT NOT NULL,
    strength TEXT,
    dosage_form TEXT,
    dose TEXT,
    route TEXT,
    frequency TEXT,
    duration TEXT,
    quantity TEXT,
    status TEXT,
    FOREIGN KEY(case_id) REFERENCES prescriptions(case_id)
);

CREATE TABLE pharmacist_reference (
    reference_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    has_medication_error INTEGER NOT NULL,
    labels_json TEXT NOT NULL,
    reviewer_role TEXT,
    reviewed_at TEXT,
    FOREIGN KEY(case_id) REFERENCES prescriptions(case_id)
);

CREATE TABLE ai_predictions (
    prediction_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    model_name TEXT,
    has_medication_error INTEGER NOT NULL,
    labels_json TEXT NOT NULL,
    raw_response_json TEXT,
    created_at TEXT,
    FOREIGN KEY(case_id) REFERENCES prescriptions(case_id)
);
