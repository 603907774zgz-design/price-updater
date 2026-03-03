"""
OCR识别模块
基于PaddleOCR实现
"""
import os
from typing import List, Tuple, Optional
from PIL import Image
import io

try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False
    print("警告: PaddleOCR未安装，将使用模拟OCR")


class OCREngine:
    """OCR引擎"""
    
    def __init__(self, use_gpu: bool = False, lang: str = 'ch'):
        self.use_gpu = use_gpu
        self.lang = lang
        self.ocr = None
        
        if PADDLE_AVAILABLE:
            self._init_engine()
    
    def _init_engine(self):
        """初始化OCR引擎"""
        try:
            self.ocr = PaddleOCR(
                use_angle_cls=True,
                lang=self.lang,
                use_gpu=self.use_gpu,
                show_log=False
            )
        except Exception as e:
            print(f"OCR引擎初始化失败: {e}")
            self.ocr = None
    
    def recognize(self, image_path: str) -> List[Tuple[str, float]]:
        """
        识别图片中的文字
        
        Args:
            image_path: 图片路径
            
        Returns:
            [(text, confidence), ...]
        """
        if not self.ocr:
            return self._mock_recognize(image_path)
        
        try:
            result = self.ocr.ocr(image_path, cls=True)
            
            texts = []
            if result and result[0]:
                for line in result[0]:
                    if line:
                        text = line[1][0]  # 文字内容
                        confidence = line[1][1]  # 置信度
                        texts.append((text, confidence))
            
            return texts
        except Exception as e:
            print(f"OCR识别失败: {e}")
            return []
    
    def recognize_bytes(self, image_bytes: bytes) -> List[Tuple[str, float]]:
        """
        从字节流识别图片
        
        Args:
            image_bytes: 图片字节
            
        Returns:
            [(text, confidence), ...]
        """
        # 保存临时文件
        temp_path = '/tmp/temp_ocr_image.png'
        try:
            with open(temp_path, 'wb') as f:
                f.write(image_bytes)
            return self.recognize(temp_path)
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def recognize_lines(self, image_path: str) -> str:
        """
        识别图片并按行返回文本
        
        Args:
            image_path: 图片路径
            
        Returns:
            按行分隔的文本
        """
        texts = self.recognize(image_path)
        
        # 按Y坐标排序，保持行顺序
        # PaddleOCR结果已经是按行排序的
        lines = [text for text, _ in texts]
        
        return '\n'.join(lines)
    
    def _mock_recognize(self, image_path: str) -> List[Tuple[str, float]]:
        """模拟OCR（用于测试）"""
        print(f"[模拟OCR] 图片: {image_path}")
        return [
            ("2月26 行情参考", 0.98),
            ("大疆pk3标准2575", 0.95),
            ("大疆pk3全能3270", 0.95),
            ("大疆ac4标准1290", 0.94),
            ("大疆ac5标准1900", 0.94),
            ("影石go ultra黑2180白2180", 0.92),
        ]


class OCRProcessor:
    """OCR处理器 - 处理多张图片并合并结果"""
    
    def __init__(self):
        self.engine = OCREngine()
    
    def process_multiple(self, image_paths: List[str]) -> str:
        """
        处理多张图片，合并识别结果
        
        Args:
            image_paths: 图片路径列表
            
        Returns:
            合并后的文本
        """
        all_lines = []
        
        for path in image_paths:
            text = self.engine.recognize_lines(path)
            if text:
                all_lines.append(text)
        
        return '\n'.join(all_lines)
    
    def process_bytes_list(self, image_bytes_list: List[bytes]) -> str:
        """
        处理多张图片字节流
        
        Args:
            image_bytes_list: 图片字节列表
            
        Returns:
            合并后的文本
        """
        all_lines = []
        
        for i, image_bytes in enumerate(image_bytes_list):
            texts = self.engine.recognize_bytes(image_bytes)
            lines = [text for text, _ in texts]
            all_lines.extend(lines)
        
        return '\n'.join(lines)


if __name__ == '__main__':
    # 测试
    processor = OCRProcessor()
    
    # 测试识别
    test_text = """2月26 行情参考
大疆pk3标准2575
大疆pk3全能3270
大疆ac4标准1290
大疆ac5标准1900
影石go ultra黑2180白2180
影石acepro一代1460
影石acepro2单电黑2250"""
    
    print("OCR测试")
    print("=" * 50)
    print(test_text)
