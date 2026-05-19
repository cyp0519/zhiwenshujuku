#!/bin/bash

echo "========================================"
echo "  智问数据库 — 一键启动"
echo "========================================"
echo

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 Python3，请先安装 Python 3.10+"
    exit 1
fi

# 检查依赖
echo "[1/3] 检查依赖..."
pip3 install -q -r requirements.txt

# 初始化数据库（如果需要）
if [ ! -f "backend/movies.db" ]; then
    echo "[2/3] 初始化数据库..."
    python3 data/create_dataset.py
else
    echo "[2/3] 数据库已存在，跳过初始化"
fi

# 启动服务
echo "[3/3] 启动服务..."
echo
echo "后端 API: http://localhost:8765"
echo "前端界面: http://localhost:8501"
echo

# 启动后端
python3 -m uvicorn backend.api:app --host 0.0.0.0 --port 8765 --reload &
BACKEND_PID=$!

# 等待后端启动
sleep 3

# 启动前端
streamlit run frontend/app.py --server.port 8501 &
FRONTEND_PID=$!

echo "服务已启动！按 Ctrl+C 停止"
echo

# 捕获退出信号
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

# 等待
wait
