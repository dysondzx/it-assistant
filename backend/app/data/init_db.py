import sqlite3
from app.config import settings
from app.logging_setup import logger


def init_sqlite_db():
    conn = sqlite3.connect(settings.SQLITE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS error_codes (
        error_code TEXT PRIMARY KEY,
        description TEXT,
        severity TEXT,
        business_impact TEXT
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS business_systems (
        system_id TEXT PRIMARY KEY,
        system_name TEXT,
        owner_id TEXT,
        region TEXT,
        status TEXT
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS owners (
        owner_id TEXT PRIMARY KEY,
        owner_name TEXT,
        email TEXT,
        phone TEXT
    )""")
    cursor.executemany(
        "INSERT OR REPLACE INTO error_codes VALUES (?, ?, ?, ?)",
        [
            ("ERR-4502", "认证服务不可用", "P1", "用户无法登录"),
            ("ERR-3301", "数据库连接池耗尽", "P0", "核心交易中断"),
            ("ERR-2207", "缓存击穿", "P2", "响应延迟升高"),
        ],
    )
    cursor.executemany(
        "INSERT OR REPLACE INTO business_systems VALUES (?, ?, ?, ?, ?)",
        [
            ("SYS-001", "核心交易系统", "OWN-001", "华东", "运行中"),
            ("SYS-002", "用户认证中心", "OWN-002", "华北", "运行中"),
            ("SYS-003", "商品目录服务", "OWN-001", "华东", "降级"),
        ],
    )
    cursor.executemany(
        "INSERT OR REPLACE INTO owners VALUES (?, ?, ?, ?)",
        [
            ("OWN-001", "张三", "zhangsan@corp.com", "13800000001"),
            ("OWN-002", "李四", "lisi@corp.com", "13800000002"),
        ],
    )
    conn.commit()
    conn.close()
    logger.info(f"SQLite 数据库初始化完成：{settings.SQLITE_PATH}")


if __name__ == "__main__":
    init_sqlite_db()