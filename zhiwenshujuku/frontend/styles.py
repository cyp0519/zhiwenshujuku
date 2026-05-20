"""
智问数据库 — 共享样式定义
"""

GLOBAL_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Noto Sans SC', sans-serif; }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ---- 按钮 ---- */
    .stButton button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
    }

    /* ---- 侧边栏 ---- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #E8F4FD 0%, #D0E8F7 100%);
    }
    section[data-testid="stSidebar"] .stMarkdown {
        color: #1E3A5F;
    }
    section[data-testid="stSidebar"] hr {
        border-color: rgba(30,58,95,0.1);
    }

    /* ---- 侧边栏导航按钮 ---- */
    section[data-testid="stSidebar"] .stButton button {
        border: 1px solid rgba(30,58,95,0.12);
        background: rgba(255,255,255,0.6);
        color: #1E3A5F;
        transition: all 0.25s ease;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        background: rgba(255,255,255,0.9);
        border-color: rgba(30,58,95,0.3);
        box-shadow: 0 2px 8px rgba(30,58,95,0.1);
    }
    section[data-testid="stSidebar"] .stButton button[kind="primary"] {
        background: linear-gradient(135deg, #4A90D9, #357ABD);
        color: white;
        border-color: transparent;
    }

    .sidebar-header {
        padding: 16px 0;
        text-align: center;
        border-bottom: 1px solid rgba(30,58,95,0.1);
        margin-bottom: 16px;
    }
    .sidebar-header .app-name {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1E3A5F;
    }
    .sidebar-header .app-sub {
        font-size: 0.8rem;
        color: rgba(30,58,95,0.7);
    }
    .sidebar-footer {
        position: fixed;
        bottom: 16px;
        left: 16px;
        right: 16px;
        font-size: 0.75rem;
        color: rgba(30,58,95,0.5);
        text-align: center;
    }

    /* ---- 指标卡片 ---- */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 18px 14px;
        text-align: center;
        border: 1px solid #E8ECF0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        transition: all 0.2s ease;
    }
    .metric-card:hover {
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
        transform: translateY(-2px);
    }
    .metric-card .value {
        font-size: 2rem;
        font-weight: 700;
        color: #1E3A5F;
        line-height: 1.2;
    }
    .metric-card .label {
        font-size: 0.78rem;
        color: #8B96A5;
        margin-top: 4px;
    }

    /* ---- 全局标题 ---- */
    h1 { color: #1E3A5F; font-weight: 700; }
    h2 { color: #1E3A5F; font-weight: 600; font-size: 1.3rem; }
    h3 { color: #2A3F5F; font-weight: 600; font-size: 1.1rem; }

    /* ---- 分隔线 ---- */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #E0E6ED, transparent);
        margin: 24px 0;
    }

    /* ---- 数据表格 ---- */
    .stDataFrame {
        border-radius: 8px;
        border: 1px solid #E8ECF0;
    }

    /* ---- 图表容器 ---- */
    .js-plotly-plot .plotly .main-svg {
        border-radius: 8px;
    }
</style>
"""


def page_header(icon: str, title: str, subtitle: str, gradient: str = "linear-gradient(135deg, #1E3A5F, #2D5A8E)"):
    """渲染统一的页面标题组件"""
    return f"""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
        <div style="background: {gradient}; width: 40px; height: 40px; border-radius: 10px;
                    display: flex; align-items: center; justify-content: center; font-size: 20px;">
            {icon}
        </div>
        <div>
            <h1 style="margin: 0; font-size: 1.6rem;">{title}</h1>
            <p style="margin: 0; color: #666; font-size: 0.85rem;">{subtitle}</p>
        </div>
    </div>
    """


def metric_cards_html(cards: list[tuple[str, str, str]]) -> str:
    """渲染一行指标卡片。每项为 (label, value, color)"""
    items = []
    for label, value, color in cards:
        items.append(f"""
        <div class="metric-card">
            <div class="value" style="color:{color};">{value}</div>
            <div class="label">{label}</div>
        </div>
        """)
    cols_html = "".join(f"<div style='flex:1;min-width:0;'>{item}</div>" for item in items)
    return f"<div style='display:flex;gap:12px;margin-bottom:20px;'>{cols_html}</div>"
