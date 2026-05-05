from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    model: str = os.getenv("MODEL", "gpt-4.1-mini")
    vector_store_name: str = os.getenv("VECTOR_STORE_NAME", "medicheck_knowledge_base")
    vector_store_id: str = os.getenv("VECTOR_STORE_ID", "")

def get_settings() -> Settings:
    return Settings()
