"""
智问数据库 — 查询历史页面
"""

import streamlit as st
import pandas as pd
from frontend.utils import get_history, execute_sql, delete_history, toggle_favorite, batch_delete_history
from frontend.styles import page_header


def page():
    st.markdown(
        page_header(
            "📜", "查询历史",
            "查看和管理所有查询记录",
            gradient="linear-gradient(135deg, #6A1B9A, #8E24AA)",
        ),
        unsafe_allow_html=True,
    )

    # ========== 筛选行 ==========
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        search = st.text_input("🔍 搜索", placeholder="问题或 SQL 关键词...", label_visibility="collapsed")
    with f2:
        status_filter = st.selectbox("状态", ["全部", "success", "failure"], label_visibility="collapsed")
    with f3:
        date_from = st.date_input("开始日期", value=None, label_visibility="collapsed")
    with f4:
        date_to = st.date_input("结束日期", value=None, label_visibility="collapsed")

    # ========== 获取数据 ==========
    df_str = date_from.isoformat() if date_from else None
    dt_str = date_to.isoformat() if date_to else None
    history = get_history(limit=500, date_from=df_str, date_to=dt_str)

    if not history:
        st.info("📭 暂无查询历史。前往「对话查询」或「SQL 编辑器」页面进行查询吧！")
        return

    # 前端过滤
    if search:
        s = search.lower()
        history = [h for h in history if s in h.get("question", "").lower()
                   or s in h.get("sql_generated", "").lower()
                   or s in h.get("sql_executed", "").lower()]
    if status_filter != "全部":
        history = [h for h in history if h.get("execution_status") == status_filter]

    if not history:
        st.info("🔍 没有匹配的记录，试试调整筛选条件。")
        return

    # ========== 构建 DataFrame ==========
    rows = []
    for h in history:
        sql_full = h.get("sql_generated") or h.get("sql_executed") or ""
        rows.append({
            "id": h.get("id"),
            "时间": (h.get("created_at") or "")[:16],
            "问题": h.get("question", "(直接SQL)")[:70],
            "SQL": sql_full[:80] + ("..." if len(sql_full) > 80 else ""),
            "状态": h.get("execution_status", ""),
            "结果": h.get("result_summary", ""),
            "收藏": h.get("is_favorite", 0),
        })

    df = pd.DataFrame(rows)
    total = len(df)

    # ========== 批量操作栏 ==========
    st.markdown(f"共 **{total}** 条记录")
    bc1, bc2, bc3 = st.columns([4, 1, 1])
    with bc1:
        selected_ids = st.multiselect(
            "选择记录进行批量操作",
            df["id"].tolist(),
            format_func=lambda x: f"#{x} — {df.loc[df['id'] == x, '问题'].values[0] if x in df['id'].values else ''}",
            label_visibility="collapsed",
            placeholder="选择要批量操作的记录...",
        )
    with bc2:
        if st.button("🗑️ 批量删除", disabled=not selected_ids, width="stretch"):
            result = batch_delete_history(selected_ids)
            if result and result.get("success"):
                st.success(f"已删除 {result.get('deleted', 0)} 条记录")
                st.rerun()
            else:
                st.error("删除失败")
    with bc3:
        show_favorites = st.checkbox("⭐ 仅收藏")
    if show_favorites:
        df = df[df["收藏"] == 1]
        if df.empty:
            st.info("没有收藏的记录。")
            return

    # ========== 数据表格 ==========
    display_df = df.copy()
    display_df["状态"] = display_df["状态"].apply(lambda x: "✅" if x == "success" else "❌")
    display_df["收藏"] = display_df["收藏"].apply(lambda x: "⭐" if x == 1 else "☆")
    display_df = display_df.drop(columns=["id"])

    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
        height=480,
    )

    # ========== 单条操作 ==========
    st.markdown("---")
    st.markdown("### 🔧 单条记录操作")

    selected_id = st.selectbox(
        "选择记录 ID 进行操作",
        [h["id"] for h in history],
        format_func=lambda x: f"#{x} — {next((h.get('question', '')[:60] for h in history if h.get('id') == x), '')}",
        label_visibility="collapsed",
    )

    if selected_id:
        record = next((h for h in history if h.get("id") == selected_id), None)
        if record:
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("🔄 重新执行", width="stretch"):
                    sql = record.get("sql_generated") or record.get("sql_executed", "")
                    with st.spinner("🔄 执行中..."):
                        result = execute_sql(sql)
                    if result and result.get("success") and result.get("data"):
                        st.success(f"✅ 返回 {len(result['data'])} 行")
                        st.dataframe(pd.DataFrame(result["data"]), hide_index=True)
                    else:
                        st.error(f"❌ {result.get('error', '执行失败') if result else '连接失败'}")
            with c2:
                fav_text = "⭐ 取消收藏" if record.get("is_favorite") else "☆ 收藏"
                if st.button(fav_text, width="stretch"):
                    toggle_favorite(selected_id)
                    st.rerun()
            with c3:
                if st.button("🗑️ 删除此记录", width="stretch"):
                    delete_history(selected_id)
                    st.rerun()

            # 显示完整 SQL
            sql_full = record.get("sql_generated") or record.get("sql_executed") or ""
            if sql_full:
                st.code(sql_full, language="sql")
