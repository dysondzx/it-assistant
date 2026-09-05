# Agentic RAG IT 助手

基于 **LangGraph + FastAPI** 的企业 IT 运维知识助手，整合三种检索能力：

- **Vector RAG**：IT 系统手册知识库（FAISS + BGE Embedding）
- **Text2SQL**：业务数据库精确查询（SQLite + SQL Agent）
- **GraphRAG**：知识图谱 N 跳遍历（错误码 -> 系统 -> 负责人 -> 联系方式）

支持 SSE 流式对话，并内置 RAGAS 评估模块。

## 1. 本地启动（开发模式）

### 1.1 后端

    cd backend
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env   # 填入 DEEPSEEK_API_KEY

    # 一次性初始化
    python -m app.data.init_db
    python -m app.data.build_faiss

    # 启动
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

验证：

    GET /health

### 1.2 前端

    cd frontend
    npm install
    npm run dev          # http://localhost:5173（前端通过 Vite proxy 把 /api 转发到 http://localhost:8000）

## 2. Docker 部署

### 2.1 开发 / 验证（不含 Nginx）

    cd backend
    cp .env.example .env
    docker compose up -d --build
    # 仅 backend，前端用 npm run dev + Vite proxy

### 2.2 生产（带 Nginx 反向代理）

    docker compose --profile prod up -d --build

    # 关掉
    docker compose --profile prod down
    docker compose --profile prod down -v   # 同时清数据卷

---

## 3. 前端构建与 Nginx 部署

### 3.1 构建 dist

    cd frontend
    npm install
    npm run build       # 产物在 frontend/dist/
    cd ..

## 4. RAGAS 评估

评估复用真实 Agent 端到端跑批，用 LLM 裁判打分

### 4.1 依赖锁定

    ragas==0.4.3
    openai==2.54.0
    instructor==1.16.0
    langchain-community==0.4.1   # 必须 0.4.1，0.4.2 冲突

### 4.2 CLI

    cd backend
    python -m app.evaluation.run_eval  # 全量
    python -m app.evaluation.run_eval --metrics faithfulness,answer_relevancy # 核心两项
    python -m app.evaluation.run_eval --limit 3  # 前 3 条

### 4.3 HTTP API

    # 健康检查
    GET /api/eval/health

    # 触发评估（异步，立即返回 task_id）
    POST /api/eval/run {"limit": 3, "metrics": ["faithfulness","answer_relevancy"]}

    # 轮询结果
    GET /api/eval/run/{task_id}
