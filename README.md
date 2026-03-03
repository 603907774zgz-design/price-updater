# 价格智能更新系统

🤖 基于OCR和NLP的价格自动识别与更新工具，支持飞书机器人交互。

## ✨ 功能特性

- 📸 **OCR识别**: 自动识别供应商报价单图片
- 📝 **文本解析**: 支持多种格式的报价文本
- 🎯 **智能匹配**: 基于NLP的SKU自动匹配
- 💬 **飞书机器人**: 支持群聊和私聊交互
- 📊 **审核流程**: 高置信度自动确认，低置信度人工审核
- 📈 **Excel导出**: 生成完整的更新报表

## 📁 项目结构

```
price-updater/
├── src/
│   ├── main.py              # FastAPI主入口
│   ├── ocr/                 # OCR识别模块
│   ├── parser/              # 文本解析模块
│   ├── matcher/             # SKU匹配引擎
│   ├── models/              # 数据库模型
│   ├── feishu/              # 飞书机器人
│   └── utils/               # 工具函数
├── scripts/                 # 数据导入脚本
├── tests/                   # 测试脚本
├── data/                    # 数据库文件
├── requirements.txt         # 依赖清单
├── .env.example            # 环境变量模板
├── FEISHU_SETUP.md         # 飞书配置指南
└── README.md               # 本文件
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制模板文件并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> 💡 查看 [FEISHU_SETUP.md](./FEISHU_SETUP.md) 获取详细的飞书配置指南

### 3. 初始化数据库

```bash
./start.sh
```

或手动执行：

```bash
python -c "from src.models.database import init_db; init_db()"
python scripts/add_test_skus.py
```

### 4. 启动服务

```bash
python src/main.py
```

服务启动后：
- API文档: http://localhost:8000/docs
- 飞书Webhook: http://localhost:8000/feishu/webhook

## 💬 飞书机器人使用

### 文本更新

在飞书中直接发送报价文本：

```
大疆pk3标准2575
大疆pk3全能3270
影石go ultra黑2180白2180
```

机器人会自动：
1. 解析每一行商品
2. 匹配标准SKU
3. 返回识别结果
4. 自动更新或等待确认

### 自然语言更新

发送自然语言指令：

```
苹果17白色256改成5799
```

### 其他命令

| 命令 | 功能 |
|------|------|
| `帮助` | 显示使用说明 |
| `统计` | 查看今日更新统计 |

## 🛠️ API接口

### 文本更新

```bash
curl -X POST "http://localhost:8000/api/price/update/text" \
  -F "text=大疆pk3标准2575" \
  -F "user_id=admin"
```

### 导出Excel

```bash
curl "http://localhost:8000/api/price/export/{session_id}" \
  -o price_update.xlsx
```

### 搜索SKU

```bash
curl "http://localhost:8000/api/sku/search?keyword=pk3"
```

## 📝 数据格式

### 支持的输入格式

**格式1: 简洁格式**
```
大疆pk3标准2575
```

**格式2: 详细格式**
```
苹果 iPhone 17 256G 黑色 5751
```

**格式3: 多颜色**
```
影石go ultra黑2180白2180
```

**格式4: 预激活版本**
```
苹果17 256G 黑色 预激活 5400
```

## 🔧 配置说明

### 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `FEISHU_APP_ID` | ✅ | 飞书应用ID |
| `FEISHU_APP_SECRET` | ✅ | 飞书应用密钥 |
| `FEISHU_ENCRYPT_KEY` | ❌ | 消息加密密钥 |
| `PORT` | ❌ | 服务端口，默认8000 |
| `DATABASE_URL` | ❌ | 数据库URL |

### 数据库模型

**标准SKU表** (`standard_skus`)
- `sku_code`: SKU唯一编码
- `category`: 商品分类（品牌）
- `series`: 商品系列
- `title`: 商品标题
- `spec`: 商品规格
- `color`: 商品颜色
- `price`: 商品行情价
- `is_preactivated`: 是否预激活

## 🧪 测试

```bash
# 运行测试
PYTHONPATH=. python tests/test_feishu.py
```

## 📊 匹配算法

匹配分数计算（0-100分）：
- 预激活匹配: 一票否决
- 颜色匹配: 30分
- 规格匹配: 25分
- 系列匹配: 25分
- 标题匹配: 20分

**匹配策略**：
- ≥90分: 自动确认
- 75-90分: 建议确认
- <75分: 人工确认

## 🚀 部署

### Docker部署（推荐）

```bash
# 构建镜像
docker build -t price-updater .

# 运行容器
docker run -d \
  -p 8000:8000 \
  -e FEISHU_APP_ID=your_app_id \
  -e FEISHU_APP_SECRET=your_app_secret \
  -v ./data:/app/data \
  price-updater
```

### Nginx反向代理

```nginx
server {
    listen 443 ssl;
    server_name api.yourdomain.com;
    
    location /feishu/ {
        proxy_pass http://localhost:8000/feishu/;
        proxy_set_header Host $host;
    }
}
```

## 📖 文档

- [飞书配置指南](./FEISHU_SETUP.md) - 详细的飞书机器人配置步骤
- [API文档](http://localhost:8000/docs) - 自动生成的API文档

## 🤝 贡献

欢迎提交Issue和PR！

## 📄 License

MIT License
