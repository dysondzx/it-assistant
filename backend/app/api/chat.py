import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.agent import build_agent
from app.logging_setup import logger

router = APIRouter()
_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent


class ChatRequest(BaseModel):
    message: str


@router.post("/api/chat")
async def chat(req: ChatRequest):
    """SSE 流式返回 Agent 回复"""
    agent = _get_agent()

    def event_stream():
        try:
            # stream_mode="values"：每个 chunk 是整个状态字典 {"messages": [...]}
            for chunk in agent.stream(
                {"messages": [{"role": "user", "content": req.message}]},
                stream_mode="values",
                config={"recursion_limit": 12},
            ):
                messages = chunk.get("messages", [])
                if not messages:
                    continue
                latest = messages[-1]
                if getattr(latest, "content", None):
                    content = latest.content
                    if isinstance(content, str) and content.strip():
                        payload = json.dumps(
                            {"type": "message", "content": content},
                            ensure_ascii=False,
                        )
                        yield f"data: {payload}\n\n"
        except Exception as e:
            logger.error(f"Agent 执行出错: {e}")
            error_payload = json.dumps(
                {"type": "error", "content": f"服务端错误：{str(e)}"},
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