from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain.agents import create_agent
from app.config import settings
from app.core.llm import get_llm
from app.logging_setup import logger

_sql_agent = None


def _get_sql_agent():
    global _sql_agent
    if _sql_agent is None:
        llm = get_llm(temperature=0)
        db = SQLDatabase.from_uri(
            f"sqlite:///{settings.SQLITE_PATH}",
            include_tables=["error_codes", "business_systems", "owners"],
        )
        toolkit = SQLDatabaseToolkit(db=db, llm=llm)
        _sql_agent = create_agent(
            model=llm,
            tools=toolkit.get_tools(),
            system_prompt="""
                你是一个 SQL 数据库交互智能体。给定一个输入问题，创建语法正确的 SQLite 查询并执行，然后查看结果返回答案。
                规则：
                1. 除非用户指定，否则查询最多返回 5 条结果。
                2. 绝对只能生成 SELECT 语句，禁止 INSERT/UPDATE/DELETE/DROP。
                3. 生成的 SQL 必须包含 LIMIT 子句，且不超过 200 行。
                4. 执行查询前必须用 sql_db_query_checker 双重检查。
                5. 如果执行查询出错，请重写查询并重试。
            """,
        ).with_config({"recursion_limit": 10})
        logger.info("SQL Agent 初始化完成")
    return _sql_agent


@tool
def sql_db_query(question: str) -> str:
    """
    查询业务数据库，获取精确统计数据、实时状态、聚合查询结果。
    当用户问"统计"、"总数"、"平均值"、"排名"、"最新状态"等需要精确计算的查询时调用。
    """
    agent = _get_sql_agent()
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    return result["messages"][-1].content