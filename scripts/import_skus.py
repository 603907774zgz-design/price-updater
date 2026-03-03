"""
导入标准SKU数据脚本
"""
import sys
import csv
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.database import db, StandardSKU, init_db


def import_skus_from_csv(csv_file_path: str):
    """
    从CSV文件导入SKU数据
    
    CSV格式:
    商品分类,商品系列,商品标题,商品规格,商品颜色,商品行情价,sku编码
    """
    session = db.get_session()
    
    try:
        count = 0
        updated = 0
        
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                sku_code = row.get('sku编码', '').strip()
                if not sku_code:
                    continue
                
                # 检查是否已存在
                existing = session.query(StandardSKU).filter_by(sku_code=sku_code).first()
                
                # 解析价格
                price_str = row.get('商品行情价', '').strip()
                price = None
                if price_str:
                    try:
                        price = int(float(price_str))
                    except:
                        price = None
                
                # 检测预激活
                title = row.get('商品标题', '')
                is_preactivated = '预激活' in title
                
                if existing:
                    # 更新现有SKU
                    existing.category = row.get('商品分类', '').strip()
                    existing.series = row.get('商品系列', '').strip()
                    existing.title = title.strip()
                    existing.spec = row.get('商品规格', '').strip()
                    existing.color = row.get('商品颜色', '').strip()
                    existing.price = price
                    existing.is_preactivated = is_preactivated
                    updated += 1
                else:
                    # 创建新SKU
                    sku = StandardSKU(
                        sku_code=sku_code,
                        category=row.get('商品分类', '').strip(),
                        series=row.get('商品系列', '').strip(),
                        title=title.strip(),
                        spec=row.get('商品规格', '').strip(),
                        color=row.get('商品颜色', '').strip(),
                        price=price,
                        is_preactivated=is_preactivated
                    )
                    session.add(sku)
                    count += 1
                
                # 每100条提交一次
                if (count + updated) % 100 == 0:
                    session.commit()
                    print(f"已处理 {count + updated} 条...")
        
        session.commit()
        
        print(f"\n导入完成!")
        print(f"  新增: {count} 条")
        print(f"  更新: {updated} 条")
        print(f"  总计: {count + updated} 条")
        
    except Exception as e:
        session.rollback()
        print(f"导入失败: {e}")
        raise
    finally:
        session.close()


def import_skus_from_text(text_content: str):
    """
    从文本导入SKU数据
    文本格式: 空格分隔的表格数据
    """
    session = db.get_session()
    
    try:
        lines = text_content.strip().split('\n')
        count = 0
        
        for line in lines:
            parts = line.split()
            if len(parts) < 7:
                continue
            
            # 解析行数据
            # 商品分类 商品系列 商品标题 商品规格 商品颜色 商品行情价 sku编码
            category = parts[0]
            series = parts[1]
            title = parts[2]
            spec = parts[3]
            color = parts[4]
            price_str = parts[5] if parts[5] != '预激活' else ''
            sku_code = parts[-1]
            
            # 检查是否包含预激活
            is_preactivated = '预激活' in line
            
            # 解析价格
            price = None
            if price_str and price_str.replace('.', '').isdigit():
                try:
                    price = int(float(price_str))
                except:
                    price = None
            
            # 检查是否已存在
            existing = session.query(StandardSKU).filter_by(sku_code=sku_code).first()
            
            if existing:
                # 更新
                existing.category = category
                existing.series = series
                existing.title = title
                existing.spec = spec
                existing.color = color
                existing.price = price
                existing.is_preactivated = is_preactivated
            else:
                # 新建
                sku = StandardSKU(
                    sku_code=sku_code,
                    category=category,
                    series=series,
                    title=title,
                    spec=spec,
                    color=color,
                    price=price,
                    is_preactivated=is_preactivated
                )
                session.add(sku)
                count += 1
        
        session.commit()
        print(f"成功导入 {count} 条SKU数据")
        
    except Exception as e:
        session.rollback()
        print(f"导入失败: {e}")
        raise
    finally:
        session.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='导入标准SKU数据')
    parser.add_argument('--csv', help='CSV文件路径')
    parser.add_argument('--init', action='store_true', help='初始化数据库')
    
    args = parser.parse_args()
    
    if args.init:
        print("初始化数据库...")
        init_db()
        print("数据库初始化完成!")
    
    if args.csv:
        if not os.path.exists(args.csv):
            print(f"错误: 文件不存在 {args.csv}")
            sys.exit(1)
        
        print(f"开始导入: {args.csv}")
        import_skus_from_csv(args.csv)
