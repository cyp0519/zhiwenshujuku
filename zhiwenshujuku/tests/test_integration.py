"""
智问数据库 — 集成测试

测试完整的 NL → SQL → 执行 流程
"""

import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage

from backend.state import State
from backend.nodes import (
    intent_classifier,
    sql_safety_validator,
    sql_syntax_validator,
    route_intent,
    check_sql_generation,
    check_sql_safety,
    check_sql_syntax,
)


class TestIntentClassifier:
    """测试意图分类"""

    def test_sql_intent(self):
        """数据查询应分类为 sql"""
        state = State(
            messages=[HumanMessage(content="有多少部电影？")],
            user_query="有多少部电影？",
        )
        # 模拟 LLM 返回
        with patch("backend.nodes._get_llm") as mock_llm:
            mock_response = MagicMock()
            mock_response.content = "sql"
            mock_llm.return_value.invoke.return_value = mock_response

            result = intent_classifier(state)
            assert result["user_intent"] == "sql"

    def test_chat_intent(self):
        """闲聊应分类为 chat"""
        state = State(
            messages=[HumanMessage(content="你好")],
            user_query="你好",
        )
        with patch("backend.nodes._get_llm") as mock_llm:
            mock_response = MagicMock()
            mock_response.content = "chat"
            mock_llm.return_value.invoke.return_value = mock_response

            result = intent_classifier(state)
            assert result["user_intent"] == "chat"


class TestSQLSafetyValidator:
    """测试 SQL 安全校验"""

    def test_safe_select(self):
        """安全的 SELECT 通过"""
        state = State(
            messages=[],
            sql_query="SELECT * FROM movies WHERE rating > 8",
        )
        result = sql_safety_validator(state)
        assert result["sql_safety_status"] == "safe"

    def test_unsafe_drop(self):
        """DROP 语句被拦截"""
        state = State(
            messages=[],
            sql_query="DROP TABLE movies",
        )
        result = sql_safety_validator(state)
        assert result["sql_safety_status"] == "unsafe"

    def test_unsafe_delete(self):
        """DELETE 语句被拦截"""
        state = State(
            messages=[],
            sql_query="DELETE FROM movies WHERE id = 1",
        )
        result = sql_safety_validator(state)
        assert result["sql_safety_status"] == "unsafe"

    def test_injection_comment(self):
        """注释注入被拦截"""
        state = State(
            messages=[],
            sql_query="SELECT * FROM movies /* DROP TABLE */",
        )
        result = sql_safety_validator(state)
        assert result["sql_safety_status"] == "unsafe"

    def test_injection_semicolon(self):
        """分号注入被拦截"""
        state = State(
            messages=[],
            sql_query="SELECT * FROM movies; DROP TABLE users",
        )
        result = sql_safety_validator(state)
        assert result["sql_safety_status"] == "unsafe"


class TestSQLSyntaxValidator:
    """测试 SQL 语法验证"""

    def test_valid_sql(self, db_manager):
        """有效 SQL 通过验证"""
        state = State(
            messages=[],
            sql_query="SELECT * FROM movies",
        )
        result = sql_syntax_validator(state, db=db_manager)
        assert result["sql_syntax_status"] == "valid"

    def test_invalid_sql(self, db_manager):
        """无效 SQL 验证失败"""
        state = State(
            messages=[],
            sql_query="SELCT * FORM movies",
        )
        with patch("backend.nodes._get_llm") as mock_llm:
            # 模拟 LLM 修复失败
            mock_response = MagicMock()
            mock_response.content = "SELCT * FORM movies"
            mock_llm.return_value.invoke.return_value = mock_response

            result = sql_syntax_validator(state, db=db_manager)
            assert result["sql_syntax_status"] == "invalid"


class TestRouteFunctions:
    """测试路由函数"""

    def test_route_intent_sql(self):
        """sql 意图路由到 sql"""
        state = State(messages=[], user_intent="sql")
        assert route_intent(state) == "sql"

    def test_route_intent_chat(self):
        """chat 意图路由到 chat"""
        state = State(messages=[], user_intent="chat")
        assert route_intent(state) == "chat"

    def test_check_sql_generation_success(self):
        """有 SQL 时返回 success"""
        state = State(messages=[], sql_query="SELECT 1")
        assert check_sql_generation(state) == "success"

    def test_check_sql_generation_failure(self):
        """无 SQL 时返回 failure"""
        state = State(messages=[], sql_query="")
        assert check_sql_generation(state) == "failure"

    def test_check_sql_safety_safe(self):
        """安全状态返回 safe"""
        state = State(messages=[], sql_safety_status="safe")
        assert check_sql_safety(state) == "safe"

    def test_check_sql_safety_unsafe(self):
        """不安全状态返回 unsafe"""
        state = State(messages=[], sql_safety_status="unsafe")
        assert check_sql_safety(state) == "unsafe"


class TestDatabaseIntegration:
    """测试数据库集成"""

    def test_full_query_flow(self, db_manager):
        """完整查询流程：执行 + 保存历史"""
        # 执行查询
        result = db_manager.execute_query("SELECT COUNT(*) as cnt FROM movies")
        assert result["success"] is True
        assert result["row_count"] == 1

        # 保存历史
        db_manager.save_history(
            session_id="test-session",
            question="有多少部电影？",
            sql_generated="SELECT COUNT(*) as cnt FROM movies",
            sql_executed="SELECT COUNT(*) as cnt FROM movies",
            status="success",
            summary="1 row",
        )

        # 验证历史
        history = db_manager.get_history(session_id="test-session")
        assert len(history) == 1
        assert history[0]["question"] == "有多少部电影？"

    def test_schema_context(self, db_manager):
        """Schema 上下文格式化"""
        context = db_manager.format_schema_context()
        assert "movies" in context
        assert "users" in context
        assert "reviews" in context
