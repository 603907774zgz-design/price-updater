#!/bin/bash
# 配置ngrok并启动

echo "🚀 配置ngrok..."

# 设置你的token（修改这一行）
NGROK_TOKEN="你的TOKEN"

if [ "$NGROK_TOKEN" = "你的TOKEN" ]; then
    echo "❌ 错误：请先修改脚本中的 NGROK_TOKEN"
    echo "请访问 https://dashboard.ngrok.com/get-started/your-authtoken 获取"
    exit 1
fi

# 配置token
ngrok config add-authtoken $NGROK_TOKEN

# 启动隧道
echo "🚀 启动ngrok隧道..."
ngrok http 8000
