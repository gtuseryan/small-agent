"""检索器 —— 封装 RAG 索引和查询的对外接口"""

from .document_loader import DocumentLoader
from .vector_store import VectorStore


class Retriever:
    """RAG 检索器，提供文档索引和查询的统一入口"""

    def __init__(self, vector_store: VectorStore, chunk_size: int = 500, chunk_overlap: int = 50):
        self.store = vector_store
        self.loader = DocumentLoader(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def index(self, path: str) -> int:
        """索引文件或目录，返回索引的文档块数量"""
        import os
        if os.path.isfile(path):
            chunks = self.loader.load_file(path)
        elif os.path.isdir(path):
            chunks = self.loader.load_directory(path)
        else:
            raise FileNotFoundError(f"路径不存在: {path}")

        if not chunks:
            return 0

        return self.store.add(chunks)

    def index_text(self, text: str, source: str = "inline") -> int:
        """索引文本"""
        chunks = self.loader.load_text(text, source)
        return self.store.add(chunks)

    def query(self, query: str, top_k: int = 5) -> list[dict]:
        """检索与查询最相关的文档片段"""
        embedding = self.store.embed(query)
        return self.store.search(embedding, top_k=top_k)

    @property
    def document_count(self) -> int:
        return self.store.count()
