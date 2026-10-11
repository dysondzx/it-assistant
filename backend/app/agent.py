from langchain.agents import create_agent

from app.core.llm import get_llm
from app.logging_setup import logger
from app.tools.graph_traverse import graph_traverse
from app.tools.manual_search import it_manual_search
from app.tools.nl2sql import sql_db_query


def build_agent(checkpointer=None):
    """构建整合了三个工具的 IT 助手 Agent

    checkpointer: 可选。生产环境传入 AsyncPostgresSaver（见 core/checkpoint.py），
    评估等无需持久化的场景传 None。
    """
    llm = get_llm(temperature=0)
    tools = [it_manual_search, sql_db_query, graph_traverse]

    agent = create_agent(
        model=llm,
        tools=tools,
        checkpointer=checkpointer,
        system_prompt="""
            你是一个企业 IT 助手，可以综合运用三种检索能力：

            1. it_manual_search：检索 IT 系统手册知识库，获取处理流程、配置说明等非结构化知识
            2. sql_db_query：查询业务数据库，获取精确统计数据、实时状态、聚合查询结果
            3. graph_traverse：在知识图谱上做 N 跳遍历，获取实体关系链（如错误码->影响系统->负责人->联系方式）

            回答时：
            - 明确区分来自不同来源的信息
            - 复杂问题可能需要组合多种工具
            - 注明信息来源
            - 如果所有工具都没有找到相关信息，明确说明"未在知识库中找到"
        """,
    ).with_config({"recursion_limit": 12})

    logger.info("IT 助手 Agent 构建完成（三引擎：Vector RAG + Text2SQL + GraphRAG）")
    return agent