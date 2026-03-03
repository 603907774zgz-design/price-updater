#!/bin/bash

# 价格更新系统启动脚本

echo "🚀 启动价格智能更新系统..."

# 检查环境
if [ ! -f ".env" ]; then
    echo "⚠️ 警告: .env 文件不存在，使用默认配置"
    echo "请复制 .env.example 到 .env 并配置飞书凭证"
fi

# 创建数据目录
mkdir -p data

# 检查数据库
if [ ! -f "data/standard_skus.db" ]; then
    echo "📦 初始化数据库..."
    PYTHONPATH=. python -c "from src.models.database import init_db; init_db()"
fi

# 启动服务
echo "📡 启动 API 服务..."
echo "📚 文档地址: http://localhost:8000/docs"
echo ""

PYTHONPATH=. python src/main.py
