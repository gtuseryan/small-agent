"""向量存储 —— 基于 ChromaDB 的轻量级向量数据库"""

import os
import hashlib
import json
from openai import OpenAI


class VectorStore:
    """轻量级向量存储，支持 ChromaDB 和基于 JSON 的简化本地存储"""

    def __init__(
        self,
        persist_dir: str = "./data/chroma_db",
        collection_name: str = "midev_knowledge",
        embedding_client: OpenAI = None,
        embedding_model: str = "text-embedding-3-small",
    ):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.embedding_client = embedding_client
        self.embedding_model = embedding_model
        self._collection = None
        self._use_chromadb = False

        # 尝试初始化 ChromaDB
        try:
            import chromadb
            os.makedirs(persist_dir, exist_ok=True)
            self._client = chromadb.PersistentClient(path=persist_dir)
            self._collection = self._client.get_or_create_collection(name=collection_name)
            self._use_chromadb = True
        except (ImportError, Exception):
            # 降级为简化 JSON 文件存储
            self._json_path = os.path.join(persist_dir, f"{collection_name}.json")
            self._documents: list[dict] = self._load_json()

    def add(self, chunks: list[dict]) -> int:
        """添加文档块到向量存储"""
        if not chunks:
            return 0

        if self._use_chromadb:
            return self._add_chromadb(chunks)
        else:
            return self._add_json(chunks)

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[dict]:
        """根据查询向量检索最相似的文档"""
        if self._use_chromadb:
            return self._search_chromadb(query_embedding, top_k)
        else:
            return self._search_json(query_embedding, top_k)

    def embed(self, text: str) -> list[float]:
        """将文本转为向量嵌入"""
        if self.embedding_client:
            resp = self.embedding_client.embeddings.create(
                model=self.embedding_model, input=text
            )
            return resp.data[0].embedding
        else:
            # 简易哈希模拟（无 API 时的降级方案）
            h = hashlib.sha256(text.encode()).digest()
            return [float(b) / 255.0 for b in h[:128]]

    def count(self) -> int:
        """返回已存储的文档块数量"""
        if self._use_chromadb:
            return self._collection.count()
        return len(self._documents)

    def _add_chromadb(self, chunks: list[dict]) -> int:
        ids = []
        docs = []
        metadatas = []
        embeddings = []

        for chunk in chunks:
            chunk_id = hashlib.md5(
                f"{chunk['source']}:{chunk['chunk_index']}".encode()
            ).hexdigest()
            ids.append(chunk_id)
            docs.append(chunk["content"])
            metadatas.append({
                "source": chunk["source"],
                "chunk_index": chunk["chunk_index"],
                "total_chunks": chunk.get("total_chunks", 0),
            })
            embeddings.append(self.embed(chunk["content"]))

        self._collection.upsert(ids=ids, documents=docs, metadatas=metadatas, embeddings=embeddings)
        return len(chunks)

    def _search_chromadb(self, query_embedding: list[float], top_k: int) -> list[dict]:
        results = self._collection.query(query_embeddings=[query_embedding], n_results=top_k)
        return [
            {
                "content": doc,
                "source": meta.get("source", "unknown"),
                "score": f"{1 - dist:.4f}" if (dist := results.get("distances", [[]])[0][i]) is not None else "N/A",
            }
            for i, (doc, meta) in enumerate(
                zip(results.get("documents", [[]])[0], results.get("metadatas", [[]])[0])
            )
        ]

    def _load_json(self) -> list[dict]:
        if os.path.exists(self._json_path):
            try:
                with open(self._json_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_json(self):
        os.makedirs(os.path.dirname(self._json_path), exist_ok=True)
        with open(self._json_path, "w", encoding="utf-8") as f:
            json.dump(self._documents, f, ensure_ascii=False, indent=2)

    def _add_json(self, chunks: list[dict]) -> int:
        for chunk in chunks:
            chunk_id = hashlib.md5(
                f"{chunk['source']}:{chunk['chunk_index']}".encode()
            ).hexdigest()
            existing = [d for d in self._documents if d.get("id") == chunk_id]
            if not existing:
                self._documents.append({
                    "id": chunk_id,
                    "content": chunk["content"],
                    "source": chunk["source"],
                    "embedding": self.embed(chunk["content"]),
                })
        self._save_json()
        return len(chunks)

    def _search_json(self, query_embedding: list[float], top_k: int) -> list[dict]:
        def cosine_sim(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = sum(x ** 2 for x in a) ** 0.5
            norm_b = sum(x ** 2 for x in b) ** 0.5
            return dot / (norm_a * norm_b) if norm_a and norm_b else 0

        scored = [
            {
                "content": d["content"][:500],
                "source": d["source"],
                "score": f"{cosine_sim(query_embedding, d['embedding']):.4f}",
            }
            for d in self._documents
        ]
        scored.sort(key=lambda x: float(x["score"]), reverse=True)
        return scored[:top_k]
