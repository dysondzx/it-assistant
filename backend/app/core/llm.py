from langchain_openai import ChatOpenAI
from app.config import settings
from app.logging_setup import logger


def get_llm(temperature: float = 0.0) -> ChatOpenAI:
    logger.info(f"初始化 LLM: {settings.DEEPSEEK_MODEL}")
    return ChatOpenAI(
        model=settings.DEEPSEEK_MODEL,
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
        temperature=temperature,
    )