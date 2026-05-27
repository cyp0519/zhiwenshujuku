# 智问数据库

> 基于检索增强（RAG）与安全校验机制的电影数据智能问答系统

现代数据库系统课程设计项目。用户可以用中文自然语言提问，系统通过 LangGraph Agent 工作流自动完成意图识别、SQL 生成、安全校验、语法验证、执行与结果分析，最终返回结构化数据和 AI 洞察。

## 功能特性

- **智能问答** -- 用中文描述需求，系统自动生成 SQL、执行查询、分析结果并自动绘制图表
- **SQL 编辑器** -- 直接编写和执行 SQL，带安全校验、执行计划分析和快速可视化
- **智能性能调优** -- 检测全表扫描瓶颈，AI 推荐索引优化方案，一键创建索引
- **数据可视化** -- 预设分析看板（评分分布、年度趋势、类型分布、导演排行等）和自定义可视化查询
- **查询历史** -- 保存、收藏、删除、批量管理历史记录，支持日期筛选
- **系统概览** -- ER 图展示、查询统计、数据字典、索引管理
- **RAG 检索增强** -- 基于 ChromaDB 向量库检索相似 SQL 样例，提升生成准确率
- **多层安全校验** -- 危险关键词过滤、SQL 注入特征检测、人工确认环节

## 技术栈

**前端**
- Streamlit -- Web UI 框架
- Plotly -- 交互式图表
- Pandas -- 数据处理

**后端**
- FastAPI -- REST API 服务
- Uvicorn -- ASGI 服务器
- LangChain / LangGraph -- LLM Agent 工作流编排
- OpenAI SDK -- LLM 调用（默认使用 DeepSeek API）

**数据存储**
- SQLite -- 业务数据库（电影、用户、评论、查询历史）
- ChromaDB -- 向量数据库（SQL 样例 RAG 检索）

**开发工具**
- Loguru -- 日志管理
- httpx -- HTTP 客户端
- slowapi -- API 速率限制
- pytest -- 测试框架
- Docker / Docker Compose -- 容器化部署

## 项目架构

```
用户输入自然语言
        |
        v
Streamlit 前端 (端口 8501)
        |
        v (HTTP)
FastAPI 后端 (端口 8765)
        |
        v
LangGraph Agent 工作流
        |
        +-- 意图分类器 (sql / chat)
        |       |
        |       +-- [chat] --> 聊天助手
        |       |
        |       +-- [sql]  --> SQL 生成器 (RAG 检索相似样例)
        |                       |
        |                       v
        |                   安全校验 (危险关键词 + 注入检测)
        |                       |
        |                       v
        |                   语法验证 (EXPLAIN 验证 + LLM 自动修复)
        |                       |
        |                       v
        |                   SQL 执行
        |                       |
        |                       v
        |                   结果分析 (LLM 生成洞察)
        |
        v
SQLite (movies.db) <--- 业务数据
ChromaDB            <--- 向量检索
```

数据流向：用户自然语言 --> LLM 生成 SQL --> 安全/语法校验 --> SQLite 执行 --> LLM 分析结果 --> 前端展示（表格 + 图表）

## 快速开始

### 方式一：本地运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 API Key（默认使用 DeepSeek）

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
# 编辑 .env，填入 API Key

# 2. 启动服务
docker-compose up --build
```

### 访问地址

- 前端界面: http://localhost:8501
- 后端 API: http://localhost:8765
- API 文档: http://localhost:8765/docs

## 项目结构

```
rajsjk/
├── backend/                    # 后端服务
│   ├── api.py                  # FastAPI 端点（全部 REST API 定义）
│   ├── graph.py                # LangGraph 工作流定义（7 节点有向图）
│   ├── nodes.py                # Agent 节点函数（意图分类、SQL 生成、校验、执行、分析）
│   ├── database.py             # SQLite 数据库适配器（查询、Schema、历史、索引管理）
│   ├── vector_store.py         # ChromaDB 向量存储（RAG 检索增强）
│   ├── config.py               # 配置管理（环境变量、路径、安全规则）
│   ├── state.py                # LangGraph Agent 状态模型定义
│   ├── movies.db               # SQLite 业务数据库
│   └── chromadb/               # ChromaDB 持久化数据
├── frontend/                   # Streamlit 前端
│   ├── app.py                  # 主入口（页面路由、选项卡导航）
│   ├── styles.py               # 全局 CSS 样式和组件函数
│   ├── utils.py                # 后端 API 调用工具函数
│   └── views/                  # 页面模块
│       ├── 智能问答.py          # 结构化问答检索页面（核心入口）
│       ├── 对话查询.py          # 多轮对话查询页面
│       ├── SQL编辑器.py         # SQL 编辑器与性能调优
│       ├── 数据可视化.py        # 预设看板与自定义图表
│       ├── 查询历史.py          # 历史记录管理
│       └── 系统概览.py          # 统计、ER 图、数据字典、索引管理
├── configs/                    # 配置文件
│   └── prompts.yml             # LLM 提示词模板（意图分类、SQL 生成、修复、分析、调优）
├── knowledge/                  # 知识库
│   ├── sql_examples.yml        # SQL 样例库（RAG 检索数据源）
│   └── data_dictionary.yml     # 数据字典（字段中文说明）
├── data/                       # 数据脚本
│   └── create_dataset.py       # 数据集生成脚本（100+ 部电影、100 用户、500 评论）
├── tests/                      # 测试用例
│   ├── conftest.py             # 测试配置和公共 fixtures
│   ├── test_database.py        # 数据库适配器测试
│   ├── test_vector_store.py    # 向量存储测试
│   ├── test_api.py             # API 端点测试
│   ├── test_nodes.py           # Agent 节点测试
│   ├── test_integration.py     # 集成测试
│   └── test_performance.py     # 性能测试
├── .streamlit/config.toml      # Streamlit 主题配置
├── Dockerfile                  # Docker 镜像配置
├── docker-compose.yml          # Docker Compose 编排
├── start.bat                   # Windows 一键启动脚本
├── start.sh                    # Linux/Mac 一键启动脚本
├── requirements.txt            # Python 依赖清单
└── .env.example                # 环境变量模板
```

## 核心文件说明

### 入口与配置

- **`frontend/app.py`** -- Streamlit 主入口，定义 6 个选项卡导航（智能问答、数据库概览、SQL 终端、数据分析、查询审计、索引管理），加载全局 CSS 样式
- **`backend/api.py`** -- FastAPI 应用入口，管理应用生命周期（初始化数据库、向量库、工作流），定义全部 REST API 端点，包含速率限制和 CORS 中间件
- **`backend/config.py`** -- 集中管理所有配置：LLM 模型（默认 DeepSeek）、数据库路径、安全规则（危险关键词、注入特征模式）、文件路径、日志配置

### 核心业务逻辑

- **`backend/graph.py`** -- LangGraph 工作流定义，构建 7 节点有向图：`intent_classifier` -> `sql_generator` / `chat_agent` -> `sql_safety_validator` -> `sql_syntax_validator` -> `sql_executor` -> `sql_result_analyzer`，使用 MemorySaver 支持 interrupt/resume 机制
- **`backend/nodes.py`** -- Agent 节点函数实现，包含：
  - 意图分类器：判断用户问题属于 SQL 查询还是普通对话
  - SQL 生成器：结合 Schema 上下文和 RAG 检索的相似样例，调用 LLM 生成 SQL（JSON 格式输出）
  - 安全校验器：检查危险关键词和注入特征模式
  - 语法验证器：用 EXPLAIN 验证语法，失败时调用 LLM 自动修复（最多重试 3 次）
  - 结果分析器：将查询结果交给 LLM 生成数据洞察
  - LLM 实例使用 `lru_cache` 缓存，避免重复创建
- **`backend/state.py`** -- Pydantic 状态模型，定义 Agent 工作流的全部状态字段（消息列表、意图、SQL、执行结果、各阶段状态标记）

### 数据与存储

- **`backend/database.py`** -- SQLite 数据库适配器，封装了查询执行、Schema 获取、历史记录 CRUD、EXPLAIN 执行计划分析、索引管理（创建/删除/列表）等操作，支持自动迁移（如添加 is_favorite 列）
- **`backend/vector_store.py`** -- ChromaDB 向量存储封装，提供 SQL 样例的向量化存储和语义检索功能，用于 RAG 检索增强
- **`knowledge/sql_examples.yml`** -- 30+ 条 SQL 样例，覆盖基础查询、多表连接、聚合统计、文本搜索等场景，作为 RAG 检索数据源
- **`knowledge/data_dictionary.yml`** -- 4 张表的完整字段说明，包含类型、约束和中文描述

### 前端页面

- **`frontend/views/智能问答.py`** -- 核心问答页面，支持安全确认中断机制（interrupt/resume），自适应图表渲染（根据数据列类型自动选择柱状图/饼图/折线图/散点图）
- **`frontend/views/SQL编辑器.py`** -- SQL 编辑器页面，集成执行计划分析、全表扫描检测、快速可视化图表和 CSV/Excel 导出
- **`frontend/views/数据可视化.py`** -- 数据分析看板，10 个预设图表（评分分布、年度趋势、类型树图、国家分布、导演排行等）+ 自定义可视化查询，使用 ThreadPoolExecutor 并发加载数据
- **`frontend/views/系统概览.py`** -- 查询统计、ER 图（Plotly 绘制表格框+关系连线）、数据字典展示、索引管理面板

## API 接口

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/chat` | 自然语言查询（支持 interrupt/resume） |
| POST | `/sql/execute` | 直接执行 SQL |
| POST | `/sql/explain` | 分析 SQL 执行计划 |
| POST | `/sql/tune` | AI 自动调优推荐索引 |
| GET | `/schema` | 获取数据库结构 |
| GET | `/schema/context` | 获取格式化 Schema |
| GET | `/schema/relations` | 获取表关系（ER 图数据） |
| GET | `/history` | 查询历史（支持日期筛选） |
| DELETE | `/history/{id}` | 删除单条历史 |
| POST | `/history/batch-delete` | 批量删除历史 |
| POST | `/history/{id}/favorite` | 切换收藏状态 |
| POST | `/export/csv` | 导出 CSV |
| POST | `/export/excel` | 导出 Excel |
| GET | `/insights` | 数据库统计信息 |
| GET | `/stats/queries` | 查询性能统计 |
| GET | `/data-dictionary` | 数据字典 |
| GET | `/index/list` | 索引列表 |
| POST | `/index/create` | 创建索引 |
| POST | `/index/drop` | 删除索引 |
| GET | `/health` | 健康检查 |

## 安全特性

- SQL 危险关键词过滤（DROP、DELETE、INSERT、ALTER 等 11 个关键词）
- SQL 注入特征检测（块注释、行注释、多语句分号、UNION 注入、文件读写、时间盲注共 8 种模式）
- API 速率限制（全局 60 次/分钟，聊天和 SQL 执行 30 次/分钟）
- CORS 跨域限制
- 人工确认环节（执行前需用户确认，基于 LangGraph interrupt 机制）

## 测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_database.py -v
pytest tests/test_api.py -v
pytest tests/test_integration.py -v
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | LLM API 密钥 | 必填 |
| `OPENAI_API_BASE` | API 基础地址 | `https://api.deepseek.com` |
| `LLM_MODEL` | 主 LLM 模型 | `deepseek-chat` |
| `LLM_MODEL_HEAVY` | 重型 LLM 模型（语法修复） | `deepseek-reasoner` |
| `EMBEDDING_MODEL` | 嵌入模型 | `text-embedding-3-small` |
| `API_PORT` | 后端端口 | `8765` |
| `SESSION_TIMEOUT` | 会话超时（秒） | `1800` |

## 许可证

本项目为现代数据库系统课程设计，仅供学习参考。
