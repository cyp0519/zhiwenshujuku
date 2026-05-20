"""
智问数据库 — 前端 API 工具
"""

import os
import httpx
import streamlit as st
from typing import Any

API_BASE = os.getenv("ZHIWEN_API_URL", "http://localhost:8765")

# trust_env=False 绕过系统代理设置
CLIENT_KWARGS = {"trust_env": False}


@st.cache_data(ttl=60)
def _cached_get(path: str, timeout: float = 10) -> dict | None:
    """带缓存的 GET 请求（仅用于不变数据）"""
    try:
        r = httpx.get(f"{API_BASE}{path}", timeout=timeout, **CLIENT_KWARGS)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def api_get(path: str, timeout: float = 10) -> dict | None:
    """GET 请求"""
    try:
        r = httpx.get(f"{API_BASE}{path}", timeout=timeout, **CLIENT_KWARGS)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def api_post(path: str, data: dict, timeout: float = 60) -> dict | None:
    """POST 请求"""
    try:
        r = httpx.post(f"{API_BASE}{path}", json=data, timeout=timeout, **CLIENT_KWARGS)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        st.error(f"请求失败: {e}")
        return None


def api_delete(path: str) -> dict | None:
    """DELETE 请求"""
    try:
        r = httpx.delete(f"{API_BASE}{path}", timeout=10, **CLIENT_KWARGS)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        st.error(f"请求失败: {e}")
        return None


def chat(message: str, session_id: str | None = None) -> dict | None:
    """发送聊天消息"""
    return api_post("/chat", {"message": message, "session_id": session_id})


def execute_sql(sql: str) -> dict | None:
    """执行 SQL 查询"""
    return api_post("/sql/execute", {"sql": sql})


def get_schema() -> dict | None:
    """获取表结构"""
    return api_get("/schema")


def get_history(session_id: str | None = None, limit: int = 200,
                date_from: str | None = None, date_to: str | None = None) -> list:
    """获取查询历史，支持日期范围筛选"""
    params = []
    if session_id:
        params.append(f"session_id={session_id}")
    if date_from:
        params.append(f"date_from={date_from}")
    if date_to:
        params.append(f"date_to={date_to}")
    params.append(f"limit={limit}")
    query = "&".join(params)
    result = api_get(f"/history?{query}")
    return result if isinstance(result, list) else []


def delete_history(history_id: int) -> dict | None:
    """删除单条历史记录"""
    return api_delete(f"/history/{history_id}")


def toggle_favorite(history_id: int) -> dict | None:
    """切换收藏状态"""
    return api_post(f"/history/{history_id}/favorite", {})


def batch_delete_history(ids: list[int]) -> dict | None:
    """批量删除历史记录"""
    return api_post("/history/batch-delete", {"ids": ids})


def get_insights() -> dict | None:
    """获取数据库统计信息（缓存 60s）"""
    return _cached_get("/insights")


def get_health() -> dict | None:
    """获取健康检查状态（缓存 30s）"""
    return _cached_get("/health")


def get_data_dictionary() -> dict | None:
    """获取数据字典（缓存 5 分钟）"""
    return _cached_get("/data-dictionary")
