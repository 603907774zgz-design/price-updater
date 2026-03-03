"""
飞书机器人完整版
支持消息处理、卡片交互和多维表格同步
"""
import json
import requests
import os
from typing import Dict, Optional, List
from fastapi import Request, APIRouter

# 加载配置
try:
    import yaml
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    FEISHU_CONFIG = config.get('feishu', {})
except:
    FEISHU_CONFIG = {
        'app_id': os.getenv('FEISHU_APP_ID', ''),
        'app_secret': os.getenv('FEISHU_APP_SECRET', ''),
    }


class FeishuBot:
    """飞书机器人"""
    
    def __init__(self, app_id: str = None, app_secret: str = None):
        self.app_id = app_id or FEISHU_CONFIG.get('app_id')
        self.app_secret = app_secret or FEISHU_CONFIG.get('app_secret')
        self.base_url = "https://open.feishu.cn/open-apis"
        self.tenant_access_token = None
    
    def get_tenant_access_token(self) -> str:
        """获取tenant_access_token"""
        if self.tenant_access_token:
            return self.tenant_access_token
        
        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            resp = requests.post(url, json=data, timeout=10)
            result = resp.json()
            
            if result.get("code") == 0:
                self.tenant_access_token = result["tenant_access_token"]
                return self.tenant_access_token
            else:
                print(f"获取token失败: {result}")
                return None
        except Exception as e:
            print(f"请求token异常: {e}")
            return None
    
    def send_text_message(self, chat_id: str, text: str) -> Dict:
        """发送文本消息"""
        token = self.get_tenant_access_token()
        if not token:
            return {"success": False, "error": "无法获取token"}
        
        url = f"{self.base_url}/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": text})
        }
        
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=10)
            return resp.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_card_message(self, chat_id: str, card_data: Dict) -> Dict:
        """发送卡片消息"""
        token = self.get_tenant_access_token()
        if not token:
            return {"success": False, "error": "无法获取token"}
        
        url = f"{self.base_url}/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "receive_id": chat_id,
            "msg_type": "interactive",
            "content": json.dumps(card_data)
        }
        
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=10)
            return resp.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_update_result_card(self, result: Dict) -> Dict:
        """创建价格更新结果卡片"""
        summary = result.get('summary', {})
        
        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**识别商品:** {summary.get('total_input', 0)}条\n"
                               f"✅ **自动更新:** {summary.get('auto_updated', 0)}条\n"
                               f"⚠️ **保留提醒:** {summary.get('need_confirm_keep', 0)}条\n"
                               f"💡 **填充提醒:** {summary.get('price_empty_remind', 0)}条\n"
                               f"🆕 **新SKU:** {summary.get('new_sku', 0)}条"
                }
            }
        ]
        
        # 添加需要确认保留的项
        need_keep = result.get('need_confirm_keep', [])
        if need_keep:
            elements.append({"tag": "hr"})
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**⚠️ 需要确认 - 保留标准表价格**"
                }
            })
            for item in need_keep[:5]:  # 最多显示5条
                sku = item.get('sku_code', '')
                series = item.get('series', '')
                spec = item.get('spec', '')
                price = item.get('standard_price', '')
                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"• {series} {spec}\n  标准表价格: ¥{price}"
                    }
                })
        
        # 添加需要填充的项
        need_fill = result.get('price_empty_remind', [])
        if need_fill:
            elements.append({"tag": "hr"})
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**💡 需要确认 - 填充空价格**"
                }
            })
            for item in need_fill[:5]:
                sku = item.get('sku_code', '')
                series = item.get('series', '')
                spec = item.get('spec', '')
                price = item.get('new_price', '')
                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"• {series} {spec}\n  建议填充: ¥{price}"
                    }
                })
        
        # 添加新SKU提醒
        new_skus = result.get('new_skus', [])
        if new_skus:
            elements.append({"tag": "hr"})
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**🆕 新SKU提醒**"
                }
            })
            for item in new_skus[:5]:
                raw = item.get('raw_text', '')
                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"• {raw[:30]}..."
                    }
                })
        
        # 添加操作按钮
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": "查看完整结果"
                    },
                    "type": "primary",
                    "value": {
                        "action": "view_full_result",
                        "batch_id": result.get('batch_id', '')
                    }
                },
                {
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": "导出Excel"
                    },
                    "type": "default",
                    "value": {
                        "action": "export_excel",
                        "batch_id": result.get('batch_id', '')
                    }
                }
            ]
        })
        
        return {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "📊 价格更新结果"
                },
                "template": "blue"
            },
            "elements": elements
        }


# 创建路由
feishu_router = APIRouter(prefix="/feishu")

@feishu_router.post("/webhook")
async def feishu_webhook(request: Request):
    """飞书Webhook入口"""
    try:
        body = await request.json()
        
        # URL验证
        if body.get("type") == "url_verification":
            return {"challenge": body.get("challenge")}
        
        # 处理事件
        event = body.get("event", {})
        event_type = event.get("type")
        
        if event_type == "im.message.receive_v1":
            message = event.get("message", {})
            chat_type = message.get("chat_type")
            chat_id = message.get("chat_id")
            msg_type = message.get("message_type")
            
            bot = FeishuBot()
            
            if msg_type == "text":
                content = json.loads(message.get("content", "{}"))
                text = content.get("text", "")
                
                # 解析命令
                if "帮助" in text or "help" in text.lower():
                    help_text = """🤖 **价格更新助手使用指南**

**📸 发送图片更新**
直接发送供应商报价单截图，自动识别并更新价格

**📝 发送文本更新**
格式示例：
```
2月26 行情参考
大疆pk3标准2575
影石acepro2单电黑2250
```

**📋 支持的命令：**
• `帮助` - 显示使用说明
• `导出表格` - 导出当前价格表
• `查看SKU` - 查看标准SKU列表

**⚠️ 提醒规则：**
• ✅ 双方有价格：自动更新
• ⚠️ 标准表有，新信息无：建议保留
• 💡 标准表无，新信息有：建议填充
• 🆕 新SKU：需要确认添加"""
                    
                    bot.send_text_message(chat_id, help_text)
                    
                elif "导出表格" in text or "导出" in text:
                    bot.send_text_message(chat_id, "📊 正在生成价格表，请稍候...")
                    # TODO: 生成并发送Excel文件
                    
                elif "查看SKU" in text:
                    bot.send_text_message(chat_id, "🔍 标准SKU列表功能开发中...")
                    
                else:
                    # 尝试解析为价格文本
                    import sys
                    sys.path.insert(0, '/workspace/projects/workspace/price-updater')
                    from src.parser.text_parser import TextParser
                    from src.matcher.sku_matcher import SKUMatcher
                    from src.models.database import db, StandardSKU
                    
                    parser = TextParser()
                    items = parser.parse(text)
                    
                    if items:
                        bot.send_text_message(chat_id, f"🔄 识别到 {len(items)} 条商品，正在处理...")
                        # TODO: 调用处理逻辑并发送结果卡片
                    else:
                        bot.send_text_message(chat_id, "❓ 无法识别消息内容，发送"帮助"查看使用说明。")
            
            elif msg_type == "image":
                bot.send_text_message(chat_id, "🖼️ 收到图片，正在识别...")
                # TODO: 下载图片并处理
        
        return {"status": "ok"}
        
    except Exception as e:
        print(f"处理飞书事件失败: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


if __name__ == '__main__':
    # 测试
    bot = FeishuBot()
    
    # 测试卡片
    test_result = {
        "batch_id": "test123",
        "summary": {
            "total_input": 10,
            "auto_updated": 5,
            "need_confirm_keep": 2,
            "price_empty_remind": 1,
            "new_sku": 2
        },
        "need_confirm_keep": [
            {
                "sku_code": "SKU001",
                "series": "Osmo Pocket3",
                "spec": "全能版",
                "standard_price": 3200
            }
        ],
        "price_empty_remind": [
            {
                "sku_code": "SKU003",
                "series": "Osmo Action 4",
                "spec": "标准版",
                "new_price": 1290
            }
        ],
        "new_skus": [
            {"raw_text": "影石新出的产品X 3000"}
        ]
    }
    
    card = bot.create_update_result_card(test_result)
    print(json.dumps(card, ensure_ascii=False, indent=2))
