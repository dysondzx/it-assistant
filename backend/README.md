# 快速开始
## 安装依赖
pip install -r requirements.txt

## 配置环境变量
cp .env.example .env

## 一次性初始化 SQLite（建表 + 种子数据）
python -m app.data.init_db

## 构建 FAISS 索引（IT 手册向量库）
python -m app.data.build_faiss

## 启动服务
uvicorn app.main:app --reload