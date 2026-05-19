"""
智问数据库 — 系统概览页面（查询统计 + ER 图）
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from frontend.utils import api_get, get_insights
from frontend.styles import page_header


def page():
    st.markdown(
        page_header(
            "📈", "系统概览",
            "查询性能统计与数据库关系图",
            gradient="linear-gradient(135deg, #E65100, #FF8F00)",
        ),
        unsafe_allow_html=True,
    )

    tab1, tab2 = st.tabs(["📊 查询统计", "🗃️ 数据库 ER 图"])

    # ========== 查询统计 ==========
    with tab1:
        _render_query_stats()

    # ========== ER 图 ==========
    with tab2:
        _render_er_diagram()


def _render_query_stats():
    """渲染查询统计面板"""
    stats = api_get("/stats/queries")
    if not stats:
        st.warning("无法获取查询统计数据，请确保后端已启动。")
        return

    # 概览指标
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总查询数", stats.get("total_queries", 0))
    col2.metric("成功查询", stats.get("success_count", 0))
    col3.metric("成功率", f"{stats.get('success_rate', 0)}%")
    col4.metric("活跃会话", len(st.session_state.get("chat_messages", [])))

    # 每日趋势
    daily = stats.get("daily_stats", [])
    if daily:
        st.markdown("### 📅 近期查询趋势")
        df = pd.DataFrame(daily)
        fig = px.bar(df, x="date", y="count",
                     labels={"date": "日期", "count": "查询次数"},
                     color_discrete_sequence=["#1E3A5F"])
        fig.update_layout(template="plotly_white", height=250,
                          margin=dict(l=10, r=10, t=10, b=10),
                          font=dict(family="Noto Sans SC"))
        st.plotly_chart(fig, width="stretch")

    # 最近查询
    recent = stats.get("recent_queries", [])
    if recent:
        st.markdown("### 🕐 最近查询")
        for q in recent:
            status = "✅" if q.get("execution_status") == "success" else "❌"
            st.markdown(f"{status} **{q.get('question', '(无问题)')}** — {q.get('created_at', '')}")


def _render_er_diagram():
    """渲染数据库 ER 图"""
    relations = api_get("/schema/relations")
    if not relations:
        st.warning("无法获取数据库关系信息。")
        return

    tables = relations.get("tables", {})
    foreign_keys = relations.get("foreign_keys", [])

    # 表信息展示
    st.markdown("### 📋 数据库表结构")

    for table_name, table_info in tables.items():
        with st.expander(f"📄 {table_name} — {table_info.get('description', '')}", expanded=False):
            cols_data = {"字段": [], "说明": []}
            for col in table_info.get("columns", []):
                if "(PK)" in col:
                    cols_data["字段"].append(col.replace(" (PK)", ""))
                    cols_data["说明"].append("🔑 主键")
                elif "(FK)" in col:
                    cols_data["字段"].append(col.replace(" (FK)", ""))
                    cols_data["说明"].append("🔗 外键")
                else:
                    cols_data["字段"].append(col)
                    cols_data["说明"].append("")
            st.dataframe(pd.DataFrame(cols_data), hide_index=True, width="stretch")

    # 关系图（Mermaid 格式展示）
    st.markdown("### 🔗 表关系图")

    mermaid = """```mermaid
erDiagram
    movies {
        INTEGER id PK
        TEXT title
        INTEGER year
        TEXT director
        TEXT genre
        REAL rating
    }
    users {
        INTEGER id PK
        TEXT username
        TEXT city
        INTEGER age
        TEXT gender
    }
    reviews {
        INTEGER id PK
        INTEGER movie_id FK
        INTEGER user_id FK
        REAL rating
        TEXT review_text
    }
    query_history {
        INTEGER id PK
        TEXT session_id
        TEXT question
        TEXT sql_executed
        TEXT execution_status
        INTEGER is_favorite
    }
    movies ||--o{ reviews : "被评论"
    users ||--o{ reviews : "发表"
```"""

    st.markdown(mermaid)

    # 也用 Plotly 画一个简化的关系图
    fig = go.Figure()

    # 表节点位置
    positions = {
        "movies": (0, 1),
        "users": (2, 1),
        "reviews": (1, 0),
        "query_history": (3, 0),
    }

    # 画表节点
    for name, (x, y) in positions.items():
        desc = tables.get(name, {}).get("description", "")
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers+text",
            marker=dict(size=60, color="#1E3A5F"),
            text=[name], textposition="bottom center",
            textfont=dict(size=14, color="#1E3A5F"),
            hovertext=[f"{name}\n{desc}"],
            showlegend=False,
        ))

    # 画关系线
    fk_lines = [
        ("movies", "reviews"),
        ("users", "reviews"),
    ]
    for src, dst in fk_lines:
        x0, y0 = positions[src]
        x1, y1 = positions[dst]
        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[y0, y1], mode="lines",
            line=dict(width=2, color="#FF6B35"),
            showlegend=False,
            hoverinfo="skip",
        ))

    fig.update_layout(
        template="plotly_white",
        height=350,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        font=dict(family="Noto Sans SC"),
    )
    st.plotly_chart(fig, width="stretch")
