#!/bin/bash

echo "======================================"
echo "   猎头公司财务分析工具"
echo "======================================"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到Python3，请安装Python 3.8+"
    exit 1
fi

# 检查依赖
echo "[1/2] 检查依赖..."
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "正在安装依赖..."
    pip3 install -r requirements.txt
fi

# 运行应用
echo "[2/2] 启动应用..."
echo ""
echo "应用将在浏览器中打开..."
echo "如未自动打开，请访问: http://localhost:8501"
echo ""

python3 -m streamlit run app.py
