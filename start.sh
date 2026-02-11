#!/bin/bash

# AI助手桌面应用启动脚本

cd "$(dirname "$0")"

echo "========================================"
echo "   AI助手桌面应用"
echo "========================================"
echo

# 检查Python
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "错误: 未找到Python，请先安装Python 3.10+"
    exit 1
fi

echo "使用Python: $($PYTHON --version)"
echo

# 检查虚拟环境
if [ -d "venv" ]; then
    echo "正在激活虚拟环境..."
    source venv/bin/activate
fi

echo "正在启动AI助手..."
echo

$PYTHON main.py

exit_code=$?

if [ $exit_code -ne 0 ]; then
    echo
    echo "程序异常退出，错误码: $exit_code"
    read -p "按Enter键退出..."
fi
