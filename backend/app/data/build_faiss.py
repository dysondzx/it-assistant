from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from app.config import settings
from app.logging_setup import logger

SAMPLE_DOCS = [
    Document(
        page_content=(
            "ERR-4502 认证服务不可用处理流程：\n"
            "1. 检查认证中心服务状态\n"
            "2. 查看认证日志 /var/log/auth-service.log\n"
            "3. 确认数据库连接池未耗尽\n"
            "4. 执行重启命令：systemctl restart auth-service\n"
            "5. 验证：调用 /health 接口返回 200"
        ),
        metadata={"source": "auth_manual.md", "page": 1},
    ),
    Document(
        page_content=(
            "ERR-3301 数据库连接池耗尽处理流程：\n"
            "1. 查看当前连接数\n"
            "2. 检查慢查询日志定位长事务\n"
            "3. 临时扩容：SET GLOBAL max_connections = 500\n"
            "4. 永久生效需修改 my.cnf 并重启\n"
            "5. 根本治理：增加连接池上限 + 优化慢 SQL"
        ),
        metadata={"source": "db_manual.md", "page": 1},
    ),
    Document(
        page_content=(
            "ERR-2207 缓存击穿处理流程：\n"
            "1. 确认 Redis 命中率是否骤降\n"
            "2. 对热点 key 启用互斥锁重建缓存\n"
            "3. 预热缓存：提前加载热点数据\n"
            "4. 设置合理的 TTL 错开过期时间\n"
            "5. 长期方案：本地缓存 + 分布式锁"
        ),
        metadata={"source": "cache_manual.md", "page": 1},
    ),
]


def build_faiss_index():
    embeddings = HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    vector_store = FAISS.from_documents(SAMPLE_DOCS, embeddings)
    vector_store.save_local(settings.FAISS_INDEX_PATH)
    logger.info(f"FAISS 索引构建完成：{settings.FAISS_INDEX_PATH}")


if __name__ == "__main__":
    build_faiss_index()