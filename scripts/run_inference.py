import argparse
from medicheck.config import get_settings
from medicheck.inference import run_inference

def main():
    settings = get_settings()
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="outputs/predictions.jsonl")
    parser.add_argument("--cache_path", default="outputs/knowledge_cache.json")
    parser.add_argument("--group_column", default=settings.group_column)
    parser.add_argument("--max_cases", type=int, default=None)
    args = parser.parse_args()
    result = run_inference(
        api_key=settings.openai_api_key,
        input_path=args.input,
        output_path=args.output,
        cache_path=args.cache_path,
        model=settings.model,
        group_column=args.group_column,
        max_cases=args.max_cases,
    )
    print(result)

if __name__ == "__main__":
    main()
