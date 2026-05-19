"""
智问数据库 — 测试配置和公共 fixtures
"""

import os
import sys
import sqlite3
import tempfile
from pathlib import Path

import pytest

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def tmp_db(tmp_path):
    """创建临时 SQLite 数据库，包含基本表结构"""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            original_title TEXT,
            year INTEGER,
            director TEXT,
            actors TEXT,
            genre TEXT,
            country TEXT,
            language TEXT,
            duration INTEGER,
            rating REAL DEFAULT 0.0,
            rating_count INTEGER DEFAULT 0,
            description TEXT
        );
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            city TEXT,
            age INTEGER,
            gender TEXT,
            registration_date TEXT
        );
        CREATE TABLE reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER REFERENCES movies(id),
            user_id INTEGER REFERENCES users(id),
            rating REAL NOT NULL,
            review_text TEXT,
            review_date TEXT
        );
        CREATE TABLE query_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            question TEXT,
            sql_generated TEXT,
            sql_executed TEXT,
            execution_status TEXT,
            result_summary TEXT,
            is_favorite INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO movies (title, year, director, genre, country, rating, duration)
        VALUES ('测试电影', 2024, '测试导演', '剧情', '中国', 8.5, 120);
        INSERT INTO movies (title, year, director, genre, country, rating, duration)
        VALUES ('高分电影', 2023, '知名导演', '科幻', '美国', 9.5, 150);
        INSERT INTO users (username, city, age, gender)
        VALUES ('用户001', '北京', 25, '男');
        INSERT INTO reviews (movie_id, user_id, rating, review_text)
        VALUES (1, 1, 8.0, '非常好看');
    """)
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def db_manager(tmp_db):
    """创建 DatabaseManager 实例"""
    from backend.database import DatabaseManager
    return DatabaseManager(tmp_db)


@pytest.fixture
def sample_state():
    """创建测试用 State 对象"""
    from langchain_core.messages import HumanMessage
    from backend.state import State

    return State(
        messages=[HumanMessage(content="有多少部电影？")],
        user_query="有多少部电影？",
    )
