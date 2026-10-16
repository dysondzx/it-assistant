"""conversations.py — 会话管理 API。

接口：
    GET    /api/conversations                 会话列表（按最近活跃倒序）
    POST   /api/conversations                 新建空会话
    DELETE /api/conversations/{id}            删除会话（级联删除 checkpoint）
    GET    /api/conversations/{id}/messages   回显历史消息（读 LangGraph checkpoint）
"""
from fastapi import APIRouter, HTTPException, Request

from app.data.conversations import (
    create_conversation,
    delete_conversation,
    get_conversation,
    list_conversations,
)
from app.logging_setup import logger

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def _content_to_text(content) -> str:
    """兼容 content 为 str 或 content blocks（list）两种形态。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return ""


def _to_history(raw_messages) -> list[dict]:
    """把 checkpoint 的 messages 压成前端可渲染的 [user/assistant] 列表。

    过滤掉 ToolMessage 与只有工具调用、没有文本的空 AI 消息；
    连续的 assistant 片段做合并（流式时前端本就在同一个气泡里）。
    """
    history: list[dict] = []
    for msg in raw_messages or []:
        msg_type = getattr(msg, "type", None)
        if msg_type not in ("human", "ai"):
            continue
        text = _content_to_text(getattr(msg, "content", ""))
        if not text:
            continue
        role = "user" if msg_type == "human" else "assistant"
        if role == "assistant" and history and history[-1]["role"] == "assistant":
            history[-1]["content"] += text
        else:
            history.append({"role": role, "content": text})
    return history


async def _load_history(checkpointer, conversation_id: str) -> list[dict]:
    """不带 checkpoint_id 时，aget_tuple 取该 thread 的最新一条 checkpoint。"""
    if checkpointer is None:
        return []
    try:
        checkpoint_tuple = await checkpointer.aget_tuple(
            {"configurable": {"thread_id": conversation_id}}
        )
    except Exception as e:
        logger.error(f"读取会话历史失败 thread_id={conversation_id}: {e}")
        return []
    if checkpoint_tuple is None:
        return []

    checkpoint = getattr(checkpoint_tuple, "checkpoint", None) or {}
    channel_values = checkpoint.get("channel_values") or {}
    return _to_history(channel_values.get("messages"))


@router.get("")
async def api_list_conversations():
    return {"items": await list_conversations()}


@router.post("")
async def api_create_conversation():
    return await create_conversation()


@router.delete("/{conversation_id}")
async def api_delete_conversation(conversation_id: str, request: Request):
    if await get_conversation(conversation_id) is None:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 先清 checkpoint（checkpoints / checkpoint_blobs / checkpoint_writes）
    checkpointer = getattr(request.app.state, "checkpointer", None)
    if checkpointer is not None:
        try:
            await checkpointer.adelete_thread(conversation_id)
        except Exception as e:
            # 清理失败不阻塞会话删除，仅记录，避免留下无法删除的目录行
            logger.error(f"删除 checkpoint 失败 thread_id={conversation_id}: {e}")

    await delete_conversation(conversation_id)
    return {"ok": True}


@router.get("/{conversation_id}/messages")
async def api_get_messages(conversation_id: str, request: Request):
    checkpointer = getattr(request.app.state, "checkpointer", None)
    return {"items": await _load_history(checkpointer, conversation_id)}
