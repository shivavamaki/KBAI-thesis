import argparse
from medicheck.config import get_settings
from medicheck.knowledge import build_knowledge_base

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--knowledge_files", nargs="+", required=True)
    parser.add_argument("--cache_path", default="outputs/knowledge_cache.json")
    parser.add_argument("--vector_store_name", default=None)
    parser.add_argument("--recreate", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    result = build_knowledge_base(
        api_key=settings.openai_api_key,
        knowledge_files=args.knowledge_files,
        vector_store_name=args.vector_store_name or settings.vector_store_name,
        cache_path=args.cache_path,
        recreate=args.recreate,
    )
    print(result)

if __name__ == "__main__":
    main()
