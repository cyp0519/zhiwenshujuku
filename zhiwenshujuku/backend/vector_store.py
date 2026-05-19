"""
智问数据库 — ChromaDB 向量存储（RAG 检索增强）
"""

from pathlib import Path
from loguru import logger
import chromadb
from chromadb.config import Settings


class VectorStore:
    """ChromaDB 向量存储，用于 SQL 样例检索"""
    
    def __init__(self, persist_dir: str | Path):
        self.persist_dir = str(persist_dir)
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # 获取或创建集合
        try:
            self.collection = self.client.get_collection("sql_examples")
            logger.info(f"✅ 加载现有集合，包含 {self.collection.count()} 条记录")
        except Exception:
            self.collection = self.client.create_collection("sql_examples")
            logger.info("✅ 创建新集合: sql_examples")
    
    def add_examples(self, examples: dict[str, dict]):
        """添加 SQL 样例到向量库"""
        ids = []
        documents = []
        metadatas = []
        
        for key, example in examples.items():
            ids.append(key)
            # 将问题+SQL组合成检索文本
            documents.append(f"问题: {example['question']}\nSQL: {example['sql']}")
            metadatas.append({
                "question": example["question"],
                "sql": example["sql"],
                "title": key
            })
        
        if documents:
            self.collection.add(
                documents=documents,
                ids=ids,
                metadatas=metadatas
            )
            logger.info(f"✅ 已添加 {len(documents)} 条 SQL 样例到向量库")
    
    def search(self, query: str, k: int = 4) -> list[dict]:
        """搜索相似 SQL 样例"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=min(k, self.collection.count())
            )
            
            examples = []
            if results["metadatas"] and results["metadatas"][0]:
                for i, metadata in enumerate(results["metadatas"][0]):
                    examples.append({
                        "question": metadata["question"],
                        "sql": metadata["sql"],
                        "score": results["distances"][0][i] if results.get("distances") else 0,
                    })
            return examples
        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return []
    
    @property
    def count(self) -> int:
        return self.collection.count()
