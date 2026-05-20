"""
智问数据库 — Streamlit 主应用
"""

import streamlit as st
from frontend.styles import GLOBAL_CSS, metric_cards_html
from frontend.utils import get_insights, get_health
from frontend.views.对话查询 import page as chat_page
from frontend.views.SQL编辑器 import page as sql_page
from frontend.views.数据可视化 import page as viz_page
from frontend.views.查询历史 import page as history_page
from frontend.views.系统概览 import page as overview_page

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
        "<hr style='border-color: rgba(30,58,95,0.12);'>",
        unsafe_allow_html=True,
    )

    # 数据库状态（带缓存）
    health = get_health()
    db_status = "🟢 已连接" if health and health.get("database") == "connected" else "🔴 未连接"
    st.markdown(f"**数据库状态**: {db_status}")

    # 统计概览（带缓存，使用统一卡片样式）
    insights = get_insights()
    if insights:
        st.markdown("**数据概览**")
        row1 = [
            ("🎬 电影总数", str(insights.get("total_movies", 0)), "#1E3A5F"),
            ("⭐ 平均评分", str(insights.get("avg_rating", 0)), "#E65100"),
        ]
        row2 = [
            ("👥 用户数", str(insights.get("total_users", 0)), "#2E7D32"),
            ("📝 评论数", str(insights.get("total_reviews", 0)), "#6A1B9A"),
        ]
        st.markdown(metric_cards_html(row1), unsafe_allow_html=True)
        st.markdown(metric_cards_html(row2), unsafe_allow_html=True)

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
