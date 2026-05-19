# 智问数据库

> 基于自然语言的智能数据库查询与分析平台

现代数据库系统课程设计项目。用户可以用中文提问，系统自动转换为 SQL 查询并返回结果。

## 功能特性

- **自然语言查询** — 用中文描述需求，自动生成 SQL
- **SQL 编辑器** — 直接编写和执行 SQL，带安全校验
- **数据可视化** — Plotly 图表展示查询结果
- **查询历史** — 保存、收藏、删除历史记录
- **系统概览** — ER 图、查询统计、性能监控

## 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit 前端                        │
│    对话查询 │ SQL编辑器 │ 数据可视化 │ 查询历史 │ 系统概览  │
└───────────────────────────┬─────────────────────────────┘
                            │ HTTP
┌───────────────────────────▼─────────────────────────────┐
│                    FastAPI 后端                          │
│  /chat │ /sql/execute │ /schema │ /history │ /export    │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│              LangGraph Agent 工作流                      │
│  意图分类 → SQL生成 → 安全校验 → 语法验证 → 执行 → 分析  │
└───────┬─────────────────────────────────┬───────────────┘
        │                                 │
   ┌────▼────┐                      ┌─────▼─────┐
   │ ChromaDB │                      │   SQLite   │
   │ 向量库   │                      │  movies.db │
   └─────────┘                      └───────────┘
```

## 快速开始

### 方式一：本地运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 OpenAI API Key

# 3. 初始化数据库
python data/create_dataset.py

# 4. 一键启动
# Windows:
start.bat
# Linux/Mac:
chmod +x start.sh && ./start.sh
```

### 方式二：Docker 运行

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 OpenAI API Key

# 2. 启动服务
docker-compose up --build
```

### 访问地址

- 前端界面: http://localhost:8501
- 后端 API: http://localhost:8765
- API 文档: http://localhost:8765/docs

## 项目结构

```
智问数据库/
├── backend/                # 后端服务
│   ├── api.py             # FastAPI 端点
│   ├── graph.py           # LangGraph 工作流
│   ├── nodes.py           # Agent 节点函数
│   ├── database.py        # SQLite 适配器
│   ├── vector_store.py    # ChromaDB 向量库
│   ├── config.py          # 配置管理
│   └── state.py           # 状态定义
├── frontend/              # 前端界面
│   ├── app.py             # Streamlit 主入口
│   ├── styles.py          # 共享样式
│   ├── utils.py           # 工具函数
│   └── pages/             # 页面模块
├── configs/               # 配置文件
│   └── prompts.yml        # LLM 提示词
├── knowledge/             # 知识库
│   └── sql_examples.yml   # SQL 样例
├── data/                  # 数据脚本
│   └── create_dataset.py  # 数据集生成
├── tests/                 # 测试用例
├── Dockerfile             # Docker 配置
├── docker-compose.yml     # Docker Compose
└── requirements.txt       # 依赖清单
```

## API 接口

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/chat` | 自然语言查询 |
| POST | `/sql/execute` | 执行 SQL |
| GET | `/schema` | 获取数据库结构 |
| GET | `/history` | 查询历史 |
| POST | `/export/csv` | 导出 CSV |
| POST | `/export/excel` | 导出 Excel |
| GET | `/health` | 健康检查 |

## 安全特性

- SQL 危险关键词过滤（DROP、DELETE、INSERT 等）
- SQL 注入特征检测（注释、分号、UNION 等）
- API 速率限制（60次/分钟）
- CORS 跨域限制
- 人工确认环节（执行前需用户确认）

## 测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_api.py -v
pytest tests/test_integration.py -v
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | OpenAI API 密钥 | 必填 |
| `LLM_MODEL` | LLM 模型 | gpt-4.1-mini |
| `API_PORT` | 后端端口 | 8765 |
| `SESSION_TIMEOUT` | 会话超时(秒) | 1800 |

## 许可证

本项目为现代数据库系统课程设计，仅供学习参考。
