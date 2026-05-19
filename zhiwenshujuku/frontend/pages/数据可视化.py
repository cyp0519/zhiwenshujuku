"""
智问数据库 — 数据可视化页面
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

import streamlit as st
import pandas as pd
import plotly.express as px
from frontend.utils import get_insights, execute_sql
from frontend.styles import page_header

CHART_QUERIES = {
    "rating_dist": "SELECT CAST(ROUND(rating) AS INTEGER) as score_bin, COUNT(*) as count FROM movies GROUP BY score_bin ORDER BY score_bin",
    "yearly": "SELECT year, COUNT(*) as count FROM movies WHERE year > 0 GROUP BY year ORDER BY year",
    "genre": "SELECT genre, COUNT(*) as count FROM movies GROUP BY genre ORDER BY count DESC",
    "country": "SELECT country, COUNT(*) as count FROM movies GROUP BY country ORDER BY count DESC",
    "top10": "SELECT title, rating FROM movies ORDER BY rating DESC LIMIT 10",
    "duration": "SELECT title, duration FROM movies WHERE duration > 0 ORDER BY duration DESC LIMIT 15",
}


def _fetch_one(key: str, sql: str) -> tuple[str, pd.DataFrame | None]:
    """执行单条 SQL 查询"""
    result = execute_sql(sql)
    if result and result.get("success"):
        return key, pd.DataFrame(result["data"])
    return key, None


@st.cache_data(ttl=60)
def _load_chart_data():
    """并行加载预设图表数据（带缓存）"""
    charts = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {
            pool.submit(_fetch_one, key, sql): key
            for key, sql in CHART_QUERIES.items()
        }
        for future in as_completed(futures):
            key, df = future.result()
            if df is not None and not df.empty:
                charts[key] = df
    return charts


def _render_chart(df: pd.DataFrame, chart_type: str, **kwargs):
    """渲染单个 Plotly 图表"""
    kwargs.setdefault("template", "plotly_white")
    kwargs.setdefault("height", 300)
    kwargs.setdefault("margin", dict(l=10, r=10, t=30, b=10))
    kwargs.setdefault("font", dict(family="Noto Sans SC"))

    if chart_type == "bar":
        fig = px.bar(df, **kwargs)
    elif chart_type == "line":
        fig = px.line(df, **kwargs)
    elif chart_type == "pie":
        fig = px.pie(df, **kwargs)
    else:
        fig = px.bar(df, **kwargs)

    fig.update_layout(**{k: v for k, v in kwargs.items() if k in ("height", "margin", "font", "template")})
    return fig


def page():
    # ========== 页面标题 ==========
    st.markdown(
        page_header(
            "📊", "数据可视化",
            "电影数据库的可视化分析看板",
            gradient="linear-gradient(135deg, #2E7D32, #4CAF50)",
        ),
        unsafe_allow_html=True,
    )

    # ========== 统计概览卡片 ==========
    insights = get_insights()
    if insights:
        cols = st.columns(5)
        metrics = [
            ("🎬 电影总数", insights.get("total_movies", 0)),
            ("⭐ 平均评分", insights.get("avg_rating", 0)),
            ("👥 用户数", insights.get("total_users", 0)),
            ("📝 评论数", insights.get("total_reviews", 0)),
            ("🎯 导演数", insights.get("total_directors", 0)),
        ]
        for i, (label, value) in enumerate(metrics):
            cols[i].markdown(
                f"""
            <div style="background: white; border-radius: 12px; padding: 16px; text-align: center;
                        border: 1px solid #E8ECF0; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                <div style="font-size: 2rem; font-weight: 700; color: #1E3A5F;">{value}</div>
                <div style="font-size: 0.8rem; color: #888; margin-top: 4px;">{label}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

    # ========== 预设图表 ==========
    st.markdown("### 📈 预设分析看板")

    with st.spinner("📊 加载分析数据..."):
        charts_data = _load_chart_data()

    if not charts_data:
        st.warning("⚠️ 无法加载分析数据，请确保后端服务和数据库已启动。")
        return

    row1 = st.columns(2)
    row2 = st.columns(2)
    row3 = st.columns(2)

    # 1. 评分分布
    with row1[0]:
        if "rating_dist" in charts_data and not charts_data["rating_dist"].empty:
            df = charts_data["rating_dist"]
            fig = _render_chart(df, "bar", x="score_bin", y="count",
                                title="🎯 电影评分分布",
                                labels={"score_bin": "评分区间", "count": "电影数量"},
                                color="count", color_continuous_scale="Blues")
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, width="stretch")

    # 2. 年度趋势
    with row1[1]:
        if "yearly" in charts_data and not charts_data["yearly"].empty:
            df = charts_data["yearly"]
            fig = _render_chart(df, "line", x="year", y="count",
                                title="📅 每年电影数量",
                                labels={"year": "年份", "count": "电影数量"},
                                markers=True)
            fig.update_traces(line_color="#FF6B35", marker=dict(size=6))
            st.plotly_chart(fig, width="stretch")

    # 3. 类型分布
    with row2[0]:
        if "genre" in charts_data and not charts_data["genre"].empty:
            df = charts_data["genre"].head(10)
            fig = _render_chart(df, "pie", values="count", names="genre",
                                title="🎭 电影类型分布",
                                color_discrete_sequence=px.colors.qualitative.Bold)
            fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig, width="stretch")

    # 4. 国家分布
    with row2[1]:
        if "country" in charts_data and not charts_data["country"].empty:
            df = charts_data["country"].head(8)
            fig = _render_chart(df, "bar", x="country", y="count",
                                title="🌍 国家/地区分布",
                                labels={"country": "国家", "count": "电影数量"},
                                color="count", color_continuous_scale="Greens",
                                text="count")
            fig.update_traces(textposition="outside")
            fig.update_layout(xaxis_tickangle=-30)
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, width="stretch")

    # 5. Top10评分
    with row3[0]:
        if "top10" in charts_data and not charts_data["top10"].empty:
            df = charts_data["top10"]
            fig = _render_chart(df, "bar", y="title", x="rating",
                                title="⭐ 评分最高 Top 10",
                                labels={"title": "", "rating": "评分"},
                                color="rating", color_continuous_scale="Reds",
                                orientation="h", text="rating",
                                height=350)
            fig.update_traces(textposition="outside", texttemplate="%{text:.1f}")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, width="stretch")

    # 6. 时长Top15
    with row3[1]:
        if "duration" in charts_data and not charts_data["duration"].empty:
            df = charts_data["duration"]
            fig = _render_chart(df, "bar", y="title", x="duration",
                                title="⏱️ 最长电影 Top 15",
                                labels={"title": "", "duration": "时长(分钟)"},
                                color="duration", color_continuous_scale="Purples",
                                orientation="h", text="duration",
                                height=350)
            fig.update_traces(textposition="outside")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, width="stretch")

    # ========== 自定义查询 ==========
    st.markdown("---")
    st.markdown("### 🔍 自定义可视化查询")

    custom_sql = st.text_area(
        "输入 SQL 查询，结果将自动可视化",
        value="SELECT country, COUNT(*) as count, ROUND(AVG(rating),2) as avg_rating FROM movies GROUP BY country ORDER BY count DESC LIMIT 10",
        height=80,
        label_visibility="collapsed",
    )

    if st.button("▶️ 查询并可视化", type="primary"):
        with st.spinner("🔄 查询中..."):
            result = execute_sql(custom_sql)

        if result and result.get("success") and result.get("data"):
            df = pd.DataFrame(result["data"])
            st.success(f"✅ 查询成功，返回 {len(df)} 行")

            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
            text_cols = df.select_dtypes(exclude=["number"]).columns.tolist()

            if len(numeric_cols) >= 1 and len(text_cols) >= 1:
                chart_type = st.selectbox("图表类型", ["柱状图", "折线图", "饼图", "散点图", "面积图"],
                                          key="custom_chart_type")
                x_col = st.selectbox("X 轴", text_cols, key="custom_x")
                y_col = st.selectbox("Y 轴", numeric_cols, key="custom_y")

                color_schemes = ["Blues", "Reds", "Greens", "Purples", "Oranges", "Viridis", "Plasma"]
                colors = st.selectbox("配色方案", color_schemes)

                chart_map = {
                    "柱状图": lambda: px.bar(df, x=x_col, y=y_col, color=y_col, color_continuous_scale=colors),
                    "折线图": lambda: px.line(df, x=x_col, y=y_col, markers=True, color_discrete_sequence=["#FF6B35"]),
                    "饼图": lambda: px.pie(df, names=x_col, values=y_col, color_discrete_sequence=px.colors.qualitative.Bold),
                    "散点图": lambda: px.scatter(df, x=x_col, y=y_col, size=y_col, color=y_col, color_continuous_scale=colors),
                    "面积图": lambda: px.area(df, x=x_col, y=y_col, color_discrete_sequence=["#2E7D32"]),
                }
                fig = chart_map.get(chart_type, chart_map["柱状图"])()
                fig.update_layout(template="plotly_white", font=dict(family="Noto Sans SC"),
                                  margin=dict(l=20, r=20, t=20, b=20), height=400)
                st.plotly_chart(fig, width="stretch")

                with st.expander("📋 查看数据表格"):
                    st.dataframe(df, width="stretch", hide_index=True)
            else:
                st.dataframe(df, width="stretch", hide_index=True)
        else:
            error = result.get("error", "无返回数据") if result else "连接失败"
            st.error(f"❌ {error}")
