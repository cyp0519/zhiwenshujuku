"""
智问数据库 — SQL 编辑器页面
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from frontend.utils import execute_sql, get_schema
from frontend.styles import page_header


def page():
    # ========== 状态初始化 ==========
    if "sql_editor_content" not in st.session_state:
        st.session_state.sql_editor_content = "SELECT * FROM movies LIMIT 10"
    if "sql_results" not in st.session_state:
        st.session_state.sql_results = None
    if "sql_error" not in st.session_state:
        st.session_state.sql_error = None
    if "sql_columns" not in st.session_state:
        st.session_state.sql_columns = None

    # ========== 页面标题 ==========
    st.markdown(
        page_header(
            "✏️", "SQL 编辑器",
            "直接编写 SQL 查询并查看结果",
            gradient="linear-gradient(135deg, #FF6B35, #FF8F65)",
        ),
        unsafe_allow_html=True,
    )

    # ========== Schema 侧栏 ==========
    with st.expander("📋 数据库表结构参考", expanded=False):
        schema = get_schema()
        if schema:
            table_descs = {
                "movies": "🎬 电影信息表",
                "users": "👥 用户信息表",
                "reviews": "📝 电影评论表",
                "query_history": "📜 查询历史表",
            }
            for table, columns in schema.items():
                desc = table_descs.get(table, "")
                st.markdown(f"**{desc or table}**")
                col_data = {"字段": [], "类型": [], "主键": []}
                for col in columns:
                    col_data["字段"].append(col["name"])
                    col_data["类型"].append(col["type"])
                    col_data["主键"].append("✅" if col.get("pk") else "")
                st.dataframe(pd.DataFrame(col_data), hide_index=True, width="stretch")
        else:
            st.info("无法获取 Schema 信息，请确保后端服务已启动。")

    # ========== SQL 输入 ==========
    sql_query = st.text_area(
        "SQL 查询",
        value=st.session_state.sql_editor_content,
        height=150,
        placeholder="输入 SQL 查询语句...",
        label_visibility="collapsed",
    )

    col1, col2, col3, col4 = st.columns([1, 1, 1, 4])
    with col1:
        if st.button("▶️ 执行", type="primary", width="stretch"):
            st.session_state.sql_editor_content = sql_query
            with st.spinner("🔄 执行中..."):
                result = execute_sql(sql_query)
            if result:
                if result.get("success") and result.get("data"):
                    st.session_state.sql_results = result["data"]
                    st.session_state.sql_columns = result["columns"]
                    st.session_state.sql_error = None
                else:
                    st.session_state.sql_results = None
                    st.session_state.sql_columns = None
                    st.session_state.sql_error = result.get("error", "查询失败")
            else:
                st.session_state.sql_results = None
                st.session_state.sql_columns = None
                st.session_state.sql_error = "无法连接到后端服务"
            st.rerun()

    with col2:
        if st.button("🧹 清空", width="stretch"):
            st.session_state.sql_editor_content = ""
            st.session_state.sql_results = None
            st.session_state.sql_error = None
            st.rerun()

    with col3:
        sample_queries = [
            "SELECT * FROM movies LIMIT 10",
            "SELECT title, year, rating FROM movies ORDER BY rating DESC LIMIT 10",
            "SELECT genre, COUNT(*) as count FROM movies GROUP BY genre ORDER BY count DESC",
            "SELECT director, COUNT(*) as cnt, ROUND(AVG(rating),2) as avg_rating FROM movies GROUP BY director HAVING cnt >= 3 ORDER BY avg_rating DESC",
        ]
        selected = st.selectbox("", ["快速示例..."] + sample_queries, label_visibility="collapsed")
        if selected != "快速示例...":
            st.session_state.sql_editor_content = selected
            st.rerun()

    # ========== 结果显示 ==========
    if st.session_state.sql_error:
        st.error(f"❌ {st.session_state.sql_error}")

    if st.session_state.sql_results is not None:
        df = pd.DataFrame(st.session_state.sql_results)

        if not df.empty:
            col1, col2, col3 = st.columns(3)
            col1.metric("📊 行数", len(df))
            col2.metric("📋 列数", len(df.columns))

            st.markdown("### 📋 查询结果")
            st.dataframe(df, width="stretch", hide_index=True)

            # 导出
            col1, col2 = st.columns(2)
            with col1:
                csv = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8")
                st.download_button(
                    "📥 下载 CSV", csv, "query_result.csv", "text/csv",
                    width="stretch",
                )
            with col2:
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    df.to_excel(writer, index=False, sheet_name="查询结果")
                excel_data = output.getvalue()
                st.download_button(
                    "📥 下载 Excel", excel_data, "query_result.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width="stretch",
                )

            # 快速可视化
            st.markdown("### 📈 快速可视化")
            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
            if len(numeric_cols) >= 1:
                viz_type = st.selectbox("图表类型", ["柱状图", "折线图", "饼图", "散点图"])
                x_col = st.selectbox("X 轴", df.columns.tolist())
                y_col = st.selectbox("Y 轴", numeric_cols)

                fig = _make_chart(df, viz_type, x_col, y_col)
                st.plotly_chart(fig, width="stretch")
        else:
            st.info("查询执行成功，但没有返回数据。")


def _make_chart(df: pd.DataFrame, chart_type: str, x_col: str, y_col: str):
    """根据类型创建 Plotly 图表"""
    color_map = {
        "柱状图": "#1E3A5F",
        "折线图": "#FF6B35",
        "散点图": "#2E7D32",
    }
    if chart_type == "柱状图":
        fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col} 按 {x_col} 分布",
                     color_discrete_sequence=[color_map["柱状图"]])
    elif chart_type == "折线图":
        fig = px.line(df, x=x_col, y=y_col, title=f"{y_col} 趋势",
                      color_discrete_sequence=[color_map["折线图"]])
    elif chart_type == "饼图":
        fig = px.pie(df, names=x_col, values=y_col, title=f"{y_col} 分布",
                     color_discrete_sequence=px.colors.sequential.Blues_r)
    elif chart_type == "散点图":
        fig = px.scatter(df, x=x_col, y=y_col, title=f"{y_col} vs {x_col}",
                         color_discrete_sequence=[color_map["散点图"]])
    else:
        fig = px.bar(df, x=x_col, y=y_col)

    fig.update_layout(
        template="plotly_white",
        font=dict(family="Noto Sans SC"),
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig
