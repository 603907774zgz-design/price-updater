# 测试项目结构
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.database import db, StandardSKU, init_db

def add_test_skus():
    """添加测试SKU数据"""
    session = db.get_session()
    
    test_skus = [
        # 大疆/影石
        {'sku_code': 'SKU756985', 'category': '大疆/影石', 'series': 'Osmo Pocket3', 'title': 'Osmo Pocket3', 'spec': '标准版', 'color': '标准', 'price': 2575, 'is_preactivated': False},
        {'sku_code': 'SKU664175', 'category': '大疆/影石', 'series': 'Osmo Pocket3', 'title': 'Osmo Pocket3', 'spec': '全能版', 'color': '标准', 'price': 3270, 'is_preactivated': False},
        {'sku_code': 'SKU292864', 'category': '大疆/影石', 'series': 'Osmo Action 6', 'title': 'Osmo Action 6', 'spec': '标准版', 'color': '标准', 'price': None, 'is_preactivated': False},
        {'sku_code': 'SKU107028', 'category': '大疆/影石', 'series': 'Osmo Action 6', 'title': 'Osmo Action 6', 'spec': '畅拍套装', 'color': '标准', 'price': None, 'is_preactivated': False},
        {'sku_code': 'SKU530890', 'category': '大疆/影石', 'series': 'Osmo Action 5 Pro', 'title': 'Osmo Action 5 Pro', 'spec': '标准版', 'color': '标准', 'price': 1900, 'is_preactivated': False},
        {'sku_code': 'SKU920030', 'category': '大疆/影石', 'series': 'Osmo Action 5 Pro', 'title': 'Osmo Action 5 Pro', 'spec': '畅拍套装', 'color': '标准', 'price': 2460, 'is_preactivated': False},
        {'sku_code': 'SKU523085', 'category': '大疆/影石', 'series': 'Osmo Action 4', 'title': 'Osmo Action 4', 'spec': '标准版', 'color': '标准', 'price': 1290, 'is_preactivated': False},
        {'sku_code': 'SKU596131', 'category': '大疆/影石', 'series': 'Insta360 AcePro2', 'title': 'Insta360 AcePro2 双电池', 'spec': '极夜黑 标准套装', 'color': '黑色', 'price': None, 'is_preactivated': False},
        {'sku_code': 'SKU224680', 'category': '大疆/影石', 'series': 'Insta360 AcePro2', 'title': 'Insta360 AcePro2 双电池', 'spec': '极夜黑 街拍套装（岩墨灰）', 'color': '黑色', 'price': None, 'is_preactivated': False},
        {'sku_code': 'SKU868345', 'category': '大疆/影石', 'series': 'Insta360 AcePro2', 'title': 'Insta360 AcePro2 双电池', 'spec': '极夜黑 街拍套装（星辉银）', 'color': '银色', 'price': None, 'is_preactivated': False},
        {'sku_code': 'SKU784931', 'category': '大疆/影石', 'series': 'Insta360 AcePro2', 'title': 'Insta360 AcePro2 单电池', 'spec': '极夜黑 标准套装', 'color': '黑色', 'price': 2250, 'is_preactivated': False},
        {'sku_code': 'SKU613108', 'category': '大疆/影石', 'series': 'Insta360 AcePro2', 'title': 'Insta360 AcePro2 单电池', 'spec': '冰川白 标准套装', 'color': '白色', 'price': 2300, 'is_preactivated': False},
        {'sku_code': 'SKU963564', 'category': '大疆/影石', 'series': 'Insta360 GO ultra', 'title': 'Insta360 GO ultra', 'spec': '星耀黑 标准版', 'color': '黑色', 'price': 2180, 'is_preactivated': False},
        {'sku_code': 'SKU616022', 'category': '大疆/影石', 'series': 'Insta360 GO ultra', 'title': 'Insta360 GO ultra', 'spec': '灵动白 标准版', 'color': '白色', 'price': 2180, 'is_preactivated': False},
    ]
    
    try:
        for data in test_skus:
            existing = session.query(StandardSKU).filter_by(sku_code=data['sku_code']).first()
            if existing:
                # 更新
                for key, value in data.items():
                    setattr(existing, key, value)
            else:
                # 新建
                sku = StandardSKU(**data)
                session.add(sku)
        
        session.commit()
        print(f"成功导入 {len(test_skus)} 条测试SKU")
        
    except Exception as e:
        session.rollback()
        print(f"导入失败: {e}")
    finally:
        session.close()

if __name__ == '__main__':
    add_test_skus()
