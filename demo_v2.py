#!/usr/bin/env python3
"""
带提醒功能的价格更新系统 - 演示
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.parser.text_parser import TextParser
from src.matcher.sku_matcher import SKUMatcher
from src.models.database import db, StandardSKU, PriceHistory, init_db

def demo_with_reminders():
    """演示带提醒功能的价格更新"""
    
    print("=" * 80)
    print("🚀 价格智能更新系统 - 带提醒功能演示")
    print("=" * 80)
    
    # 准备测试数据
    print("\n📋 准备测试数据...")
    print("-" * 80)
    
    session = db.get_session()
    
    # 先清空现有数据
    session.query(PriceHistory).delete()
    session.query(StandardSKU).delete()
    session.commit()
    
    # 创建测试SKU（模拟标准表中的SKU）
    test_skus = [
        # 情况1: 标准表有价格，新信息也有价格 → 自动更新
        {'sku_code': 'SKU001', 'category': '大疆/影石', 'series': 'Osmo Pocket3', 'title': 'Osmo Pocket3', 'spec': '标准版', 'color': '标准', 'price': 2500},
        
        # 情况2: 标准表有价格，新信息无价格 → 提醒保留
        {'sku_code': 'SKU002', 'category': '大疆/影石', 'series': 'Osmo Pocket3', 'title': 'Osmo Pocket3', 'spec': '全能版', 'color': '标准', 'price': 3200},
        
        # 情况3: 标准表无价格，新信息有价格 → 提醒填充
        {'sku_code': 'SKU003', 'category': '大疆/影石', 'series': 'Osmo Action 4', 'title': 'Osmo Action 4', 'spec': '标准版', 'color': '标准', 'price': None},
        
        # 情况4: 标准表有价格，新信息也有价格 → 自动更新
        {'sku_code': 'SKU004', 'category': '影石', 'series': 'Insta360 AcePro2', 'title': 'Insta360 AcePro2', 'spec': '单电池 极夜黑', 'color': '黑色', 'price': 2200},
    ]
    
    for data in test_skus:
        sku = StandardSKU(**data)
        session.add(sku)
    
    session.commit()
    print(f"✅ 已创建 {len(test_skus)} 条测试SKU")
    
    # 显示初始状态
    print("\n📊 标准表初始状态:")
    for sku in session.query(StandardSKU).all():
        price_str = f"¥{sku.price}" if sku.price else "（空）"
        print(f"   {sku.sku_code}: {sku.series} {sku.spec} = {price_str}")
    
    session.close()
    
    # 模拟供应商报价（包含4种情况）
    print("\n" + "=" * 80)
    print("📥 供应商报价输入")
    print("=" * 80)
    
    supplier_quote = """2月26日行情参考
大疆pk3标准2575
大疆pk3全能
大疆ac4标准1290
影石acepro2单电黑2250
影石新出的产品X 3000"""
    
    print(supplier_quote)
    print("\n💡 分析:")
    print("   第1条: SKU001 标准表有价格(2500)，新信息有价格(2575) → 自动更新")
    print("   第2条: SKU002 标准表有价格(3200)，新信息无价格 → 提醒保留")
    print("   第3条: SKU003 标准表无价格，新信息有价格(1290) → 提醒填充")
    print("   第4条: SKU004 标准表有价格(2200)，新信息有价格(2250) → 自动更新")
    print("   第5条: 新SKU，标准表中不存在 → 新SKU提醒")
    
    # 解析和处理
    print("\n" + "=" * 80)
    print("🔍 解析并处理")
    print("=" * 80)
    
    parser = TextParser()
    matcher = SKUMatcher()
    session = db.get_session()
    
    items = parser.parse(supplier_quote)
    
    auto_updated = []
    need_confirm_keep = []
    price_empty_remind = []
    new_skus = []
    
    for item in items:
        candidates = []
        if item.brand:
            candidates = matcher.get_candidates_by_category(item.brand)
        
        from src.matcher.sku_matcher import ExtractedItem
        extracted = ExtractedItem(raw_text=item.raw_text, price=item.price)
        extracted.brand = item.brand
        extracted.series = item.series
        extracted.spec = item.spec
        extracted.color = item.color
        extracted.is_preactivated = item.is_preactivated
        
        matched_sku, score = matcher.match_sku(extracted, candidates)
        
        if matched_sku and score >= 60:
            old_price = matched_sku.price
            new_price = item.price
            
            if old_price is not None and new_price is None:
                # 提醒保留
                need_confirm_keep.append({
                    'sku': matched_sku,
                    'old_price': old_price,
                    'reason': '标准表有价格，新信息无价格'
                })
            elif old_price is None and new_price is not None:
                # 提醒填充
                price_empty_remind.append({
                    'sku': matched_sku,
                    'new_price': new_price,
                    'reason': '标准表无价格，新信息有价格'
                })
            elif new_price is not None:
                # 自动更新
                matched_sku.price = new_price
                auto_updated.append({
                    'sku': matched_sku,
                    'old_price': old_price,
                    'new_price': new_price
                })
        else:
            new_skus.append(item)
    
    session.commit()
    
    # 显示结果
    print("\n" + "=" * 80)
    print("✅ 自动更新")
    print("=" * 80)
    if auto_updated:
        for item in auto_updated:
            sku = item['sku']
            print(f"   {sku.sku_code}: {sku.series} {sku.spec}")
            print(f"      价格: {item['old_price']} → {item['new_price']}")
    else:
        print("   无")
    
    print("\n" + "=" * 80)
    print("⚠️  需要确认 - 保留标准表价格")
    print("=" * 80)
    if need_confirm_keep:
        for item in need_confirm_keep:
            sku = item['sku']
            print(f"   {sku.sku_code}: {sku.series} {sku.spec}")
            print(f"      标准表价格: ¥{item['old_price']}")
            print(f"      新信息价格: （无）")
            print(f"      建议: 保留标准表当前价格 ¥{item['old_price']}")
    else:
        print("   无")
    
    print("\n" + "=" * 80)
    print("💡 需要确认 - 填充空价格")
    print("=" * 80)
    if price_empty_remind:
        for item in price_empty_remind:
            sku = item['sku']
            print(f"   {sku.sku_code}: {sku.series} {sku.spec}")
            print(f"      标准表价格: （空）")
            print(f"      新信息价格: ¥{item['new_price']}")
            print(f"      建议: 填充新价格 ¥{item['new_price']}")
    else:
        print("   无")
    
    print("\n" + "=" * 80)
    print("🆕 新SKU提醒")
    print("=" * 80)
    if new_skus:
        for item in new_skus:
            print(f"   原文: {item.raw_text}")
            print(f"      状态: 标准表中不存在此SKU")
            print(f"      建议: 请确认是否需要添加到标准表")
    else:
        print("   无")
    
    # 显示更新后的状态
    print("\n" + "=" * 80)
    print("📊 更新后的标准表状态")
    print("=" * 80)
    
    for sku in session.query(StandardSKU).all():
        price_str = f"¥{sku.price}" if sku.price else "（空）"
        print(f"   {sku.sku_code}: {sku.series} {sku.spec} = {price_str}")
    
    # 清理
    matcher.close()
    session.close()
    
    print("\n" + "=" * 80)
    print("✨ 演示完成!")
    print("=" * 80)
    print("\n提醒功能说明:")
    print("  1. ✅ 自动更新: 双方都有价格，自动用新价格覆盖")
    print("  2. ⚠️  保留提醒: 标准表有价格，新信息无价格，建议保留原价格")
    print("  3. 💡 填充提醒: 标准表无价格，新信息有价格，建议填充新价格")
    print("  4. 🆕 新SKU提醒: 标准表中不存在，需要人工确认是否添加")
    print("=" * 80)


if __name__ == '__main__':
    demo_with_reminders()
