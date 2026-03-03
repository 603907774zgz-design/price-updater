# 飞书机器人配置指南

## 🎯 快速配置步骤

### 步骤 1：创建飞书应用

1. 访问 [飞书开放平台](https://open.feishu.cn/app)
2. 点击 **创建企业自建应用**
3. 填写应用信息：
   - 应用名称: `价格更新助手`
   - 应用描述: `智能识别供应商报价，自动更新价格`
   - 应用图标: 上传一个图标（可选）

### 步骤 2：获取凭证信息

创建完成后，进入应用详情页：

1. 点击左侧 **凭证与基础信息**
2. 复制以下信息：
   - `App ID` (cli_xxx)
   - `App Secret` (点击显示后复制)

### 步骤 3：配置机器人

1. 点击左侧 **机器人**
2. 打开 **启用机器人** 开关
3. 配置：
   - 机器人名称: `价格更新助手`
   - 机器人描述: `智能价格更新机器人`
   - 消息卡片：启用

### 步骤 4：配置事件订阅

1. 点击左侧 **事件与回调**
2. 设置 **请求地址URL**: 
   ```
   https://你的服务器地址/feishu/webhook
   ```
   例如: `https://api.example.com/feishu/webhook`
3. 点击 **保存** 进行URL验证
4. 添加以下事件：
   - ✅ `接收消息` (im.message.receive_v1)

### 步骤 5：配置权限

点击左侧 **权限管理**，添加以下权限：

| 权限 | 说明 |
|------|------|
| `im:chat:readonly` | 获取群信息 |
| `im:message` | 发送消息 |
| `im:message.group_msg` | 接收群消息 |

### 步骤 6：发布应用

1. 点击左侧 **版本管理与发布**
2. 点击 **创建版本**
3. 填写版本信息：
   - 版本号: `1.0.0`
   - 更新说明: `首次发布`
4. 点击 **保存** → **申请发布**
5. 等待管理员审批（如果是自己的企业，直接通过）

### 步骤 7：将机器人添加到群聊/私聊

**群聊方式：**
1. 进入目标群聊
2. 点击群设置 → 群机器人 → 添加机器人
3. 选择 `价格更新助手`

**私聊方式：**
1. 在飞书搜索框搜索 `价格更新助手`
2. 点击开始聊天

---

## ⚙️ 服务端配置

### 方式一：环境变量（推荐）

创建 `.env` 文件：

```bash
# 飞书配置
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
FEISHU_ENCRYPT_KEY=                    # 可选，用于消息加密

# 服务配置
PORT=8000
HOST=0.0.0.0

# 数据库
DATABASE_URL=sqlite:///data/standard_skus.db
```

### 方式二：配置文件

编辑 `config/config.yaml`：

```yaml
feishu:
  app_id: "cli_xxxxxxxxxxxxxxxxx"
  app_secret: "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  encrypt_key: ""  # 可选
```

---

## 🚀 启动服务

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化数据库
python -c "from src.models.database import init_db; init_db()"

# 3. 导入SKU数据
python scripts/import_user_data.py

# 4. 启动服务
python src/main.py
```

---

## 📝 使用方法

### 文本更新

在飞书中发送：
```
大疆pk3标准2575
大疆pk3全能3270
影石go ultra黑2180白2180
```

机器人会：
1. 解析每一行
2. 匹配SKU
3. 返回识别结果卡片
4. 自动更新或等待确认

### 自然语言更新

发送：
```
苹果17白色256改成5799
```

### 查看统计

发送：
```
统计
```

### 查看帮助

发送：
```
帮助
```

---

## 🔧 常见问题

### Q: URL验证失败怎么办？

A: 确保：
1. 服务器已启动并可以访问
2. URL填写正确，包含 `/feishu/webhook`
3. 防火墙已开放对应端口
4. 如果使用HTTPS，证书有效

### Q: 机器人收不到消息？

A: 检查：
1. 事件订阅中已添加 `im.message.receive_v1`
2. 权限管理中已添加 `im:message` 权限
3. 已重新发布应用
4. 机器人已添加到群聊/私聊

### Q: 如何调试？

A: 查看日志：
```bash
# 查看飞书事件日志
tail -f logs/feishu.log

# 或直接运行调试模式
python src/main.py
```

---

## 🔒 安全配置

### 生产环境建议

1. **启用消息加密**：
   - 在飞书后台设置 Encrypt Key
   - 在 `.env` 中配置 `FEISHU_ENCRYPT_KEY`

2. **使用HTTPS**：
   - 配置Nginx反向代理
   - 申请SSL证书

3. **IP白名单**：
   - 在飞书后台配置服务器出口IP

### Nginx配置示例

```nginx
server {
    listen 443 ssl;
    server_name api.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location /feishu/ {
        proxy_pass http://localhost:8000/feishu/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 📞 联系方式

如有问题，请联系管理员或查看日志排查。
