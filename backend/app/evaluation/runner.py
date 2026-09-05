"""
RAGAS 评估运行器（端到端）
对测试集逐条跑出 response 与 retrieved_contexts，再用 RAGAS 打分
"""

import asyncio
from typing import Optional
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import AIMessage, ToolMessage

from ragas.metrics.collections import (
    Faithfulness,
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    AnswerCorrectness,
)
from ragas.metrics.collections.base import MetricResult

from app.evaluation.config import get_judge_llm, get_judge_embeddings
from app.evaluation.dataset import EvalSample


async def _run_agent(agent: CompiledStateGraph, user_input: str) -> tuple[str, list[str]]:
    """
    调用真实 Agent，拿到 (最终答案, 检索到的上下文列表)
    """
    final_answer = ""
    result = await agent.ainvoke({"messages": [{"role": "user", "content": user_input}]}, config={"recursion_limit": 12})
    messages = result.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            final_answer = msg.content
            break
    # contexts: list[str] = [m.content for m in messages if isinstance(m, ToolMessage) and m.content]
    contexts: list[str] = []
    for m in messages:
        if isinstance(m, ToolMessage) and m.content:
            contexts.extend([
                chunk.strip()
                for chunk in m.content.split("\n\n")
                if chunk.strip()
            ])

    return final_answer, contexts


async def evaluate_sample(
    agent,
    sample: EvalSample,
    llm,
    embeddings,
    metrics_config: Optional[dict] = None,
) -> dict:
    """
    对单条样本：跑 Agent -> 填 response/contexts -> 计算全部指标
    metrics_config: 控制启用哪些指标，默认全开
    """
    # 1. 端到端运行 Agent，填充运行时字段
    response, contexts = await _run_agent(agent, sample.user_input)
    sample.response = response
    sample.retrieved_contexts = contexts

    # 2. 初始化指标（每条新实例化，避免状态污染）
    cfg = metrics_config or {"faithfulness": True, "answer_relevancy": True,
                             "context_precision": True, "context_recall": True,
                             "answer_correctness": True}

    faithfulness = Faithfulness(llm=llm) if cfg.get("faithfulness") else None
    answer_relevancy = AnswerRelevancy(llm=llm, embeddings=embeddings) if cfg.get("answer_relevancy") else None
    context_precision = ContextPrecision(llm=llm) if cfg.get("context_precision") else None
    context_recall = ContextRecall(llm=llm) if cfg.get("context_recall") else None
    answer_correctness = AnswerCorrectness(llm=llm) if cfg.get("answer_correctness") else None

    scores: dict[str, float] = {"faithfulness": 0.0, "answer_relevancy": 0.0,
                                "context_precision": 0.0, "context_recall": 0.0,
                                "answer_correctness": 0.0}

    # 3. 逐指标打分
    if faithfulness:
        try:
            r: MetricResult = await faithfulness.ascore(
                user_input=sample.user_input,
                response=sample.response,
                retrieved_contexts=sample.retrieved_contexts,
            )
            scores["faithfulness"] = r.value
        except Exception as e:
            print(f"  [WARN] Faithfulness 失败: {e}")

    if answer_relevancy:
        try:
            r = await answer_relevancy.ascore(
                user_input=sample.user_input,
                response=sample.response,
            )
            scores["answer_relevancy"] = r.value
        except Exception as e:
            print(f"  [WARN] AnswerRelevancy 失败: {e}")

    # 以下三个指标需要有 reference
    if sample.reference:
        if context_precision:
            try:
                r = await context_precision.ascore(
                    user_input=sample.user_input,
                    retrieved_contexts=sample.retrieved_contexts,
                    reference=sample.reference,
                )
                scores["context_precision"] = r.value
            except Exception as e:
                print(f"  [WARN] ContextPrecision 失败: {e}")

        if context_recall:
            try:
                r = await context_recall.ascore(
                    user_input=sample.user_input,
                    retrieved_contexts=sample.retrieved_contexts,
                    reference=sample.reference,
                )
                scores["context_recall"] = r.value
            except Exception as e:
                print(f"  [WARN] ContextRecall 失败: {e}")

        if answer_correctness:
            try:
                r = await answer_correctness.ascore(
                    user_input=sample.user_input,
                    response=sample.response,
                    reference=sample.reference,
                )
                scores["answer_correctness"] = r.value
            except Exception as e:
                print(f"  [WARN] AnswerCorrectness 失败: {e}")

    return {
        "user_input": sample.user_input,
        "response": sample.response,
        "retrieved_contexts": sample.retrieved_contexts,
        **scores,
    }


async def run_evaluation(
    agent,
    dataset: list[EvalSample],
    metrics_config: Optional[dict] = None,
) -> list[dict]:
    """
    批量评估入口：遍历数据集，汇总每条样本的得分。
    """
    llm = get_judge_llm()
    embeddings = get_judge_embeddings()

    results = []
    for i, sample in enumerate(dataset, 1):
        print(f"[{i}/{len(dataset)}] 评估: {sample.user_input}")
        result = await evaluate_sample(agent, sample, llm, embeddings, metrics_config)
        results.append(result)
        print(f"    Faithfulness={result['faithfulness']:.3f}  "
              f"AnswerRelevancy={result['answer_relevancy']:.3f}  "
              f"ContextRecall={result['context_recall']:.3f}")

    print("\n===== 评估汇总 =====")
    n = len(results)
    if n == 0:
        return results
    avg = {k: sum(r[k] for r in results) / n for k in
           ["faithfulness", "answer_relevancy", "context_precision", "context_recall", "answer_correctness"]}
    for k, v in avg.items():
        print(f"  平均 {k}: {v:.4f}")
    return results