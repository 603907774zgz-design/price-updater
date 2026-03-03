"""
文本解析模块
解析OCR识别出的文本，提取商品和价格信息
"""
import re
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class ParsedItem:
    """解析后的商品项"""
    raw_text: str           # 原始文本
    brand: Optional[str]    # 品牌
    series: Optional[str]   # 系列
    spec: Optional[str]     # 规格
    color: Optional[str]    # 颜色
    price: Optional[int]    # 价格
    is_preactivated: bool   # 是否预激活
    source_line: int        # 来源行号


class TextParser:
    """文本解析器"""
    
    # 品牌关键词
    BRAND_KEYWORDS = {
        '苹果': ['苹果', 'iphone', 'iPhone', 'Apple'],
        '华为': ['华为', 'huawei', 'Huawei'],
        '小米': ['小米', 'xiaomi', 'Xiaomi', '红米', 'redmi', 'Redmi'],
        '大疆/影石': ['大疆', 'dji', 'DJI', '影石', 'insta360', 'Insta360'],
        'OPPO': ['oppo', 'OPPO'],
        'vivo': ['vivo', 'VIVO', 'Vivo'],
        '荣耀': ['荣耀', 'honor', 'Honor'],
        '一加': ['一加', 'oneplus', 'OnePlus'],
        '真我': ['真我', 'realme', 'Realme'],
        'IQOO': ['iqoo', 'IQOO', 'iQOO'],
    }
    
    # 系列关键词映射
    SERIES_PATTERNS = [
        # 大疆/影石
        (r'pk3|pocket3|pocket\s*3', 'Osmo Pocket3'),
        (r'ac4|action4|action\s*4', 'Osmo Action 4'),
        (r'ac5|action5|action\s*5', 'Osmo Action 5 Pro'),
        (r'ac6|action6|action\s*6', 'Osmo Action 6'),
        (r'acepro2|ace\s*pro\s*2', 'Insta360 AcePro2'),
        (r'acepro|ace\s*pro', 'Insta360 AcePro'),
        (r'x5', 'Insta360 X5'),
        (r'x4\s*air|x4air', 'Insta360 X4 Air'),
        (r'x4', 'Insta360 X4'),
        (r'x3', 'Insta360 X3'),
        (r'go\s*ultra|goultra', 'Insta360 GO ultra'),
        (r'go\s*3s|go3s', 'Insta360 GO 3S'),
        
        # 苹果
        (r'iphone\s*17\s*pro\s*max|苹果17\s*promax', 'iPhone 17 ProMax'),
        (r'iphone\s*17\s*pro|苹果17\s*pro', 'iPhone 17Pro'),
        (r'iphone\s*17|苹果17', 'iPhone 17'),
        (r'iphone\s*16\s*pro\s*max|苹果16\s*promax', 'iPhone 16 ProMax'),
        (r'iphone\s*16\s*pro|苹果16\s*pro', 'iPhone 16 Pro'),
        (r'iphone\s*16|苹果16', 'iPhone 16'),
        (r'iphone\s*15|苹果15', 'iPhone 15'),
        (r'iphone\s*14|苹果14', 'iPhone 14'),
        (r'ipad\s*pro', 'iPad Pro'),
        (r'ipad\s*air', 'iPad Air'),
        (r'ipad\s*mini', 'iPad mini'),
        (r'ipad', 'iPad'),
        
        # 华为
        (r'mate\s*80\s*pro\s*max|mate80\s*promax', 'Mate 80 Pro Max'),
        (r'mate\s*80\s*pro|mate80\s*pro', 'Mate 80 Pro'),
        (r'mate\s*80|mate80', 'Mate 80'),
        (r'mate\s*70\s*pro\+', 'Mate 70 Pro+'),
        (r'mate\s*70\s*pro|mate70\s*pro', 'Mate 70 Pro'),
        (r'mate\s*70|mate70', 'Mate 70'),
        (r'mate\s*x7', 'Mate X7'),
        (r'mate\s*x6', 'Mate X6'),
        (r'pura\s*80', 'Pura 80'),
        (r'pura\s*x', 'Pura X'),
        (r'nova\s*15', 'Nova 15'),
        (r'nova\s*14', 'Nova 14'),
        (r'nova\s*13', 'Nova 13'),
        
        # 小米
        (r'小米\s*17|xiaomi\s*17', '小米17'),
        (r'小米\s*15|xiaomi\s*15', '小米15'),
        (r'小米\s*14|xiaomi\s*14', '小米14'),
        (r'红米\s*k90|redmi\s*k90', '红米 K90'),
        (r'红米\s*k80|redmi\s*k80', '红米 K80'),
        (r'红米\s*turbo\s*5|redmi\s*turbo\s*5', '红米 Turbo 5'),
        (r'红米\s*note\s*15|redmi\s*note\s*15', '红米 Note15'),
        
        # OPPO
        (r'find\s*x9\s*pro|findx9pro', 'Find X9 Pro'),
        (r'find\s*x9|findx9', 'Find X9'),
        (r'find\s*x8', 'Find X8'),
        (r'reno\s*15\s*pro|reno15pro', 'Reno 15 Pro'),
        (r'reno\s*15|reno15', 'Reno 15'),
        (r'a6\s*pro|a6pro', 'A6 Pro'),
        (r'a6', 'A6'),
        
        # vivo
        (r'x300\s*pro|x300pro', 'X300 Pro'),
        (r'x300', 'X300'),
        (r'x200\s*pro|x200pro', 'X200 Pro'),
        (r'x200', 'X200'),
        (r's50\s*pro|s50pro', 'S50 Pro'),
        (r's50', 'S50'),
        (r'y500', 'Y500'),
        (r'y300', 'Y300'),
        
        # 荣耀
        (r'magic\s*8\s*pro|magic8pro', 'Magic8 Pro'),
        (r'magic\s*8|magic8', 'Magic8'),
        (r'magic\s*7\s*pro|magic7pro', 'Magic7 Pro'),
        (r'magic\s*7|magic7', 'Magic7'),
        (r'荣耀\s*500|honor\s*500', '荣耀500'),
        (r'荣耀\s*400|honor\s*400', '荣耀400'),
        (r'荣耀\s*gt|honor\s*gt', '荣耀 GT'),
        
        # 一加
        (r'一加\s*15|oneplus\s*15', '一加15'),
        (r'一加\s*13|oneplus\s*13', '一加13'),
        (r'ace\s*6|ace6', 'Ace 6'),
        (r'ace\s*5|ace5', 'Ace 5'),
        
        # 真我
        (r'gt\s*8\s*pro|gt8pro', 'GT8 Pro'),
        (r'gt\s*8|gt8', 'GT8'),
        (r'gt\s*7\s*pro|gt7pro', 'GT7 Pro'),
        (r'gt\s*7|gt7', 'GT7'),
        (r'neo\s*8|neo8', 'Neo8'),
        (r'neo\s*7|neo7', 'Neo7'),
        
        # IQOO
        (r'iqoo\s*15|iqoo15', 'iQOO15'),
        (r'iqoo\s*neo\s*11|iqooneo11', 'iQOO Neo11'),
        (r'z11\s*turbo|z11turbo', 'Z11 Turbo'),
        (r'z10\s*turbo|z10turbo', 'Z10 Turbo'),
    ]
    
    # 规格模式
    SPEC_PATTERNS = [
        (r'(\d+)[Gg]', '存储'),  # 256G, 512G
        (r'标准版?|标准套装', '标准版'),
        (r'全能版?|全能套装', '全能版'),
        (r'畅拍版?|畅拍套装', '畅拍套装'),
        (r'单电|单电池|单电版', '单电池'),
        (r'双电|双电池|双电版', '双电池'),
        (r'预激活|预激活版', '预激活'),
    ]
    
    # 颜色模式
    COLOR_PATTERNS = [
        (r'极夜黑|曜石黑|星耀黑|曜金黑|幻夜黑|静夜黑|深空黑|绒黑色|石墨黑|岩墨灰', '黑色'),
        (r'冰川白|灵动白|雪域白|云白色|零度白|月光白|月影白|晨雾白|玉龙雪', '白色'),
        (r'海岛蓝|天海青|天青色|天青釉|苍空蓝|冰川蓝|湖光青|星海蓝|晴空蓝|绣球蓝', '蓝色'),
        (r'晨曦金|香槟金|极昼金|沙漠金|蜜糖金', '金色'),
        (r'钛空银|原色|金属原色|星际银|冰霜银', '银色'),
        (r'罗兰紫|羽纱紫|鸢尾紫|槿紫', '紫色'),
        (r'云杉绿|向新绿|竹韵青|湖水青|松石绿|青松|苍岭绿|海湖青', '绿色'),
        (r'樱花粉|淡桃粉|珊瑚粉|星光粉|樱语粉|莹彩粉', '粉色'),
        (r'深空灰|烟云灰|苍山灰|星际灰|钛灰色|星空灰', '灰色'),
        (r'朱砂红|珊瑚红|玫红|中国红', '红色'),
        (r'燃橙色|珊瑚橙|赤茶橘', '橙色'),
    ]
    
    def __init__(self):
        # 编译正则表达式
        self.series_regex = [(re.compile(p, re.IGNORECASE), s) for p, s in self.SERIES_PATTERNS]
        self.spec_regex = [(re.compile(p, re.IGNORECASE), s) for p, s in self.SPEC_PATTERNS]
        self.color_regex = [(re.compile(p, re.IGNORECASE), s) for p, s in self.COLOR_PATTERNS]
    
    def parse(self, text: str) -> List[ParsedItem]:
        """
        解析文本，提取所有商品项
        
        Args:
            text: 输入文本（多行）
            
        Returns:
            ParsedItem列表
        """
        items = []
        lines = text.strip().split('\n')
        
        for line_no, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            # 跳过纯日期/标题行
            if self._is_header_line(line):
                continue
            
            # 解析单行
            item = self._parse_line(line, line_no)
            if item and item.price:
                items.append(item)
        
        # 处理多颜色条目
        items = self._split_multi_color(items)
        
        return items
    
    def _is_header_line(self, line: str) -> bool:
        """判断是否为标题行（非商品行）"""
        # 纯日期
        if re.match(r'^\d{1,2}月\d{1,2}', line):
            return True
        # 纯文字无数字
        if not re.search(r'\d', line):
            return True
        # 行情参考等标题
        if '行情' in line or '参考' in line or '价格' in line:
            if len(line) < 10:
                return True
        return False
    
    def _parse_line(self, line: str, line_no: int) -> Optional[ParsedItem]:
        """解析单行文本"""
        item = ParsedItem(
            raw_text=line,
            brand=None,
            series=None,
            spec=None,
            color=None,
            price=None,
            is_preactivated=False,
            source_line=line_no
        )
        
        # 提取价格
        item.price = self._extract_price(line)
        
        # 检测预激活
        item.is_preactivated = '预激活' in line
        
        # 提取品牌
        item.brand = self._extract_brand(line)
        
        # 提取系列
        item.series = self._extract_series(line)
        
        # 提取规格
        item.spec = self._extract_spec(line)
        
        # 提取颜色
        item.color = self._extract_color(line)
        
        return item
    
    def _extract_price(self, text: str) -> Optional[int]:
        """提取价格"""
        # 匹配3-5位数字（不使用\b单词边界，因为对中文支持不好）
        matches = re.findall(r'(?:^|\D)(\d{3,5})(?:$|\D)', text)
        if matches:
            prices = [int(m) for m in matches]
            # 过滤合理范围
            valid_prices = [p for p in prices if 500 <= p <= 50000]
            if valid_prices:
                return max(valid_prices)
        return None
    
    def _extract_brand(self, text: str) -> Optional[str]:
        """提取品牌"""
        text = text.lower()
        for brand, keywords in self.BRAND_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in text:
                    return brand
        return None
    
    def _extract_series(self, text: str) -> Optional[str]:
        """提取系列"""
        for pattern, series in self.series_regex:
            if pattern.search(text):
                return series
        return None
    
    def _extract_spec(self, text: str) -> Optional[str]:
        """提取规格"""
        specs = []
        
        # 提取存储
        storage_match = re.search(r'(\d+)[Gg]', text)
        if storage_match:
            specs.append(f"{storage_match.group(1)}G")
        
        # 提取版本
        for pattern, spec_name in self.spec_regex:
            if pattern.search(text):
                if spec_name not in ['存储', '预激活']:
                    specs.append(spec_name)
        
        return ' '.join(specs) if specs else None
    
    def _extract_color(self, text: str) -> Optional[str]:
        """提取颜色"""
        for pattern, color_name in self.color_regex:
            if pattern.search(text):
                return color_name
        
        # 简单匹配单字颜色
        simple_colors = {
            '黑': '黑色',
            '白': '白色',
            '蓝': '蓝色',
            '金': '金色',
            '银': '银色',
            '紫': '紫色',
            '绿': '绿色',
            '粉': '粉色',
            '灰': '灰色',
            '红': '红色',
            '橙': '橙色',
            '黄': '黄色',
        }
        
        for char, color in simple_colors.items():
            if char in text:
                return color
        
        return None
    
    def _split_multi_color(self, items: List[ParsedItem]) -> List[ParsedItem]:
        """拆分多颜色条目"""
        result = []
        
        for item in items:
            text = item.raw_text
            
            # 检测多个颜色+价格组合
            color_price_matches = re.findall(r'(黑|白|蓝|金|银|紫|绿|粉|灰|红|橙|黄)(\d{3,5})', text)
            
            if len(color_price_matches) >= 2:
                # 拆分多个颜色
                for color_keyword, price in color_price_matches:
                    new_item = ParsedItem(
                        raw_text=f"{text[:text.find(color_keyword)]}{color_keyword}{price}",
                        brand=item.brand,
                        series=item.series,
                        spec=item.spec,
                        color=self._keyword_to_color(color_keyword),
                        price=int(price),
                        is_preactivated=item.is_preactivated,
                        source_line=item.source_line
                    )
                    result.append(new_item)
            else:
                result.append(item)
        
        return result
    
    def _keyword_to_color(self, keyword: str) -> str:
        """颜色关键字转标准颜色"""
        mapping = {
            '黑': '黑色',
            '白': '白色',
            '蓝': '蓝色',
            '金': '金色',
            '银': '银色',
            '紫': '紫色',
            '绿': '绿色',
            '粉': '粉色',
            '灰': '灰色',
            '红': '红色',
            '橙': '橙色',
            '黄': '黄色',
        }
        return mapping.get(keyword, '未知')


if __name__ == '__main__':
    # 测试
    parser = TextParser()
    
    test_text = """2月26 行情参考
大疆pk3标准2575
大疆pk3全能3270
大疆ac4标准1290
大疆ac5标准1900
大疆ac5畅拍2460
影石go ultra黑2180白2180
影石acepro一代1460
影石acepro2单电黑2250
苹果17 256G 黑色 5751
华为Mate80 12+256G 曜石黑 5048"""
    
    print("文本解析测试")
    print("=" * 60)
    
    items = parser.parse(test_text)
    
    print(f"\n共解析到 {len(items)} 条商品:\n")
    
    for i, item in enumerate(items, 1):
        print(f"{i}. 原文: {item.raw_text}")
        print(f"   品牌: {item.brand}, 系列: {item.series}")
        print(f"   规格: {item.spec}, 颜色: {item.color}")
        print(f"   价格: {item.price}, 预激活: {item.is_preactivated}")
        print()
