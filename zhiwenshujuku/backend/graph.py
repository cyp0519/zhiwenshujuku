"""
智问数据库 — LangGraph Agent 工作流定义
"""

from functools import partial
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from loguru import logger

from backend.state import State
from backend import nodes
from backend.database import DatabaseManager
from backend.vector_store import VectorStore


def create_graph(db: DatabaseManager, vs: VectorStore):
    """创建并编译 LangGraph Agent 工作流"""
    
    workflow = StateGraph(State)
    memory = MemorySaver()
    
    # 创建带依赖的节点（注入数据库和向量库）
    sql_gen_node = partial(nodes.sql_generator, db=db, vs=vs)
    sql_syntax_node = partial(nodes.sql_syntax_validator, db=db)
    sql_exec_node = partial(nodes.sql_executor, db=db)
    
    # === 添加节点 ===
    workflow.add_node("intent_classifier", nodes.intent_classifier)
    workflow.add_node("chat_agent", nodes.chat_agent)
    workflow.add_node("sql_generator", sql_gen_node)
    workflow.add_node("sql_safety_validator", nodes.sql_safety_validator)
    workflow.add_node("sql_syntax_validator", sql_syntax_node)
    workflow.add_node("human_feedback", nodes.human_feedback)
    workflow.add_node("sql_executor", sql_exec_node)
    workflow.add_node("sql_result_analyzer", nodes.sql_result_analyzer)
    
    # === 构建边 ===
    workflow.add_edge(START, "intent_classifier")
    
    workflow.add_conditional_edges(
        "intent_classifier",
        nodes.route_intent,
        {"sql": "sql_generator", "chat": "chat_agent"},
    )
    
    workflow.add_conditional_edges(
        "sql_generator",
        nodes.check_sql_generation,
        {"success": "sql_safety_validator", "failure": END},
    )
    
    workflow.add_conditional_edges(
        "sql_safety_validator",
        nodes.check_sql_safety,
        {"safe": "sql_syntax_validator", "unsafe": END},
    )
    
    workflow.add_conditional_edges(
        "sql_syntax_validator",
        nodes.check_sql_syntax,
        {"valid": "human_feedback", "invalid": END},
    )
    
    workflow.add_conditional_edges(
        "human_feedback",
        nodes.check_human_feedback,
        {"approved": "sql_executor", "rejected": END},
    )
    
    workflow.add_conditional_edges(
        "sql_executor",
        nodes.check_sql_execution,
        {"success": "sql_result_analyzer", "failure": END},
    )
    
    workflow.add_edge("sql_result_analyzer", END)
    workflow.add_edge("chat_agent", END)
    
    logger.info("✅ LangGraph 工作流构建完成 (8个节点)")
    
    # 编译工作流（必须用 checkpointer 支持 interrupt 和 Command(resume=...)）
    compiled = workflow.compile(checkpointer=memory)
    return compiled
