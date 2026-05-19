"""
智问数据库 — DatabaseManager 测试
"""

import pytest
from backend.database import DatabaseManager


class TestDatabaseManager:
    """DatabaseManager 核心功能测试"""

    def test_get_connection(self, db_manager):
        conn = db_manager.get_connection()
        assert conn is not None
        conn.close()

    def test_execute_query_select(self, db_manager):
        result = db_manager.execute_query("SELECT COUNT(*) as cnt FROM movies")
        assert result["success"] is True
        assert result["row_count"] == 1
        assert result["data"][0]["cnt"] == 2

    def test_execute_query_with_columns(self, db_manager):
        result = db_manager.execute_query("SELECT title, rating FROM movies LIMIT 1")
        assert result["success"] is True
        assert "title" in result["columns"]
        assert "rating" in result["columns"]

    def test_execute_query_invalid_sql(self, db_manager):
        result = db_manager.execute_query("SELECT * FROM nonexistent_table")
        assert result["success"] is False
        assert result["error"] is not None

    def test_execute_query_elapsed_time(self, db_manager):
        result = db_manager.execute_query("SELECT 1")
        assert result["elapsed"] > 0

    def test_get_schema_dict(self, db_manager):
        schema = db_manager.get_schema_dict()
        assert "movies" in schema
        assert "users" in schema
        assert "reviews" in schema
        assert "query_history" in schema

    def test_get_schema_dict_columns(self, db_manager):
        schema = db_manager.get_schema_dict()
        movie_cols = [c["name"] for c in schema["movies"]]
        assert "id" in movie_cols
        assert "title" in movie_cols
        assert "rating" in movie_cols

    def test_format_schema_context(self, db_manager):
        context = db_manager.format_schema_context()
        assert "movies" in context
        assert "电影信息表" in context
        assert "title" in context

    def test_save_and_get_history(self, db_manager):
        db_manager.save_history(
            session_id="test-session",
            question="测试问题",
            sql_generated="SELECT 1",
            sql_executed="SELECT 1",
            status="success",
            summary="1 row",
        )
        history = db_manager.get_history(session_id="test-session")
        assert len(history) >= 1
        assert history[0]["question"] == "测试问题"

    def test_get_history_limit(self, db_manager):
        for i in range(5):
            db_manager.save_history(
                session_id="limit-test",
                question=f"问题{i}",
                sql_generated="SELECT 1",
                sql_executed="SELECT 1",
                status="success",
                summary="1 row",
            )
        history = db_manager.get_history(session_id="limit-test", limit=3)
        assert len(history) == 3


class TestDatabaseSafety:
    """SQL 安全性相关测试"""

    def test_unsafe_keywords_defined(self):
        from backend.config import UNSAFE_SQL_KEYWORDS
        assert "drop" in UNSAFE_SQL_KEYWORDS
        assert "delete" in UNSAFE_SQL_KEYWORDS
        assert "insert" in UNSAFE_SQL_KEYWORDS

    def test_select_is_safe(self, db_manager):
        result = db_manager.execute_query("SELECT * FROM movies")
        assert result["success"] is True
