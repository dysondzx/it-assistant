from langchain_core.tools import tool
from app.data.kg import (
    get_or_build_kg,
    traverse_kg,
    serialize_subgraph,
)


@tool
def graph_traverse(entity: str, max_hops: int = 2) -> str:
    """在 IT 运维知识图谱上做 N 跳遍历，获取实体关系链
    当用户问需要沿实体关系链推理的问题时调用
    entity 参数为起始实体名
    """
    kg = get_or_build_kg()
    if entity not in kg:
        candidates = [n for n in kg.nodes if entity in n]
        if not candidates:
            return f"（知识图谱中未找到实体：{entity}）"
        entity = candidates[0]
    edges = traverse_kg(kg, entity, max_hops=max_hops)
    return serialize_subgraph(edges)