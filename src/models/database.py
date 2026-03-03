"""
数据库模型定义
"""
from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, Text, DECIMAL, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class StandardSKU(Base):
    """标准SKU表"""
    __tablename__ = 'standard_skus'
    
    sku_code = Column(String(20), primary_key=True)
    category = Column(String(50), nullable=False, index=True)  # 商品分类
    series = Column(String(100), nullable=False, index=True)   # 商品系列
    title = Column(String(200), nullable=False)                # 商品标题
    spec = Column(String(100), nullable=False, index=True)     # 商品规格
    color = Column(String(100), nullable=False, index=True)    # 商品颜色
    price = Column(Integer, nullable=True)                     # 商品行情价（允许NULL）
    is_preactivated = Column(Boolean, default=False)           # 是否预激活
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 复合索引，用于加速匹配查询
    __table_args__ = (
        Index('idx_match', 'category', 'series', 'is_preactivated'),
        Index('idx_price_null', 'price'),
    )
    
    def to_dict(self):
        return {
            'sku_code': self.sku_code,
            'category': self.category,
            'series': self.series,
            'title': self.title,
            'spec': self.spec,
            'color': self.color,
            'price': self.price,
            'is_preactivated': self.is_preactivated
        }


class PriceHistory(Base):
    """价格历史表"""
    __tablename__ = 'price_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sku_code = Column(String(20), nullable=False, index=True)
    old_price = Column(Integer, nullable=True)
    new_price = Column(Integer, nullable=True)
    source_type = Column(String(20), nullable=False)  # IMAGE_OCR, TEXT, MANUAL, AUTO_UPDATE, CONFIRM_FILL
    source_content = Column(Text)                     # 原始报价文本
    batch_id = Column(String(20), nullable=True)      # 批次ID
    update_time = Column(DateTime, default=datetime.now, index=True)
    updated_by = Column(String(50))
    
    def to_dict(self):
        return {
            'id': self.id,
            'sku_code': self.sku_code,
            'old_price': self.old_price,
            'new_price': self.new_price,
            'change_amount': (self.new_price or 0) - (self.old_price or 0),
            'source_type': self.source_type,
            'source_content': self.source_content,
            'update_time': self.update_time.isoformat() if self.update_time else None,
            'updated_by': self.updated_by
        }


class AliasMapping(Base):
    """别名映射表"""
    __tablename__ = 'alias_mappings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    alias_type = Column(String(20), nullable=False, index=True)  # BRAND, SERIES, SPEC, COLOR
    alias_key = Column(String(100), nullable=False, index=True)  # 输入值
    standard_value = Column(String(200), nullable=False)         # 标准值
    confidence = Column(DECIMAL(3, 2), default=1.00)
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index('idx_alias', 'alias_type', 'alias_key'),
    )


class UpdateSession(Base):
    """更新会话表（用于存储待审核的更新）"""
    __tablename__ = 'update_sessions'
    
    session_id = Column(String(50), primary_key=True)
    user_id = Column(String(50), nullable=False)
    status = Column(String(20), default='PENDING')  # PENDING, CONFIRMED, CANCELLED
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)
    total_items = Column(Integer, default=0)
    auto_matched = Column(Integer, default=0)
    need_confirm = Column(Integer, default=0)
    new_sku_count = Column(Integer, default=0)


class PendingUpdate(Base):
    """待审核更新项"""
    __tablename__ = 'pending_updates'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), nullable=False, index=True)
    sku_code = Column(String(20), nullable=True)  # 可能为NULL（新SKU）
    raw_text = Column(Text, nullable=False)        # 原始识别文本
    extracted_brand = Column(String(50))
    extracted_series = Column(String(100))
    extracted_spec = Column(String(100))
    extracted_color = Column(String(100))
    extracted_price = Column(Integer)
    is_preactivated = Column(Boolean, default=False)
    match_score = Column(Integer, default=0)       # 匹配分数0-100
    match_status = Column(String(20), default='PENDING')  # PENDING, CONFIRMED, REJECTED
    matched_sku_code = Column(String(20))          # 匹配到的SKU
    notes = Column(Text)                           # 备注
    created_at = Column(DateTime, default=datetime.now)


# 数据库连接管理
class Database:
    def __init__(self, db_url: str = "sqlite:///data/standard_skus.db"):
        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def init_db(self):
        """初始化数据库表"""
        Base.metadata.create_all(self.engine)
        print("数据库表已初始化")
    
    def get_session(self):
        """获取数据库会话"""
        return self.SessionLocal()
    
    def close(self):
        """关闭数据库连接"""
        self.engine.dispose()


# 全局数据库实例
db = Database()

def init_db():
    """初始化数据库（供命令行调用）"""
    # 确保数据目录存在
    os.makedirs('data', exist_ok=True)
    db.init_db()
    
    # 初始化别名映射
    _init_alias_mappings()

def _init_alias_mappings():
    """初始化默认别名映射"""
    session = db.get_session()
    
    # 检查是否已有数据
    existing = session.query(AliasMapping).first()
    if existing:
        session.close()
        return
    
    # 品牌别名
    brand_aliases = [
        ('BRAND', '大疆', '大疆/影石'),
        ('BRAND', 'DJI', '大疆/影石'),
        ('BRAND', 'dji', '大疆/影石'),
        ('BRAND', '影石', '大疆/影石'),
        ('BRAND', 'Insta360', '大疆/影石'),
        ('BRAND', 'insta360', '大疆/影石'),
        ('BRAND', '苹果', '苹果'),
        ('BRAND', 'Apple', '苹果'),
        ('BRAND', 'iphone', '苹果'),
        ('BRAND', '华为', '华为'),
        ('BRAND', '小米', '小米'),
        ('BRAND', '红米', '小米'),
    ]
    
    # 型号别名
    series_aliases = [
        ('SERIES', 'pk3', 'Osmo Pocket3'),
        ('SERIES', 'pocket3', 'Osmo Pocket3'),
        ('SERIES', 'ac4', 'Osmo Action 4'),
        ('SERIES', 'ac5', 'Osmo Action 5 Pro'),
        ('SERIES', 'ac6', 'Osmo Action 6'),
        ('SERIES', 'go ultra', 'Insta360 GO ultra'),
        ('SERIES', 'goultra', 'Insta360 GO ultra'),
        ('SERIES', 'acepro', 'Insta360 AcePro'),
        ('SERIES', 'acepro2', 'Insta360 AcePro2'),
        ('SERIES', 'x5', 'Insta360 X5'),
        ('SERIES', 'x4', 'Insta360 X4'),
    ]
    
    # 规格别名
    spec_aliases = [
        ('SPEC', '标准', '标准版'),
        ('SPEC', '全能', '全能版'),
        ('SPEC', '畅拍', '畅拍套装'),
        ('SPEC', '单电', '单电池'),
        ('SPEC', '双电', '双电池'),
    ]
    
    # 颜色别名
    color_aliases = [
        ('COLOR', '黑', '黑色'),
        ('COLOR', '极夜黑', '黑色'),
        ('COLOR', '曜石黑', '黑色'),
        ('COLOR', '星耀黑', '黑色'),
        ('COLOR', '曜金黑', '黑色'),
        ('COLOR', '幻夜黑', '黑色'),
        ('COLOR', '静夜黑', '黑色'),
        ('COLOR', '深空黑', '黑色'),
        ('COLOR', '绒黑色', '黑色'),
        ('COLOR', '石墨黑', '黑色'),
        ('COLOR', '白', '白色'),
        ('COLOR', '冰川白', '白色'),
        ('COLOR', '灵动白', '白色'),
        ('COLOR', '雪域白', '白色'),
        ('COLOR', '云白色', '白色'),
        ('COLOR', '零度白', '白色'),
        ('COLOR', '月光白', '白色'),
        ('COLOR', '月影白', '白色'),
        ('COLOR', '晨雾白', '白色'),
        ('COLOR', '玉龙雪', '白色'),
    ]
    
    all_aliases = brand_aliases + series_aliases + spec_aliases + color_aliases
    
    for alias_type, alias_key, standard_value in all_aliases:
        mapping = AliasMapping(
            alias_type=alias_type,
            alias_key=alias_key,
            standard_value=standard_value
        )
        session.add(mapping)
    
    session.commit()
    session.close()
    print(f"已初始化 {len(all_aliases)} 条别名映射")


if __name__ == '__main__':
    init_db()
