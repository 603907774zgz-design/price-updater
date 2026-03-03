# 飞书机器人配置检查清单

## ✅ 配置步骤

### 1. 飞书开放平台配置

- [ ] 访问 https://open.feishu.cn/app
- [ ] 创建企业自建应用
- [ ] 记录 App ID 和 App Secret
- [ ] 启用机器人功能
- [ ] 配置事件订阅 URL: `http://你的服务器/feishu/webhook`
- [ ] 添加事件: `im.message.receive_v1`
- [ ] 添加权限: `im:chat:readonly`, `im:message`, `im:message.group_msg`
- [ ] 创建版本并发布应用
- [ ] 将机器人添加到群聊或私聊

### 2. 服务器配置

- [ ] 复制 `.env.example` 到 `.env`
- [ ] 填写 FEISHU_APP_ID
- [ ] 填写 FEISHU_APP_SECRET
- [ ] 配置服务器防火墙，开放端口
- [ ] 如果使用域名，配置Nginx反向代理

### 3. 启动服务

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
./start.sh
```

### 4. 验证配置

- [ ] 访问 `http://服务器地址:8000/` 显示服务信息
- [ ] 访问 `http://服务器地址:8000/docs` 显示API文档
- [ ] 在飞书发送"帮助"，机器人回复使用说明

---

## 🔧 测试命令

在飞书中发送以下命令测试：

```
帮助
```

```
大疆pk3标准2575
大疆pk3全能3270
```

```
统计
```

---

## 🆘 故障排查

### 问题1: URL验证失败

**症状**: 飞书后台提示URL验证失败

**解决**:
1. 确认服务已启动: `curl http://localhost:8000/health`
2. 确认端口开放: `netstat -tlnp | grep 8000`
3. 检查防火墙设置
4. 确认URL格式正确: `http://域名/feishu/webhook`

### 问题2: 机器人无响应

**症状**: 发送消息机器人不回复

**解决**:
1. 检查日志: 查看控制台输出
2. 确认App ID和App Secret正确
3. 确认已添加 `im.message.receive_v1` 事件订阅
4. 确认机器人已添加到当前会话

### 问题3: 消息发送失败

**症状**: 收到消息但无法回复

**解决**:
1. 检查App Secret是否正确
2. 确认已添加 `im:message` 权限
3. 确认应用已发布

---

## 📞 获取帮助

如遇到无法解决的问题，请提供：
1. 错误日志截图
2. 飞书应用配置截图（脱敏）
3. 服务器环境信息
