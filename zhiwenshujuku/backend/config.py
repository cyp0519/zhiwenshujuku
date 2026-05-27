"""
智问数据库 — 配置模块
"""

import os
import sys
import warnings

# 抑制 langchain_core Reviver 的 pending deprecation 警告
# 来源：langgraph.checkpoint.serde.jsonplus 模块级实例化 Reviver() 未传 allowed_objects
# 这是第三方库内部问题，待 langchain-core >= 0.4 修复后可移除
warnings.filterwarnings("ignore", message=".*allowed_objects.*", category=PendingDeprecationWarning)
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent

# 加载 .env 文件
load_dotenv(ROOT_DIR / ".env")

# ========== LLM 配置 ==========
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.deepseek.com")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_MODEL_HEAVY = os.getenv("LLM_MODEL_HEAVY", "deepseek-reasoner")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# ========== 数据库配置 ==========
DB_PATH = ROOT_DIR / "backend" / "movies.db"

# ========== 安全检查 ==========
UNSAFE_SQL_KEYWORDS = [
    "drop", "delete", "truncate", "alter", "update", "insert", "create",
    "rename", "grant", "revoke", "deny",
]

# SQL 注入特征模式
SQL_INJECTION_PATTERNS = [
    r"/\*.*?\*/",           # 块注释 /* ... */
    r"--\s*",               # 行注释 --
    r";\s*\w",              # 多语句分号
    r"union\s+select",      # UNION 注入
    r"into\s+outfile",      # 文件写入
    r"load_file\s*\(",      # 文件读取
    r"benchmark\s*\(",      # 时间盲注
    r"sleep\s*\(",          # 时间盲注
]

# ========== 知识库配置 ==========
PROMPTS_PATH = ROOT_DIR / "configs" / "prompts.yml"
SQL_EXAMPLES_PATH = ROOT_DIR / "knowledge" / "sql_examples.yml"
DATA_DICTIONARY_PATH = ROOT_DIR / "knowledge" / "data_dictionary.yml"

# ========== 服务器配置 ==========
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8765"))

# ========== 日志配置 ==========
LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 移除默认 handler，添加文件 + 控制台 handler
logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level:<7} | {message}")
logger.add(
    LOG_DIR / "zhiwen_{time:YYYY-MM-DD}.log",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<7} | {name}:{function}:{line} | {message}",
)
