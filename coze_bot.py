"""
扣子平台 - 飞书机器人适配器
直接运行在扣子平台上，无需额外服务器
"""
import json
import os
from typing import Dict, List, Optional

# 扣子平台的消息格式处理
class CozeFeishuAdapter:
    """扣子飞书适配器"""
    
    def __init__(self):
        self.session_id = None
        self.user_id = None
        self.chat_id = None
        self.message_type = None
        self.content = None
    
    def parse_request(self, request_body: Dict) -> Dict:
        """
        解析扣子平台发来的飞书消息
        扣子会将飞书消息转换后转发给Bot
        """
        # 扣子的消息格式
        self.session_id = request_body.get('session_id')
        self.user_id = request_body.get('user_id')
        
        # 获取消息内容
        message = request_body.get('message', {})
        self.chat_id = message.get('chat_id')
        self.message_type = message.get('msg_type')
        
        if self.message_type == 'text':
            content = json.loads(message.get('content', '{}'))
            self.content = content.get('text', '')
        elif self.message_type == 'image':
            self.content = message.get('image_key', '')
        
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'chat_id': self.chat_id,
            'msg_type': self.message_type,
            'content': self.content
        }
    
    def create_text_response(self, text: str) -> Dict:
        """创建文本回复"""
        return {
            'type': 'text',
            'content': text
        }
    
    def create_card_response(self, title: str, elements: List[Dict]) -> Dict:
        """创建卡片回复"""
        return {
            'type': 'card',
            'card': {
                'config': {'wide_screen_mode': True},
                'header': {
                    'title': {'tag': 'plain_text', 'content': title},
                    'template': 'blue'
                },
                'elements': elements
            }
        }


# 核心处理逻辑
class PriceUpdateHandler:
    """价格更新处理器"""
    
    def __init__(self):
        # 初始化组件
        import sys
        sys.path.insert(0, '/workspace/projects/workspace/price-updater')
        
        from src.parser.text_parser import TextParser
        from src.matcher.sku_matcher import SKUMatcher
        from src.models.database import db, StandardSKU, PriceHistory
        
        self.parser = TextParser()
        self.matcher = SKUMatcher()
        self.db = db
    
    def process_text(self, text: str) -> Dict:
        """处理文本消息，更新价格"""
        from src.models.database import StandardSKU, PriceHistory
        
        # 解析文本
        items = self.parser.parse(text)
        
        if not items:
            return {
                'success': False,
                'message': '未识别到任何商品信息'
            }
        
        # 获取所有SKU
        session = self.db.get_session()
        all_skus = session.query(StandardSKU).all()
        
        # 按分类分组
        skus_by_category = {}
        for sku in all_skus:
            if sku.category not in skus_by_category:
                skus_by_category[sku.category] = []
            skus_by_category[sku.category].append(sku)
        
        # 处理每个商品
        auto_updated = []
        need_confirm_keep = []
        price_empty_remind = []
        new_skus = []
        
        for item in items:
            candidates = []
            if item.brand and item.brand in skus_by_category:
                candidates = skus_by_category[item.brand]
            
            # 匹配SKU
            from src.matcher.sku_matcher import ExtractedItem
            extracted = ExtractedItem(raw_text=item.raw_text, price=item.price)
            extracted.brand = item.brand
            extracted.series = item.series
            extracted.spec = item.spec
            extracted.color = item.color
            extracted.is_preactivated = item.is_preactivated
            
            matched_sku, score = self.matcher.match_sku(extracted, candidates)
            
            if matched_sku and score >= 60:
                # 在session中找到对应SKU
                from src.models.database import StandardSKU
                sku_obj = session.query(StandardSKU).filter_by(sku_code=matched_sku.sku_code).first()
                
                if sku_obj:
                    old_price = sku_obj.price
                    new_price = item.price
                    
                    if old_price is not None and new_price is None:
                        # 提醒保留
                        need_confirm_keep.append({
                            'sku_code': sku_obj.sku_code,
                            'series': sku_obj.series,
                            'spec': sku_obj.spec,
                            'color': sku_obj.color,
                            'standard_price': old_price,
                            'suggestion': '供应商报价中无此SKU价格，建议保留标准表当前价格'
                        })
                    elif old_price is None and new_price is not None:
                        # 提醒填充
                        price_empty_remind.append({
                            'sku_code': sku_obj.sku_code,
                            'series': sku_obj.series,
                            'spec': sku_obj.spec,
                            'color': sku_obj.color,
                            'new_price': new_price,
                            'suggestion': '标准表中此SKU价格为空，供应商报价有价格，建议填充'
                        })
                    elif new_price is not None:
                        # 自动更新
                        history = PriceHistory(
                            sku_code=sku_obj.sku_code,
                            old_price=old_price,
                            new_price=new_price,
                            source_type='COZE_BOT',
                            source_content=item.raw_text
                        )
                        session.add(history)
                        sku_obj.price = new_price
                        
                        auto_updated.append({
                            'sku_code': sku_obj.sku_code,
                            'series': sku_obj.series,
                            'spec': sku_obj.spec,
                            'color': sku_obj.color,
                            'old_price': old_price,
                            'new_price': new_price,
                            'change': (new_price or 0) - (old_price or 0)
                        })
            else:
                # 新SKU
                new_skus.append({
                    'raw_text': item.raw_text,
                    'parsed_brand': item.brand,
                    'parsed_series': item.series,
                    'parsed_price': item.price,
                    'suggestion': '标准表中不存在此SKU，请确认是否需要添加'
                })
        
        session.commit()
        session.close()
        
        return {
            'success': True,
            'summary': {
                'total_input': len(items),
                'auto_updated': len(auto_updated),
                'need_confirm_keep': len(need_confirm_keep),
                'price_empty_remind': len(price_empty_remind),
                'new_sku': len(new_skus)
            },
            'auto_updated': auto_updated,
            'need_confirm_keep': need_confirm_keep,
            'price_empty_remind': price_empty_remind,
            'new_skus': new_skus
        }
    
    def format_result_card(self, result: Dict) -> str:
        """格式化结果为卡片文本"""
        summary = result.get('summary', {})
        
        text = f"📊 价格更新结果\n\n"
        text += f"识别商品: {summary.get('total_input', 0)}条\n"
        text += f"✅ 自动更新: {summary.get('auto_updated', 0)}条\n"
        text += f"⚠️ 保留提醒: {summary.get('need_confirm_keep', 0)}条\n"
        text += f"💡 填充提醒: {summary.get('price_empty_remind', 0)}条\n"
        text += f"🆕 新SKU: {summary.get('new_sku', 0)}条\n"
        
        # 自动更新详情
        auto_updated = result.get('auto_updated', [])
        if auto_updated:
            text += "\n✅ 自动更新:\n"
            for item in auto_updated:
                change = item.get('change', 0)
                change_str = f"+{change}" if change > 0 else f"{change}"
                text += f"  {item['sku_code']}: {item['series']} {item['spec']}\n"
                text += f"    {item['old_price']} → {item['new_price']} ({change_str})\n"
        
        # 保留提醒
        need_keep = result.get('need_confirm_keep', [])
        if need_keep:
            text += "\n⚠️ 建议保留标准表价格:\n"
            for item in need_keep:
                text += f"  {item['sku_code']}: {item['series']} {item['spec']}\n"
                text += f"    标准表价格: ¥{item['standard_price']} (供应商未报价)\n"
        
        # 填充提醒
        need_fill = result.get('price_empty_remind', [])
        if need_fill:
            text += "\n💡 建议填充空价格:\n"
            for item in need_fill:
                text += f"  {item['sku_code']}: {item['series']} {item['spec']}\n"
                text += f"    建议填充: ¥{item['new_price']}\n"
        
        # 新SKU
        new_skus = result.get('new_skus', [])
        if new_skus:
            text += "\n🆕 新SKU提醒:\n"
            for item in new_skus:
                text += f"  {item['raw_text'][:30]}... (标准表中不存在)\n"
        
        return text


# 扣子平台入口函数
def main(request_body: Dict) -> Dict:
    """
    扣子平台主入口
    扣子会将飞书消息以特定格式传入此函数
    """
    adapter = CozeFeishuAdapter()
    message = adapter.parse_request(request_body)
    
    handler = PriceUpdateHandler()
    
    # 处理不同类型的消息
    if message['msg_type'] == 'text':
        text = message['content']
        
        # 处理命令
        if '帮助' in text or 'help' in text.lower():
            help_text = """🤖 价格更新助手使用指南

📸 发送图片：直接上传供应商报价单截图
📝 发送文本：直接粘贴报价文本

支持的格式：
大疆pk3标准2575
影石acepro2单电黑2250

📋 命令：
• 帮助 - 显示使用说明
• 导出 - 导出当前价格表

⚠️ 提醒规则：
✅ 双方有价格 → 自动更新
⚠️ 标准表有，新信息无 → 建议保留
💡 标准表无，新信息有 → 建议填充
🆕 新SKU → 需要确认添加"""
            return adapter.create_text_response(help_text)
        
        elif '导出' in text:
            return adapter.create_text_response("📊 导出功能开发中...")
        
        else:
            # 尝试解析为价格更新
            result = handler.process_text(text)
            
            if result.get('success'):
                result_text = handler.format_result_card(result)
                return adapter.create_text_response(result_text)
            else:
                return adapter.create_text_response(result.get('message', '处理失败'))
    
    elif message['msg_type'] == 'image':
        return adapter.create_text_response("🖼️ 图片识别功能开发中，请暂时使用文本方式发送报价")
    
    else:
        return adapter.create_text_response('❓ 暂不支持此消息类型，发送"帮助"查看使用说明')


# 测试
if __name__ == '__main__':
    # 模拟扣子请求
    test_request = {
        'session_id': 'test123',
        'user_id': 'user001',
        'message': {
            'chat_id': 'chat001',
            'msg_type': 'text',
            'content': json.dumps({'text': '大疆pk3标准2575\n大疆ac4标准1290'})
        }
    }
    
    result = main(test_request)
    print(json.dumps(result, ensure_ascii=False, indent=2))
