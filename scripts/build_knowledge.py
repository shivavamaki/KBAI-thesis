import argparse
from medicheck.config import get_settings
from medicheck.knowledge import build_knowledge_base


def main():
    parser = argparse.ArgumentParser(description="Build OpenAI vector store knowledge base.")
    parser.add_argument("--knowledge_files", nargs="+", required=True,
                        help="Paths to knowledge files (.pdf, .txt, .json, .jsonl)")
    parser.add_argument("--cache_path", default="outputs/knowledge_cache.json")
    parser.add_argument("--vector_store_name", default=None)
    parser.add_argument("--force_new_vector_store", action="store_true",
                        help="Force creation of a new vector store even if one exists in cache")
    args = parser.parse_args()

    settings = get_settings()
    result = build_knowledge_base(
        api_key=settings.openai_api_key,
        knowledge_files=args.knowledge_files,
        vector_store_name=args.vector_store_name or settings.vector_store_name,
        cache_path=args.cache_path,
        force_new_vector_store=args.force_new_vector_store,
    )
    print(result)


if __name__ == "__main__":
    main()
