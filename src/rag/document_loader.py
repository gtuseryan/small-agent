"""文档加载器 —— 支持多种文件格式的解析和分块"""

import os
import re
from typing import Iterator


class DocumentLoader:
    """加载并分块处理各类文档文件"""

    SUPPORTED_EXTS = {".md", ".txt", ".py", ".java", ".go", ".js", ".ts", ".yaml", ".yml", ".json", ".xml"}

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def load_file(self, file_path: str) -> list[dict]:
        """加载单个文件并返回分块列表"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.SUPPORTED_EXTS:
            return []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return []

        if not content.strip():
            return []

        chunks = self._split_text(content)
        return [
            {
                "content": chunk,
                "source": file_path,
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            for i, chunk in enumerate(chunks)
        ]

    def load_directory(self, dir_path: str) -> list[dict]:
        """递归加载目录下所有支持的文件"""
        all_chunks = []
        for root, _, files in os.walk(dir_path):
            # 跳过隐藏目录和常见非文档目录
            if any(skip in root for skip in ["node_modules", "__pycache__", ".git", "venv", ".venv", "dist", "build"]):
                continue
            for fname in files:
                if fname.startswith("."):
                    continue
                fpath = os.path.join(root, fname)
                chunks = self.load_file(fpath)
                all_chunks.extend(chunks)
        return all_chunks

    def load_text(self, text: str, source: str = "inline") -> list[dict]:
        """直接加载文本字符串"""
        if not text.strip():
            return []
        chunks = self._split_text(text)
        return [
            {
                "content": chunk,
                "source": source,
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            for i, chunk in enumerate(chunks)
        ]

    def _split_text(self, text: str) -> list[str]:
        """按段落和句子边界智能分块"""
        # 先按双换行分段
        paragraphs = re.split(r"\n\s*\n", text)
        chunks = []
        current = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(current) + len(para) <= self.chunk_size:
                current += para + "\n\n"
            else:
                if current.strip():
                    chunks.append(current.strip())
                current = para + "\n\n"
        if current.strip():
            chunks.append(current.strip())

        # 如果没有自然段落，按字符长度切分
        if not chunks:
            for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
                chunk = text[i : i + self.chunk_size]
                if chunk.strip():
                    chunks.append(chunk.strip())
        return chunks
