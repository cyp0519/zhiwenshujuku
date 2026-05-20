"""
智问数据库 — 系统概览页面（查询统计 + ER 图）
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from frontend.utils import api_get, get_insights, get_data_dictionary
from frontend.styles import page_header

FONT_FAMILY = "Noto Sans SC"

TABLE_COLORS = {
    "movies": "#4A90D9",
    "users": "#4CAF50",
    "reviews": "#FF6B35",
    "query_history": "#9C27B0",
}

TABLE_LABELS = {
    "movies": "movies · 电影信息表",
    "users": "users · 用户信息表",
    "reviews": "reviews · 电影评论表",
    "query_history": "query_history · 查询历史表",
}

POSITIONS = {
    "movies": (2.2, 3.9),
    "users": (7, 3.9),
    "reviews": (4.6, 1.8),
    "query_history": (8.5, 1.8),
}

RELATIONSHIPS = [
    ("movies", "reviews", "1 : N", "被评论"),
    ("users", "reviews", "1 : N", "发表"),
]

BOX_W = 2.8
ROW_H = 0.22
HEADER_H = 0.42
MAX_VISIBLE_COLS = 5


def page():
    st.markdown(
        page_header(
            "📈", "系统概览",
            "查询性能统计与数据库关系图",
            gradient="linear-gradient(135deg, #E65100, #FF8F00)",
        ),
        unsafe_allow_html=True,
    )

    tab1, tab2, tab3 = st.tabs(["📊 查询统计", "🗃️ 数据库 ER 图", "📖 数据字典"])

    with tab1:
        _render_query_stats()

    with tab2:
        _render_er_diagram()

    with tab3:
        _render_data_dictionary()


def _render_query_stats():
    @st.cache_data(ttl=120)
    def _cached_query_stats():
        return api_get("/stats/queries")

    stats = _cached_query_stats()
    if not stats:
        st.warning("无法获取查询统计数据，请确保后端已启动。")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总查询数", stats.get("total_queries", 0))
    col2.metric("成功查询", stats.get("success_count", 0))
    col3.metric("成功率", f"{stats.get('success_rate', 0)}%")
    col4.metric("活跃会话", len(st.session_state.get("chat_messages", [])))

    daily = stats.get("daily_stats", [])
    if daily:
        st.markdown("### 📅 近期查询趋势")
        df = pd.DataFrame(daily)
        fig = px.bar(df, x="date", y="count",
                     labels={"date": "日期", "count": "查询次数"},
                     color_discrete_sequence=["#4A90D9"])
        fig.update_layout(
            template="plotly_white", height=260,
            margin=dict(l=10, r=10, t=10, b=10),
            font=dict(family=FONT_FAMILY, size=12, color="#333"),
        )
        fig.update_xaxes(tickfont=dict(family=FONT_FAMILY), gridcolor="#f5f5f5")
        fig.update_yaxes(tickfont=dict(family=FONT_FAMILY), gridcolor="#f5f5f5")
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    recent = stats.get("recent_queries", [])
    if recent:
        st.markdown("### 🕐 最近查询")
        for q in recent:
            icon = "✅" if q.get("execution_status") == "success" else "❌"
            st.markdown(f"{icon} **{q.get('question', '(无问题)')}** — {q.get('created_at', '')}")


def _render_er_diagram():
    @st.cache_data(ttl=300)
    def _cached_schema_relations():
        return api_get("/schema/relations")

    relations = _cached_schema_relations()
    if not relations:
        st.warning("无法获取数据库关系信息。")
        return

    tables = relations.get("tables", {})
    foreign_keys = relations.get("foreign_keys", [])

    # ========== 可视化 ER 图 ==========
    st.markdown("### 🔗 数据库关系图")
    _render_visual_er(tables, foreign_keys)

    # ========== Mermaid 代码（可折叠） ==========
    with st.expander("📝 Mermaid ER 图源码", expanded=False):
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
    }
    movies ||--o{ reviews : "被评论"
    users ||--o{ reviews : "发表"
```"""
        st.markdown(mermaid)

    # ========== 表结构详情 ==========
    st.markdown("### 📋 表结构详情")
    for table_name, table_info in tables.items():
        color = TABLE_COLORS.get(table_name, "#666")
        with st.expander(f"📄 {table_name} — {table_info.get('description', '')}", expanded=False):
            rows = []
            for col in table_info.get("columns", []):
                tag = ""
                if "(PK)" in col:
                    col_clean = col.replace(" (PK)", "")
                    tag = "🔑 主键"
                elif "(FK)" in col:
                    col_clean = col.replace(" (FK)", "")
                    tag = "🔗 外键"
                else:
                    col_clean = col
                    tag = ""
                rows.append({"字段": col_clean, "说明": tag})
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


def _render_visual_er(tables: dict, foreign_keys: list):
    """渲染专业的 ER 图 —— 表格框 + 关系连线"""

    def _parse_columns(name: str, columns: list[str]):
        """解析列信息，返回 [(col_name, tag), ...]，最多展示 MAX_VISIBLE_COLS 个"""
        parsed = []
        for col in columns:
            if " (PK)" in col:
                parsed.append((col.replace(" (PK)", ""), "PK"))
            elif " (FK)" in col:
                parsed.append((col.replace(" (FK)", ""), "FK"))
            else:
                parsed.append((col, ""))
        if len(parsed) > MAX_VISIBLE_COLS:
            parsed = parsed[:MAX_VISIBLE_COLS - 1] + [("...", "")]
        return parsed

    fig = go.Figure()

    # ---------- 绘制表格框 ----------
    for name, (cx, cy) in POSITIONS.items():
        if name not in tables:
            continue

        color = TABLE_COLORS.get(name, "#666")
        columns = _parse_columns(name, tables[name].get("columns", []))
        n_cols = len(columns)
        box_h = HEADER_H + n_cols * ROW_H + 0.12
        half_w = BOX_W / 2
        half_h = box_h / 2

        # 表格主体（白色背景）
        fig.add_shape(
            type="rect",
            x0=cx - half_w, y0=cy - half_h, x1=cx + half_w, y1=cy + half_h,
            line=dict(color=color, width=2),
            fillcolor="white",
            layer="below",
        )

        # 表头（彩色背景）
        fig.add_shape(
            type="rect",
            x0=cx - half_w, y0=cy + half_h - HEADER_H, x1=cx + half_w, y1=cy + half_h,
            line=dict(color=color, width=2),
            fillcolor=color,
            layer="below",
        )

        # 表头文字
        label = TABLE_LABELS.get(name, name)
        fig.add_annotation(
            x=cx, y=cy + half_h - HEADER_H / 2,
            text=f"<b>{label}</b>",
            showarrow=False,
            font=dict(family=FONT_FAMILY, size=11, color="white"),
            align="center",
        )

        # 列行
        row_top = cy + half_h - HEADER_H
        for i, (col_name, tag) in enumerate(columns):
            row_cy = row_top - ROW_H / 2 - i * ROW_H

            # 行分隔线
            if i > 0:
                fig.add_shape(
                    type="line",
                    x0=cx - half_w + 0.12, y0=row_cy + ROW_H / 2,
                    x1=cx + half_w - 0.12, y1=row_cy + ROW_H / 2,
                    line=dict(color="#E8ECF0", width=0.5),
                    layer="below",
                )

            # 列名
            icon = "🔑" if tag == "PK" else ("🔗" if tag == "FK" else "")
            text = f"{icon} {col_name}" if icon else f"  {col_name}"
            text_color = "#1565C0" if tag == "PK" else ("#E65100" if tag == "FK" else "#444")

            fig.add_annotation(
                x=cx - half_w + 0.18, y=row_cy,
                text=text,
                showarrow=False,
                font=dict(family="monospace", size=9.5, color=text_color),
                xanchor="left",
            )

            # 类型标签
            if tag:
                fig.add_annotation(
                    x=cx + half_w - 0.18, y=row_cy,
                    text=f"<i>{tag}</i>",
                    showarrow=False,
                    font=dict(family=FONT_FAMILY, size=8, color=text_color),
                    xanchor="right",
                )

    # ---------- 绘制关系连线 ----------
    for src, dst, cardinality, label in RELATIONSHIPS:
        if src not in POSITIONS or dst not in POSITIONS:
            continue

        sx, sy = POSITIONS[src]
        dx, dy = POSITIONS[dst]
        src_color = TABLE_COLORS.get(src, "#666")

        # 计算连线起止点（从框底部到框顶部）
        src_half_h = _box_half_size(src, tables)
        dst_half_h = _box_half_size(dst, tables)
        x0, y0 = sx, sy - src_half_h
        x1, y1 = dx, dy + dst_half_h

        # 用三折线代替直线，更符合 ER 图规范
        mid_y = (y0 + y1) / 2
        fig.add_shape(
            type="line",
            x0=x0, y0=y0, x1=x0, y1=mid_y,
            line=dict(color=src_color, width=2),
        )
        fig.add_shape(
            type="line",
            x0=x0, y0=mid_y, x1=x1, y1=mid_y,
            line=dict(color=src_color, width=2),
        )
        fig.add_shape(
            type="line",
            x0=x1, y0=mid_y, x1=x1, y1=y1,
            line=dict(color=src_color, width=2),
        )

        # "多" 端标记 (小填充圆)
        fig.add_trace(go.Scatter(
            x=[x1], y=[y1 + 0.04],
            mode="markers",
            marker=dict(size=10, color=src_color, symbol="circle"),
            showlegend=False,
            hoverinfo="skip",
        ))

        # 关系标签
        label_x = (x0 + x1) / 2 + 0.3
        label_y = mid_y + 0.15
        fig.add_annotation(
            x=label_x, y=label_y,
            text=f"<b>{cardinality}</b>  {label}",
            showarrow=False,
            font=dict(family=FONT_FAMILY, size=10, color="#555"),
            bgcolor="rgba(255,255,255,0.9)",
            borderpad=4,
            bordercolor="#E0E0E0",
        )

    # ---------- 图例 ----------
    legend_x = 9.8
    legend_start_y = 4.2
    legend_items = [
        ("🔑  主键 Primary Key", "#1565C0"),
        ("🔗  外键 Foreign Key", "#E65100"),
        ("●  一对多关系", "#888"),
    ]
    fig.add_annotation(
        x=legend_x, y=legend_start_y + 0.2,
        text="<b>图例</b>",
        showarrow=False,
        font=dict(family=FONT_FAMILY, size=12, color="#333"),
        xanchor="right",
    )
    for i, (text, color) in enumerate(legend_items):
        fig.add_annotation(
            x=legend_x, y=legend_start_y - 0.2 - i * 0.28,
            text=text,
            showarrow=False,
            font=dict(family=FONT_FAMILY, size=10.5, color=color),
            xanchor="right",
        )

    # ---------- 布局 ----------
    fig.update_layout(
        template="plotly_white",
        height=420,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(range=[0, 11], showgrid=False, zeroline=False, showticklabels=False, fixedrange=True),
        yaxis=dict(range=[0, 5.5], showgrid=False, zeroline=False, showticklabels=False, fixedrange=True),
        font=dict(family=FONT_FAMILY),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        dragmode=False,
    )

    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _box_half_size(name: str, tables: dict):
    """返回指定表格框的半高"""
    if name not in tables:
        return 0.75
    columns = tables[name].get("columns", [])
    n_cols = min(len(columns), MAX_VISIBLE_COLS)
    box_h = HEADER_H + n_cols * ROW_H + 0.12
    return box_h / 2


def _render_data_dictionary():
    """渲染数据字典 tab"""
    dd = get_data_dictionary()
    if not dd:
        st.warning("无法加载数据字典。")
        return

    for table_name, table_info in dd.items():
        if not isinstance(table_info, dict):
            continue
        color = TABLE_COLORS.get(table_name, "#666")
        with st.expander(f"📄 {table_name} — {table_info.get('name', '')}", expanded=False):
            st.markdown(f"_{table_info.get('description', '')}_")
            rows = []
            for col in table_info.get("columns", []):
                key_tag = ""
                if col.get("key") == "PK":
                    key_tag = "🔑 主键"
                elif col.get("key") == "FK":
                    key_tag = "🔗 外键"
                rows.append({
                    "字段": col.get("field", ""),
                    "类型": col.get("type", ""),
                    "说明": col.get("description", ""),
                    "约束": key_tag,
                })
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
