"""
智问数据库 — 共享样式定义
方向：editorial cinema — 暖色调、衬线标题、克制层次
"""

GLOBAL_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&display=swap');

    #MainMenu, footer { visibility: hidden; }
    header { background-color: transparent !important; }

    /* ── 完全隐藏侧边栏及其按钮 ── */
    [data-testid="stSidebar"], [data-testid="stSidebarCollapseButton"] {
        display: none !important;
    }

    /* ── 主内容区背景 ── */
    .stApp {
        background-color: #F7F4F0 !important;
    }

    /* ── 主内容区文字 → 深色 ── */
    .main p, .main li, .main td, .main th,
    .main label {
        color: #2C2417 !important;
    }
    .main h1, .main h2, .main h3, .main h4 {
        color: #2C2417 !important;
        font-family: 'Noto Serif SC', serif !important;
    }

    /* ── 主内容区按钮 → 深色加粗 ── */
    .main .stButton button {
        background: #FFFFFF !important;
        color: #2C2417 !important;
        font-weight: 700 !important;
        border: 1px solid #D4C8B8 !important;
        border-radius: 6px !important;
    }
    .main .stButton button p {
        color: #2C2417 !important;
        font-weight: 700 !important;
    }
    .main .stButton button:hover {
        border-color: #C17B2A !important;
    }
    .main .stButton button:hover p {
        color: #2C2417 !important;
    }
    .main .stButton button[data-testid="stBaseButton-primary"] {
        background: #2C2417 !important;
        color: #FFFFFF !important;
        border-color: #2C2417 !important;
    }
    .main .stButton button[data-testid="stBaseButton-primary"] p {
        color: #FFFFFF !important;
    }

    /* ── 输入框 ── */
    .stTextArea textarea,
    .stTextInput input,
    .stChatInput textarea {
        color: #2C2417 !important;
        background-color: #FFFFFF !important;
        border-color: #E4DDD4 !important;
    }

    /* ── 选择框 ── */
    .stSelectbox [data-baseweb="select"] > div {
        color: #2C2417 !important;
    }

    /* ── 数据表格 ── */
    .stDataFrame th {
        color: #2C2417 !important;
        font-weight: 700 !important;
    }
    .stDataFrame td {
        color: #2C2417 !important;
    }

    /* ── Expander ── */
    .streamlit-expanderHeader {
        color: #2C2417 !important;
        font-weight: 600 !important;
        background-color: #FFFFFF !important;
    }
    .streamlit-expanderContent {
        background-color: #FFFFFF !important;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab"] {
        color: #766A5E !important;
    }
    .stTabs [aria-selected="true"] {
        color: #C17B2A !important;
        border-bottom-color: #C17B2A !important;
    }

    /* ── Metric 组件 ── */
    .main [data-testid="stMetric"] {
        background: #FFFFFF !important;
        border: 1px solid #E4DDD4 !important;
        border-radius: 8px !important;
    }
    .main [data-testid="stMetricValue"] {
        color: #2C2417 !important;
        font-family: 'Noto Serif SC', serif !important;
        font-weight: 700 !important;
    }
    .main [data-testid="stMetricLabel"] {
        color: #766A5E !important;
    }

    /* ── Alert ── */
    .stAlert p, .stAlert span {
        color: inherit !important;
    }

    /* ── Code ── */
    .stCodeBlock code {
        color: #2C2417 !important;
    }

    /* ── Checkbox / Radio / Slider / Date ── */
    label span, label p {
        color: #2C2417 !important;
    }

    /* ── Download button ── */
    .stDownloadButton button p {
        color: #2C2417 !important;
        font-weight: 700 !important;
    }

    /* ── 指标卡片（HTML 注入） ── */
    .metric-card {
        background: #FFFFFF !important;
        border: 1px solid #E4DDD4 !important;
        border-radius: 8px;
        padding: 20px 16px 16px;
        position: relative;
        transition: border-color 0.2s;
    }
    .metric-card:hover {
        border-color: #C17B2A !important;
    }
    .metric-card .value {
        font-family: 'Noto Serif SC', serif !important;
        font-size: 2.2rem !important;
        font-weight: 700 !important;
        line-height: 1;
        color: #2C2417 !important;
    }
    .metric-card .label {
        font-size: 0.72rem !important;
        color: #766A5E !important;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        margin-top: 8px;
    }
    .metric-card .accent-dot {
        position: absolute;
        top: 16px;
        right: 16px;
        width: 6px;
        height: 6px;
        border-radius: 50%;
    }

    /* ── 分隔线 ── */
    .main hr {
        background: #E4DDD4 !important;
        border: none !important;
        height: 1px !important;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #E4DDD4; border-radius: 3px; }

    /* ── 对话气泡（支持 Markdown 内部渲染） ── */
    .user-bubble-container {
        display: flex;
        justify-content: flex-end;
        margin: 12px 0;
    }
    .user-bubble {
        background-color: #2C2417 !important;
        color: #EDE6DC !important;
        border-radius: 6px;
        padding: 10px 14px;
        max-width: 75%;
        font-size: 0.88rem;
        line-height: 1.6;
    }
    .user-bubble p {
        color: #EDE6DC !important;
        margin: 0;
    }
    .assistant-bubble-container {
        display: flex;
        justify-content: flex-start;
        margin: 12px 0;
    }
    .assistant-bubble {
        background-color: #FFFFFF !important;
        border: 1px solid #E4DDD4 !important;
        border-left: 3px solid #C17B2A !important;
        border-radius: 4px;
        padding: 12px 16px;
        max-width: 85%;
        font-size: 0.88rem;
        line-height: 1.65;
        color: #2C2417 !important;
    }
    .assistant-bubble p, .assistant-bubble li, .assistant-bubble span, .assistant-bubble td, .assistant-bubble th {
        color: #2C2417 !important;
    }
    .assistant-bubble p:last-child {
        margin-bottom: 0;
    }
</style>
"""


def page_header(icon: str, title: str, subtitle: str,
                gradient: str = "linear-gradient(135deg, #1E3A5F, #2D5A8E)"):
    """渲染统一的页面标题组件 — editorial 风格"""
    return f"""
    <div style="margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid #E4DDD4;">
        <div style="display: flex; align-items: center; gap: 14px;">
            <div style="background: #2C2417; width: 36px; height: 36px; border-radius: 6px;
                        display: flex; align-items: center; justify-content: center; font-size: 18px;
                        flex-shrink: 0;">
                {icon}
            </div>
            <div>
                <h1 style="margin: 0; font-size: 1.5rem; color: #2C2417; font-family: 'Noto Serif SC', serif; font-weight: 700;">
                    {title}
                </h1>
                <p style="margin: 2px 0 0; color: #766A5E; font-size: 0.82rem; letter-spacing: 0.02em;">
                    {subtitle}
                </p>
            </div>
        </div>
    </div>
    """


def metric_cards_html(cards: list[tuple[str, str, str]]) -> str:
    """渲染一行指标卡片。每项为 (label, value, accent_color)"""
    items = []
    for label, value, color in cards:
        items.append(f"""
        <div class="metric-card">
            <div class="accent-dot" style="background: {color};"></div>
            <div class="value">{value}</div>
            <div class="label">{label}</div>
        </div>
        """)
    cols_html = "".join(f"<div style='flex:1;min-width:0;'>{item}</div>" for item in items)
    return f"<div style='display:flex;gap:12px;margin-bottom:24px;'>{cols_html}</div>"
