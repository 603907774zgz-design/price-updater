@echo off
chcp 65001 >nul
:: ============================================
:: 价格智能更新系统 - Windows 一键安装脚本
:: ============================================

echo ============================================
echo   价格智能更新系统 - Windows 安装
echo ============================================
echo.

:: 检查 Python
echo [INFO] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未检测到 Python，请先安装 Python 3.9 或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

python --version
echo.

:: 创建虚拟环境
echo [INFO] 创建 Python 虚拟环境...
if exist venv (
    echo [WARNING] 虚拟环境已存在，跳过创建
) else (
    python -m venv venv
    echo [SUCCESS] 虚拟环境创建完成
)

:: 激活虚拟环境并安装依赖
echo [INFO] 安装项目依赖...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip

if exist requirements.txt (
    pip install -r requirements.txt
    echo [SUCCESS] 依赖安装完成
) else (
    echo [WARNING] 未找到 requirements.txt
)

:: 配置环境变量
echo [INFO] 配置环境变量...
if exist .env (
    echo [WARNING] .env 文件已存在，跳过配置
) else (
    if exist .env.example (
        copy .env.example .env
        echo [SUCCESS] 环境变量文件已创建 (.env)
    ) else (
        :: 创建默认 .env 文件
        (
            echo # 飞书应用配置
            echo FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxxx
            echo FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
            echo FEISHU_ENCRYPT_KEY=
            echo.
            echo # 服务配置
            echo PORT=8000
            echo HOST=0.0.0.0
            echo.
            echo # 数据库配置
            echo DATABASE_URL=sqlite:///data/price_updater.db
            echo.
            echo # 日志配置
            echo LOG_LEVEL=INFO
        ) > .env
        echo [SUCCESS] 默认环境变量文件已创建 (.env)
    )
)

:: 创建必要目录
echo [INFO] 创建必要目录...
if not exist data mkdir data
if not exist logs mkdir logs
echo [SUCCESS] 目录创建完成

:: 初始化数据库
echo [INFO] 初始化数据库...
python -c "from src.models.database import init_db; init_db()" 2>nul
if errorlevel 1 (
    echo [WARNING] 数据库初始化失败，可能缺少依赖或配置
) else (
    echo [SUCCESS] 数据库初始化完成
)

:: 添加测试数据
echo [INFO] 添加测试 SKU 数据...
if exist scripts\add_test_skus.py (
    python scripts\add_test_skus.py 2>nul
    echo [SUCCESS] 测试数据添加完成
) else (
    echo [WARNING] 未找到测试数据脚本，跳过
)

:: 创建启动脚本
echo [INFO] 创建启动脚本...
(
    echo @echo off
    echo chcp 65001 ^>nul
    echo :: 价格智能更新系统启动脚本
    echo.
    echo call venv\Scripts\activate.bat
    echo.
    echo echo 启动价格智能更新系统...
    echo echo API 文档: http://localhost:8000/docs
    echo echo 飞书 Webhook: http://localhost:8000/feishu/webhook
    echo echo.
    echo.
    echo python src\main.py
    echo pause
) > run.bat

echo [SUCCESS] 启动脚本已创建 (run.bat)
echo.

:: 显示完成信息
echo ============================================
echo  安装完成！
echo ============================================
echo.
echo 后续步骤：
echo.
echo 1. 编辑 .env 文件，配置飞书应用信息：
echo    FEISHU_APP_ID=你的应用ID
echo    FEISHU_APP_SECRET=你的应用密钥
echo.
echo 2. 启动服务：
echo    run.bat
echo.
echo 3. 访问 API 文档：
echo    http://localhost:8000/docs
echo.
echo 4. 飞书 Webhook 地址：
echo    http://localhost:8000/feishu/webhook
echo.
echo 更多信息请参阅 README.md 和 FEISHU_SETUP.md
echo.
pause
