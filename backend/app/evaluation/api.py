"""
评估 API 路由
接口：
    GET  /api/eval/health 健康检查 + 数据集规模
    POST /api/eval/run  触发一次完整评估（后台任务，立即返回 task_id）
    GET  /api/eval/run/{task_id}  查询评估进度与结果
说明：
    评估是长耗时任务（逐条调用 LLM 裁判），同步等待会导致网关超时。因此 POST /api/eval/run 仅启动后台任务并立刻返回 task_id，客户端轮询 GET /api/eval/run/{task_id} 获取进度与最终结果
"""

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agent import build_agent
from app.evaluation.dataset import DEFAULT_DATASET
from app.evaluation.runner import run_evaluation

router = APIRouter()

# 进程内任务注册表：task_id -> 状态 dict
_TASKS: dict[str, dict] = {}

class EvalRequest(BaseModel):
    """评估请求参数"""

    limit: int = 0  # 0 表示评估全部样本
    metrics: list[str] = [
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
        "answer_correctness",
    ]


def _available_metrics() -> set[str]:
    return {"faithfulness", "answer_relevancy", "context_precision",
            "context_recall", "answer_correctness"}


async def _run_task(task_id: str, dataset, metrics_config: dict):
    """后台任务：真正执行评估，并更新任务状态。"""
    try:
        _TASKS[task_id]["status"] = "running"
        agent = build_agent()
        results = await run_evaluation(agent, dataset, metrics_config)
        _TASKS[task_id].update(
            status="success",
            total=len(results),
            results=results,
        )
    except Exception as e:
        _TASKS[task_id].update(status="failed", error=str(e))


@router.get("/api/eval/health")
async def health():
    return {
        "status": "ok",
        "dataset_size": len(DEFAULT_DATASET)
    }


@router.post("/api/eval/run")
async def start_eval(req: EvalRequest):
    """
    触发评估（后台异步执行，立即返回 task_id）。
    客户端用 task_id 轮询 /api/eval/run/{task_id} 获取结果。
    """
    unknown = set(req.metrics) - _available_metrics()
    if unknown:
        raise HTTPException(status_code=400, detail=f"未知指标: {sorted(unknown)}")

    metrics_config = {m: (m in req.metrics) for m in _available_metrics()}
    dataset = DEFAULT_DATASET if req.limit <= 0 else DEFAULT_DATASET[: req.limit]

    task_id = str(uuid.uuid4())
    _TASKS[task_id] = {"status": "pending", "total": 0, "results": None, "error": None}

    import asyncio
    asyncio.create_task(_run_task(task_id, dataset, metrics_config))

    return {
        "task_id": task_id,
        "status": "pending",
        "dataset_size": len(dataset),
        "message": "评估已启动，请轮询 /api/eval/run/{task_id} 获取进度",
    }


@router.get("/api/eval/run/{task_id}")
async def get_eval_result(task_id: str):
    """查询评估任务的进度与最终结果。"""
    task = _TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task_id 不存在或已过期")
    resp = {"task_id": task_id, "status": task["status"]}
    if task["status"] == "success":
        resp["total"] = task["total"]
        resp["results"] = task["results"]
    elif task["status"] == "failed":
        resp["error"] = task["error"]
    return resp