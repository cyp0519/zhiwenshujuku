"""
智问数据库 — Streamlit 主应用
"""

import streamlit as st
from frontend.styles import GLOBAL_CSS
from frontend.utils import get_insights, api_get
from frontend.pages.对话查询 import page as chat_page
from frontend.pages.SQL编辑器 import page as sql_page
from frontend.pages.数据可视化 import page as viz_page
from frontend.pages.查询历史 import page as history_page
from frontend.pages.系统概览 import page as overview_page

# ========== 页面配置 ==========
st.set_page_config(
    page_title="智问数据库",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ========== 全局样式 ==========
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# ========== 侧边栏 ==========
with st.sidebar:
    st.markdown(
        """
    <div class="sidebar-header">
        <div class="app-name">🎬 智问数据库</div>
        <div class="app-sub">自然语言 → SQL → 数据洞察</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # 导航页面定义
    pages = {
        "💬 对话查询": chat_page,
        "✏️ SQL 编辑器": sql_page,
        "📊 数据可视化": viz_page,
        "📜 查询历史": history_page,
        "📈 系统概览": overview_page,
    }

    # 侧边栏导航按钮
    st.markdown("### 导航")
    if "page" not in st.session_state:
        st.session_state.page = "💬 对话查询"

    for label in pages:
        is_active = st.session_state.page == label
        if st.button(
            label,
            key=f"nav_{label}",
            width="stretch",
            type="primary" if is_active else "secondary",
        ):
            st.session_state.page = label
            st.rerun()

    st.markdown(
        "<hr style='border-color: rgba(255,255,255,0.1);'>",
        unsafe_allow_html=True,
    )

    # 数据库状态
    health = api_get("/health")
    db_status = "🟢 已连接" if health and health.get("database") == "connected" else "🔴 未连接"
    st.markdown(f"**数据库状态**: {db_status}")

    # 统计概览
    insights = get_insights()
    if insights:
        st.markdown("**数据概览**")
        cols = st.columns(2)
        cols[0].metric("🎬 电影", insights.get("total_movies", 0))
        cols[1].metric("⭐ 均分", insights.get("avg_rating", 0))
        cols[0].metric("👥 用户", insights.get("total_users", 0))
        cols[1].metric("📝 评论", insights.get("total_reviews", 0))

    st.markdown(
        """
    <div class="sidebar-footer">
        智问数据库 v1.0<br>
        现代数据库系统课程设计
    </div>
    """,
        unsafe_allow_html=True,
    )

# ========== 渲染当前页面 ==========
page_fn = pages.get(st.session_state.page, chat_page)
page_fn()
