import argparse
import json
from pathlib import Path
from medicheck.evaluation import evaluate_predictions

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prediction", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--output", default="outputs/evaluation_report.json")
    args = parser.parse_args()

    report = evaluate_predictions(args.prediction, args.reference)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
