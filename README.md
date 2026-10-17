# Agentic RAG IT 助手

基于 **LangGraph + FastAPI** 的企业 IT 运维知识助手，整合三种检索能力：

- **Vector RAG**：IT 系统手册知识库（FAISS + BGE Embedding）
- **Text2SQL**：业务数据库精确查询（SQLite + SQL Agent）
- **GraphRAG**：知识图谱 N 跳遍历（如：错误码 -> 系统 -> 负责人 -> 联系方式）

支持 SSE 流式对话，并内置 RAGAS 评估模块。

会话记忆由 **LangGraph `AsyncPostgresSaver`** 持久化到 Postgres：服务重启不丢，多轮上下文按 `thread_id` 隔离。

---

## 1. 配置

首次部署需要两个 `.env`，作用不同：

`.env`（项目根目录）： 供 compose 做 `${...}` 变量插值，如 `POSTGRES_PASSWORD`、`POSTGRES_DB` 
`backend/.env` ： 应用自身配置，如 `DEEPSEEK_API_KEY`、`EMBEDDING_MODEL`，经 compose 的 `env_file` 注入

```bash
cp .env.example .env                      # 修改 POSTGRES_PASSWORD
cp backend/.env.example backend/.env      # 填写 DEEPSEEK_API_KEY
```

说明：

- `backend/.env` 必须存在，否则 compose 的 `env_file` 会直接报错。
- `backend/.env.example` 中的 `POSTGRES_URI` 指向 `localhost:5432`，Docker 模式下会被 compose 的
  `environment` 覆盖为 `postgres:5432`，**无需修改**；

---

## 2. 生产部署（nginx + backend + postgres）

三个容器，统一从 80 端口访问：

| 服务 | 作用 | 对外端口 |
| --- | --- | --- |
| `postgres` | 会话记忆持久化（`AsyncPostgresSaver`） | 仅内网 |
| `backend` | FastAPI（`uvicorn`，2 worker） | 仅内网（`expose 8000`） |
| `nginx` | 前端静态资源 + `/api/` 反向代理（SSE 不缓冲） | `80` |

`nginx` 由 compose 的 `prod` profile 控制：**不带** `--profile prod` 时只启动 `postgres` + `backend`。

### 步骤 1：准备配置

见第 1 节。

### 步骤 2：构建前端产物

nginx 直接挂载宿主机的 `frontend/dist`，必须先构建：

```bash
cd frontend
npm install
npm run build        # 产物输出到 frontend/dist/
cd ..
```

### 步骤 3：启动

```bash
docker compose --profile prod up -d --build
docker compose restart nginx
```

> 每次重建 `backend` 后都要执行 `docker compose restart nginx`：`nginx.conf` 用
> `upstream rag_backend { server backend:8000; }` 反代，且仅在加载配置时解析一次 DNS；
> backend 容器重建后 IP 变化，不重启 nginx 会持续返回 502。

### 步骤 4：验证

```bash
docker compose ps                  # 三个容器 Up；backend 稍后变为 (healthy)
curl -i http://localhost/health    # 期望 200 {"status":"ok"}
# 浏览器访问 http://localhost
```

### 步骤 5：数据初始化（由容器自动完成）

backend 容器启动时按顺序执行以下三步（见 `backend/Dockerfile` 的 `CMD`）：

```
python -m app.data.init_db        # 建立 SQLite 表并写入示例数据
python -m app.data.build_faiss    # 构建 FAISS 向量索引
uvicorn app.main:app ...          # 启动 API 服务
```

- 前两条初始化命令**幂等**，容器重启会重跑，不会出错。
- 首次启动需要完成数据库与向量索引初始化，耗时较久。
- **不要在宿主机上重复执行这两条**：`backend/.env` 中 `SQLITE_PATH`、`FAISS_INDEX_PATH`
  是相对路径，会在 `backend/` 下生成一套与容器内 `/data` 卷无关的数据。

---

## 3. 开发验证部署（只起 postgres + backend）

```bash
docker compose up -d --build
```

> backend 仅 `expose 8000`，未映射到宿主机，宿主机无法直连 `localhost:8000`。
> 若要与前端 `npm run dev` 联调，请使用第 5 节的本地启动方式，或在 `docker-compose.yml`
> 的 backend 服务下加 `ports: ["8000:8000"]`。

---

## 4. 本地启动（不用 Docker 运行后端）

前置：需要一个可用的 Postgres。本地没有可先起容器（需要第 2 节的根目录 `.env`）：

```bash
docker compose up -d postgres
```

### 4.1 后端

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # 填写 DEEPSEEK_API_KEY，并把 POSTGRES_URI 改成实际地址

# 一次性初始化（仅本地裸跑模式需要手动执行，见第 6 节对照表）
python -m app.data.init_db
python -m app.data.build_faiss

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

验证：`curl http://localhost:8000/health`

### 4.2 前端

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

Vite 已配置 proxy，把 `/api` 转发到 `http://localhost:8000`。

---

## 5. 启动方式对照

| 模式 | 命令 | 访问入口 | `init_db` / `build_faiss` 由谁执行 |
| --- | --- | --- | --- |
| 本地裸跑 | `uvicorn app.main:app ...` | `:8000` | 手动执行一次 |
| Docker 验证 | `docker compose up -d --build` | 仅容器网络 | backend 容器自动执行 |
| Docker 生产 | `docker compose --profile prod up -d --build` | `:80` | backend 容器自动执行 |

---

## 6. 运维

```bash
docker compose --profile prod logs -f backend    # 查看后端日志
docker compose --profile prod restart nginx      # 重建 backend 后执行
docker compose exec nginx nginx -t               # 校验 nginx 配置
docker compose --profile prod down               # 停止，保留数据
docker compose --profile prod down -v            # 停止并删除数据卷
```

---

## 7. RAGAS 评估

评估复用真实 Agent 端到端跑批，用 LLM 裁判打分。

### 7.1 依赖锁定

```
ragas==0.4.3
openai==2.54.0
instructor==1.16.0
langchain-community==0.4.1   # 必须 0.4.1，0.4.2 冲突
```

### 7.2 CLI

```bash
cd backend
python -m app.evaluation.run_eval                                         # 全量
python -m app.evaluation.run_eval --metrics faithfulness,answer_relevancy # 核心两项
python -m app.evaluation.run_eval --limit 3                               # 前 3 条
```

### 7.3 HTTP API

```bash
# 健康检查 + 数据集规模
curl http://localhost/api/eval/health

# 触发评估（后台任务，立即返回 task_id）
curl -X POST http://localhost/api/eval/run \
     -H "Content-Type: application/json" \
     -d '{"limit": 3, "metrics": ["faithfulness","answer_relevancy"]}'

# 轮询进度与结果
curl http://localhost/api/eval/run/{task_id}
```

> 上面的地址以生产模式（经 nginx 的 80 端口）为例。本地裸跑时改为
> `http://localhost:8000/api/eval/...`。

### 7.4 指标与 reference

| 指标 | 含义 | 需 reference |
| --- | --- | :---: |
| Faithfulness | 答案是否被上下文支持 | 否 |
| AnswerRelevancy | 答案是否解决用户问题 | 否 |
| ContextPrecision | 召回上下文精确度 | 是 |
| ContextRecall | 召回上下文召回率 | 是 |
| AnswerCorrectness | 与标准答案一致性 | 是 |

不提供 reference 时，依赖它的三个指标自动跳过。
