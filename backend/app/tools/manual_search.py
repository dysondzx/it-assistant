from langchain_core.tools import tool
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from app.config import settings

_embeddings = None
_vector_store = None


def _get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings


def _get_vector_store():
    global _vector_store
    if _vector_store is None:
        try:
            _vector_store = FAISS.load_local(
                settings.FAISS_INDEX_PATH,
                _get_embeddings(),
                allow_dangerous_deserialization=True,
            )
        except Exception:
            return None
    return _vector_store


@tool
def it_manual_search(query: str) -> str:
    """检索 IT 系统手册知识库，获取错误的处理流程、配置说明等非结构化知识
    当用户问"处理流程"、"配置说明"、"错误描述"等非结构化知识时调用此工具
    """
    vs = _get_vector_store()
    if vs is None:
        return "（IT 手册向量库尚未构建，请先运行 python -m app.data.build_faiss）"
    docs = vs.similarity_search(query, k=3)
    if not docs:
        return "（知识库中未检索到相关内容）"
    return "\n\n".join(d.page_content for d in docs)