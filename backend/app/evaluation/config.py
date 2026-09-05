import os
from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.embeddings import embedding_factory


def _get_api_key() -> str:
    """从环境变量读取 DeepSeek API Key，未设置时给出明确提示。"""
    key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not key:
        print("  [WARN] 环境变量 DEEPSEEK_API_KEY 未设置，裁判 LLM 将无法调用")
    return key


def _get_base_url() -> str:
    return os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")


def get_judge_llm():
    """
    构建 RAGAS 裁判 LLM
    """
    client = AsyncOpenAI(api_key=_get_api_key(), base_url=_get_base_url())
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    return llm_factory(model, client=client)


def get_judge_embeddings():
    """
    构建 RAGAS 裁判 Embedding
    """
    return embedding_factory(
        "huggingface",
        model=os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5"),
    )