"""
评估命令行入口
"""

import argparse
import asyncio

from app.agent import build_agent
from app.evaluation.dataset import DEFAULT_DATASET
from app.evaluation.runner import run_evaluation


def parse_args():
    parser = argparse.ArgumentParser(description="RAGAS 评估工具")
    parser.add_argument(
        "--metrics",
        type=str,
        default="faithfulness,answer_relevancy,context_precision,context_recall,answer_correctness",
        help="启用的指标，逗号分隔",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="只评估前 N 条样本（0 表示全部）",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    enabled = {m.strip() for m in args.metrics.split(",") if m.strip()}
    metrics_config = {
        "faithfulness": "faithfulness" in enabled,
        "answer_relevancy": "answer_relevancy" in enabled,
        "context_precision": "context_precision" in enabled,
        "context_recall": "context_recall" in enabled,
        "answer_correctness": "answer_correctness" in enabled,
    }

    dataset = DEFAULT_DATASET
    if args.limit > 0:
        dataset = dataset[: args.limit]

    print(f"待评估样本数: {len(dataset)}")
    print(f"启用指标: {[k for k, v in metrics_config.items() if v]}\n")

    agent = build_agent()
    results = asyncio.run(run_evaluation(agent, dataset, metrics_config))
    print(f"\n完成，共 {len(results)} 条结果。")


if __name__ == "__main__":
    main()