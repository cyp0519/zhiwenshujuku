"""
智问数据库 — FastAPI 后端服务
"""

import os
import re
import uuid
from datetime import datetime
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from loguru import logger
import pandas as pd
import io

from backend.database import DatabaseManager
from backend.vector_store import VectorStore
from backend.graph import create_graph
from backend.config import DB_PATH, API_HOST, API_PORT, SQL_EXAMPLES_PATH, UNSAFE_SQL_KEYWORDS, SQL_INJECTION_PATTERNS
import yaml


# ========== Pydantic 模型 ==========

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None

class ChatResponse(BaseModel):
    message: str
    session_id: str
    sql_query: str | None = None
    sql_explanation: str | None = None
    metadata: dict | None = None
    interrupt: bool = False

class SQLExecuteRequest(BaseModel):
    sql: str
    session_id: str | None = None

class SQLExecuteResponse(BaseModel):
    success: bool
    data: list | None = None
    columns: list[str] | None = None
    row_count: int
    error: str | None = None
    elapsed: float


# ========== 速率限制 ==========
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

# ========== 全局状态 ==========

SESSION_TIMEOUT_SECONDS = int(os.getenv("SESSION_TIMEOUT", "1800"))  # 默认 30 分钟


class AppState:
    def __init__(self):
        self.db: DatabaseManager | None = None
        self.vs: VectorStore | None = None
        self.graph = None
        self.sessions: dict[str, dict] = {}

    def touch_session(self, session_id: str):
        """更新会话最后活跃时间"""
        import time
        self.sessions[session_id] = {"last_active": time.time()}

    def cleanup_stale_sessions(self):
        """清理超时会话"""
        import time
        now = time.time()
        stale = [
            sid for sid, info in self.sessions.items()
            if now - info.get("last_active", 0) > SESSION_TIMEOUT_SECONDS
        ]
        for sid in stale:
            del self.sessions[sid]
            logger.info(f"清理超时会话: {sid}")
        return len(stale)


app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 智问数据库 后端启动中...")
    
    # 初始化数据库
    app_state.db = DatabaseManager(DB_PATH)
    
    # 初始化向量库
    persist_dir = str(DB_PATH.parent / "chromadb")
    app_state.vs = VectorStore(persist_dir)
    
    # 如果向量库为空，加载 SQL 样例
    if app_state.vs.count == 0:
        logger.info("加载 SQL 样例到向量库...")
        with open(SQL_EXAMPLES_PATH, encoding="utf-8") as f:
            examples = yaml.safe_load(f)
        app_state.vs.add_examples(examples)
    
    # 构建工作流
    app_state.graph = create_graph(app_state.db, app_state.vs)
    
    logger.info("✅ 智问数据库 后端就绪")
    yield
    logger.info("🛑 智问数据库 后端关闭")


app = FastAPI(
    title="智问数据库 API",
    description="基于自然语言的智能数据库查询与分析平台",
    version="1.0.0",
    lifespan=lifespan,
)

# 注册速率限制
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8501").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== API 端点 ==========

@app.get("/")
async def root():
    return {
        "name": "智问数据库",
        "version": "1.0.0",
        "docs": "/docs",
    }

@app.get("/health")
async def health():
    import os
    db_ok = os.path.exists(DB_PATH)
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "not_found",
        "vector_store": app_state.vs.count if app_state.vs else 0,
    }


@app.post("/chat")
@limiter.limit("30/minute")
async def chat(req: ChatRequest, request: Request):
    """聊天接口：用户输入自然语言，返回查询结果或对话"""
    try:
        session_id = req.session_id or str(uuid.uuid4())
        app_state.touch_session(session_id)

        # 定期清理超时会话
        if len(app_state.sessions) % 10 == 0:
            app_state.cleanup_stale_sessions()

        config = {"configurable": {"thread_id": session_id}}
        user_msg = HumanMessage(content=req.message)
        
        # 获取当前线程状态
        try:
            existing_state = app_state.graph.get_state(config)
            is_resume = bool(existing_state.next)
        except Exception:
            # 新线程或无状态
            is_resume = False
        
        if is_resume:
            # 从中断点恢复（human_feedback 节点等待确认）
            result = app_state.graph.invoke(
                Command(resume=req.message), config=config
            )
        else:
            # 新对话
            result = app_state.graph.invoke(
                {"messages": [user_msg]}, config=config
            )
        
        # 从状态快照中提取数据
        state_snapshot = app_state.graph.get_state(config)
        state_values = state_snapshot.values if hasattr(state_snapshot, 'values') else result
        
        # 检查是否被 interrupt 挂起（等待人工确认）
        if state_snapshot.next:
            # 找到 interrupt 消息
            tasks = state_snapshot.tasks
            interrupt_msg = "请确认是否执行该查询。"
            if tasks:
                try:
                    task = tasks[0]
                    if hasattr(task, 'interrupts') and task.interrupts:
                        interrupt_msg = str(task.interrupts[0].value)
                    elif hasattr(task, 'state'):
                        interrupt_msg = str(task.state)
                except Exception:
                    pass
            
            sql_query = state_values.get("sql_query", "")
            sql_explanation = state_values.get("sql_explanation", "")
            
            return ChatResponse(
                message=interrupt_msg,
                session_id=session_id,
                sql_query=sql_query,
                sql_explanation=sql_explanation,
                interrupt=True,
            )
        
        # 提取最终回复
        last_msg = None
        if state_values.get("messages"):
            for msg in reversed(state_values["messages"]):
                if hasattr(msg, "type") and msg.type != "human":
                    last_msg = msg.content
                    break
        
        # 保存历史
        sql_exec_result = state_values.get("sql_execution_result")
        if sql_exec_result and sql_exec_result.get("success"):
            app_state.db.save_history(
                session_id=session_id,
                question=req.message,
                sql_generated=state_values.get("sql_query", ""),
                sql_executed=sql_exec_result.get("query", ""),
                status="success",
                summary=f"{sql_exec_result.get('row_count', 0)} rows"
            )
        
        return ChatResponse(
            message=last_msg or "处理完成。",
            session_id=session_id,
            sql_query=state_values.get("sql_query"),
            sql_explanation=state_values.get("sql_explanation"),
            metadata={
                "intent": state_values.get("user_intent"),
                "sql_status": state_values.get("sql_execution_status"),
                "row_count": sql_exec_result.get("row_count") if sql_exec_result else None,
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Chat 请求失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试")


@app.post("/sql/execute", response_model=SQLExecuteResponse)
@limiter.limit("30/minute")
async def execute_sql(req: SQLExecuteRequest, request: Request):
    """直接执行 SQL 查询"""
    try:
        if not req.sql.strip():
            raise HTTPException(status_code=400, detail="SQL 不能为空")

        # 安全校验 — 阻止危险 SQL 关键词和注入特征
        found_unsafe = [
            kw for kw in UNSAFE_SQL_KEYWORDS
            if re.search(rf"\b{kw}\b", req.sql, re.IGNORECASE)
        ]
        # 检查注入特征
        for pattern in SQL_INJECTION_PATTERNS:
            if re.search(pattern, req.sql, re.IGNORECASE | re.DOTALL):
                found_unsafe.append(f"注入特征: {pattern}")
                break
        if found_unsafe:
            raise HTTPException(
                status_code=403,
                detail=f"禁止执行包含危险关键词的 SQL: {', '.join(k.upper() for k in found_unsafe)}"
            )

        result = app_state.db.execute_query(req.sql)
        
        # 保存历史
        app_state.db.save_history(
            session_id=req.session_id or "direct",
            question="[直接SQL]",
            sql_generated="",
            sql_executed=req.sql,
            status="success" if result["success"] else "failure",
            summary=f"{result['row_count']} rows / {result.get('elapsed', 0)}ms"
        )
        
        return SQLExecuteResponse(
            success=result["success"],
            data=result["data"],
            columns=result["columns"],
            row_count=result["row_count"],
            error=result["error"],
            elapsed=result["elapsed"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SQL 执行端点错误: {e}")
        raise HTTPException(status_code=500, detail="SQL 执行失败，请检查语句后重试")


@app.get("/schema")
async def get_schema():
    """获取数据库 Schema"""
    return app_state.db.get_schema_dict()


@app.get("/schema/context")
async def get_schema_context():
    """获取格式化 Schema（给前端展示）"""
    return {"context": app_state.db.format_schema_context()}


@app.get("/history")
async def get_history(session_id: str | None = None, limit: int = 200,
                      date_from: str | None = None, date_to: str | None = None):
    """获取查询历史，支持日期范围筛选"""
    return app_state.db.get_history(session_id, limit, date_from, date_to)


@app.delete("/history/{history_id}")
async def delete_history(history_id: int):
    """删除单条查询历史"""
    try:
        conn = app_state.db.get_connection()
        cursor = conn.execute("DELETE FROM query_history WHERE id = ?", (history_id,))
        conn.commit()
        deleted = cursor.rowcount
        conn.close()
        if deleted == 0:
            raise HTTPException(status_code=404, detail="记录不存在")
        return {"success": True, "deleted": deleted}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除历史记录失败: {e}")
        raise HTTPException(status_code=500, detail="删除失败")


@app.post("/history/batch-delete")
async def batch_delete_history(data: dict):
    """批量删除查询历史"""
    ids = data.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="ids 不能为空")
    deleted = app_state.db.batch_delete_history(ids)
    return {"success": True, "deleted": deleted}


@app.post("/history/{history_id}/favorite")
async def toggle_favorite(history_id: int):
    """切换查询历史的收藏状态"""
    try:
        conn = app_state.db.get_connection()
        row = conn.execute("SELECT id FROM query_history WHERE id = ?", (history_id,)).fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="记录不存在")
        conn.execute(
            "UPDATE query_history SET is_favorite = NOT COALESCE(is_favorite, 0) WHERE id = ?",
            (history_id,)
        )
        conn.commit()
        new_state = conn.execute(
            "SELECT is_favorite FROM query_history WHERE id = ?", (history_id,)
        ).fetchone()
        conn.close()
        return {"success": True, "is_favorite": bool(new_state["is_favorite"])}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"切换收藏失败: {e}")
        raise HTTPException(status_code=500, detail="操作失败")


@app.post("/export/csv")
async def export_csv(data: dict):
    """导出查询结果为 CSV"""
    df = pd.DataFrame(data.get("data", []))
    if df.empty:
        raise HTTPException(status_code=400, detail="无数据可导出")
    
    buf = io.StringIO()
    df.to_csv(buf, index=False, encoding="utf-8-sig")
    buf.seek(0)
    
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=export_{datetime.now():%Y%m%d_%H%M%S}.csv"}
    )


@app.post("/export/excel")
async def export_excel(data: dict):
    """导出查询结果为 Excel"""
    df = pd.DataFrame(data.get("data", []))
    if df.empty:
        raise HTTPException(status_code=400, detail="无数据可导出")
    
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="查询结果")
    buf.seek(0)
    
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=export_{datetime.now():%Y%m%d_%H%M%S}.xlsx"}
    )


@app.get("/insights")
async def get_insights():
    """获取数据库基本统计信息（用于前端展示）"""
    db = app_state.db
    conn = db.get_connection()
    cursor = conn.cursor()

    total_movies = cursor.execute("SELECT COUNT(*) as cnt FROM movies").fetchone()["cnt"]
    total_users = cursor.execute("SELECT COUNT(*) as cnt FROM users").fetchone()["cnt"]
    total_reviews = cursor.execute("SELECT COUNT(*) as cnt FROM reviews").fetchone()["cnt"]
    total_directors = cursor.execute("SELECT COUNT(DISTINCT director) as cnt FROM movies").fetchone()["cnt"]
    avg_rating = cursor.execute("SELECT ROUND(AVG(rating),2) as avg FROM movies").fetchone()["avg"]
    year_range = dict(cursor.execute("SELECT MIN(year) as min, MAX(year) as max FROM movies").fetchone())

    conn.close()

    return {
        "total_movies": total_movies,
        "total_users": total_users,
        "total_reviews": total_reviews,
        "total_directors": total_directors,
        "avg_rating": avg_rating,
        "year_range": year_range,
    }


@app.get("/stats/queries")
async def get_query_stats():
    """查询性能统计"""
    db = app_state.db
    conn = db.get_connection()

    # 总查询数
    total = conn.execute("SELECT COUNT(*) as cnt FROM query_history").fetchone()["cnt"]

    # 成功率
    success = conn.execute(
        "SELECT COUNT(*) as cnt FROM query_history WHERE execution_status = 'success'"
    ).fetchone()["cnt"]

    # 按日期统计
    daily = conn.execute("""
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM query_history
        GROUP BY DATE(created_at)
        ORDER BY date DESC
        LIMIT 7
    """).fetchall()

    # 热门查询（最近）
    recent = conn.execute("""
        SELECT question, execution_status, created_at
        FROM query_history
        ORDER BY created_at DESC
        LIMIT 5
    """).fetchall()

    conn.close()

    return {
        "total_queries": total,
        "success_count": success,
        "success_rate": round(success / total * 100, 1) if total > 0 else 0,
        "daily_stats": [dict(row) for row in daily],
        "recent_queries": [dict(row) for row in recent],
    }


@app.get("/schema/relations")
async def get_schema_relations():
    """获取表关系信息（用于 ER 图展示）"""
    relations = {
        "tables": {
            "movies": {
                "description": "电影信息表",
                "columns": ["id (PK)", "title", "original_title", "year", "director",
                            "actors", "genre", "country", "language", "duration",
                            "rating", "rating_count", "description"],
            },
            "users": {
                "description": "用户信息表",
                "columns": ["id (PK)", "username", "city", "age", "gender",
                            "registration_date"],
            },
            "reviews": {
                "description": "电影评论表",
                "columns": ["id (PK)", "movie_id (FK)", "user_id (FK)", "rating",
                            "review_text", "review_date"],
            },
            "query_history": {
                "description": "查询历史记录表",
                "columns": ["id (PK)", "session_id", "question", "sql_generated",
                            "sql_executed", "execution_status", "result_summary",
                            "is_favorite", "created_at"],
            },
        },
        "foreign_keys": [
            {"from": "reviews.movie_id", "to": "movies.id", "label": "评论属于电影"},
            {"from": "reviews.user_id", "to": "users.id", "label": "用户发表评论"},
        ],
    }
    return relations


@app.get("/data-dictionary")
async def get_data_dictionary():
    """获取数据字典（字段中文说明）"""
    from backend.config import DATA_DICTIONARY_PATH
    try:
        with open(DATA_DICTIONARY_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}


if __name__ == "__main__":
    uvicorn.run("backend.api:app", host=API_HOST, port=API_PORT, reload=True)
