# 飞书部署指南

## 一、创建飞书应用

### 1. 登录飞书开放平台
- 访问: https://open.feishu.cn/
- 登录你的飞书账号

### 2. 创建企业自建应用
1. 点击「创建应用」
2. 选择「企业自建应用」
3. 填写应用名称: "价格更新助手"
4. 选择应用类型: "机器人"
5. 创建完成

### 3. 获取应用凭证
在应用详情页获取:
- **App ID**: `cli_xxxxx`
- **App Secret**: 点击显示并复制

将这两个值填入 `config/config.yaml`:
```yaml
feishu:
  app_id: "cli_xxxxx"
  app_secret: "xxxxxxxx"
```

### 4. 配置权限
在「权限管理」中添加以下权限:
- `im:chat:readonly` (读取群组信息)
- `im:message:send` (发送消息)
- `im:message.group_msg` (接收群消息)
- `im:message.p2p_msg` (接收单聊消息)
- `bitable:app:readonly` (读取多维表格)
- `bitable:app:write` (写入多维表格)

### 5. 启用机器人
在「机器人」页面:
1. 开启机器人
2. 设置机器人名称和头像
3. 添加机器人简介

### 6. 配置事件订阅
在「事件订阅」页面:
1. 开启事件订阅
2. 设置请求地址: `https://你的服务器地址/feishu/webhook`
3. 添加事件:
   - `im.message.receive_v1` (接收消息)

### 7. 发布应用
在「版本管理与发布」页面:
1. 点击「创建版本」
2. 填写版本号和更新说明
3. 点击「保存并发布」
4. 申请发布，等待审核

---

## 二、创建飞书多维表格（标准SKU库）

### 1. 创建多维表格
1. 在飞书中创建新的多维表格
2. 命名: "标准SKU库"
3. 设置字段（列）:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| 商品分类 | 文本 | 如: 苹果、华为、大疆/影石 |
| 商品系列 | 文本 | 如: iPhone 17、Mate 80 |
| 商品标题 | 文本 | 如: iPhone17 |
| 商品规格 | 文本 | 如: 256G、标准版、全能版 |
| 商品颜色 | 文本 | 如: 黑色、白色 |
| 商品行情价 | 数字 | 当前价格（可为空） |
| sku编码 | 文本 | 唯一标识，如: SKU831920 |

### 2. 获取多维表格凭证
1. 打开多维表格
2. 点击右上角「...」→「设置」
3. 复制「App Token」和「Table ID」
4. 将这两个值填入 `config/config.yaml`:

```yaml
feishu:
  bitable:
    app_token: "你的AppToken"
    table_id: "你的TableID"
```

### 3. 导入现有SKU数据
1. 将标准表导出为CSV
2. 在多维表格中点击「导入」→「从Excel/CSV导入」
3. 选择CSV文件导入

---

## 三、部署后端服务

### 方式1: 本地部署（测试）
```bash
cd /workspace/projects/workspace/price-updater
pip install -r requirements.txt
python src/main_v2.py
```

使用 ngrok 暴露本地服务:
```bash
ngrok http 8000
```
将生成的 https 地址填入飞书事件订阅配置。

### 方式2: 服务器部署
```bash
# 克隆代码到服务器
git clone <你的代码仓库>
cd price-updater

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
export FEISHU_APP_ID="cli_xxxxx"
export FEISHU_APP_SECRET="xxxxxxxx"

# 启动服务（使用gunicorn）
gunicorn src.main_v2:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### 方式3: Docker部署
```bash
# 构建镜像
docker build -t price-updater .

# 运行容器
docker run -d \
  -p 8000:8000 \
  -e FEISHU_APP_ID="cli_xxxxx" \
  -e FEISHU_APP_SECRET="xxxxxxxx" \
  price-updater
```

---

## 四、使用飞书机器人

### 1. 添加机器人到群聊
1. 在目标群聊中点击「设置」
2. 选择「群机器人」
3. 点击「添加机器人」
4. 搜索并添加「价格更新助手」

### 2. 常用命令

#### 更新价格（发送图片）
直接发送供应商报价单截图，机器人会自动识别。

#### 更新价格（发送文本）
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

#### 导出价格表
```
@价格更新助手 导出表格
```

---

## 五、飞书多维表格同步

### 从多维表格同步到本地
```bash
python -c "
from src.sync.feishu_sync import FeishuBaseSync
sync = FeishuBaseSync(app_id='cli_xxxxx', app_secret='xxxxxxxx')
result = sync.sync_from_bitable(app_token='你的AppToken', table_id='你的TableID')
print(result)
"
```

### 从本地同步到多维表格
```bash
python -c "
from src.sync.feishu_sync import FeishuBaseSync
sync = FeishuBaseSync(app_id='cli_xxxxx', app_secret='xxxxxxxx')
result = sync.export_to_bitable(app_token='你的AppToken', table_id='你的TableID')
print(result)
"
```

---

## 六、常见问题

### Q1: 机器人不回复消息？
- 检查事件订阅地址是否正确
- 检查权限是否配置完整
- 检查应用是否已发布

### Q2: 无法读取多维表格？
- 确保已添加 bitable 相关权限
- 确保多维表格已分享给应用（在多维表格设置中添加应用）

### Q3: OCR识别率低？
- 确保图片清晰
- 确保文字是印刷体
- 可以尝试裁剪图片只保留文字部分

---

## 七、联系我获取帮助

如有问题，请联系我协助配置。
