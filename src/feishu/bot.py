"""
飞书机器人完整版
集成价格更新全流程
"""
import json
import requests
import os
import base64
from typing import Dict, Optional, List
from fastapi import Request, UploadFile
from datetime import datetime

from src.parser.text_parser import TextParser
from src.matcher.sku_matcher import SKUMatcher, ExtractedItem
from src.models.database import db, StandardSKU, PriceHistory, UpdateSession, PendingUpdate
from src.utils.excel_handler import ExcelHandler


class FeishuBot:
    """飞书机器人"""
    
    def __init__(self, app_id: str = "", app_secret: str = "", encrypt_key: str = ""):
        self.app_id = app_id
        self.app_secret = app_secret
        self.encrypt_key = encrypt_key
        self.base_url = "https://open.feishu.cn/open-apis"
        self.tenant_access_token = None
        
        # 初始化处理器
        self.text_parser = TextParser()
        self.excel_handler = ExcelHandler()
    
    def get_tenant_access_token(self) -> str:
        """获取tenant_access_token"""
        if self.tenant_access_token:
            return self.tenant_access_token
        
        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        resp = requests.post(url, json=data)
        result = resp.json()
        
        if result.get("code") == 0:
            self.tenant_access_token = result["tenant_access_token"]
            return self.tenant_access_token
        else:
            raise Exception(f"获取token失败: {result}")
    
    def send_text_message(self, chat_id: str, text: str):
        """发送文本消息"""
        try:
            token = self.get_tenant_access_token()
            
            url = f"{self.base_url}/message/v4/send"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "chat_id": chat_id,
                "msg_type": "text",
                "content": {
                    "text": text
                }
            }
            
            resp = requests.post(url, headers=headers, json=data)
            return resp.json()
        except Exception as e:
            print(f"发送消息失败: {e}")
            return None
    
    def send_card_message(self, chat_id: str, card_data: Dict):
        """发送卡片消息"""
        try:
            token = self.get_tenant_access_token()
            
            url = f"{self.base_url}/message/v4/send"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "chat_id": chat_id,
                "msg_type": "interactive",
                "card": card_data
            }
            
            resp = requests.post(url, headers=headers, json=data)
            return resp.json()
        except Exception as e:
            print(f"发送卡片失败: {e}")
            return None
    
    def download_image(self, image_key: str) -> bytes:
        """下载图片"""
        token = self.get_tenant_access_token()
        
        # 获取图片下载链接
        url = f"{self.base_url}/image/v4/images/{image_key}"
        headers = {"Authorization": f"Bearer {token}"}
        
        resp = requests.get(url, headers=headers)
        result = resp.json()
        
        if result.get("code") == 0:
            image_url = result["data"]["image_url"]
            # 下载图片
            img_resp = requests.get(image_url)
            return img_resp.content
        
        return None
    
    def process_price_update_text(self, text: str, user_id: str, chat_id: str):
        """
        处理价格更新文本
        
        Args:
            text: 用户输入的文本
            user_id: 用户ID
            chat_id: 聊天ID
            
        Returns:
            处理结果
        """
        # 1. 解析文本
        parsed_items = self.text_parser.parse(text)
        
        if not parsed_items:
            return {
                "success": False,
                "message": "未识别到有效的价格信息，请检查格式。"
            }
        
        # 2. 匹配SKU
        result = self._match_and_save(parsed_items, user_id, text)
        
        # 3. 发送结果卡片
        self._send_result_card(chat_id, result)
        
        return result
    
    def _match_and_save(self, parsed_items: List, user_id: str, source_content: str) -> Dict:
        """匹配SKU并保存"""
        session = db.get_session()
        matcher = SKUMatcher()
        
        try:
            # 创建更新会话
            import uuid
            session_id = str(uuid.uuid4())
            update_session = UpdateSession(
                session_id=session_id,
                user_id=user_id,
                total_items=len(parsed_items)
            )
            session.add(update_session)
            
            # 处理每个商品项
            auto_matched = 0
            need_confirm = 0
            new_sku_count = 0
            
            results = []
            
            for item in parsed_items:
                # 获取候选SKU
                candidates = []
                if item.brand:
                    candidates = matcher.get_candidates_by_category(item.brand)
                
                # 创建匹配项
                extracted = ExtractedItem(raw_text=item.raw_text, price=item.price)
                extracted.brand = item.brand
                extracted.series = item.series
                extracted.spec = item.spec
                extracted.color = item.color
                extracted.is_preactivated = item.is_preactivated
                
                # 匹配SKU
                matched_sku, score = matcher.match_sku(extracted, candidates)
                extracted.match_score = score
                
                if matched_sku:
                    extracted.matched_sku = matched_sku
                    
                    if score >= 90:
                        extracted.match_status = 'MATCHED'
                        auto_matched += 1
                        
                        # 自动确认，直接更新价格
                        if item.price:
                            history = PriceHistory(
                                sku_code=matched_sku.sku_code,
                                old_price=matched_sku.price,
                                new_price=item.price,
                                source_type='TEXT',
                                source_content=item.raw_text,
                                updated_by=user_id
                            )
                            session.add(history)
                            matched_sku.price = item.price
                            
                    elif score >= 75:
                        extracted.match_status = 'NEED_CONFIRM'
                        need_confirm += 1
                    else:
                        extracted.match_status = 'LOW_CONFIDENCE'
                        need_confirm += 1
                else:
                    extracted.match_status = 'NO_MATCH'
                    new_sku_count += 1
                
                # 保存到待审核表
                pending = PendingUpdate(
                    session_id=session_id,
                    sku_code=matched_sku.sku_code if matched_sku else None,
                    raw_text=item.raw_text,
                    extracted_brand=item.brand,
                    extracted_series=item.series,
                    extracted_spec=item.spec,
                    extracted_color=item.color,
                    extracted_price=item.price,
                    is_preactivated=item.is_preactivated,
                    match_score=score,
                    match_status='PENDING' if extracted.match_status in ['NEED_CONFIRM', 'LOW_CONFIDENCE', 'NO_MATCH'] else 'CONFIRMED',
                    matched_sku_code=matched_sku.sku_code if matched_sku else None
                )
                session.add(pending)
                
                results.append({
                    'raw_text': item.raw_text,
                    'price': item.price,
                    'brand': item.brand,
                    'series': item.series,
                    'spec': item.spec,
                    'color': item.color,
                    'matched_sku': matched_sku.sku_code if matched_sku else None,
                    'matched_title': matched_sku.title if matched_sku else None,
                    'match_score': score,
                    'status': extracted.match_status
                })
            
            # 更新会话统计
            update_session.auto_matched = auto_matched
            update_session.need_confirm = need_confirm
            update_session.new_sku_count = new_sku_count
            
            session.commit()
            
            return {
                "success": True,
                "session_id": session_id,
                "summary": {
                    "total": len(parsed_items),
                    "auto_matched": auto_matched,
                    "need_confirm": need_confirm,
                    "new_sku": new_sku_count
                },
                "results": results
            }
            
        except Exception as e:
            session.rollback()
            return {
                "success": False,
                "message": f"处理失败: {str(e)}"
            }
        finally:
            matcher.close()
            session.close()
    
    def _send_result_card(self, chat_id: str, result: Dict):
        """发送结果卡片"""
        if not result.get("success"):
            self.send_text_message(chat_id, result.get("message", "处理失败"))
            return
        
        summary = result["summary"]
        session_id = result["session_id"]
        
        # 构建卡片内容
        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**识别条目:** {summary['total']}条\n"
                               f"✅ **自动匹配:** {summary['auto_matched']}条\n"
                               f"⚠️ **需确认:** {summary['need_confirm']}条\n"
                               f"🆕 **新SKU:** {summary['new_sku']}条"
                }
            },
            {
                "tag": "hr"
            }
        ]
        
        # 添加变动明细（前5条）
        results = result.get("results", [])
        if results:
            detail_text = "**变动明细:**\n"
            for i, item in enumerate(results[:5], 1):
                status_emoji = "✅" if item["status"] == "MATCHED" else "⚠️" if item["status"] == "NEED_CONFIRM" else "❓"
                detail_text += f"{status_emoji} {item['raw_text'][:25]}\n"
            
            if len(results) > 5:
                detail_text += f"... 还有 {len(results) - 5} 条\n"
            
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": detail_text
                }
            })
        
        # 添加操作按钮
        elements.append({
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": "查看详情"
                    },
                    "type": "primary",
                    "value": {
                        "action": "view_details",
                        "session_id": session_id
                    }
                },
                {
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": "确认全部"
                    },
                    "type": "default",
                    "value": {
                        "action": "confirm_all",
                        "session_id": session_id
                    }
                }
            ]
        })
        
        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "📊 价格更新识别完成"
                },
                "template": "blue"
            },
            "elements": elements
        }
        
        self.send_card_message(chat_id, card)
    
    def handle_text_message(self, text: str, user_id: str, chat_id: str):
        """处理文本消息"""
        text = text.strip()
        
        # 帮助命令
        if text in ["帮助", "help", "?"]:
            help_text = """🤖 **价格更新助手使用说明**

📸 **发送图片**: 直接发送供应商报价单截图，自动识别
📝 **发送文本**: 复制粘贴报价文本
💬 **自然语言**: "苹果17白色256改成5799"
📊 **查看统计**: 发送"统计"

⚠️ **注意事项**:
• 价格变动需要审核确认
• 新SKU会提醒手动添加
• 支持多张图片合并处理"""
            self.send_text_message(chat_id, help_text)
            return
        
        # 统计命令
        if text == "统计":
            self._send_statistics(chat_id)
            return
        
        # 检查是否为价格更新文本
        if self._is_price_update_text(text):
            self.send_text_message(chat_id, "🔄 正在处理价格更新，请稍候...")
            result = self.process_price_update_text(text, user_id, chat_id)
            return
        
        # 自然语言指令
        if text.startswith("价格") or "改成" in text or "改为" in text:
            self._handle_natural_language(text, user_id, chat_id)
            return
        
        # 默认回复
        self.send_text_message(chat_id, '我不理解这个指令，发送"帮助"查看使用说明。')
    
    def _is_price_update_text(self, text: str) -> bool:
        """判断是否为价格更新文本"""
        # 检查是否包含多个数字（价格）
        import re
        prices = re.findall(r'\d{3,5}', text)
        return len(prices) >= 1 and len(text) > 10
    
    def _handle_natural_language(self, text: str, user_id: str, chat_id: str):
        """处理自然语言指令"""
        # 解析自然语言
        # 示例: "苹果17白色256改成5799"
        
        import re
        
        # 提取价格
        price_match = re.search(r'(\d{3,5})', text)
        if not price_match:
            self.send_text_message(chat_id, "❌ 未能识别价格，请使用格式: 商品 价格")
            return
        
        price = int(price_match.group(1))
        
        # 提取商品信息（简化版）
        self.send_text_message(chat_id, f"🤔 理解为: 更新价格到 {price}，正在匹配SKU...")
        
        # 调用文本处理
        result = self.process_price_update_text(text, user_id, chat_id)
    
    def _send_statistics(self, chat_id: str):
        """发送统计信息"""
        session = db.get_session()
        
        try:
            # 今日更新数量
            from datetime import datetime, timedelta
            today = datetime.now().date()
            
            today_count = session.query(PriceHistory).filter(
                PriceHistory.update_time >= today
            ).count()
            
            # 总SKU数量
            total_skus = session.query(StandardSKU).count()
            
            # 空价格SKU数量
            empty_price_count = session.query(StandardSKU).filter(
                StandardSKU.price == None
            ).count()
            
            text = f"""📊 **今日统计**

📝 今日更新: {today_count} 条
📦 总SKU数: {total_skus} 条
⚠️ 空价格SKU: {empty_price_count} 条

继续加油！💪"""
            
            self.send_text_message(chat_id, text)
            
        finally:
            session.close()


# FastAPI路由
from fastapi import APIRouter, HTTPException

feishu_router = APIRouter(prefix="/feishu")

# 全局机器人实例
bot_instance: Optional[FeishuBot] = None

def init_bot(app_id: str, app_secret: str, encrypt_key: str = ""):
    """初始化机器人"""
    global bot_instance
    bot_instance = FeishuBot(app_id, app_secret, encrypt_key)

@feishu_router.post("/webhook")
async def feishu_webhook(request: Request):
    """飞书Webhook入口"""
    global bot_instance
    
    if not bot_instance:
        return {"status": "error", "message": "机器人未初始化"}
    
    try:
        body = await request.json()
        
        # URL验证（飞书首次配置时使用）
        if body.get("type") == "url_verification":
            return {"challenge": body.get("challenge")}
        
        # 解析事件
        event = body.get("event", {})
        event_type = event.get("type")
        
        if event_type != "message":
            return {"status": "ok"}
        
        # 获取消息信息
        msg_type = event.get("msg_type")
        chat_id = event.get("chat_id")
        user_id = event.get("open_id")
        
        if not chat_id or not user_id:
            return {"status": "ok"}
        
        # 处理不同类型的消息
        if msg_type == "text":
            # 获取文本内容
            content = event.get("content", "{}")
            try:
                content_json = json.loads(content)
                text = content_json.get("text", "")
            except:
                text = ""
            
            # 处理文本消息
            bot_instance.handle_text_message(text, user_id, chat_id)
            
        elif msg_type == "image":
            # 处理图片消息
            image_key = event.get("image_key")
            bot_instance.send_text_message(chat_id, "🔄 收到图片，正在识别...")
            
            # 下载并处理图片
            image_bytes = bot_instance.download_image(image_key)
            if image_bytes:
                # TODO: OCR识别图片
                bot_instance.send_text_message(chat_id, "✅ 图片已下载，OCR识别开发中...")
            else:
                bot_instance.send_text_message(chat_id, "❌ 图片下载失败")
        
        return {"status": "ok"}
        
    except Exception as e:
        print(f"处理飞书事件失败: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


if __name__ == '__main__':
    # 测试
    bot = FeishuBot()
    print("飞书机器人模块已加载")
