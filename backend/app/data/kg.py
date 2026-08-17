import networkx as nx
import pickle
import os
from app.config import settings


def build_knowledge_graph() -> nx.DiGraph:
    kg = nx.DiGraph()
    triples = [
        ("ERR-4502", "IMPACTS", "核心交易系统", "Error", "System"),
        ("ERR-4502", "IMPACTS", "用户认证中心", "Error", "System"),
        ("ERR-3301", "IMPACTS", "核心交易系统", "Error", "System"),
        ("ERR-2207", "IMPACTS", "商品目录服务", "Error", "System"),
        ("核心交易系统", "OWNS", "张三", "System", "Owner"),
        ("用户认证中心", "OWNS", "李四", "System", "Owner"),
        ("商品目录服务", "OWNS", "张三", "System", "Owner"),
        ("张三", "CONTACT", "13800000001", "Owner", "Contact"),
        ("李四", "CONTACT", "13800000002", "Owner", "Contact"),
        ("张三", "EMAIL", "zhangsan@corp.com", "Owner", "Email"),
        ("李四", "EMAIL", "lisi@corp.com", "Owner", "Email"),
        ("ERR-4502", "HAS_SYMPTOM", "用户无法登录", "Error", "Symptom"),
        ("ERR-3301", "HAS_SYMPTOM", "核心交易中断", "Error", "Symptom"),
        ("ERR-2207", "HAS_SYMPTOM", "响应延迟升高", "Error", "Symptom"),
        ("ERR-4502", "RESOLVED_BY", "重启认证服务", "Error", "Solution"),
        ("ERR-3301", "RESOLVED_BY", "扩容数据库连接池", "Error", "Solution"),
        ("ERR-2207", "RESOLVED_BY", "预热缓存", "Error", "Solution"),
        ("核心交易系统", "DEPLOYED_IN", "华东", "System", "Region"),
        ("用户认证中心", "DEPLOYED_IN", "华北", "System", "Region"),
        ("商品目录服务", "DEPLOYED_IN", "华东", "System", "Region"),
    ]
    for subj, rel, obj, subj_type, obj_type in triples:
        kg.add_node(subj, type=subj_type)
        kg.add_node(obj, type=obj_type)
        kg.add_edge(subj, obj, relation=rel)
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