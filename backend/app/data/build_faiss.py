import sys
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from app.config import settings
from app.logging_setup import logger

# 多租户隔离用的租户标识。
# 真实项目中由上游网关解析 Token 后统一透传，脱敏环境先固定为 default_tenant。
# 必须写进每个 Document 块的 metadata，否则检索侧
# similarity_search(..., filter={"tenant_id": "default_tenant"}) 会把所有候选过滤掉。
TENANT_ID = "default_tenant"

# 知识库文档目录（app/docs），与 kg.py 抽取图谱用的是同一批 Markdown 文件
DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"

# 先按 Markdown 标题层级切
HEADERS_TO_SPLIT_ON = [("#", "h1"), ("##", "h2"), ("###", "h3")]


def load_and_split(
    docs_dir: Path = DOCS_DIR,
    tenant_id: str = TENANT_ID,
) -> list[Document]:
    """加载 docs 目录下的 Markdown 手册，切分成可入库的文档块。
    两级切分：
    1) MarkdownHeaderTextSplitter：按 #/##/### 切成语义小节，标题保留在正文里；
    2) RecursiveCharacterTextSplitter：把小节内部再按段落/句子切成 chunk_size 上限的块。
    """
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS_TO_SPLIT_ON,
        strip_headers=False,
    )
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=60,
        separators=["\n\n", "\n", "。", "；", ""],
        keep_separator="end",
    )

    files = sorted(docs_dir.glob("*.md"))
    if not files:
        raise FileNotFoundError(f"未找到 Markdown 知识库文档：{docs_dir}")

    chunks: list[Document] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        sections = header_splitter.split_text(text)
        doc_chunks = text_splitter.split_documents(sections)
        for index, chunk in enumerate(doc_chunks):
            chunk.metadata.update(
                {
                    "tenant_id": tenant_id,
                    "source": path.name,
                    "chunk_id": index,
                }
            )
            chunks.append(chunk)
        logger.info(f"已切分 {path.name}：{len(sections)} 个小节 -> {len(doc_chunks)} 个文档块")

    return chunks


def build_faiss_index(force: bool = False) -> None:
    index_file = Path(settings.FAISS_INDEX_PATH) / "index.faiss"
    if index_file.exists() and not force:
        logger.info(
            f"FAISS 索引已存在，跳过构建：{settings.FAISS_INDEX_PATH}"
        )
        return

    chunks = load_and_split()
    embeddings = HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    vector_store = FAISS.from_documents(chunks, embeddings)
    vector_store.save_local(settings.FAISS_INDEX_PATH)
    logger.info(
        f"FAISS 索引构建完成：{len(chunks)} 个文档块 -> {settings.FAISS_INDEX_PATH}"
    )


if __name__ == "__main__":
    build_faiss_index()
