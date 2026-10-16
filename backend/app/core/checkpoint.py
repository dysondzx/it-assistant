"""checkpoint.py — PostgreSQL 连接池与 AsyncPostgresSaver 的生命周期管理。

把"建池、建表、关池"封装成独立模块，供 FastAPI lifespan 调用。
"""
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.config import settings
from app.logging_setup import logger

# 会话级咨询锁 key（同一个库内唯一即可），用于串行化建表
_SETUP_LOCK_KEY = 20241011

_checkpointer: AsyncPostgresSaver | None = None
_pool: AsyncConnectionPool | None = None


async def _setup_tables(pool: AsyncConnectionPool) -> None:
    """幂等建表，并用 PG 咨询锁串行化。

    CREATE TABLE IF NOT EXISTS 并非并发安全：多个 worker 同时执行时，
    双方都先看到"表不存在"，于是一起往 pg_class/pg_type 插记录，
    后者会撞唯一索引 pg_type_typname_nsp_index → UniqueViolation。
    用会话级咨询锁把这一步变成串行，无论开几个 worker 都安全。
    """
    async with pool.connection() as conn:
        await conn.execute("SELECT pg_advisory_lock(%s)", (_SETUP_LOCK_KEY,))
        try:
            # 建表借用这条连接即可；运行期的 saver 必须绑定 pool
            await AsyncPostgresSaver(conn).setup()
        finally:
            await conn.execute("SELECT pg_advisory_unlock(%s)", (_SETUP_LOCK_KEY,))


@asynccontextmanager
async def checkpointer_lifespan():
    """进程级共享一个 AsyncPostgresSaver（内部维护连接池）。

    在 FastAPI 的 lifespan 中进入/退出，负责建表与连接池的创建、关闭。
    """
    global _checkpointer, _pool
    async with AsyncConnectionPool(
        conninfo=settings.POSTGRES_URI,      # ← 用项目的变量名，别用 DATABASE_URL
        min_size=2,
        max_size=20,
        max_idle=300.0,
        max_lifetime=3600.0,
        open=False,                          # 不在构造时打开，消除弃用警告
        kwargs={
            "autocommit": True,              # setup() 里的 CREATE INDEX CONCURRENTLY 需要
            "prepare_threshold": 0,          # LangGraph 官方推荐
            "row_factory": dict_row,
        },
    ) as pool:
        await pool.open()                    # __aenter__ 已打开，这里是显式表意
        await pool.wait()                    # 等 min_size 个连接就绪，启动期 fail-fast

        await _setup_tables(pool)

        saver = AsyncPostgresSaver(pool)     # ← 绑 pool，运行期并发安全
        _checkpointer = saver
        _pool = pool
        logger.info("AsyncPostgresSaver 初始化完成")
        try:
            yield saver
        finally:
            _checkpointer = None
            _pool = None
            logger.info("AsyncPostgresSaver 已关闭")


def get_checkpointer() -> AsyncPostgresSaver:
    if _checkpointer is None:
        raise RuntimeError("Checkpointer 未初始化：请在 FastAPI lifespan 中先初始化")
    return _checkpointer


def get_pool() -> AsyncConnectionPool:
    """供会话表等外围表复用同一个连接池（避免另起一套连接）。"""
    if _pool is None:
        raise RuntimeError("连接池未初始化：请在 FastAPI lifespan 中先初始化")
    return _pool
