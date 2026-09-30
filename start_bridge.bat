@echo off
REM 启动 TV-Schwab 下单桥 (Windows)
cd /d %~dp0
if not exist .env (
    echo 找不到 .env, 先复制 .env.example 为 .env 并填好
    pause
    exit /b 1
)
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
    echo %%a | findstr /b "#" >nul || set "%%a=%%b"
)
echo DRY_RUN=%DRY_RUN%
.venv\Scripts\uvicorn app:app --host 127.0.0.1 --port 8000
pause
