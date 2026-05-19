"""
智问数据库 — VectorStore 测试
"""

import pytest


class TestVectorStore:
    """VectorStore 核心功能测试"""

    @pytest.fixture
    def vs(self, tmp_path):
        """创建临时向量库"""
        from backend.vector_store import VectorStore
        return VectorStore(str(tmp_path / "chromadb"))

    def test_initial_count_zero(self, vs):
        assert vs.count == 0

    def test_add_examples(self, vs):
        examples = {
            "test1": {"question": "有多少部电影？", "sql": "SELECT COUNT(*) FROM movies"},
            "test2": {"question": "评分最高的电影", "sql": "SELECT * FROM movies ORDER BY rating DESC LIMIT 1"},
        }
        vs.add_examples(examples)
        assert vs.count == 2

    def test_search_returns_results(self, vs):
        examples = {
            "q1": {"question": "电影总数", "sql": "SELECT COUNT(*) FROM movies"},
            "q2": {"question": "评分最高的电影", "sql": "SELECT * FROM movies ORDER BY rating DESC"},
            "q3": {"question": "导演列表", "sql": "SELECT DISTINCT director FROM movies"},
        }
        vs.add_examples(examples)

        results = vs.search("有多少电影", k=2)
        assert len(results) <= 2
        assert all("question" in r and "sql" in r for r in results)

    def test_search_empty_store(self, tmp_path):
        from backend.vector_store import VectorStore
        vs = VectorStore(str(tmp_path / "empty_chromadb"))
        results = vs.search("test")
        assert results == []

    def test_search_with_score(self, vs):
        examples = {
            "q1": {"question": "电影数量统计", "sql": "SELECT COUNT(*) FROM movies"},
        }
        vs.add_examples(examples)
        results = vs.search("电影数量", k=1)
        assert len(results) == 1
        assert "score" in results[0]
