"""
智问数据库 — 对话查询页面 (主界面)
"""

import uuid
import streamlit as st
from frontend.utils import chat
from frontend.styles import page_header


def page():
    # ========== 状态初始化 ==========
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "chat_session_id" not in st.session_state:
        st.session_state.chat_session_id = str(uuid.uuid4())
    if "pending_sql" not in st.session_state:
        st.session_state.pending_sql = None

    # ========== 页面标题 ==========
    st.markdown(
        page_header(
            "💬", "对话查询",
            "用自然语言描述你的问题，AI 自动生成 SQL 查询并分析结果",
        ),
        unsafe_allow_html=True,
    )

    # ========== 功能提示 ==========
    with st.expander("试试这样问", expanded=len(st.session_state.chat_messages) == 0):
        examples = [
            "评分最高的10部电影有哪些？",
            "2000年后评分超过9分的有哪些电影？",
            "周星驰导演过哪些电影？",
            "各国电影的平均评分是多少？",
            "宫崎骏的电影作品列表",
            "近十年每年上映了多少部电影？",
        ]
        cols = st.columns(3)
        for i, ex in enumerate(examples):
            with cols[i % 3]:
                if st.button(f"{ex}", key=f"ex_{i}", width="stretch"):
                    st.session_state.chat_messages.append(("user", ex))
                    st.session_state._pending_input = ex
                    st.rerun()

    # ========== 对话容器 ==========
    chat_container = st.container()

    with chat_container:
        for role, content in st.session_state.chat_messages:
            if role == "user":
                st.markdown(
                    f'<div class="user-bubble-container"><div class="user-bubble">\n\n{content}\n\n</div></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="assistant-bubble-container"><div class="assistant-bubble">\n\n{content}\n\n</div></div>',
                    unsafe_allow_html=True,
                )

    # ========== 输入区域 ==========
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    input_col, btn_col = st.columns([6, 1])
    with input_col:
        user_input = st.chat_input(
            "输入你的问题，例如：评分最高的10部电影有哪些？", key="chat_input"
        )

    with btn_col:
        if st.button("🔄 新会话", width="stretch"):
            st.session_state.chat_messages = []
            st.session_state.chat_session_id = str(uuid.uuid4())
            st.session_state.pending_sql = None
            st.rerun()

    # ========== 处理输入 ==========
    pending = st.session_state.pop("_pending_input", None)
    if user_input or pending:
        prompt = user_input or pending
        if user_input:
            st.session_state.chat_messages.append(("user", user_input))

        with st.spinner("思考中..."):
            result = chat(prompt, st.session_state.chat_session_id)

        if result:
            msg = result.get("message", "")
            st.session_state.pending_sql = None
            st.session_state.chat_messages.append(("assistant", msg))
        else:
            st.session_state.chat_messages.append(
                ("assistant", "❌ 抱歉，处理请求时出错，请稍后再试。")
            )

        st.rerun()
