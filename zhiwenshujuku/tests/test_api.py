"""
智问数据库 — API 端点测试
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def mock_app_state():
    """模拟 AppState"""
    with patch("backend.api.app_state") as mock:
        mock.db = MagicMock()
        mock.vs = MagicMock()
        mock.graph = MagicMock()
        mock.sessions = {}
        mock.touch_session = MagicMock()
        mock.cleanup_stale_sessions = MagicMock()
        yield mock


@pytest.fixture
def client(mock_app_state):
    """创建测试客户端"""
    from backend.api import app
    return TestClient(app)


class TestHealthEndpoint:
    """测试 /health 端点"""

    def test_health_ok(self, client, mock_app_state):
        """数据库存在时返回 ok"""
        with patch("backend.api.os.path.exists", return_value=True):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["database"] == "connected"

    def test_health_degraded(self, client, mock_app_state):
        """数据库不存在时返回 degraded"""
        with patch("backend.api.os.path.exists", return_value=False):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"


class TestSchemaEndpoint:
    """测试 /schema 端点"""

    def test_get_schema(self, client, mock_app_state):
        """获取数据库 schema"""
        mock_app_state.db.get_schema_dict.return_value = {
            "movies": [{"name": "id", "type": "INTEGER", "pk": True}]
        }
        response = client.get("/schema")
        assert response.status_code == 200
        assert "movies" in response.json()


class TestSQLEndpoint:
    """测试 /sql/execute 端点"""

    def test_empty_sql(self, client):
        """空 SQL 应返回 400"""
        response = client.post("/sql/execute", json={"sql": ""})
        assert response.status_code == 400

    def test_unsafe_sql_blocked(self, client):
        """危险 SQL 应被拦截"""
        response = client.post("/sql/execute", json={"sql": "DROP TABLE movies"})
        assert response.status_code == 403
        assert "危险关键词" in response.json()["detail"]

    def test_injection_blocked(self, client):
        """SQL 注入应被拦截"""
        response = client.post("/sql/execute", json={
            "sql": "SELECT * FROM movies /* 注入 */ DROP TABLE movies"
        })
        assert response.status_code == 403

    def test_comment_injection_blocked(self, client):
        """注释注入应被拦截"""
        response = client.post("/sql/execute", json={
            "sql": "SELECT * FROM movies -- WHERE 1=1"
        })
        assert response.status_code == 403

    def test_safe_select_allowed(self, client, mock_app_state):
        """安全的 SELECT 应被允许"""
        mock_app_state.db.execute_query.return_value = {
            "success": True,
            "data": [{"cnt": 10}],
            "columns": ["cnt"],
            "row_count": 1,
            "error": None,
            "elapsed": 1.5,
        }
        response = client.post("/sql/execute", json={
            "sql": "SELECT COUNT(*) as cnt FROM movies"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["row_count"] == 1


class TestHistoryEndpoint:
    """测试 /history 端点"""

    def test_get_history(self, client, mock_app_state):
        """获取查询历史"""
        mock_app_state.db.get_history.return_value = [
            {"id": 1, "question": "测试问题", "execution_status": "success"}
        ]
        response = client.get("/history")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_delete_history(self, client, mock_app_state):
        """删除历史记录"""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.rowcount = 1
        mock_app_state.db.get_connection.return_value = mock_conn

        response = client.delete("/history/1")
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_delete_not_found(self, client, mock_app_state):
        """删除不存在的记录应返回 404"""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.rowcount = 0
        mock_app_state.db.get_connection.return_value = mock_conn

        response = client.delete("/history/999")
        assert response.status_code == 404


class TestExportEndpoint:
    """测试导出端点"""

    def test_export_csv(self, client):
        """导出 CSV"""
        response = client.post("/export/csv", json={
            "data": [{"name": "测试", "value": 123}]
        })
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]

    def test_export_empty(self, client):
        """空数据导出应返回 400"""
        response = client.post("/export/csv", json={"data": []})
        assert response.status_code == 400
