"""
智问数据库 — 智能问答检索页面 (结构化检索版)
"""

import uuid
import streamlit as st
import pandas as pd
import plotly.express as px
from frontend.utils import chat, execute_sql
from frontend.styles import page_header

# 调色板定义
PALETTE = ["#C17B2A", "#5A8C5A", "#6B8EAF", "#9B7BAF", "#B54A4A"]

def page():
    # ========== 状态初始化 ==========
    if "qa_session_id" not in st.session_state:
        st.session_state.qa_session_id = str(uuid.uuid4())
    if "qa_query" not in st.session_state:
        st.session_state.qa_query = ""
    if "qa_results" not in st.session_state:
        st.session_state.qa_results = None
    if "qa_df" not in st.session_state:
        st.session_state.qa_df = None
    if "qa_waiting_confirm" not in st.session_state:
        st.session_state.qa_waiting_confirm = False
    if "qa_temp_sql" not in st.session_state:
        st.session_state.qa_temp_sql = None
    if "qa_temp_explanation" not in st.session_state:
        st.session_state.qa_temp_explanation = None

    # ========== 页面标题 ==========
    st.markdown(
        page_header(
            "🎬", "电影数据智能问答",
            "用自然语言提问，系统将自动安全检索数据库、输出 AI 数据洞察并自动为您绘制图表",
            gradient="linear-gradient(135deg, #A855F7, #6366F1)",
        ),
        unsafe_allow_html=True,
    )

    # ========== 检索输入框 ==========
    with st.container():
        input_col, search_btn_col, reset_btn_col = st.columns([6, 1, 1])
        with input_col:
            user_input = st.text_input(
                "输入你的问题，例如：评分最高的10部电影有哪些？",
                value=st.session_state.qa_query,
                placeholder="在此输入您的中文提问...",
                label_visibility="collapsed",
                key="qa_text_input"
            )
        with search_btn_col:
            trigger_search = st.button("🎬 智能检索", type="primary", width='stretch')
        with reset_btn_col:
            if st.button("🔄 重置状态", width='stretch'):
                st.session_state.qa_session_id = str(uuid.uuid4())
                st.session_state.qa_query = ""
                st.session_state.qa_results = None
                st.session_state.qa_df = None
                st.session_state.qa_waiting_confirm = False
                st.session_state.qa_temp_sql = None
                st.session_state.qa_temp_explanation = None

    # 快捷输入建议
    with st.expander("💡 试试以下提问示例", expanded=st.session_state.qa_results is None):
        examples = [
            "评分最高的10部电影有哪些？",
            "2000年后评分超过9分的有哪些电影？",
            "周星驰导演过哪些电影？",
            "各国电影的平均评分是多少？",
            "近十年每年上映了多少部电影？"
        ]
        cols = st.columns(len(examples))
        for idx, ex in enumerate(examples):
            with cols[idx]:
                if st.button(ex, key=f"ex_btn_{idx}", width='stretch'):
                    st.session_state.qa_query = ex
                    st.session_state.qa_results = None
                    st.session_state.qa_df = None
                    st.session_state.qa_waiting_confirm = False
                    st.session_state.qa_temp_sql = None
                    st.session_state.qa_temp_explanation = None
                    # 模拟直接触发搜索
                    with st.spinner("思考并检索中..."):
                        _run_qa_search(ex)
                    st.rerun()

    # ========== 搜索执行逻辑 ==========
    if trigger_search and user_input.strip():
        st.session_state.qa_query = user_input
        # 执行检索
        with st.spinner("思考并检索中..."):
            _run_qa_search(user_input)
        st.rerun()

    # ========== 安全校验二次确认面板 ==========
    if st.session_state.qa_waiting_confirm:
        st.markdown("---")
        st.markdown("### ⚠️ 安全校验确认")
        st.info("系统为了解答您的提问，已自动编写了如下 SQL。为保证数据访问安全，执行前请您进行最终确认：")
        
        st.markdown(f"**自动生成 SQL**：")
        st.code(st.session_state.qa_temp_sql, language="sql")
        if st.session_state.qa_temp_explanation:
            st.markdown(f"**逻辑说明**：{st.session_state.qa_temp_explanation}")

        c1, c2, _ = st.columns([1.5, 1.5, 5])
        with c1:
            if st.button("✅ 确认执行此查询", type="primary", width='stretch'):
                with st.spinner("执行 SQL 并生成 AI 分析中..."):
                    _confirm_qa_search("yes")
                st.rerun()
        with c2:
            if st.button("❌ 取消执行", width='stretch'):
                _confirm_qa_search("no")

    # ========== 结果看板渲染 ==========
    if st.session_state.qa_results and not st.session_state.qa_waiting_confirm:
        st.markdown("---")
        st.markdown("### 📊 检索分析看板")

        res = st.session_state.qa_results
        
        # 1. AI 深度洞察与总结
        st.markdown("#### 🤖 AI 数据洞察与回答")
        st.markdown(
            f"""
            <div style="background-color: #FFFFFF; border-left: 4px solid #C17B2A; padding: 16px 20px; 
                        border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 24px; color: #2C2417;">
                {res.get('message', '没有返回描述信息。')}
            </div>
            """,
            unsafe_allow_html=True
        )

        # 2. 查询到的数据集与自适应图表
        df = st.session_state.qa_df
        if df is not None and not df.empty:
            col_data, col_chart = st.columns([1, 1])
            with col_data:
                st.markdown("#### 📋 查询结果数据")
                st.dataframe(df, width='stretch', hide_index=True, height=360)
            
            with col_chart:
                st.markdown("#### 📈 自适应分析图表")
                _render_auto_chart(df)
        
        # 3. 底层执行的 SQL（折叠）
        sql = res.get("sql_query")
        if sql:
            with st.expander("💻 查看本次检索执行的 SQL 逻辑"):
                st.code(sql, language="sql")
                if res.get("sql_explanation"):
                    st.markdown(f"**查询逻辑说明**：{res.get('sql_explanation')}")


def _run_qa_search(query: str):
    """向后端发送问答检索请求"""
    session_id = st.session_state.qa_session_id
    result = chat(query, session_id)
    
    if result:
        # 检查是否为 interrupt (安全确认)
        if result.get("interrupt"):
            st.session_state.qa_waiting_confirm = True
            st.session_state.qa_temp_sql = result.get("sql_query")
            st.session_state.qa_temp_explanation = result.get("sql_explanation")
        else:
            st.session_state.qa_waiting_confirm = False
            st.session_state.qa_results = result
            
            # 如果有 SQL，立即查出数据以渲染表格和图表
            sql = result.get("sql_query")
            if sql:
                data_res = execute_sql(sql, save_history=False)
                if data_res and data_res.get("success") and data_res.get("data"):
                    st.session_state.qa_df = pd.DataFrame(data_res["data"])
                else:
                    st.session_state.qa_df = None
            else:
                st.session_state.qa_df = None


def _confirm_qa_search(decision: str):
    """处理安全确认（yes 或 no）"""
    session_id = st.session_state.qa_session_id
    result = chat(decision, session_id)
    
    # 状态恢复
    st.session_state.qa_waiting_confirm = False
    st.session_state.qa_temp_sql = None
    st.session_state.qa_temp_explanation = None

    if decision == "yes" and result:
        st.session_state.qa_results = result
        sql = result.get("sql_query")
        if sql:
            data_res = execute_sql(sql, save_history=False)
            if data_res and data_res.get("success") and data_res.get("data"):
                st.session_state.qa_df = pd.DataFrame(data_res["data"])
            else:
                st.session_state.qa_df = None
    else:
        # 取消时重置结果
        st.session_state.qa_results = None
        st.session_state.qa_df = None


def _render_auto_chart(df: pd.DataFrame):
    """自适应图表渲染逻辑：分析列属性并自动绘制合适的可视化图表"""
    # 找出数值列和非数值（分类/文本）列
    num_cols = df.select_dtypes(include=["number"]).columns.tolist()
    text_cols = df.select_dtypes(exclude=["number"]).columns.tolist()

    # 1. 尝试过滤出一些 ID 或 PK 列
    for col in list(num_cols):
        if col.lower() in ["id", "movie_id", "user_id", "review_id", "year"]:
            # 年份可以做 X 轴，先不全部过滤，但如果是单独纯 id 则过滤
            if col.lower() != "year":
                num_cols.remove(col)

    if not num_cols:
        st.info("数据全是文本，无法进行自适应图表渲染。已渲染数据表格。")
        return

    # 2. 如果有一个文本列和一个数值列，绘制柱状图或饼图
    if len(text_cols) >= 1 and len(num_cols) >= 1:
        x_col = text_cols[0]
        y_col = num_cols[0]
        
        # 数据行数少于等于 6 行时，用饼图，否则用柱状图
        if len(df) <= 6:
            fig = px.pie(df, names=x_col, values=y_col, color_discrete_sequence=px.colors.sequential.Brwnyl)
        else:
            fig = px.bar(df, x=x_col, y=y_col, color=y_col, color_continuous_scale="Brwnyl")
            fig.update_layout(xaxis=dict(tickangle=-25))
            
    # 3. 特殊情况：如果有 year（年份）和一个数值列，绘制折线图
    elif "year" in df.columns and len(num_cols) >= 1:
        x_col = "year"
        y_col = num_cols[0]
        fig = px.line(df, x=x_col, y=y_col, markers=True, color_discrete_sequence=[PALETTE[0]])

    # 4. 如果只有数值列，绘制散点图或折线图
    elif len(num_cols) >= 2:
        x_col = num_cols[0]
        y_col = num_cols[1]
        fig = px.scatter(df, x=x_col, y=y_col, color_discrete_sequence=[PALETTE[1]])
        
    else:
        # 兜底图表
        st.info("未找到足够的多维关联数据用于自适应分析图表。")
        return

    # 应用统一皮肤
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Noto Sans SC, sans-serif", size=10, color="#6B5E4E"),
        margin=dict(l=10, r=10, t=10, b=10),
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(gridcolor="#E4DDD4")
    fig.update_yaxes(gridcolor="#E4DDD4")
    
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
