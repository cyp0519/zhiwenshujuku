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

    .stButton button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s;
    }
    .stButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1E3A5F 0%, #152B45 100%);
    }
    section[data-testid="stSidebar"] .stMarkdown {
        color: white;
    }

    .sidebar-header {
        padding: 16px 0;
        text-align: center;
        border-bottom: 1px solid rgba(255,255,255,0.1);
        margin-bottom: 16px;
    }
    .sidebar-header .app-name {
        font-size: 1.5rem;
        font-weight: 700;
        color: white;
    }
    .sidebar-header .app-sub {
        font-size: 0.8rem;
        color: rgba(255,255,255,0.7);
    }
    .sidebar-footer {
        position: fixed;
        bottom: 16px;
        left: 16px;
        right: 16px;
        font-size: 0.75rem;
        color: rgba(255,255,255,0.5);
        text-align: center;
    }

    h1 { color: #1E3A5F; font-weight: 600; }
    h2, h3 { font-weight: 600; }
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
