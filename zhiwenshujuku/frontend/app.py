"""
智问数据库 — Streamlit 主应用
"""

import streamlit as st
from frontend.styles import GLOBAL_CSS
from frontend.views.智能问答 import page as qa_page
from frontend.views.SQL编辑器 import page as sql_page
from frontend.views.数据可视化 import page as viz_page
from frontend.views.查询历史 import page as history_page
from frontend.views.系统概览 import page as overview_page, _render_index_management as index_page

# ========== 页面配置 ==========
st.set_page_config(
    page_title="基于检索增强（RAG）与安全校验机制的电影数据智能问答系统",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ========== 全局样式 ==========
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# ========== 页面头部 ==========
st.markdown(
    """
    <div style="text-align: center; margin-bottom: 24px; padding-bottom: 12px; border-bottom: 1px solid #E4DDD4;">
        <h1 style="font-family: 'Noto Serif SC', serif; font-size: 1.7rem; font-weight: 700; color: #2C2417; margin: 0;">基于检索增强（RAG）与安全校验机制的电影数据智能问答系统</h1>
    </div>
    """,
    unsafe_allow_html=True,
)

# ========== 水平选项卡导航 ==========
tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎬 智能问答",
    "🏠 数据库概览",
    "✏️ SQL 终端",
    "📊 数据分析",
    "📜 查询审计",
    "⚡ 索引管理"
])

with tab0:
    qa_page()

with tab1:
    overview_page()

with tab2:
    sql_page()

with tab3:
    viz_page()

with tab4:
    history_page()

with tab5:
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    index_page()
