@echo off

echo ========================================
echo   ZhiWen Database - Starting...
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] Checking dependencies...
.venv\Scripts\pip.exe install -q -r requirements.txt 2>nul

echo [2/3] Checking database...
if not exist "backend\movies.db" (
    echo Creating database...
    .venv\Scripts\python.exe data\create_dataset.py
) else (
    echo Database exists.
)

echo [3/3] Starting services...
echo.
echo Backend API: http://127.0.0.1:8765
echo Frontend:    http://127.0.0.1:8501
echo.

start "Backend" .venv\Scripts\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port 8765 --reload

timeout /t 3 /nobreak >nul

start "Frontend" .venv\Scripts\python.exe -m streamlit run frontend\app.py --server.port 8501 --server.address 127.0.0.1

echo Services started! Press any key to exit...
pause >nul
