"""
智问数据库 — LangGraph Agent 节点函数 (全中文)
"""

import json
import re
from functools import lru_cache
from typing import Literal

import yaml
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import interrupt
from loguru import logger

from backend.state import State
from backend.database import DatabaseManager
from backend.vector_store import VectorStore
from backend.config import (
    PROMPTS_PATH, UNSAFE_SQL_KEYWORDS, SQL_INJECTION_PATTERNS, LLM_MODEL, LLM_MODEL_HEAVY
)


# ========== 工具函数 ==========

def load_prompt(target: str) -> dict:
    """从 prompts.yml 加载提示词"""
    with open(PROMPTS_PATH, encoding="utf-8") as f:
        prompts = yaml.safe_load(f)
    return prompts.get(target, {})


def get_chat_history(messages: list, last_n: int = 6) -> str:
    """获取最近的聊天历史"""
    return "\n".join(
        f"{'用户' if isinstance(m, HumanMessage) else '助手'}: {m.content[:200]}"
        for m in messages[-last_n:-1]
    )


def format_answer(state: State) -> str:
    """格式化 SQL 查询答案"""
    ans = f"**SQL 查询**:\n```sql\n{state.sql_query}\n```"
    if state.sql_explanation:
        ans += f"\n\n**说明**:\n{state.sql_explanation}\n"
    return ans


# ========== LLM 初始化 ==========

@lru_cache(maxsize=8)
def _get_cached_llm(model: str, temp: float, json_mode: bool):
    """缓存 LLM 实例，避免重复创建"""
    kwargs = dict(model=model, model_provider="openai", temperature=temp)
    if json_mode:
        kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}
    return init_chat_model(**kwargs)


def _get_llm(model: str = None, temp: float = 0, json_mode: bool = False):
    return _get_cached_llm(model or LLM_MODEL, temp, json_mode)


# ========== Agent 节点 ==========

def intent_classifier(state: State) -> dict:
    """判断用户意图：sql 还是 chat"""
    logger.info("🔄 [节点] 意图分类")
    
    chat_history = get_chat_history(state.messages)
    user_query = state.messages[-1].content
    
    prompt = load_prompt("intent_classifier")
    llm = _get_llm()
    
    response = llm.invoke(
        prompt["system_prompt"] + "\n\n" +
        prompt["user_prompt"].format(
            user_message=user_query,
            chat_history=chat_history
        )
    )
    
    intent = response.content.strip().lower()
    if intent not in ["sql", "chat"]:
        intent = "chat"
    
    logger.info(f"  检测到意图: {intent}")
    return {"user_intent": intent, "user_query": user_query}


def sql_generator(state: State, db: DatabaseManager, vs: VectorStore) -> dict:
    """根据用户问题生成 SQL 查询"""
    logger.info("🔄 [节点] SQL 生成器")
    
    schema_context = db.format_schema_context()
    chat_history = get_chat_history(state.messages)
    
    # RAG 检索相似样例
    similar = vs.search(state.user_query, k=4)
    sql_examples_context = "\n\n".join(
        f"问题: {s['question']}\nSQL: {s['sql']}" for s in similar
    ) if similar else "暂无相似样例"
    
    prompt = load_prompt("sql_generator")
    llm = _get_llm(json_mode=True)
    
    response = llm.invoke(
        prompt["system_prompt"].format(
            schema_context=schema_context,
            sql_examples=sql_examples_context,
            chat_history=chat_history,
        )
        + "\n\n"
        + prompt["user_prompt"].format(user_query=state.user_query)
    )
    
    try:
        result = json.loads(response.content)
    except (json.JSONDecodeError, TypeError):
        logger.error("JSON 解析失败，尝试提取")
        try:
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {"sql_query": "", "sql_explanation": "无法生成 SQL"}
        except (json.JSONDecodeError, TypeError, AttributeError):
            result = {"sql_query": "", "sql_explanation": "无法生成 SQL"}
    
    sql = result.get("sql_query", "").strip()
    # 清理可能的 markdown 代码块
    sql = re.sub(r'^```sql\s*|```\s*$', '', sql, flags=re.IGNORECASE).strip()
    sql = re.sub(r'^```\s*|```\s*$', '', sql).strip()
    
    logger.info(f"  生成 SQL: {sql[:80]}...")
    return {
        "sql_query": sql,
        "sql_explanation": result.get("sql_explanation", ""),
    }


def sql_safety_validator(state: State) -> dict:
    """SQL 安全校验"""
    logger.info("🔄 [节点] 安全校验")

    sql = state.sql_query
    found_unsafe = []

    # 检查危险关键词
    for keyword in UNSAFE_SQL_KEYWORDS:
        if re.search(rf"\b{keyword}\b", sql, re.IGNORECASE):
            found_unsafe.append(keyword.upper())

    # 检查注入特征模式
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, sql, re.IGNORECASE | re.DOTALL):
            found_unsafe.append(f"注入特征: {pattern}")
            break

    if found_unsafe:
        msg = f"❌ SQL 安全检查失败: {', '.join(found_unsafe)}"
        logger.warning(msg)
        return {"sql_safety_status": "unsafe", "messages": [AIMessage(content=msg)]}

    logger.info("  ✅ SQL 安全通过")
    return {"sql_safety_status": "safe"}


def sql_syntax_validator(state: State, db: DatabaseManager) -> dict:
    """SQL 语法验证（用数据库实际执行 EXPLAIN）"""
    logger.info("🔄 [节点] 语法验证")
    
    max_retries = 3
    current_sql = state.sql_query
    
    for attempt in range(max_retries):
        # 用 EXPLAIN 验证语法而不实际执行
        conn = db.get_connection()
        try:
            conn.execute(f"EXPLAIN {current_sql}")
            conn.close()
            logger.info("  ✅ SQL 语法有效")
            return {"sql_syntax_status": "valid", "sql_query": current_sql}
        except Exception as e:
            error_msg = str(e)
            logger.debug(f"  语法错误 (尝试 {attempt+1}): {error_msg[:60]}")
            conn.close()
            
            if attempt == max_retries - 1:
                return {
                    "sql_syntax_status": "invalid",
                    "messages": [AIMessage(content=f"❌ SQL 语法错误: {error_msg}")]
                }
            
            # 用 LLM 修复
            prompt = load_prompt("sql_syntax_fixer")
            llm = _get_llm(model=LLM_MODEL_HEAVY)
            fixed = llm.invoke(
                prompt["system_prompt"] + "\n\n"
                + prompt["user_prompt"].format(query=current_sql, error=error_msg)
            )
            current_sql = fixed.content.strip()
            current_sql = re.sub(r'^```sql\s*|```\s*$', '', current_sql, flags=re.IGNORECASE).strip()
            current_sql = re.sub(r'^```\s*|```\s*$', '', current_sql).strip()
    
    return {"sql_syntax_status": "invalid"}


def human_feedback(state: State) -> dict:
    """等待用户确认"""
    logger.info("🔄 [节点] 人工确认")
    
    formatted = format_answer(state)
    formatted += "\n\n**是否执行该查询？回复 yes 或 no**"
    
    ai_msg = AIMessage(content=formatted)
    
    reply = interrupt({"messages": ai_msg, "waiting_for_confirmation": True})
    
    content = reply.content if hasattr(reply, 'content') else str(reply)
    approved = "y" in content.strip().lower()
    
    status = "approved" if approved else "rejected"
    logger.info(f"  用户反馈: {status}")
    
    return {
        "messages": [ai_msg, HumanMessage(content=content.strip())],
        "user_feedback_status": status,
    }


def sql_executor(state: State, db: DatabaseManager) -> dict:
    """执行 SQL 查询"""
    logger.info("🔄 [节点] SQL 执行")
    
    result = db.execute_query(state.sql_query)
    status = "success" if result["success"] else "failure"
    
    logger.info(f"  执行{'成功' if status == 'success' else '失败'}, 耗时 {result['elapsed']}ms")
    return {
        "sql_execution_status": status,
        "sql_execution_result": result,
    }


def sql_result_analyzer(state: State) -> dict:
    """用 LLM 分析查询结果"""
    logger.info("🔄 [节点] 结果分析")
    
    result = state.sql_execution_result
    
    if not result.get("success"):
        msg = f"❌ 查询执行失败: {result.get('error', '未知错误')}"
        return {"messages": [AIMessage(content=msg)]}
    
    # 格式化结果
    if result.get("data"):
        data_preview = result["data"][:10]
        summary = f"查询返回 {result['row_count']} 行, {len(result['columns'])} 列\n"
        summary += f"字段: {', '.join(result['columns'])}\n\n"
        summary += "前几条数据:\n"
        for row in data_preview:
            summary += str(row) + "\n"
    else:
        summary = "查询执行成功，无返回数据。"
    
    prompt = load_prompt("result_analyzer")
    llm = _get_llm(temp=0.1)
    
    response = llm.invoke(
        prompt["system_prompt"] + "\n\n"
        + prompt["user_prompt"].format(
            user_query=state.user_query,
            sql_query=state.sql_query,
            query_results=summary,
        )
    )
    
    analysis = response.content
    logger.info("  ✅ 结果分析完成")
    
    return {
        "messages": [AIMessage(content=analysis)],
        "sql_execution_analysis": analysis,
    }


def chat_agent(state: State) -> dict:
    """通用对话节点"""
    logger.info("🔄 [节点] 聊天助手")
    
    system_prompt = """你是一个智能电影数据库助手的 AI 助手，能用中文回答用户关于电影数据库的问题。
你可以：
1. 回答关于数据库功能的问题
2. 解释 SQL 查询结果
3. 给出电影推荐和分析
4. 进行友好的日常对话

请用热情、专业、简洁的中文回答用户。如果用户想查数据，引导他们用自然语言描述需求。"""
    
    chat_history = get_chat_history(state.messages)
    last_msg = state.messages[-1].content
    
    llm = _get_llm(temp=0.7)
    response = llm.invoke(
        f"{system_prompt}\n\n聊天历史:\n{chat_history}\n\n用户: {last_msg}\n助手:"
    )
    
    return {"messages": [AIMessage(content=response.content)]}


# ========== 路由函数 ==========

def route_intent(state: State) -> Literal["sql", "chat"]:
    return state.user_intent or "chat"

def check_sql_generation(state: State) -> Literal["success", "failure"]:
    return "success" if state.sql_query and state.sql_query.strip() else "failure"

def check_sql_safety(state: State) -> Literal["safe", "unsafe"]:
    return "safe" if state.sql_safety_status == "safe" else "unsafe"

def check_sql_syntax(state: State) -> Literal["valid", "invalid"]:
    return "valid" if state.sql_syntax_status == "valid" else "invalid"

def check_human_feedback(state: State) -> Literal["approved", "rejected"]:
    return "approved" if state.user_feedback_status == "approved" else "rejected"

def check_sql_execution(state: State) -> Literal["success", "failure"]:
    return "success" if state.sql_execution_status == "success" else "failure"
