# ========== 阶段 1：构建依赖 ==========
FROM python:3.11-slim AS builder

WORKDIR /build

# 安装依赖到本地目录，便于多阶段复制
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ========== 阶段 2：运行镜像（最小化）==========
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 从构建阶段复制已安装的依赖
COPY --from=builder /install /usr/local

# 复制应用代码
COPY app/ ./app/

# 创建数据目录（SQLite / FAISS / 知识图谱持久化）
RUN mkdir -p /app/data

EXPOSE 8000

# 启动：先初始化数据，再起服务
# 数据已通过卷挂载持久化，容器重建不丢
CMD ["sh", "-c", "python -m app.data.init_db && python -m app.data.build_faiss && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"]