# 价格智能更新系统 - 完整使用指南

## 📦 系统功能

### 核心功能
1. **图片OCR识别** - 识别供应商报价单截图
2. **文本解析** - 解析自然语言和表格文本
3. **SKU智能匹配** - 自动匹配标准表中的SKU
4. **价格更新** - 自动更新价格，支持四种场景处理
5. **提醒功能** - 需要人工确认的情况自动提醒
6. **历史记录** - 记录每次价格变动
7. **飞书集成** - 支持飞书机器人交互
8. **多维表格同步** - 与飞书多维表格双向同步

### 四种处理场景

| 场景 | 标准表 | 新信息 | 处理方式 |
|------|--------|--------|----------|
| ✅ 自动更新 | 有价格 | 有价格 | 自动用新价格覆盖 |
| ⚠️ 保留提醒 | 有价格 | 无价格 | 提醒保留标准表价格 |
| 💡 填充提醒 | 无价格 | 有价格 | 提醒填充新价格 |
| 🆕 新SKU | 不存在 | - | 提醒是否添加新SKU |

---

## 🚀 快速开始

### 1. 安装依赖
```bash
cd /workspace/projects/workspace/price-updater
pip install -r requirements.txt
```

### 2. 初始化数据库
```bash
python -c "from src.models.database import init_db; init_db()"
```

### 3. 导入标准SKU
```bash
# 方式1: 从CSV导入
python -c "
from src.sync.feishu_sync import LocalSKUManager
manager = LocalSKUManager()
manager.import_from_csv('你的标准表.csv')
"

# 方式2: 从飞书多维表格同步
python -c "
from src.sync.feishu_sync import FeishuBaseSync
sync = FeishuBaseSync(app_id='cli_xx', app_secret='xx')
sync.sync_from_bitable(app_token='xx', table_id='xx')
"
```

### 4. 启动服务
```bash
# 本地启动
python src/main_v2.py

# 或使用部署脚本
./deploy.sh
```

---

## 🤖 飞书机器人配置

### 步骤1: 运行配置助手
```bash
python setup_feishu.py
```
按提示输入 App ID 和 App Secret

### 步骤2: 配置飞书应用
1. 登录 https://open.feishu.cn/
2. 创建企业自建应用
3. 添加权限:
   - `im:message:send`
   - `im:message.group_msg`
   - `im:message.p2p_msg`
   - `bitable:app:readonly`
   - `bitable:app:write`
4. 启用机器人
5. 配置事件订阅: `https://你的地址/feishu/webhook`
6. 发布应用

### 步骤3: 添加机器人到群聊
在目标群聊中添加「价格更新助手」机器人

---

## 📖 使用方式

### 方式1: Web API

#### 上传图片更新价格
```bash
curl -X POST "http://localhost:8000/api/price/update/image" \
  -F "images=@报价单.png" \
  -F "user_id=user001"
```

#### 发送文本更新价格
```bash
curl -X POST "http://localhost:8000/api/price/update/text" \
  -F "text=大疆pk3标准2575" \
  -F "user_id=user001"
```

#### 确认价格更新
```bash
curl -X POST "http://localhost:8000/api/price/confirm" \
  -F "batch_id=abc123" \
  -F 'confirm_fill=[{"sku_code":"SKU003","new_price":1290}]'
```

#### 导入标准SKU
```bash
curl -X POST "http://localhost:8000/api/sku/import/csv" \
  -F "file=@标准表.csv"
```

#### 导出价格表
```bash
curl -O "http://localhost:8000/api/price/export"
```

### 方式2: 飞书机器人

#### 发送图片
直接发送供应商报价单截图到群聊

#### 发送文本
```
@价格更新助手
2月26 行情参考
大疆pk3标准2575
大疆pk3全能3270
影石acepro2单电黑2250
```

#### 查看帮助
```
@价格更新助手 帮助
```

#### 导出表格
```
@价格更新助手 导出表格
```

---

## 🗄️ 标准表格式

### CSV格式
```csv
商品分类,商品系列,商品标题,商品规格,商品颜色,商品行情价,sku编码
大疆/影石,Osmo Pocket3,Osmo Pocket3,标准版,标准,2575,SKU001
大疆/影石,Osmo Pocket3,Osmo Pocket3,全能版,标准,3270,SKU002
苹果,iPhone 17,iPhone17,256G,黑色,5751,SKU003
```

### 飞书多维表格字段
| 字段名 | 类型 | 必填 |
|--------|------|------|
| 商品分类 | 文本 | ✓ |
| 商品系列 | 文本 | ✓ |
| 商品标题 | 文本 | ✓ |
| 商品规格 | 文本 | ✓ |
| 商品颜色 | 文本 | ✓ |
| 商品行情价 | 数字 | 可为空 |
| sku编码 | 文本 | ✓ |

---

## 🔧 配置文件

### config/config.yaml
```yaml
database:
  url: "sqlite:///data/standard_skus.db"

ocr:
  use_gpu: false
  lang: "ch"

matching:
  auto_confirm_threshold: 60
  
feishu:
  app_id: "cli_xxxxx"
  app_secret: "xxxxxxxx"
  bitable:
    app_token: "你的AppToken"
    table_id: "你的TableID"
```

---

## 📁 项目结构

```
price-updater/
├── src/
│   ├── main_v2.py          # 主服务（带提醒功能）
│   ├── ocr/                # OCR识别
│   ├── parser/             # 文本解析
│   ├── matcher/            # SKU匹配
│   ├── models/             # 数据库模型
│   ├── feishu/             # 飞书机器人
│   ├── sync/               # 飞书同步
│   └── utils/              # 工具
├── data/
│   └── standard_skus.db    # 数据库
├── config/
│   └── config.yaml         # 配置文件
├── demo_v2.py              # 演示脚本
├── setup_feishu.py         # 飞书配置助手
├── FEISHU_DEPLOY.md        # 飞书部署指南
└── requirements.txt        # 依赖
```

---

## 🔍 演示测试

### 本地演示
```bash
python demo_v2.py
```

### API测试
```bash
# 测试文本更新
curl -X POST "http://localhost:8000/api/price/update/text" \
  -F "text=大疆pk3标准2575
大疆ac4标准1290
影石acepro2单电黑2250"
```

---

## ⚠️ 常见问题

### Q1: 匹配分数太低？
- 检查别名映射表是否完整
- 调整 `auto_confirm_threshold` 阈值
- 在 `src/models/database.py` 中添加更多别名

### Q2: 新SKU识别错误？
- 添加新SKU到标准表
- 更新系列关键词匹配规则

### Q3: OCR识别率低？
- 确保图片清晰
- 使用印刷体报价单
- 裁剪图片只保留文字区域

### Q4: 飞书机器人无响应？
- 检查事件订阅地址
- 确认权限已添加
- 查看应用是否已发布

---

## 📞 技术支持

如有问题，请联系开发团队协助配置。

---

## 📝 更新日志

### v2.0.0 (2026-03-01)
- ✅ 新增四种场景处理（自动更新/保留提醒/填充提醒/新SKU）
- ✅ 新增飞书机器人卡片消息
- ✅ 新增飞书多维表格同步
- ✅ 优化SKU匹配算法
- ✅ 新增演示脚本
