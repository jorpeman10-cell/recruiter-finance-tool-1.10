@echo off
echo ======================================
echo   猎头公司财务分析工具
echo ======================================
echo.

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请安装Python 3.8+
    pause
    exit /b 1
)

:: 检查依赖
echo [1/2] 检查依赖...
pip show streamlit >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖...
    pip install -r requirements.txt
)

:: 运行应用
echo [2/2] 启动应用...
echo.
echo 应用将在浏览器中打开...
echo 如未自动打开，请访问: http://localhost:8501
echo.

streamlit run app.py

pause
