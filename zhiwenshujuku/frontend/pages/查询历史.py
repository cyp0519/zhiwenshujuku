"""
智问数据库 — 查询历史页面
"""

import streamlit as st
import pandas as pd
from frontend.utils import get_history, execute_sql, delete_history, toggle_favorite
from frontend.styles import page_header

PAGE_SIZE = 20


def page():
    st.markdown(
        page_header(
            "📜", "查询历史",
            "查看和管理所有查询记录",
            gradient="linear-gradient(135deg, #6A1B9A, #8E24AA)",
        ),
        unsafe_allow_html=True,
    )

    # ========== 筛选 ==========
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        search = st.text_input("🔍 搜索问题或 SQL", placeholder="输入关键词过滤...",
                               label_visibility="collapsed")
    with col2:
        status_filter = st.selectbox("状态筛选", ["全部", "success", "failure"])
    with col3:
        show_favorites = st.checkbox("⭐ 仅收藏")

    # ========== 获取历史 ==========
    history = get_history()

    if not history:
        st.info("📭 暂无查询历史。前往「对话查询」或「SQL 编辑器」页面进行查询吧！")
        st.markdown(
            """
        <div style="text-align: center; padding: 40px; color: #888;">
            <div style="font-size: 3rem; margin-bottom: 16px;">🔍</div>
            <div>你的查询记录将出现在这里</div>
        </div>
        """,
            unsafe_allow_html=True,
        )
        return

    # 过滤
    if search:
        search_lower = search.lower()
        history = [
            h for h in history
            if search_lower in h.get("question", "").lower()
            or search_lower in h.get("sql_generated", "").lower()
            or search_lower in h.get("sql_executed", "").lower()
        ]
    if status_filter != "全部":
        history = [h for h in history if h.get("execution_status") == status_filter]
    if show_favorites:
        history = [h for h in history if h.get("is_favorite")]

    # ========== 分页 ==========
    total = len(history)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    if "history_page" not in st.session_state:
        st.session_state.history_page = 0

    page_num = st.session_state.history_page
    start = page_num * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)
    page_items = history[start:end]

    # 分页控件
    st.markdown(f"共 **{total}** 条记录 · 第 {page_num + 1}/{total_pages} 页")
    pcol1, pcol2, pcol3 = st.columns([1, 4, 1])
    with pcol1:
        if st.button("⬅️ 上一页", disabled=page_num <= 0):
            st.session_state.history_page -= 1
            st.rerun()
    with pcol3:
        if st.button("下一页 ➡️", disabled=page_num >= total_pages - 1):
            st.session_state.history_page += 1
            st.rerun()

    # ========== 渲染记录 ==========
    for i, record in enumerate(page_items):
        history_id = record.get("id")
        question = record.get("question", "")
        sql = record.get("sql_generated", "") or record.get("sql_executed", "")
        status = record.get("execution_status", "")
        summary = record.get("result_summary", "")
        created_at = record.get("created_at", "")
        is_fav = record.get("is_favorite", 0)

        is_success = status == "success"
        status_icon = "✅" if is_success else "❌"
        status_color = "#2E7D32" if is_success else "#C62828"
        fav_icon = "⭐" if is_fav else "☆"

        st.markdown(
            f"""
        <div style="background: white; border-radius: 12px; padding: 16px; margin: 8px 0;
                    border: 1px solid #E8ECF0; border-left: 4px solid {status_color};
                    box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div style="flex: 1;">
                    <div style="font-weight: 500; color: #1A202C; margin-bottom: 4px;">
                        {fav_icon} {status_icon} {question or "(直接SQL)"}
                    </div>
                    <div style="font-size: 0.8rem; color: #888;">{created_at}</div>
                </div>
                <div style="text-align: right;">
                    <span style="font-size: 0.75rem; padding: 2px 8px; border-radius: 4px;
                                 background: {status_color}15; color: {status_color};
                                 font-weight: 500;">{status}</span>
                </div>
            </div>
            <div style="margin-top: 8px; font-size: 0.85rem; font-family: monospace;
                        background: #F5F7FA; padding: 8px; border-radius: 6px; overflow-x: auto;">
                <code>{sql[:200]}{"..." if len(sql) > 200 else ""}</code>
            </div>
            <div style="margin-top: 6px; font-size: 0.8rem; color: #666;">{summary}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # 操作按钮
        col1, col2, col3, col4 = st.columns([1, 1, 1, 8])
        with col1:
            if st.button("🔄 重执行", key=f"rerun_{start + i}"):
                with st.spinner("🔄 执行中..."):
                    result = execute_sql(sql)
                if result and result.get("success") and result.get("data"):
                    df = pd.DataFrame(result["data"])
                    st.success(f"✅ 执行成功，返回 {len(df)} 行")
                    st.dataframe(df, width="stretch", hide_index=True)
                else:
                    st.error(f"❌ {result.get('error', '执行失败') if result else '连接失败'}")
        with col2:
            if st.button(fav_icon, key=f"fav_{start + i}", help="切换收藏"):
                if history_id:
                    toggle_favorite(history_id)
                    st.rerun()
        with col3:
            if st.button("🗑️", key=f"del_{start + i}", help="删除此记录"):
                if history_id:
                    delete_history(history_id)
                    st.rerun()

    # 清空缓存
    st.markdown("---")
    if st.button("🗑️ 清空显示", type="secondary"):
        st.cache_data.clear()
        st.rerun()
