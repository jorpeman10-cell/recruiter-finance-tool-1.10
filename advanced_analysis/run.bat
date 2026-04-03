@echo off
echo ======================================
echo   猎头进阶财务分析工具 - 三速差模型
echo ======================================
echo.
echo 核心功能：
echo   - 职位流速度分析
echo   - 顾问产能分析
echo   - 现金周转分析
echo   - 单职位边际贡献
echo   - 现金流日历
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
    pip install -r ../requirements.txt
)

:: 运行应用
echo [2/2] 启动进阶分析工具...
echo.
echo 应用将在浏览器中打开...
echo 如未自动打开，请访问: http://localhost:8502
echo.

streamlit run app.py --server.port=8502

pause
