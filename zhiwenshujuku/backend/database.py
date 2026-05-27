"""
智问数据库 — SQLite 数据库适配器
"""

import sqlite3
import time
import re
from pathlib import Path
import pandas as pd
from loguru import logger


class DatabaseManager:
    """SQLite 数据库管理器"""
    
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._ensure_db()
    
    def _ensure_db(self):
        """确保数据库文件和表存在"""
        if not Path(self.db_path).exists():
            logger.warning(f"数据库文件不存在: {self.db_path}")
            logger.info("请先运行 data/create_dataset.py 初始化数据库")
            return
        # 迁移：确保 is_favorite 列存在
        try:
            conn = self.get_connection()
            conn.execute("SELECT is_favorite FROM query_history LIMIT 1")
            conn.close()
        except sqlite3.OperationalError:
            logger.info("迁移: 添加 is_favorite 列到 query_history 表")
            conn = self.get_connection()
            conn.execute("ALTER TABLE query_history ADD COLUMN is_favorite INTEGER DEFAULT 0")
            conn.commit()
            conn.close()
    
    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn
    
    def execute_query(self, sql: str) -> dict:
        """执行 SQL 查询并返回结果"""
        result = {
            "success": False,
            "data": None,
            "columns": [],
            "row_count": 0,
            "error": None,
            "query": sql.strip(),
            "elapsed": 0,
        }

        start = time.time()
        try:
            conn = self.get_connection()
            cursor = conn.execute(sql)

            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                data = [dict(zip(columns, row)) for row in rows]
                result["data"] = data
                result["columns"] = columns
                result["row_count"] = len(data)

            # 仅在写操作时 commit
            sql_upper = sql.strip().upper()
            if any(sql_upper.startswith(kw) for kw in ("INSERT", "UPDATE", "DELETE", "ALTER", "CREATE", "DROP")):
                conn.commit()

            conn.close()
            result["success"] = True

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"SQL 执行失败: {e}")
        finally:
            result["elapsed"] = round((time.time() - start) * 1000, 2)

        return result
    
    def get_schema_dict(self) -> dict:
        """获取数据库 Schema 信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 获取所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row["name"] for row in cursor.fetchall()]
        
        schema = {}
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = []
            for row in cursor.fetchall():
                columns.append({
                    "name": row["name"],
                    "type": row["type"],
                    "notnull": bool(row["notnull"]),
                    "default": row["dflt_value"],
                    "pk": bool(row["pk"])
                })
            schema[table] = columns
        
        conn.close()
        return schema
    
    def format_schema_context(self) -> str:
        """格式化 Schema 为 LLM 上下文"""
        schema = self.get_schema_dict()
        parts = []
        
        table_descriptions = {
            "movies": "电影信息表（包含电影标题、年份、导演、演员、类型、评分等）",
            "users": "用户信息表（包含用户昵称、城市、年龄、性别等）",
            "reviews": "电影评论表（包含用户对电影的评分和评论文本）",
            "query_history": "查询历史记录表（记录用户的历史查询）",
        }
        
        for table_name, columns in schema.items():
            desc = table_descriptions.get(table_name, "")
            parts.append(f"表名: {table_name} — {desc}")
            parts.append("字段:")
            for col in columns:
                pk_tag = " [主键]" if col["pk"] else ""
                nn_tag = " [非空]" if col["notnull"] else ""
                parts.append(f"  - {col['name']} ({col['type']}){pk_tag}{nn_tag}")
            parts.append("")
        
        return "\n".join(parts)
    
    def get_history(self, session_id: str | None = None, limit: int = 200,
                    date_from: str | None = None, date_to: str | None = None) -> list[dict]:
        """获取查询历史，支持日期范围筛选"""
        conn = self.get_connection()
        cursor = conn.cursor()

        conditions = []
        params = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        if date_from:
            conditions.append("DATE(created_at) >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("DATE(created_at) <= ?")
            params.append(date_to)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM query_history {where_clause} ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, tuple(params))
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def batch_delete_history(self, ids: list[int]) -> int:
        """批量删除查询历史，返回删除行数"""
        if not ids:
            return 0
        conn = self.get_connection()
        placeholders = ",".join(["?"] * len(ids))
        cursor = conn.execute(
            f"DELETE FROM query_history WHERE id IN ({placeholders})",
            tuple(ids)
        )
        conn.commit()
        deleted = cursor.rowcount
        conn.close()
        return deleted
    
    def save_history(self, session_id: str, question: str, sql_generated: str,
                     sql_executed: str, status: str, summary: str):
        """保存查询记录"""
        conn = self.get_connection()
        conn.execute(
            "INSERT INTO query_history (session_id, question, sql_generated, sql_executed, execution_status, result_summary) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, question, sql_generated, sql_executed, status, summary)
        )
        conn.commit()
        conn.close()

    def explain_query(self, sql: str) -> dict:
        """运行 EXPLAIN QUERY PLAN 并分析结果"""
        result = {
            "success": False,
            "raw_plan": [],
            "has_table_scan": False,
            "scan_tables": [],
            "error": None
        }
        try:
            conn = self.get_connection()
            cursor = conn.execute(f"EXPLAIN QUERY PLAN {sql}")
            rows = cursor.fetchall()
            
            plan = []
            for row in rows:
                row_dict = dict(row)
                plan.append(row_dict)
                detail = row_dict.get("detail", "")
                if "SCAN" in detail:
                    result["has_table_scan"] = True
                    match = re.search(r"SCAN\s+(?:TABLE\s+)?([a-zA-Z0-9_]+)", detail)
                    if match:
                        table = match.group(1)
                        if table not in result["scan_tables"]:
                            result["scan_tables"].append(table)
            
            result["raw_plan"] = plan
            result["success"] = True
            conn.close()
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"EXPLAIN SQL 失败: {e}")
        return result

    def get_indexes(self) -> list[dict]:
        """获取当前数据库中的所有索引（包含自动和自定义创建的）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, tbl_name, sql 
            FROM sqlite_master 
            WHERE type = 'index' AND tbl_name NOT LIKE 'sqlite_%'
        """)
        rows = cursor.fetchall()
        
        indexes = []
        for row in rows:
            row_dict = dict(row)
            is_custom = bool(row_dict.get("sql"))
            indexes.append({
                "index_name": row_dict["name"],
                "table_name": row_dict["tbl_name"],
                "sql": row_dict["sql"] or "自动创建 (主键/唯一约束)",
                "is_custom": is_custom
            })
        conn.close()
        return indexes

    def create_index(self, table: str, column: str, index_name: str) -> dict:
        """在指定的表和列上创建索引"""
        result = {"success": False, "error": None}
        if not (re.match(r"^\w+$", table) and re.match(r"^\w+$", column) and re.match(r"^\w+$", index_name)):
            result["error"] = "非法的表名、列名或索引名格式"
            return result
        
        sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table}({column})"
        try:
            conn = self.get_connection()
            conn.execute(sql)
            conn.commit()
            conn.close()
            result["success"] = True
            logger.info(f"成功创建索引: {index_name} ON {table}({column})")
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"创建索引失败: {e}")
        return result

    def drop_index(self, index_name: str) -> dict:
        """删除指定的索引"""
        result = {"success": False, "error": None}
        if not re.match(r"^\w+$", index_name):
            result["error"] = "非法的索引名格式"
            return result
            
        sql = f"DROP INDEX IF EXISTS {index_name}"
        try:
            conn = self.get_connection()
            conn.execute(sql)
            conn.commit()
            conn.close()
            result["success"] = True
            logger.info(f"成功删除索引: {index_name}")
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"删除索引失败: {e}")
        return result
