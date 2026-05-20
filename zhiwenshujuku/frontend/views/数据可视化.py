"""
智问数据库 — 数据可视化页面
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from frontend.utils import get_insights, execute_sql
from frontend.styles import page_header, metric_cards_html

CHART_QUERIES = {
    "rating_dist": "SELECT CAST(ROUND(rating) AS INTEGER) as score_bin, COUNT(*) as count FROM movies GROUP BY score_bin ORDER BY score_bin",
    "yearly": "SELECT year, COUNT(*) as count FROM movies WHERE year > 0 GROUP BY year ORDER BY year",
    "genre": "SELECT genre, COUNT(*) as count FROM movies GROUP BY genre ORDER BY count DESC",
    "country": "SELECT country, COUNT(*) as count FROM movies GROUP BY country ORDER BY count DESC",
    "top10": "SELECT title, rating FROM movies ORDER BY rating DESC LIMIT 10",
    "duration": "SELECT title, duration FROM movies WHERE duration > 0 ORDER BY duration DESC LIMIT 15",
    "scatter_data": "SELECT title, rating, duration, genre, year FROM movies WHERE rating > 0 AND duration > 0 AND duration < 400",
    "decade_stats": "SELECT (year/10)*10 as decade, COUNT(*) as count, ROUND(AVG(rating),2) as avg_rating FROM movies WHERE year > 0 GROUP BY decade ORDER BY decade",
    "director_top": "SELECT director, COUNT(*) as movie_count, ROUND(AVG(rating),2) as avg_rating FROM movies GROUP BY director HAVING movie_count >= 3 ORDER BY avg_rating DESC LIMIT 15",
    "genre_rating_box": "SELECT genre, rating FROM movies WHERE rating > 0",
}

MOVIE_COLUMNS = ["title", "year", "director", "genre", "country", "language", "duration", "rating", "rating_count"]
MOVIE_COL_LABELS = {"title": "电影名称", "year": "年份", "director": "导演", "genre": "类型", "country": "国家", "language": "语言", "duration": "时长(分)", "rating": "评分", "rating_count": "评分人数"}
PAGE_SIZE = 20

CHART_COLORS = {
    "blue": px.colors.sequential.Blues_r,
    "green": px.colors.sequential.Greens_r,
    "red": px.colors.sequential.Reds_r,
    "purple": px.colors.sequential.Purples_r,
    "orange": px.colors.sequential.Oranges_r,
}

FONT_FAMILY = "Noto Sans SC"
LAYOUT_DEFAULTS = dict(
    template="plotly_white",
    font=dict(family=FONT_FAMILY, size=12, color="#333"),
    margin=dict(l=20, r=20, t=50, b=20),
    height=340,
)


def _fetch_one(key: str, sql: str) -> tuple[str, pd.DataFrame | None]:
    result = execute_sql(sql)
    if result and result.get("success"):
        return key, pd.DataFrame(result["data"])
    return key, None


@st.cache_data(ttl=60)
def _load_chart_data():
    charts = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(_fetch_one, key, sql): key for key, sql in CHART_QUERIES.items()}
        for future in as_completed(futures):
            key, df = future.result()
            if df is not None and not df.empty:
                charts[key] = df
    return charts


def _render_chart(df: pd.DataFrame, chart_type: str, **kwargs):
    """渲染 Plotly 图表，自动分离布局参数并应用统一样式"""
    layout_keys = ("height", "margin", "font", "template", "showlegend")
    layout_kwargs = {k: kwargs.pop(k) for k in layout_keys if k in kwargs}

    chart_fn = {
        "bar": px.bar,
        "line": px.line,
        "pie": px.pie,
        "scatter": px.scatter,
        "treemap": px.treemap,
        "box": px.box,
    }
    fn = chart_fn.get(chart_type, px.bar)

    if chart_type == "treemap" and "color" not in kwargs:
        kwargs.setdefault("color_continuous_scale", "Blues")

    fig = fn(df, **kwargs)

    cfg = dict(LAYOUT_DEFAULTS)
    cfg.update(layout_kwargs)
    fig.update_layout(**cfg)
    fig.update_xaxes(tickfont=dict(family=FONT_FAMILY, size=10), title_font=dict(family=FONT_FAMILY, size=12), gridcolor="#f0f0f0")
    fig.update_yaxes(tickfont=dict(family=FONT_FAMILY, size=10), title_font=dict(family=FONT_FAMILY, size=12), gridcolor="#f0f0f0")
    return fig


@st.cache_data(ttl=300)
def _load_movie_filters():
    genres, countries, languages = [], [], []
    for col, lst in [("genre", genres), ("country", countries), ("language", languages)]:
        r = execute_sql(f"SELECT DISTINCT {col} FROM movies ORDER BY {col}")
        if r and r.get("data"):
            lst.extend(item[col] for item in r["data"])
    return genres, countries, languages


def _render_movie_table():
    genres, countries, languages = _load_movie_filters()

    f1, f2, f3, f4 = st.columns(4)
    with f1:
        search = st.text_input("🔍 搜索", placeholder="电影名称、导演...", label_visibility="collapsed")
        c1, c2 = st.columns(2)
        with c1:
            year_from = st.number_input("年份从", value=1900, min_value=1900, max_value=2030, step=1, label_visibility="collapsed")
        with c2:
            year_to = st.number_input("年份至", value=2030, min_value=1900, max_value=2030, step=1, label_visibility="collapsed")
    with f2:
        genre_filter = st.selectbox("类型", ["全部"] + genres, label_visibility="collapsed")
        rating_from = st.slider("评分 ≥", 0.0, 10.0, 0.0, 0.1, label_visibility="collapsed")
    with f3:
        country_filter = st.selectbox("国家", ["全部"] + countries, label_visibility="collapsed")
        rating_to = st.slider("评分 ≤", 0.0, 10.0, 10.0, 0.1, label_visibility="collapsed")
    with f4:
        language_filter = st.selectbox("语言", ["全部"] + languages, label_visibility="collapsed")
        sort_col = st.selectbox("排序", list(MOVIE_COL_LABELS.keys()), format_func=lambda x: MOVIE_COL_LABELS[x], label_visibility="collapsed")
        sort_dir = st.radio("方向", ["↓ 降序", "↑ 升序"], horizontal=True, label_visibility="collapsed")

    where = []
    if search:
        s = search.replace("'", "''")
        where.append(f"(title LIKE '%{s}%' OR original_title LIKE '%{s}%' OR director LIKE '%{s}%')")
    if year_from > 1900:
        where.append(f"year >= {year_from}")
    if year_to < 2030:
        where.append(f"year <= {year_to}")
    if genre_filter != "全部":
        where.append(f"genre = '{genre_filter}'")
    if country_filter != "全部":
        where.append(f"country = '{country_filter}'")
    if language_filter != "全部":
        where.append(f"language = '{language_filter}'")
    if rating_from > 0:
        where.append(f"rating >= {rating_from}")
    if rating_to < 10:
        where.append(f"rating <= {rating_to}")

    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    order_dir = "DESC" if "降序" in sort_dir else "ASC"
    columns_str = ", ".join(MOVIE_COLUMNS)

    if "movie_page" not in st.session_state:
        st.session_state.movie_page = 0

    count_sql = f"SELECT COUNT(*) as cnt FROM movies {where_clause}"
    count_result = execute_sql(count_sql)
    total = count_result["data"][0]["cnt"] if count_result and count_result.get("data") else 0

    query_sql = f"SELECT {columns_str} FROM movies {where_clause} ORDER BY {sort_col} {order_dir} LIMIT {PAGE_SIZE} OFFSET {st.session_state.movie_page * PAGE_SIZE}"
    result = execute_sql(query_sql)

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    pc1, pc2, pc3 = st.columns([1, 3, 1])
    with pc1:
        if st.button("⬅ 上一页", disabled=st.session_state.movie_page <= 0, key="movie_prev"):
            st.session_state.movie_page -= 1
            st.rerun()
    with pc2:
        st.markdown(f"<div style='text-align:center;color:#888;padding-top:6px;'>共 <b>{total}</b> 部电影 · 第 {st.session_state.movie_page + 1}/{total_pages} 页</div>", unsafe_allow_html=True)
    with pc3:
        if st.button("下一页 ➡", disabled=st.session_state.movie_page >= total_pages - 1, key="movie_next"):
            st.session_state.movie_page += 1
            st.rerun()

    if result and result.get("data"):
        df = pd.DataFrame(result["data"])
        df.rename(columns=MOVIE_COL_LABELS, inplace=True)
        st.dataframe(df, width="stretch", hide_index=True, height=700)
    elif total == 0:
        st.info("🔍 没有匹配的电影，试试调整筛选条件。")


def page():
    # ========== 页面标题 ==========
    st.markdown(
        page_header("📊", "数据可视化", "电影数据库的可视化分析看板", gradient="linear-gradient(135deg, #2E7D32, #4CAF50)"),
        unsafe_allow_html=True,
    )

    # ========== 统计概览卡片 ==========
    insights = get_insights()
    if insights:
        cards = [
            ("🎬 电影总数", str(insights.get("total_movies", 0)), "#1E3A5F"),
            ("⭐ 平均评分", str(insights.get("avg_rating", 0)), "#E65100"),
            ("👥 用户数", str(insights.get("total_users", 0)), "#2E7D32"),
            ("📝 评论数", str(insights.get("total_reviews", 0)), "#6A1B9A"),
            ("🎯 导演数", str(insights.get("total_directors", 0)), "#1565C0"),
        ]
        st.markdown(metric_cards_html(cards), unsafe_allow_html=True)

    # ========== 加载数据 ==========
    with st.spinner("📊 加载分析数据..."):
        cd = _load_chart_data()
    if not cd:
        st.warning("⚠️ 无法加载分析数据，请确保后端服务和数据库已启动。")
        return

    # ========== 预设分析看板 ==========
    st.markdown("### 📈 预设分析看板")
    _section_charts(cd)

    # ========== 高级分析 ==========
    with st.expander("🔬 高级分析", expanded=True):
        _advanced_charts(cd)

    # ========== 全部电影表格 ==========
    st.markdown("---")
    st.markdown("### 🎬 全部电影")
    _render_movie_table()

    # ========== 自定义查询 ==========
    st.markdown("---")
    st.markdown("### 🔍 自定义可视化查询")
    _custom_query_section()


# ===================== 预设图表 =====================

def _section_charts(cd: dict):
    r1 = st.columns(2)
    r2 = st.columns(2)
    r3 = st.columns(2)

    # 1. 评分分布柱状图
    with r1[0]:
        if "rating_dist" in cd:
            fig = _render_chart(cd["rating_dist"], "bar", x="score_bin", y="count",
                                title="电影评分分布", labels={"score_bin": "评分区间", "count": "电影数量"},
                                color="count", color_continuous_scale="Blues", height=320)
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    # 2. 年度趋势折线图
    with r1[1]:
        if "yearly" in cd:
            fig = _render_chart(cd["yearly"], "line", x="year", y="count",
                                title="每年电影数量趋势", labels={"year": "年份", "count": "电影数量"},
                                markers=True, height=320)
            fig.update_traces(line=dict(color="#FF6B35", width=2.5), marker=dict(size=5, color="#FF6B35"))
            fig.update_layout(xaxis=dict(tickangle=-30))
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    # 3. 类型树图
    with r2[0]:
        if "genre" in cd:
            df = cd["genre"].head(12)
            fig = _render_chart(df, "treemap", path=["genre"], values="count",
                                title="电影类型分布", color="count",
                                color_continuous_scale="Blues", height=340)
            fig.update_traces(textinfo="label+value", textfont=dict(family=FONT_FAMILY, size=13))
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    # 4. 国家/地区分布横向柱状图
    with r2[1]:
        if "country" in cd:
            df = cd["country"].head(10)
            fig = _render_chart(df, "bar", y="country", x="count",
                                title="国家/地区分布 Top 10", labels={"country": "", "count": "电影数量"},
                                color="count", color_continuous_scale="Greens",
                                text="count", orientation="h", height=340)
            fig.update_traces(textposition="outside", textfont=dict(size=11))
            fig.update_layout(yaxis=dict(autorange="reversed"), showlegend=False)
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    # 5. Top10 评分横向柱状图
    with r3[0]:
        if "top10" in cd:
            fig = _render_chart(cd["top10"], "bar", y="title", x="rating",
                                title="评分最高 Top 10", labels={"title": "", "rating": "评分"},
                                color="rating", color_continuous_scale="Reds",
                                orientation="h", text="rating", height=360)
            fig.update_traces(textposition="outside", texttemplate="%{text:.1f}", textfont=dict(size=11))
            fig.update_layout(yaxis=dict(autorange="reversed"), showlegend=False)
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    # 6. 最长电影 Top 15
    with r3[1]:
        if "duration" in cd:
            fig = _render_chart(cd["duration"], "bar", y="title", x="duration",
                                title="最长电影 Top 15", labels={"title": "", "duration": "时长(分钟)"},
                                color="duration", color_continuous_scale="Purples",
                                orientation="h", text="duration", height=360)
            fig.update_traces(textposition="outside", textfont=dict(size=11))
            fig.update_layout(yaxis=dict(autorange="reversed"), showlegend=False)
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


# ===================== 高级分析图表 =====================

def _advanced_charts(cd: dict):
    r1 = st.columns(2)
    r2 = st.columns(2)

    # 7. 评分 vs 时长散点图
    with r1[0]:
        if "scatter_data" in cd:
            df = cd["scatter_data"]
            if len(df) > 500:
                df = df.sample(500, random_state=42)
            fig = _render_chart(df, "scatter", x="duration", y="rating", color="genre",
                                title="评分与时长关系", labels={"duration": "时长(分钟)", "rating": "评分", "genre": "类型"},
                                hover_data=["title", "year"], height=380,
                                opacity=0.7, size_max=12)
            fig.update_traces(marker=dict(size=8, line=dict(width=0.5, color="white")))
            fig.update_layout(legend=dict(orientation="h", y=-0.25, font=dict(size=9)),
                              xaxis=dict(gridcolor="#f5f5f5"), yaxis=dict(gridcolor="#f5f5f5"))
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        else:
            st.info("暂无散点数据")

    # 8. 年代趋势 (双轴图表)
    with r1[1]:
        if "decade_stats" in cd:
            df = cd["decade_stats"]
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df["decade"], y=df["count"], name="电影数量",
                                 marker=dict(color="#4A90D9", opacity=0.7), yaxis="y"))
            fig.add_trace(go.Scatter(x=df["decade"], y=df["avg_rating"], name="平均评分",
                                     mode="lines+markers", line=dict(color="#E65100", width=3),
                                     marker=dict(size=10, color="#E65100"), yaxis="y2"))
            fig.update_layout(
                title=dict(text="年代发展趋势", font=dict(family=FONT_FAMILY, size=15, color="#1E3A5F"), x=0.5),
                template="plotly_white", font=dict(family=FONT_FAMILY, size=12, color="#333"),
                height=380, margin=dict(l=20, r=20, t=50, b=20),
                legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center", font=dict(size=11)),
                xaxis=dict(title="年代", gridcolor="#f5f5f5", tickfont=dict(family=FONT_FAMILY)),
                yaxis=dict(title="电影数量", gridcolor="#f5f5f5", tickfont=dict(family=FONT_FAMILY)),
                yaxis2=dict(title="平均评分", overlaying="y", side="right", range=[0, 10],
                            gridcolor="rgba(0,0,0,0)", tickfont=dict(family=FONT_FAMILY)),
            )
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        else:
            st.info("暂无年代数据")

    # 9. 类型评分箱线图
    with r2[0]:
        if "genre_rating_box" in cd:
            df = cd["genre_rating_box"]
            top_genres = df["genre"].value_counts().head(8).index.tolist()
            df = df[df["genre"].isin(top_genres)]
            fig = _render_chart(df, "box", x="genre", y="rating", color="genre",
                                title="各类型评分分布", labels={"genre": "类型", "rating": "评分"},
                                height=380, color_discrete_sequence=px.colors.qualitative.Bold)
            fig.update_layout(showlegend=False, xaxis=dict(tickangle=-25, tickfont=dict(size=10)))
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        else:
            st.info("暂无类型数据")

    # 10. 导演高产 Top 15
    with r2[1]:
        if "director_top" in cd:
            df = cd["director_top"]
            fig = _render_chart(df, "bar", y="director", x="avg_rating",
                                title="高产导演平均评分 Top 15", labels={"director": "", "avg_rating": "平均评分"},
                                color="avg_rating", color_continuous_scale="Oranges",
                                orientation="h", text="avg_rating", height=440)
            fig.update_traces(textposition="outside", texttemplate="%{text:.1f}", textfont=dict(size=10),
                              hovertemplate="<b>%{y}</b><br>平均评分: %{x:.2f}<br>作品数: %{customdata[0]}部<extra></extra>",
                              customdata=df[["movie_count"]])
            fig.update_layout(yaxis=dict(autorange="reversed"), showlegend=False)
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        else:
            st.info("暂无导演数据")


# ===================== 自定义查询 =====================

def _custom_query_section():
    custom_sql = st.text_area(
        "输入 SQL 查询，结果将自动可视化",
        value="SELECT country, COUNT(*) as count, ROUND(AVG(rating),2) as avg_rating FROM movies GROUP BY country ORDER BY count DESC LIMIT 10",
        height=80, label_visibility="collapsed",
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
                c1, c2 = st.columns(2)
                with c1:
                    chart_type = st.selectbox("图表类型", ["柱状图", "折线图", "饼图", "散点图", "面积图"], key="custom_type")
                    x_col = st.selectbox("X 轴", text_cols, key="custom_x")
                with c2:
                    y_col = st.selectbox("Y 轴", numeric_cols, key="custom_y")
                    colors = st.selectbox("配色方案", ["Blues", "Reds", "Greens", "Purples", "Oranges", "Viridis", "Plasma"], key="custom_colors")

                chart_map = {
                    "柱状图": lambda: px.bar(df, x=x_col, y=y_col, color=y_col, color_continuous_scale=colors),
                    "折线图": lambda: px.line(df, x=x_col, y=y_col, markers=True, color_discrete_sequence=["#FF6B35"]),
                    "饼图": lambda: px.pie(df, names=x_col, values=y_col, color_discrete_sequence=px.colors.qualitative.Bold),
                    "散点图": lambda: px.scatter(df, x=x_col, y=y_col, size=y_col, color=y_col, color_continuous_scale=colors),
                    "面积图": lambda: px.area(df, x=x_col, y=y_col, color_discrete_sequence=["#2E7D32"]),
                }
                fig = chart_map.get(chart_type, chart_map["柱状图"])()
                fig.update_layout(
                    template="plotly_white", font=dict(family=FONT_FAMILY, size=12, color="#333"),
                    margin=dict(l=20, r=20, t=20, b=20), height=420,
                )
                fig.update_xaxes(tickfont=dict(family=FONT_FAMILY), title_font=dict(family=FONT_FAMILY))
                fig.update_yaxes(tickfont=dict(family=FONT_FAMILY), title_font=dict(family=FONT_FAMILY))
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

                with st.expander("📋 查看数据表格"):
                    st.dataframe(df, width="stretch", hide_index=True)
            else:
                st.dataframe(df, width="stretch", hide_index=True)
        else:
            error = result.get("error", "无返回数据") if result else "连接失败"
            st.error(f"❌ {error}")
