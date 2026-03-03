"""
SKU智能匹配引擎
"""
from typing import List, Dict, Optional, Tuple
from fuzzywuzzy import fuzz
from sqlalchemy import or_, and_
from src.models.database import db, StandardSKU, AliasMapping
import re


class ExtractedItem:
    """提取的商品项"""
    def __init__(self, raw_text: str, price: Optional[int] = None):
        self.raw_text = raw_text
        self.price = price
        self.brand: Optional[str] = None
        self.series: Optional[str] = None
        self.spec: Optional[str] = None
        self.color: Optional[str] = None
        self.is_preactivated: bool = False
        self.match_score: int = 0
        self.matched_sku: Optional[StandardSKU] = None
        self.match_status: str = 'PENDING'  # PENDING, MATCHED, NEED_CONFIRM, NO_MATCH
    
    def to_dict(self):
        return {
            'raw_text': self.raw_text,
            'price': self.price,
            'brand': self.brand,
            'series': self.series,
            'spec': self.spec,
            'color': self.color,
            'is_preactivated': self.is_preactivated,
            'match_score': self.match_score,
            'match_status': self.match_status,
            'matched_sku': self.matched_sku.to_dict() if self.matched_sku else None
        }


class SKUMatcher:
    """SKU匹配器"""
    
    # 颜色关键词映射
    COLOR_KEYWORDS = {
        '黑色': ['黑', '极夜黑', '曜石黑', '星耀黑', '曜金黑', '幻夜黑', '静夜黑', '深空黑', '绒黑色', '石墨黑', '岩墨灰'],
        '白色': ['白', '冰川白', '灵动白', '雪域白', '云白色', '零度白', '月光白', '月影白', '晨雾白', '玉龙雪'],
        '蓝色': ['蓝', '海岛蓝', '天海青', '天青色', '天青釉', '苍空蓝', '冰川蓝', '湖光青', '星海蓝', '晴空蓝', '绣球蓝'],
        '金色': ['金', '晨曦金', '香槟金', '极昼金', '沙漠金', '蜜糖金'],
        '银色': ['银', '钛空银', '原色', '金属原色', '星际银', '冰霜银', '月影白', '月光银'],
        '紫色': ['紫', '罗兰紫', '羽纱紫', '鸢尾紫', '槿紫', '紫', '紫/粉色', '星光蝴蝶紫'],
        '绿色': ['绿', '云杉绿', '向新绿', '竹韵青', '湖水青', '松石绿', '青松', '苍岭绿', '海湖青', '天海青'],
        '粉色': ['粉', '樱花粉', '淡桃粉', '珊瑚粉', '星光粉', '樱语粉', '莹彩粉'],
        '灰色': ['灰', '深空灰', '烟云灰', '苍山灰', '星际灰', '钛灰色', '星空灰', '曜石黑', '钛空灰'],
        '红色': ['红', '朱砂红', '珊瑚红', '玫红', '中国红'],
        '橙色': ['橙', '燃橙色', '珊瑚橙', '赤茶橘'],
        '黄色': ['黄', '柠檬黄', '鹅黄'],
    }
    
    def __init__(self):
        self.session = db.get_session()
        self._load_aliases()
    
    def _load_aliases(self):
        """加载别名映射到内存"""
        self.aliases = {
            'BRAND': {},
            'SERIES': {},
            'SPEC': {},
            'COLOR': {}
        }
        
        mappings = self.session.query(AliasMapping).all()
        for mapping in mappings:
            if mapping.alias_type in self.aliases:
                self.aliases[mapping.alias_type][mapping.alias_key.lower()] = mapping.standard_value
    
    def normalize_text(self, text: str) -> str:
        """文本标准化"""
        # 统一空格
        text = ' '.join(text.split())
        # 转小写
        text = text.lower()
        return text
    
    def extract_price(self, text: str) -> Optional[int]:
        """从文本中提取价格"""
        # 匹配数字（4-5位，常见价格范围）
        matches = re.findall(r'\b(\d{3,5})\b', text)
        if matches:
            # 返回最大的数字（通常价格是最高的）
            prices = [int(m) for m in matches]
            # 过滤合理的价格范围（500-50000）
            valid_prices = [p for p in prices if 500 <= p <= 50000]
            if valid_prices:
                return max(valid_prices)
        return None
    
    def check_preactivated(self, text: str) -> bool:
        """检测是否包含预激活"""
        return '预激活' in text or '预激活版' in text
    
    def normalize_brand(self, brand: str) -> Optional[str]:
        """标准化品牌"""
        brand = brand.lower()
        return self.aliases['BRAND'].get(brand, brand)
    
    def normalize_series(self, series: str) -> Optional[str]:
        """标准化系列"""
        series = series.lower().replace(' ', '')
        return self.aliases['SERIES'].get(series, series)
    
    def normalize_spec(self, spec: str) -> str:
        """标准化规格"""
        spec = spec.lower()
        # 检查别名
        for alias, standard in self.aliases['SPEC'].items():
            if alias in spec:
                return standard
        return spec
    
    def extract_colors(self, text: str) -> List[str]:
        """从文本中提取颜色"""
        colors = []
        for standard_color, keywords in self.COLOR_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    colors.append(standard_color)
                    break
        return colors if colors else ['未知']
    
    def parse_item(self, text: str) -> ExtractedItem:
        """解析单条文本"""
        item = ExtractedItem(raw_text=text)
        
        # 提取价格
        item.price = self.extract_price(text)
        
        # 检测预激活
        item.is_preactivated = self.check_preactivated(text)
        
        # 提取颜色（需要在其他处理前，因为颜色可能包含在型号中）
        colors = self.extract_colors(text)
        if colors:
            item.color = colors[0]  # 先取第一个，后续处理多颜色
        
        # TODO: 品牌、系列、规格的提取需要更智能的NLP
        # 这里先使用简单的关键词匹配
        
        return item
    
    def split_multi_color_items(self, items: List[ExtractedItem]) -> List[ExtractedItem]:
        """拆分多颜色条目"""
        result = []
        
        for item in items:
            text = item.raw_text
            
            # 检测是否有多个颜色+价格组合
            # 模式1: "黑2180白2180"
            # 模式2: "黑/白/蓝 2100"
            
            color_price_pattern = re.findall(r'(黑|白|蓝|金|银|紫|绿|粉|灰|红|橙|黄)(\d{3,5})', text)
            
            if len(color_price_pattern) >= 2:
                # 有多个颜色价格组合，拆分
                for color_keyword, price in color_price_pattern:
                    new_item = ExtractedItem(raw_text=f"{text.split(color_keyword)[0]}{color_keyword}{price}",
                                            price=int(price))
                    new_item.is_preactivated = item.is_preactivated
                    
                    # 映射颜色
                    for standard, keywords in self.COLOR_KEYWORDS.items():
                        if color_keyword in keywords:
                            new_item.color = standard
                            break
                    
                    result.append(new_item)
            else:
                # 检查是否有多个颜色但同价
                multi_color_pattern = re.findall(r'([黑白蓝金银紫绿粉灰红橙黄])[、，,\/]([黑白蓝金银紫绿粉灰红橙黄])', text)
                if multi_color_pattern and item.price:
                    # 提取所有颜色
                    all_colors = re.findall(r'[黑白蓝金银紫绿粉灰红橙黄]', text)
                    for color_keyword in all_colors:
                        if color_keyword in text:
                            new_item = ExtractedItem(raw_text=f"{text.split(color_keyword)[0]}{color_keyword} {item.price}",
                                                    price=item.price)
                            new_item.is_preactivated = item.is_preactivated
                            
                            for standard, keywords in self.COLOR_KEYWORDS.items():
                                if color_keyword in keywords:
                                    new_item.color = standard
                                    break
                            
                            result.append(new_item)
                else:
                    result.append(item)
        
        return result
    
    def match_sku(self, item: ExtractedItem, candidates: List[StandardSKU]) -> Tuple[Optional[StandardSKU], int]:
        """
        匹配SKU，返回最佳匹配和分数
        只匹配标准表中已存在的SKU，新SKU返回None
        """
        if not candidates:
            return None, 0
        
        best_match = None
        best_score = 0
        
        for sku in candidates:
            score = self._calculate_match_score(item, sku)
            if score > best_score:
                best_score = score
                best_match = sku
        
        # 只返回高置信度匹配（>=60分），低于此阈值视为未匹配（新SKU或无法识别）
        if best_score >= 60:
            return best_match, best_score
        else:
            return None, best_score
    
    def _calculate_match_score(self, item: ExtractedItem, sku: StandardSKU) -> int:
        """计算匹配分数（0-100）"""
        score = 0
        max_possible = 0
        
        # 1. 预激活匹配（一票否决）
        if item.is_preactivated != sku.is_preactivated:
            return 0  # 预激活不匹配直接0分
        
        # 2. 系列匹配（35分）- 最重要
        if item.raw_text:
            series_score = self._match_series(item.raw_text, sku.series)
            score += series_score * 35
            max_possible += 35
        
        # 3. 规格匹配（30分）- 第二重要
        if item.raw_text:
            spec_score = self._match_spec(item.raw_text, sku.spec)
            score += spec_score * 30
            max_possible += 30
        
        # 4. 颜色匹配（20分）- 可选，输入中有颜色才匹配
        if item.color and item.color != '未知':
            color_score = self._match_color(item.color, sku.color)
            score += color_score * 20
            max_possible += 20
        
        # 5. 标题匹配（15分）
        if item.raw_text:
            title_score = fuzz.partial_ratio(item.raw_text.lower(), sku.title.lower()) / 100.0
            score += title_score * 15
            max_possible += 15
        
        # 归一化到100分
        if max_possible > 0:
            normalized_score = int(score / max_possible * 100)
        else:
            normalized_score = 0
        
        return normalized_score
    
    def _match_color(self, extracted_color: str, sku_color: str) -> float:
        """匹配颜色"""
        if extracted_color == sku_color:
            return 1.0
        
        # 检查是否是别名
        extracted_normalized = extracted_color
        sku_normalized = sku_color
        
        # 检查提取的颜色是否在SKU颜色的别名中
        for standard, keywords in self.COLOR_KEYWORDS.items():
            if extracted_color == standard:
                for keyword in keywords:
                    if keyword in sku_color or sku_color in keyword:
                        return 0.9
        
        # 模糊匹配
        return fuzz.ratio(extracted_color, sku_color) / 100.0
    
    def _match_spec(self, raw_text: str, sku_spec: str) -> float:
        """匹配规格"""
        # 提取存储规格（如256G, 512G）
        storage_match = re.search(r'(\d+)[Gg]', raw_text)
        if storage_match:
            extracted_storage = storage_match.group(1) + 'G'
            if extracted_storage in sku_spec:
                return 1.0
        
        # 匹配版本类型
        if '标准' in raw_text and ('标准' in sku_spec or '标准版' in sku_spec):
            return 1.0
        if '全能' in raw_text and ('全能' in sku_spec or '全能版' in sku_spec):
            return 1.0
        if '畅拍' in raw_text and '畅拍' in sku_spec:
            return 1.0
        
        return fuzz.partial_ratio(raw_text, sku_spec) / 100.0
    
    def _match_series(self, raw_text: str, sku_series: str) -> float:
        """匹配系列"""
        # 标准化文本
        text = raw_text.lower().replace(' ', '')
        series = sku_series.lower().replace(' ', '')
        
        # 常见型号映射
        series_mappings = {
            'pk3': 'pocket3',
            'pocket3': 'pocket3',
            'ac4': 'action4',
            'ac5': 'action5',
            'ac6': 'action6',
            'acepro': 'acepro',
            'acepro2': 'acepro2',
            'x5': 'x5',
            'x4': 'x4',
            'x4air': 'x4air',
            'goultra': 'goultra',
            'goult': 'goultra',
        }
        
        # 检查系列映射
        for alias, standard in series_mappings.items():
            if alias in text and standard in series:
                return 1.0
        
        # 模糊匹配
        return fuzz.partial_ratio(text, series) / 100.0
    
    def get_candidates_by_category(self, category: str) -> List[StandardSKU]:
        """按分类获取候选SKU"""
        return self.session.query(StandardSKU).filter(
            StandardSKU.category == category
        ).all()
    
    def get_all_categories(self) -> List[str]:
        """获取所有分类"""
        result = self.session.query(StandardSKU.category).distinct().all()
        return [r[0] for r in result]
    
    def close(self):
        """关闭会话"""
        self.session.close()


if __name__ == '__main__':
    # 测试
    matcher = SKUMatcher()
    
    # 测试文本
    test_texts = [
        "大疆pk3标准2575",
        "影石go ultra黑2180白2180",
        "苹果17 256G 黑色 5799",
        "华为Mate80 12+256G 曜石黑 5048",
    ]
    
    for text in test_texts:
        print(f"\n原文: {text}")
        item = matcher.parse_item(text)
        print(f"价格: {item.price}, 预激活: {item.is_preactivated}, 颜色: {item.color}")
    
    matcher.close()
