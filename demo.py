#!/usr/bin/env python3
"""
价格更新系统 - 完整演示脚本
展示从图片/文本输入到价格更新的完整流程
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.parser.text_parser import TextParser
from src.matcher.sku_matcher import SKUMatcher
from src.models.database import db, StandardSKU, PriceHistory, init_db
from src.utils.excel_handler import ExcelHandler

def demo_price_update():
    """演示价格更新流程"""
    
    print("=" * 70)
    print("🚀 价格智能更新系统 - 演示")
    print("=" * 70)
    
    # 1. 显示当前标准表状态
    print("\n📋 当前标准SKU表状态")
    print("-" * 70)
    
    session = db.get_session()
    skus = session.query(StandardSKU).all()
    
    total = len(skus)
    with_price = len([s for s in skus if s.price is not None])
    without_price = total - with_price
    
    print(f"   总SKU数: {total}")
    print(f"   有价格: {with_price}")
    print(f"   无价格: {without_price}")
    
    # 按分类统计
    categories = {}
    for sku in skus:
        cat = sku.category
        if cat not in categories:
            categories[cat] = 0
        categories[cat] += 1
    
    print("\n   分类分布:")
    for cat, count in sorted(categories.items()):
        print(f"      {cat}: {count}条")
    
    # 2. 模拟供应商报价输入
    print("\n" + "=" * 70)
    print("📥 供应商报价输入")
    print("=" * 70)
    
    supplier_quote = """2月26日行情参考
大疆pk3标准2575
大疆pk3全能3270
大疆ac4标准1290
大疆ac5标准1900
大疆ac5畅拍2460
大疆ac6标准2750
大疆ac6畅拍3170
影石acepro2单电黑2250
影石acepro2单电白2300
影石acepro2双电黑2300
影石go ultra黑2180白2180
影石新出的产品X 3000"""
    
    print(supplier_quote)
    
    # 3. 解析报价
    print("\n" + "=" * 70)
    print("🔍 解析报价文本")
    print("=" * 70)
    
    parser = TextParser()
    items = parser.parse(supplier_quote)
    
    print(f"✅ 共解析到 {len(items)} 条商品记录")
    
    # 4. 匹配SKU并更新
    print("\n" + "=" * 70)
    print("🎯 SKU匹配与更新")
    print("=" * 70)
    
    updated_items = []
    skipped_items = []
    
    # 预加载所有SKU到内存，避免长时间占用数据库连接
    all_skus = session.query(StandardSKU).all()
    skus_by_category = {}
    for sku in all_skus:
        if sku.category not in skus_by_category:
            skus_by_category[sku.category] = []
        skus_by_category[sku.category].append(sku)
    
    matcher = SKUMatcher()
    
    for item in items:
        # 获取候选SKU
        candidates = []
        if item.brand and item.brand in skus_by_category:
            candidates = skus_by_category[item.brand]
        
        # 匹配
        from src.matcher.sku_matcher import ExtractedItem
        extracted = ExtractedItem(raw_text=item.raw_text, price=item.price)
        extracted.brand = item.brand
        extracted.series = item.series
        extracted.spec = item.spec
        extracted.color = item.color
        extracted.is_preactivated = item.is_preactivated
        
        matched_sku, score = matcher.match_sku(extracted, candidates)
        
        if matched_sku:
            # 在session中找到对应的SKU对象
            sku_to_update = session.query(StandardSKU).filter_by(sku_code=matched_sku.sku_code).first()
            if sku_to_update:
                # 更新价格
                old_price = sku_to_update.price
                sku_to_update.price = item.price
                
                # 记录历史
                history = PriceHistory(
                    sku_code=sku_to_update.sku_code,
                    old_price=old_price,
                    new_price=item.price,
                    source_type='DEMO',
                    source_content=item.raw_text
                )
                session.add(history)
                
                updated_items.append({
                    'sku': sku_to_update,
                    'old_price': old_price,
                    'new_price': item.price,
                    'score': score
                })
                
                change = (item.price or 0) - (old_price or 0)
                change_str = f"+{change}" if change > 0 else f"{change}" if change < 0 else "-"
                
                print(f"✅ {sku_to_update.sku_code} | {sku_to_update.series} {sku_to_update.spec}")
                print(f"   价格: {old_price} → {item.price} ({change_str}) | 匹配分:{score}")
        else:
            skipped_items.append(item)
            print(f"⏭️  跳过: {item.raw_text[:40]}... (未匹配到标准SKU)")
    
    matcher.close()
    session.commit()
    
    # 5. 统计结果
    print("\n" + "=" * 70)
    print("📊 更新统计")
    print("=" * 70)
    
    print(f"   输入商品: {len(items)}条")
    print(f"   ✅ 已更新: {len(updated_items)}条")
    print(f"   ⏭️  已跳过: {len(skipped_items)}条 (标准表中不存在)")
    
    if updated_items:
        price_up = len([i for i in updated_items if (i['new_price'] or 0) > (i['old_price'] or 0)])
        price_down = len([i for i in updated_items if (i['new_price'] or 0) < (i['old_price'] or 0)])
        price_same = len([i for i in updated_items if i['new_price'] == i['old_price']])
        
        print(f"\n   价格变动:")
        print(f"      🔺 上涨: {price_up}条")
        print(f"      🔻 下跌: {price_down}条")
        print(f"      ➡️  持平: {price_same}条")
    
    # 先关闭matcher和session，释放数据库连接
    matcher.close()
    session.close()
    
    # 6. 生成Excel
    print("\n" + "=" * 70)
    print("📁 生成Excel文件")
    print("=" * 70)
    
    handler = ExcelHandler()
    excel_path = handler.generate_standard_excel()
    print(f"✅ 价格表已生成: {excel_path}")
    handler.close()
    
    # 7. 查询历史记录（新开session）
    print("\n" + "=" * 70)
    print("📜 本次更新历史记录")
    print("=" * 70)
    
    session2 = db.get_session()
    history_records = session2.query(PriceHistory).filter_by(source_type='DEMO').order_by(PriceHistory.id.desc()).limit(10).all()
    
    for h in history_records:
        change = (h.new_price or 0) - (h.old_price or 0)
        change_str = f"+{change}" if change > 0 else f"{change}"
        print(f"   {h.sku_code}: {h.old_price} → {h.new_price} ({change_str})")
    
    session2.close()
    
    print("\n" + "=" * 70)
    print("✨ 演示完成!")
    print("=" * 70)
    print("\n功能说明:")
    print("  1. 标准表随时可通过 /api/sku/import/csv 接口更新")
    print("  2. 只更新标准表中已存在的SKU")
    print("  3. 新SKU自动跳过，不做提醒")
    print("  4. 空价格SKU保持原样，不做改动")
    print("=" * 70)


if __name__ == '__main__':
    # 确保数据库已初始化
    if not os.path.exists('data/standard_skus.db'):
        print("初始化数据库...")
        init_db()
        
        # 导入测试数据
        print("导入测试数据...")
        from scripts.add_test_skus import add_test_skus
        add_test_skus()
    
    demo_price_update()
