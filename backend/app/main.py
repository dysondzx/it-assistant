import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent import build_agent
from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.core.checkpoint import checkpointer_lifespan
from app.data.conversations import ensure_conversations_table
from app.data.kg import get_or_build_kg
from app.evaluation.api import router as eval_router
from app.logging_setup import logger

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 开启LangSmith
    os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "true")
    os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")
    os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "default")

    get_or_build_kg()
    async with checkpointer_lifespan() as checkpointer:
        # 挂到 app.state，供各路由通过 request.app.state 获取
        app.state.checkpointer = checkpointer
        app.state.agent = build_agent(checkpointer=checkpointer)
        # 会话表建在同一个 Postgres 上，复用 checkpointer 的连接池
        await ensure_conversations_table()
        logger.info("IT Assistant 后端启动完成")
        yield
    logger.info("IT Assistant 后端关闭")


app = FastAPI(title="IT Assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(conversations_router)
app.include_router(eval_router)


@app.get("/health")
def health():
    return {"status": "ok"}
