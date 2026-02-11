@echo off
chcp 65001 >nul
title AI助手桌面应用
cd /d "%~dp0"

echo ========================================
echo    AI助手桌面应用
echo ========================================
echo.

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.10+
    pause
    exit /b 1
)

:: 检查虚拟环境
if exist venv\Scripts\activate.bat (
    echo 正在激活虚拟环境...
    call venv\Scripts\activate.bat
) else (
    echo 未找到虚拟环境，使用系统Python
)

echo 正在启动AI助手...
echo.

python main.py

if errorlevel 1 (
    echo.
    echo 程序异常退出，错误码: %errorlevel%
    pause
)
