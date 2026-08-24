import networkx as nx
import pickle
import os
from app.config import settings
from openai import OpenAI
import json

def build_knowledge_graph() -> nx.DiGraph:
    sys_prompt = """
        你是一个知识图谱抽取器，从给定文本中抽取实体-实体类型-关系-实体-实体类型五元组。
        只输出JSON数组，不要MarkDown代码块，不要额外说明。
        每个元素的格式：{"head": "实体1", "head_type": "类型1", "relation": "关系", "tail": "实体2", "tail_type": "类型2"}
        类型只能是：Error, System, Owner, Symptom, Solution, Contact, Email, Region
        关系只能是：IMPACTS, OWNS, HAS_SYMPTOM, RESOLVED_BY, DEPLOYED_IN, CONTACT, RESPONSIBLE_FOR, EMAIL
        要求：
        1、输出的必须是合法的JSON数组
        2、对同一实体的不同表述应使用统一的完整标识符
        3、只输出JSON数组，不要任何额外说明
    """
    client = OpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
    )
    with open("../docs/billing.md", 'r', encoding='utf-8') as f:
        content = f.read()

    response = client.chat.completions.create(
        model=settings.DEEPSEEK_MODEL,
        messages=[{
            "role": "system", "content": sys_prompt
        }, {
            "role": "user", "content": f"抽取以下文本的五元组：\n{content}"
        }],
        max_tokens=2000,
        response_format={"type": "json_object"},
        extra_body={"thinking": {"type": "disabled"}},
        temperature=0
    )

    raw = response.choices[0].message.content
    triples = json.loads(raw) if raw and raw.strip() else []
    kg = nx.DiGraph()
    for triple in triples:
        kg.add_node(triple["head"], type=triple["head_type"])
        kg.add_node(triple["tail"], type=triple["tail_type"])
        kg.add_edge(triple["head"], triple["tail"], relation=triple["relation"])
    return kg

def traverse_kg(graph: nx.DiGraph, start_entity: str, max_hops: int = 2,
                filter_node_type: str = None):
    visited_edges = []
    current_layer = {start_entity}
    visited_nodes = {start_entity}
    for _ in range(max_hops):
        next_layer = set()
        for node in current_layer:
            if node not in graph:
                continue
            for successor in graph.successors(node):
                if filter_node_type and graph.nodes[successor].get("type") != filter_node_type:
                    continue
                edge_rel = graph[node][successor]["relation"]
                visited_edges.append((node, edge_rel, successor))
                if successor not in visited_nodes:
                    next_layer.add(successor)
                    visited_nodes.add(successor)
        current_layer = next_layer
        if not current_layer:
            break
    return visited_edges


def serialize_subgraph(edges) -> str:
    if not edges:
        return "知识图谱中未找到相关实体关系"
    return "\n".join(f"- {s} --{r}--> {o}" for s, r, o in edges)


def get_or_build_kg() -> nx.DiGraph:
    if os.path.exists(settings.KG_PATH):
        with open(settings.KG_PATH, "rb") as f:
            return pickle.load(f)
    kg = build_knowledge_graph()
    with open(settings.KG_PATH, "wb") as f:
        pickle.dump(kg, f)
    return kg