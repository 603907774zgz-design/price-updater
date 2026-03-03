"""
简化版主入口 - FastAPI服务
移除新SKU提醒和空价格提醒，只更新匹配到的SKU
"""
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Optional
import os
import uuid
import json
from datetime import datetime

from src.ocr.paddle_ocr import OCRProcessor
from src.parser.text_parser import TextParser, ParsedItem
from src.matcher.sku_matcher import SKUMatcher, ExtractedItem
from src.models.database import db, StandardSKU, PriceHistory, init_db
from src.utils.excel_handler import ExcelHandler
from src.sync.feishu_sync import LocalSKUManager

app = FastAPI(title="价格智能更新系统 - 简化版", version="1.1.0")

# 全局处理器
ocr_processor = OCRProcessor()
text_parser = TextParser()
excel_handler = ExcelHandler()
sku_manager = LocalSKUManager()


@app.get("/")
def root():
    return {"message": "价格智能更新系统 API (简化版)", "version": "1.1.0"}


@app.post("/api/price/update/image")
async def update_price_from_image(
    images: List[UploadFile] = File(...),
    user_id: str = Form("anonymous")
):
    """
    从图片更新价格 - 简化版
    只更新标准表中已存在的SKU，忽略新SKU
    """
    try:
        # 1. 保存上传的图片
        image_paths = []
        for image in images:
            file_ext = os.path.splitext(image.filename)[1]
            temp_path = f"/tmp/{uuid.uuid4()}{file_ext}"
            with open(temp_path, "wb") as f:
                content = await image.read()
                f.write(content)
            image_paths.append(temp_path)
        
        # 2. OCR识别
        all_text = ""
        for path in image_paths:
            text = ocr_processor.engine.recognize_lines(path)
            all_text += text + "\n"
        
        # 3. 解析文本
        parsed_items = text_parser.parse(all_text)
        
        # 4. 匹配并更新（简化逻辑）
        result = await _process_and_update(parsed_items, user_id, all_text)
        
        # 5. 清理临时文件
        for path in image_paths:
            if os.path.exists(path):
                os.remove(path)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/price/update/text")
async def update_price_from_text(
    text: str = Form(...),
    user_id: str = Form("anonymous")
):
    """
    从文本更新价格 - 简化版
    只更新标准表中已存在的SKU
    """
    try:
        # 1. 解析文本
        parsed_items = text_parser.parse(text)
        
        # 2. 匹配并更新
        result = await _process_and_update(parsed_items, user_id, text)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _process_and_update(parsed_items: List[ParsedItem], user_id: str, source_content: str):
    """
    处理解析后的商品项 - 简化版
    只更新匹配到的SKU，忽略新SKU和空价格
    """
    session = db.get_session()
    matcher = SKUMatcher()
    
    try:
        updated_items = []
        skipped_items = []  # 未匹配的（新SKU或无法识别）
        
        for item in parsed_items:
            # 获取候选SKU（按品牌分类）
            candidates = []
            if item.brand:
                candidates = matcher.get_candidates_by_category(item.brand)
            
            # 创建匹配项
            extracted = ExtractedItem(raw_text=item.raw_text, price=item.price)
            extracted.brand = item.brand
            extracted.series = item.series
            extracted.spec = item.spec
            extracted.color = item.color
            extracted.is_preactivated = item.is_preactivated
            
            # 匹配SKU
            matched_sku, score = matcher.match_sku(extracted, candidates)
            
            if matched_sku and score >= 60:
                # 只更新匹配到的SKU
                old_price = matched_sku.price
                new_price = item.price
                
                # 记录历史（即使价格相同也记录，用于溯源）
                history = PriceHistory(
                    sku_code=matched_sku.sku_code,
                    old_price=old_price,
                    new_price=new_price,
                    source_type='IMAGE_OCR',
                    source_content=item.raw_text,
                    updated_by=user_id
                )
                session.add(history)
                
                # 更新价格
                matched_sku.price = new_price
                
                updated_items.append({
                    'sku_code': matched_sku.sku_code,
                    'category': matched_sku.category,
                    'series': matched_sku.series,
                    'title': matched_sku.title,
                    'spec': matched_sku.spec,
                    'color': matched_sku.color,
                    'old_price': old_price,
                    'new_price': new_price,
                    'change': (new_price or 0) - (old_price or 0),
                    'match_score': score,
                    'raw_text': item.raw_text
                })
            else:
                # 未匹配的SKU（新SKU或无法识别），直接跳过
                skipped_items.append({
                    'raw_text': item.raw_text,
                    'reason': '未匹配到标准SKU'
                })
        
        session.commit()
        
        return {
            "success": True,
            "summary": {
                "total_input": len(parsed_items),
                "updated": len(updated_items),
                "skipped": len(skipped_items)
            },
            "updated_items": updated_items,
            "skipped_items": skipped_items  # 可选返回，方便用户了解哪些被跳过了
        }
        
    finally:
        matcher.close()
        session.close()


@app.post("/api/sku/import/csv")
async def import_skus_from_csv(file: UploadFile = File(...)):
    """
    从CSV导入标准SKU
    用于随时更新标准表
    """
    try:
        # 保存上传的文件
        temp_path = f"/tmp/{uuid.uuid4()}.csv"
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 导入SKU
        result = sku_manager.import_from_csv(temp_path)
        
        # 清理临时文件
        os.remove(temp_path)
        
        if result["success"]:
            return {
                "success": True,
                "message": f"导入成功！新增 {result['added']} 条，更新 {result['updated']} 条"
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sku/export/csv")
async def export_skus_to_csv():
    """
    导出标准SKU到CSV
    """
    try:
        output_path = f"/tmp/standard_skus_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        result = sku_manager.export_to_csv(output_path)
        
        return FileResponse(
            result,
            filename="standard_skus.csv",
            media_type="text/csv"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sku/list")
async def list_skus(
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 50
):
    """
    列出标准SKU
    """
    session = db.get_session()
    
    try:
        query = session.query(StandardSKU)
        
        if category:
            query = query.filter(StandardSKU.category == category)
        
        if keyword:
            query = query.filter(
                db.engine.or_(
                    StandardSKU.sku_code.contains(keyword),
                    StandardSKU.series.contains(keyword),
                    StandardSKU.title.contains(keyword)
                )
            )
        
        total = query.count()
        skus = query.offset((page - 1) * page_size).limit(page_size).all()
        
        return {
            "success": True,
            "total": total,
            "page": page,
            "page_size": page_size,
            "data": [sku.to_dict() for sku in skus]
        }
        
    finally:
        session.close()


@app.post("/api/sku/update/{sku_code}")
async def update_sku_price(
    sku_code: str,
    price: int = Form(...),
    user_id: str = Form("anonymous")
):
    """
    手动更新单个SKU价格
    """
    session = db.get_session()
    
    try:
        sku = session.query(StandardSKU).filter_by(sku_code=sku_code).first()
        
        if not sku:
            raise HTTPException(status_code=404, detail="SKU不存在")
        
        # 记录历史
        history = PriceHistory(
            sku_code=sku_code,
            old_price=sku.price,
            new_price=price,
            source_type='MANUAL',
            source_content=f'手动更新: {user_id}',
            updated_by=user_id
        )
        session.add(history)
        
        # 更新价格
        sku.price = price
        
        session.commit()
        
        return {
            "success": True,
            "message": "价格更新成功",
            "data": sku.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.get("/api/price/export")
async def export_current_prices():
    """
    导出当前价格表（标准表）
    """
    try:
        output_path = excel_handler.generate_standard_excel()
        
        return FileResponse(
            output_path,
            filename=f"price_table_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sku/categories")
async def get_categories():
    """
    获取所有商品分类
    """
    session = db.get_session()
    
    try:
        categories = session.query(StandardSKU.category).distinct().all()
        return {
            "success": True,
            "data": [c[0] for c in categories if c[0]]
        }
    finally:
        session.close()


if __name__ == "__main__":
    import uvicorn
    
    # 确保数据目录存在
    os.makedirs("data", exist_ok=True)
    
    # 初始化数据库
    init_db()
    
    # 启动服务
    uvicorn.run(app, host="0.0.0.0", port=8000)
