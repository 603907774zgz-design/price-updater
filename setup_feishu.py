#!/usr/bin/env python3
"""
飞书机器人配置助手
生成配置文件和部署脚本
"""
import json
import os

def generate_config():
    """生成配置文件模板"""
    
    print("=" * 70)
    print("🤖 飞书机器人配置助手")
    print("=" * 70)
    
    print("\n📋 步骤1: 获取飞书应用凭证")
    print("-" * 70)
    print("1. 访问 https://open.feishu.cn/")
    print("2. 创建企业自建应用")
    print("3. 在应用详情页获取 App ID 和 App Secret")
    print()
    
    # 用户输入
    app_id = input("请输入 App ID (格式: cli_xxxx): ").strip()
    app_secret = input("请输入 App Secret: ").strip()
    
    print("\n📋 步骤2: 多维表格配置（可选）")
    print("-" * 70)
    print("如需从飞书多维表格同步标准SKU，请输入以下信息:")
    print()
    
    use_bitable = input("是否配置多维表格同步? (y/n): ").strip().lower() == 'y'
    
    bitable_config = {}
    if use_bitable:
        bitable_token = input("多维表格 App Token: ").strip()
        table_id = input("表格 Table ID: ").strip()
        bitable_config = {
            "app_token": bitable_token,
            "table_id": table_id
        }
    
    # 生成配置文件
    config = {
        "database": {
            "url": "sqlite:///data/standard_skus.db",
            "echo": False
        },
        "ocr": {
            "use_gpu": False,
            "lang": "ch"
        },
        "matching": {
            "auto_confirm_threshold": 60,
            "suggest_threshold": 60,
            "max_candidates": 5
        },
        "feishu": {
            "app_id": app_id,
            "app_secret": app_secret,
            "encrypt_key": "",
            "verification_token": "",
            "bitable": bitable_config
        },
        "logging": {
            "level": "INFO"
        }
    }
    
    # 保存配置文件
    config_path = "config/config.yaml"
    os.makedirs("config", exist_ok=True)
    
    import yaml
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False)
    
    print(f"\n✅ 配置文件已保存到: {config_path}")
    
    # 生成环境变量文件
    env_content = f"""# 飞书配置
FEISHU_APP_ID={app_id}
FEISHU_APP_SECRET={app_secret}
"""
    
    env_path = ".env"
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print(f"✅ 环境变量文件已保存到: {env_path}")
    
    # 生成Dockerfile
    dockerfile_content = '''FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "src/main_v2.py"]
'''
    
    with open("Dockerfile", 'w') as f:
        f.write(dockerfile_content)
    
    print(f"✅ Dockerfile 已生成")
    
    # 生成部署脚本
    deploy_script = '''#!/bin/bash
# 部署脚本

echo "🚀 开始部署价格更新系统..."

# 检查环境变量
if [ -z "$FEISHU_APP_ID" ]; then
    echo "❌ 错误: 未设置 FEISHU_APP_ID 环境变量"
    exit 1
fi

if [ -z "$FEISHU_APP_SECRET" ]; then
    echo "❌ 错误: 未设置 FEISHU_APP_SECRET 环境变量"
    exit 1
fi

# 安装依赖
echo "📦 安装依赖..."
pip install -r requirements.txt

# 初始化数据库
echo "🗄️  初始化数据库..."
python -c "from src.models.database import init_db; init_db()"

# 启动服务
echo "🚀 启动服务..."
python src/main_v2.py
'''
    
    with open("deploy.sh", 'w') as f:
        f.write(deploy_script)
    
    os.chmod("deploy.sh", 0o755)
    print(f"✅ 部署脚本已生成: deploy.sh")
    
    print("\n" + "=" * 70)
    print("📖 下一步操作")
    print("=" * 70)
    print()
    print("1. 本地测试:")
    print("   ./deploy.sh")
    print()
    print("2. 使用 ngrok 暴露本地服务:")
    print("   ngrok http 8000")
    print("   # 将生成的 https 地址填入飞书事件订阅配置")
    print()
    print("3. Docker 部署:")
    print("   docker build -t price-updater .")
    print("   docker run -d -p 8000:8000 --env-file .env price-updater")
    print()
    print("4. 配置飞书事件订阅:")
    print("   请求地址: https://你的地址/feishu/webhook")
    print("   事件: im.message.receive_v1")
    print()
    print("=" * 70)


if __name__ == '__main__':
    try:
        import yaml
    except ImportError:
        print("正在安装 PyYAML...")
        os.system("pip install pyyaml -q")
        import yaml
    
    generate_config()
