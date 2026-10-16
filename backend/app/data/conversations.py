"""conversations.py — 会话（对话）元数据表的建表与 CRUD。

设计取舍：
    本表只存"目录"信息（id / 标题 / 时间），消息正文仍由 LangGraph checkpoint 承载，
    避免消息双写带来的不一致。表里的 id 即前端的 session_id，也是 LangGraph 的 thread_id。
"""
import uuid

from app.core.checkpoint import get_pool
from app.logging_setup import logger

# 会话级咨询锁 key：与 checkpoint 建表用不同的 key，各自串行化即可
_SETUP_LOCK_KEY = 20241012

DEFAULT_TITLE = "新对话"
TITLE_MAX_LEN = 20

# 与会话列表相关的列，统一在这里维护，避免各处 SELECT 写散
_SELECT_COLUMNS = "id, title, created_at, updated_at"

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS conversations (
    id         TEXT PRIMARY KEY,
    title      TEXT NOT NULL DEFAULT '新对话',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""

_CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_conversations_updated_at
    ON conversations (updated_at DESC)
"""


def derive_title(text: str) -> str:
    """用首条用户消息截断生成会话标题。"""
    normalized = " ".join(text.strip().split())
    return normalized[:TITLE_MAX_LEN] or DEFAULT_TITLE


async def ensure_conversations_table() -> None:
    """幂等建表，用 PG 咨询锁串行化。

    与 checkpoint 建表同理：CREATE TABLE IF NOT EXISTS 并非并发安全，
    多 worker 同时执行会撞唯一索引，所以这一步必须串行。
    """
    pool = get_pool()
    async with pool.connection() as conn:
        await conn.execute("SELECT pg_advisory_lock(%s)", (_SETUP_LOCK_KEY,))
        try:
            await conn.execute(_CREATE_TABLE_SQL)
            await conn.execute(_CREATE_INDEX_SQL)
        finally:
            await conn.execute("SELECT pg_advisory_unlock(%s)", (_SETUP_LOCK_KEY,))
    logger.info("conversations 表准备完成")


async def list_conversations() -> list[dict]:
    """按最近活跃倒序列出全部会话。"""
    pool = get_pool()
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT " + _SELECT_COLUMNS + " FROM conversations ORDER BY updated_at DESC"
        )
        rows = await cur.fetchall()
    return list(rows)


async def get_conversation(conversation_id: str) -> dict | None:
    pool = get_pool()
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT " + _SELECT_COLUMNS + " FROM conversations WHERE id = %s",
            (conversation_id,),
        )
        return await cur.fetchone()


async def create_conversation(conversation_id: str | None = None) -> dict:
    """新建空会话；不传 id 时由服务端生成。"""
    pool = get_pool()
    async with pool.connection() as conn:
        cur = await conn.execute(
            """
            INSERT INTO conversations (id, title)
            VALUES (%s, %s)
            ON CONFLICT (id) DO UPDATE SET updated_at = now()
            RETURNING """ + _SELECT_COLUMNS,
            (conversation_id or str(uuid.uuid4()), DEFAULT_TITLE),
        )
        return await cur.fetchone()


async def upsert_on_chat(conversation_id: str, message: str) -> None:
    """发消息时兜底：会话不存在则插入，存在则刷新 updated_at。

    标题仍为默认值时才用本次消息补上，避免覆盖已命名的会话。
    """
    if not conversation_id:
        return

    pool = get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            """
            INSERT INTO conversations (id, title)
            VALUES (%s, %s)
            ON CONFLICT (id) DO UPDATE
                SET title = CASE
                        WHEN conversations.title = %s THEN EXCLUDED.title
                        ELSE conversations.title
                    END,
                    updated_at = now()
            """,
            (conversation_id, derive_title(message), DEFAULT_TITLE),
        )


async def delete_conversation(conversation_id: str) -> bool:
    """删除会话目录行；消息本身由调用方级联清理 checkpoint。"""
    pool = get_pool()
    async with pool.connection() as conn:
        cur = await conn.execute(
            "DELETE FROM conversations WHERE id = %s RETURNING id",
            (conversation_id,),
        )
        return await cur.fetchone() is not None
