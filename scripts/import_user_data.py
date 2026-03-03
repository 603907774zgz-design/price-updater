"""
临时导入脚本 - 导入用户提供的标准SKU数据
"""
import sys
import os
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.database import db, StandardSKU, init_db

def parse_line(line):
    """解析单行数据"""
    # 使用正则表达式匹配格式
    # 格式: 商品分类 商品系列 商品标题 商品规格 商品颜色 [价格|预激活] [预激活] sku编码
    
    # 先找SKU编码 (SKU开头)
    sku_match = re.search(r'(SKU\d+)', line)
    if not sku_match:
        return None
    
    sku_code = sku_match.group(1)
    
    # 检查是否包含预激活
    is_preactivated = '预激活' in line
    
    # 移除SKU编码后的内容
    line_before_sku = line[:sku_match.start()].strip()
    
    # 分割
    parts = line_before_sku.split()
    if len(parts) < 5:
        return None
    
    category = parts[0]
    series = parts[1]
    title = parts[2]
    spec = parts[3]
    color = parts[4]
    
    # 解析价格
    price = None
    price_match = re.search(r'(\d+\.?\d*)', line_before_sku)
    if price_match:
        try:
            price = int(float(price_match.group(1)))
        except:
            price = None
    
    return {
        'sku_code': sku_code,
        'category': category,
        'series': series,
        'title': title,
        'spec': spec,
        'color': color,
        'price': price,
        'is_preactivated': is_preactivated
    }

def import_from_user_data():
    """从用户数据导入"""
    # 用户提供的样本数据
    user_data = """苹果 iPhone 17 iPhone17 256G 黑色 5751.00 SKU831920
苹果 iPhone 17 iPhone17 256G 白色 5752.00 SKU623654
苹果 iPhone 17 iPhone17 256G 蓝色 5754.00 SKU357763
苹果 iPhone 17 iPhone17 256G 绿色 5753.00 SKU558924
苹果 iPhone 17 iPhone17 256G 紫色 5750.00 SKU832070
苹果 iPhone 17 iPhone17 256G 黑色 预激活 SKU135318
苹果 iPhone 17 iPhone17 256G 白色 预激活 SKU809239
苹果 iPhone 17 iPhone17 256G 蓝色 预激活 SKU119412
苹果 iPhone 17 iPhone17 256G 绿色 预激活 SKU107696
苹果 iPhone 17 iPhone17 256G 紫色 预激活 SKU855768
大疆/影石 Osmo Pocket3 Osmo Pocket3 标准版 SKU756985
大疆/影石 Osmo Pocket3 Osmo Pocket3 全能版 SKU664175
大疆/影石 Insta360 AcePro2 双电池 Insta360 AcePro2 双电池 极夜黑 标准套装 SKU596131"""

    session = db.get_session()
    
    try:
        lines = user_data.strip().split('\n')
        count = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            data = parse_line(line)
            if not data:
                print(f"跳过行: {line}")
                continue
            
            # 检查是否已存在
            existing = session.query(StandardSKU).filter_by(sku_code=data['sku_code']).first()
            
            if existing:
                # 更新
                existing.category = data['category']
                existing.series = data['series']
                existing.title = data['title']
                existing.spec = data['spec']
                existing.color = data['color']
                existing.price = data['price']
                existing.is_preactivated = data['is_preactivated']
            else:
                # 新建
                sku = StandardSKU(**data)
                session.add(sku)
                count += 1
        
        session.commit()
        print(f"成功导入 {count} 条SKU数据")
        
    except Exception as e:
        session.rollback()
        print(f"导入失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == '__main__':
    import_from_user_data()
