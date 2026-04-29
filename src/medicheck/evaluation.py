import ast
import json
import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.metrics import precision_recall_fscore_support, classification_report, cohen_kappa_score

def _parse_labels(value):
    if pd.isna(value) or value in ("", "[]"):
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = ast.literal_eval(value)
        return parsed if isinstance(parsed, list) else [str(parsed)]
    except Exception:
        return [str(value)]

def load_predictions_jsonl(path: str) -> pd.DataFrame:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                rows.append({
                    "case_id": item.get("order_id") or item.get("case_id"),
                    "has_medication_error": item.get("has_medication_error", False),
                    "error_categories": item.get("error_categories", []),
                })
    return pd.DataFrame(rows)

def evaluate_predictions(prediction_path: str, reference_path: str) -> dict:
    pred = load_predictions_jsonl(prediction_path)
    ref = pd.read_csv(reference_path)

    pred["error_categories"] = pred["error_categories"].apply(_parse_labels)
    ref["error_categories"] = ref["error_categories"].apply(_parse_labels)

    merged = ref.merge(pred, on="case_id", suffixes=("_ref", "_pred"))
    labels = sorted(set(sum(merged["error_categories_ref"].tolist() + merged["error_categories_pred"].tolist(), [])))

    mlb = MultiLabelBinarizer(classes=labels)
    y_true = mlb.fit_transform(merged["error_categories_ref"])
    y_pred = mlb.transform(merged["error_categories_pred"])

    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, average="micro", zero_division=0
    )

    exact_match = (y_true == y_pred).all(axis=1).mean() if len(merged) else 0
    kappa = cohen_kappa_score(
        merged["has_medication_error_ref"].astype(bool),
        merged["has_medication_error_pred"].astype(bool),
    )

    return {
        "n_cases": int(len(merged)),
        "labels": labels,
        "micro_precision": float(precision),
        "micro_recall": float(recall),
        "micro_f1": float(f1),
        "subset_accuracy": float(exact_match),
        "cohens_kappa_binary_error": float(kappa),
        "classification_report": classification_report(
            y_true, y_pred, target_names=labels, zero_division=0, output_dict=True
        ) if labels else {},
    }
