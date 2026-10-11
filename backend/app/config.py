import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
    SQLITE_PATH = os.getenv("SQLITE_PATH", "./it_ops.db")
    FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "./faiss_it_manual")
    KG_PATH = os.getenv("KG_PATH", "./it_ops_kg.pkl")
    POSTGRES_URI = os.getenv(
        "POSTGRES_URI",
        "postgresql://postgres:postgres@localhost:5432/langgraph",
    )


settings = Settings()