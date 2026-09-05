"""
定义评估样本的 schema，并提供默认的测试集。

评估样本字段：
- user_input: 用户问题
- reference: 人工标注的标准答案（金标准，用于 Context Recall / Answer Correctness）
- retrieved_contexts: 本次检索到的上下文片段（运行时填充）
- response: RAG 系统生成的答案（运行时填充）

说明：retrieved_contexts / response 在真实跑批时由系统填入；
      reference 是离线标注、必须预先准备好，否则依赖它的指标无法计算。
"""

from pydantic import BaseModel


class EvalSample(BaseModel):
    """单条评估样本（对应 Dataset 中的一行）"""

    user_input: str
    reference: str = ""
    retrieved_contexts: list[str] = []
    response: str = ""


# 默认黄金测试集（示例用，实际应替换为真实业务问题 + 人工标注答案）
DEFAULT_DATASET: list[EvalSample] = [
    EvalSample(
        user_input="ERR-4502 的处理流程是什么？",
        reference=(
            "1. 检查认证中心服务状态；"
            "2. 查看认证日志 /var/log/auth-service.log；"
            "3. 确认数据库连接池未耗尽；"
            "4. 执行 systemctl restart auth-service 重启；"
            "5. 调用 /health 接口验证返回 200。"
        ),
    ),
    EvalSample(
        user_input="ERR-4502 影响了哪些业务系统？这些系统的负责人联系方式是什么？",
        reference=(
            "ERR-4502 影响了核心交易系统和用户认证中心。"
            "核心交易系统负责人是张三，联系方式 13800000001，邮箱 zhangsan@corp.com；"
            "用户认证中心负责人是李四，联系方式 13800000002，邮箱 lisi@corp.com。"
        ),
    ),
    EvalSample(
        user_input="上个月华东区发生 ERR-4502 的次数统计",
        reference="可通过业务数据库统计上个月华东区 ERR-4502 的发生次数（精确统计数据）。",
    ),
    EvalSample(
        user_input="ERR-3301 数据库连接池耗尽如何处理？",
        reference=(
            "1. 查看当前连接数；"
            "2. 检查慢查询日志定位长事务；"
            "3. 临时扩容 SET GLOBAL max_connections = 500；"
            "4. 永久生效需修改 my.cnf 并重启；"
            "5. 根本治理为增加连接池上限并优化慢 SQL。"
        ),
    ),
    EvalSample(
        user_input="ERR-2207 缓存击穿的解决方法是？",
        reference=(
            "1. 确认 Redis 命中率是否骤降；"
            "2. 对热点 key 启用互斥锁重建缓存；"
            "3. 预热缓存提前加载热点数据；"
            "4. 设置合理 TTL 错开过期时间；"
            "5. 长期方案为本地缓存 + 分布式锁。"
        ),
    ),
]