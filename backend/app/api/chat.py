import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk
from pydantic import BaseModel

from app.logging_setup import logger

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""


@router.post("/api/chat")
async def chat(req: ChatRequest, request: Request):
    """SSE 流式返回 Agent 回复"""
    agent = request.app.state.agent

    def _chunk_text(content) -> str:
        """兼容 content 为 str 或 content blocks（list）两种形态"""
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

    async def event_stream():
        try:
            async for chunk, _metadata in agent.astream(
                {"messages": [{"role": "user", "content": req.message}]},
                stream_mode="messages",
                config={
                    "recursion_limit": 12,
                    # thread_id 即会话标识，对应前端持久化的 session_id
                    "configurable": {"thread_id": req.session_id},
                },
            ):
                if not isinstance(chunk, AIMessageChunk):
                    continue
                # 模型决定调用工具时也会产出分片，但 content 为空，这里自然被跳过
                text = _chunk_text(chunk.content)
                if not text:
                    continue
                payload = json.dumps(
                    {"type": "message", "content": text},
                    ensure_ascii=False,
                )
                yield f"data: {payload}\n\n"
        except Exception as e:
            logger.error(f"Agent 执行出错: {e}")
            error_payload = json.dumps(
                {"type": "error", "content": f"服务端错误：{e}"},
                ensure_ascii=False,
            )
            yield f"data: {error_payload}\n\n"
        finally:
            # 结束时发送 done 事件
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
