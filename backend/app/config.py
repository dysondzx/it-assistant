import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
    SQLITE_PATH = os.getenv("SQLITE_PATH", "./it_ops.db")
    FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "./faiss_it_manual")
    KG_PATH = os.getenv("KG_PATH", "./it_ops_kg.pkl")


settings = Settings()