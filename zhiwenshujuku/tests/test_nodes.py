"""
智问数据库 — Agent 节点函数测试（无需 LLM 调用的部分）
"""

import re
import pytest
from backend.config import UNSAFE_SQL_KEYWORDS


class TestSQLSafetyValidator:
    """sql_safety_validator 节点测试"""

    def _validate(self, sql: str) -> dict:
        """模拟 sql_safety_validator 的核心逻辑"""
        from backend.state import State
        from langchain_core.messages import HumanMessage

        state = State(
            messages=[HumanMessage(content="test")],
            user_query="test",
            sql_query=sql,
        )

        found_unsafe = []
        for keyword in UNSAFE_SQL_KEYWORDS:
            if re.search(rf"\b{keyword}\b", state.sql_query, re.IGNORECASE):
                found_unsafe.append(keyword.upper())

        if found_unsafe:
            return {"sql_safety_status": "unsafe", "found": found_unsafe}
        return {"sql_safety_status": "safe"}

    def test_safe_select(self):
        result = self._validate("SELECT * FROM movies WHERE rating > 9")
        assert result["sql_safety_status"] == "safe"

    def test_unsafe_drop(self):
        result = self._validate("DROP TABLE movies")
        assert result["sql_safety_status"] == "unsafe"
        assert "DROP" in result["found"]

    def test_unsafe_delete(self):
        result = self._validate("DELETE FROM movies WHERE id = 1")
        assert result["sql_safety_status"] == "unsafe"
        assert "DELETE" in result["found"]

    def test_unsafe_insert(self):
        result = self._validate("INSERT INTO movies (title) VALUES ('test')")
        assert result["sql_safety_status"] == "unsafe"

    def test_unsafe_update(self):
        result = self._validate("UPDATE movies SET rating = 0")
        assert result["sql_safety_status"] == "unsafe"

    def test_unsafe_multiple_keywords(self):
        result = self._validate("DROP TABLE movies; DELETE FROM users")
        assert result["sql_safety_status"] == "unsafe"
        assert len(result["found"]) >= 2

    def test_safe_join_query(self):
        result = self._validate(
            "SELECT m.title, r.rating FROM movies m JOIN reviews r ON m.id = r.movie_id"
        )
        assert result["sql_safety_status"] == "safe"

    def test_safe_subquery(self):
        result = self._validate(
            "SELECT * FROM movies WHERE rating > (SELECT AVG(rating) FROM movies)"
        )
        assert result["sql_safety_status"] == "safe"

    def test_unsafe_case_insensitive(self):
        result = self._validate("drop table movies")
        assert result["sql_safety_status"] == "unsafe"


class TestRouteFunctions:
    """路由函数测试"""

    def test_route_intent_sql(self):
        from backend.nodes import route_intent
        from backend.state import State
        from langchain_core.messages import HumanMessage

        state = State(
            messages=[HumanMessage(content="test")],
            user_intent="sql",
        )
        assert route_intent(state) == "sql"

    def test_route_intent_chat(self):
        from backend.nodes import route_intent
        from backend.state import State
        from langchain_core.messages import HumanMessage

        state = State(
            messages=[HumanMessage(content="test")],
            user_intent="chat",
        )
        assert route_intent(state) == "chat"

    def test_check_sql_generation_success(self):
        from backend.nodes import check_sql_generation
        from backend.state import State
        from langchain_core.messages import HumanMessage

        state = State(
            messages=[HumanMessage(content="test")],
            sql_query="SELECT 1",
        )
        assert check_sql_generation(state) == "success"

    def test_check_sql_generation_failure(self):
        from backend.nodes import check_sql_generation
        from backend.state import State
        from langchain_core.messages import HumanMessage

        state = State(
            messages=[HumanMessage(content="test")],
            sql_query="",
        )
        assert check_sql_generation(state) == "failure"


class TestUtilityFunctions:
    """工具函数测试"""

    def test_load_prompt(self):
        from backend.nodes import load_prompt
        result = load_prompt("intent_classifier")
        assert "system_prompt" in result
        assert "user_prompt" in result

    def test_get_chat_history(self):
        from backend.nodes import get_chat_history
        from langchain_core.messages import HumanMessage, AIMessage

        messages = [
            HumanMessage(content="你好"),
            AIMessage(content="你好！"),
            HumanMessage(content="有多少电影？"),
        ]
        history = get_chat_history(messages)
        assert "你好" in history
        assert "有多少电影" in history

    def test_format_answer(self):
        from backend.nodes import format_answer
        from backend.state import State
        from langchain_core.messages import HumanMessage

        state = State(
            messages=[HumanMessage(content="test")],
            sql_query="SELECT COUNT(*) FROM movies",
            sql_explanation="查询电影总数",
        )
        answer = format_answer(state)
        assert "SELECT COUNT(*)" in answer
        assert "查询电影总数" in answer
