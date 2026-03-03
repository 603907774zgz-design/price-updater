# 扣子平台快速部署 - 3步完成

## ✅ 你的信息已配置

```
飞书 App ID: cli_a9299274ff785ceb
飞书 App Secret: o7OIObgyvGxhXbHfaiR56eC744jwoesz
多维表格 App Token: F3ibwwsxwiujmwkW0SXc10h0nuc
多维表格 Table ID: tbl4nlhJzZdjkDBb
```

---

## 🚀 部署步骤（只需3步）

### 第1步：创建扣子 Bot

1. 打开 https://www.coze.cn
2. 点击「创建 Bot」
3. 填写：
   - 名称：`价格更新助手`
   - 描述：`智能识别供应商报价，自动更新标准SKU价格`
   - 图标：随便上传一个

---

### 第2步：配置工作流

1. 进入 Bot → 「工作流」页面
2. 点击「创建工作流」
3. 名称：`price_update`
4. 按下图配置节点：

```
开始节点（飞书消息）
    ↓
代码节点（解析消息）
    ↓
条件分支
    ├─ 是「帮助」→ 回复帮助文本 → 结束
    ├─ 是文本 → 调用价格处理代码 → 格式化 → 回复结果 → 结束
    └─ 其他 → 回复不支持 → 结束
```

**关键代码节点配置：**

节点1 - 解析消息（代码）：
```python
import json
def main(args):
    msg = args['message']
    if msg.get('msg_type') == 'text':
        content = json.loads(msg.get('content', '{}'))
        return {'text': content.get('text', ''), 'is_text': True}
    return {'is_text': False}
```

节点2 - 处理价格（代码）：
```python
import sys
sys.path.insert(0, '/workspace/projects/workspace/price-updater')

from src.parser.text_parser import TextParser
from src.matcher.sku_matcher import SKUMatcher, ExtractedItem
from src.models.database import db, StandardSKU, PriceHistory

parser = TextParser()
matcher = SKUMatcher()
session = db.get_session()

def main(args):
    text = args.get('text', '')
    items = parser.parse(text)
    
    # 获取所有SKU
    all_skus = session.query(StandardSKU).all()
    skus_by_category = {}
    for sku in all_skus:
        if sku.category not in skus_by_category:
            skus_by_category[sku.category] = []
        skus_by_category[sku.category].append(sku)
    
    auto_updated = []
    need_confirm = []
    new_skus = []
    
    for item in items:
        candidates = skus_by_category.get(item.brand, [])
        extracted = ExtractedItem(raw_text=item.raw_text, price=item.price)
        extracted.brand = item.brand
        extracted.series = item.series
        extracted.spec = item.spec
        extracted.color = item.color
        extracted.is_preactivated = item.is_preactivated
        
        matched_sku, score = matcher.match_sku(extracted, candidates)
        
        if matched_sku and score >= 60:
            sku_obj = session.query(StandardSKU).filter_by(sku_code=matched_sku.sku_code).first()
            if sku_obj:
                old_price = sku_obj.price
                new_price = item.price
                
                if old_price is not None and new_price is None:
                    need_confirm.append({'type': 'keep', 'sku': sku_obj.sku_code, 'price': old_price})
                elif old_price is None and new_price is not None:
                    need_confirm.append({'type': 'fill', 'sku': sku_obj.sku_code, 'price': new_price})
                elif new_price is not None:
                    history = PriceHistory(sku_code=sku_obj.sku_code, old_price=old_price, new_price=new_price, source_type='COZE')
                    session.add(history)
                    sku_obj.price = new_price
                    auto_updated.append({'sku': sku_obj.sku_code, 'old': old_price, 'new': new_price})
        else:
            new_skus.append(item.raw_text)
    
    session.commit()
    session.close()
    matcher.close()
    
    return {
        'updated': auto_updated,
        'confirm': need_confirm,
        'new': new_skus,
        'total': len(items)
    }
```

节点3 - 格式化输出（代码）：
```python
def main(args):
    result = args
    text = f"📊 价格更新结果\n\n"
    text += f"识别: {result.get('total', 0)}条\n"
    text += f"✅ 自动更新: {len(result.get('updated', []))}条\n"
    text += f"⚠️ 需确认: {len(result.get('confirm', []))}条\n"
    text += f"🆕 新SKU: {len(result.get('new', []))}条\n"
    
    if result.get('updated'):
        text += "\n✅ 已更新:\n"
        for item in result['updated']:
            text += f"  {item['sku']}: {item['old']} → {item['new']}\n"
    
    if result.get('confirm'):
        text += "\n⚠️ 需确认:\n"
        for item in result['confirm']:
            if item['type'] == 'keep':
                text += f"  {item['sku']}: 保留 ¥{item['price']}\n"
            else:
                text += f"  {item['sku']}: 填充 ¥{item['price']}\n"
    
    return {'text': text}
```

---

### 第3步：配置飞书并发布

1. 进入 Bot → 「发布」
2. 选择「飞书」渠道
3. 点击「配置」
4. 填写：
   - App ID: `cli_a9299274ff785ceb`
   - App Secret: `o7OIObgyvGxhXbHfaiR56eC744jwoesz`
   - Encrypt Key: `F3ibwwsxwiujmwkW0SXc10h0nuc`
5. 点击「保存」
6. 点击「发布」

---

## 🎯 完成！开始使用

在飞书群中添加「价格更新助手」机器人，然后：

```
@价格更新助手
大疆pk3标准2575
大疆ac4标准1290
```

机器人会回复处理结果！

---

## ❓ 遇到问题？

1. **检查日志**：扣子平台 → 工作流 → 查看运行日志
2. **测试连接**：在飞书开放平台检查事件订阅是否成功
3. **检查权限**：确保飞书应用已添加必要权限

---

## 📚 完整文档

详细配置说明见：`COZE_DEPLOY.md`
