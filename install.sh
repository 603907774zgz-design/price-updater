#!/bin/bash

# ============================================
# 价格智能更新系统 - 一键安装脚本
# ============================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目配置
PROJECT_NAME="price-updater"
PYTHON_VERSION_REQUIRED="3.9"

# 打印函数
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查 Python 版本
check_python() {
    print_info "检查 Python 环境..."
    
    if ! command_exists python3; then
        print_error "未检测到 Python3，请先安装 Python 3.9 或更高版本"
        echo "  Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-venv python3-pip"
        echo "  macOS: brew install python3"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    print_success "检测到 Python $PYTHON_VERSION"
}

# 创建虚拟环境
setup_venv() {
    print_info "设置 Python 虚拟环境..."
    
    if [ -d "venv" ]; then
        print_warning "虚拟环境已存在，跳过创建"
    else
        python3 -m venv venv
        print_success "虚拟环境创建完成"
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    print_success "虚拟环境已激活"
}

# 安装依赖
install_dependencies() {
    print_info "安装项目依赖..."
    
    # 升级 pip
    pip install --upgrade pip
    
    # 安装 requirements.txt
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_success "依赖安装完成"
    else
        print_warning "未找到 requirements.txt，跳过依赖安装"
    fi
}

# 配置环境变量
setup_env() {
    print_info "配置环境变量..."
    
    if [ -f ".env" ]; then
        print_warning ".env 文件已存在，跳过配置"
        echo ""
        print_info "如需重新配置，请手动编辑 .env 文件或删除后重新运行脚本"
    else
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_success "环境变量文件已创建 (.env)"
            print_warning "请编辑 .env 文件配置你的飞书应用信息"
        else
            # 创建默认 .env 文件
            cat > .env << 'EOF'
# 飞书应用配置
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
FEISHU_ENCRYPT_KEY=

# 服务配置
PORT=8000
HOST=0.0.0.0

# 数据库配置
DATABASE_URL=sqlite:///data/price_updater.db

# 日志配置
LOG_LEVEL=INFO
EOF
            print_success "默认环境变量文件已创建 (.env)"
            print_warning "请务必编辑 .env 文件，填入你的飞书应用 ID 和密钥"
        fi
    fi
}

# 创建必要目录
create_directories() {
    print_info "创建必要目录..."
    
    mkdir -p data
    mkdir -p logs
    print_success "目录创建完成"
}

# 初始化数据库
init_database() {
    print_info "初始化数据库..."
    
    # 检查 src/models/database.py 是否存在
    if [ -f "src/models/database.py" ]; then
        python -c "from src.models.database import init_db; init_db()"
        print_success "数据库初始化完成"
    else
        print_warning "未找到数据库初始化脚本，跳过"
    fi
}

# 添加测试数据
add_test_data() {
    print_info "添加测试 SKU 数据..."
    
    if [ -f "scripts/add_test_skus.py" ]; then
        python scripts/add_test_skus.py
        print_success "测试数据添加完成"
    else
        print_warning "未找到测试数据脚本，跳过"
    fi
}

# 创建启动脚本
create_start_script() {
    print_info "创建启动脚本..."
    
    cat > run.sh << 'EOF'
#!/bin/bash

# 价格智能更新系统启动脚本

# 激活虚拟环境
source venv/bin/activate

# 启动服务
echo "启动价格智能更新系统..."
echo "API 文档: http://localhost:8000/docs"
echo "飞书 Webhook: http://localhost:8000/feishu/webhook"
echo ""

python src/main.py
EOF

    chmod +x run.sh
    print_success "启动脚本已创建 (run.sh)"
}

# 显示安装完成信息
show_completion_info() {
    echo ""
    echo "==========================================="
    echo -e "${GREEN}🎉 安装完成！${NC}"
    echo "==========================================="
    echo ""
    echo "📋 后续步骤："
    echo ""
    
    if [ ! -f ".env" ] || grep -q "cli_xxxxxxxxxxxxxxxxx" .env 2>/dev/null; then
        echo "1. 编辑 .env 文件，配置飞书应用信息："
        echo "   FEISHU_APP_ID=你的应用ID"
        echo "   FEISHU_APP_SECRET=你的应用密钥"
        echo ""
    fi
    
    echo "2. 启动服务："
    echo "   ./run.sh"
    echo ""
    echo "3. 访问 API 文档："
    echo "   http://localhost:8000/docs"
    echo ""
    echo "4. 飞书 Webhook 地址："
    echo "   http://localhost:8000/feishu/webhook"
    echo ""
    echo "📖 更多信息请参阅："
    echo "   - README.md - 项目说明"
    echo "   - FEISHU_SETUP.md - 飞书配置指南"
    echo ""
}

# 主函数
main() {
    echo "==========================================="
    echo "  价格智能更新系统 - 一键安装"
    echo "==========================================="
    echo ""
    
    # 检查是否在项目目录中
    if [ ! -f "requirements.txt" ]; then
        print_error "请在 price-updater 项目目录中运行此脚本"
        exit 1
    fi
    
    # 执行安装步骤
    check_python
    setup_venv
    install_dependencies
    setup_env
    create_directories
    init_database
    add_test_data
    create_start_script
    
    # 显示完成信息
    show_completion_info
}

# 运行主函数
main
