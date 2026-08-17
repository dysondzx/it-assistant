from langgraph.checkpoint.memory import MemorySaver


def get_checkpointer():
    """持久化层：
    当前用 MemorySaver（会话级记忆），重启后丢失。
    生产环境可替换为 AsyncPostgresSaver
    """
    return MemorySaver()