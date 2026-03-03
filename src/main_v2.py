"""
带提醒功能的主入口 - FastAPI服务
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
from src.feishu.bot_v2 import feishu_router, FeishuBot

app = FastAPI(title="价格智能更新系统", version="2.0.0")

# 注册飞书机器人路由
app.include_router(feishu_router)

# 全局处理器
ocr_processor = OCRProcessor()
text_parser = TextParser()
excel_handler = ExcelHandler()
sku_manager = LocalSKUManager()


@app.get("/")
def root():
    return {"message": "价格智能更新系统 API (带提醒功能)", "version": "2.0.0"}


@app.post("/api/price/update/image")
async def update_price_from_image(
    images: List[UploadFile] = File(...),
    user_id: str = Form("anonymous")
):
    """
    从图片更新价格
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
        
        # 4. 匹配并更新
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
    从文本更新价格
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
    处理解析后的商品项 - 带提醒功能
    """
    session = db.get_session()
    matcher = SKUMatcher()
    
    try:
        # 创建更新批次
        batch_id = str(uuid.uuid4())[:8]
        
        auto_updated = []        # 自动更新
        need_confirm_keep = []   # 需要确认保留原价格（标准表有，新信息无）
        price_empty_remind = []  # 标准表空价格提醒（标准表空，新信息有）
        new_skus = []            # 新SKU
        
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
                old_price = matched_sku.price
                new_price = item.price
                
                # 判断处理逻辑
                if old_price is not None and new_price is None:
                    # 情况1: 标准表有价格，新信息没价格 → 保留标准表价格，提醒确认
                    need_confirm_keep.append({
                        'type': 'KEEP_STANDARD_PRICE',
                        'sku_code': matched_sku.sku_code,
                        'category': matched_sku.category,
                        'series': matched_sku.series,
                        'title': matched_sku.title,
                        'spec': matched_sku.spec,
                        'color': matched_sku.color,
                        'standard_price': old_price,
                        'new_price': None,
                        'suggestion': '供应商报价中无此SKU价格，建议保留标准表当前价格',
                        'raw_text': item.raw_text,
                        'match_score': score
                    })
                    
                elif old_price is None and new_price is not None:
                    # 情况2: 标准表没价格，新信息有价格 → 提醒确认是否填充
                    price_empty_remind.append({
                        'type': 'FILL_EMPTY_PRICE',
                        'sku_code': matched_sku.sku_code,
                        'category': matched_sku.category,
                        'series': matched_sku.series,
                        'title': matched_sku.title,
                        'spec': matched_sku.spec,
                        'color': matched_sku.color,
                        'standard_price': None,
                        'new_price': new_price,
                        'suggestion': '标准表中此SKU价格为空，供应商报价有价格，建议填充',
                        'raw_text': item.raw_text,
                        'match_score': score
                    })
                    
                elif new_price is not None:
                    # 情况3: 双方都有价格 → 自动更新
                    history = PriceHistory(
                        sku_code=matched_sku.sku_code,
                        old_price=old_price,
                        new_price=new_price,
                        source_type='AUTO_UPDATE',
                        source_content=item.raw_text,
                        updated_by=user_id,
                        batch_id=batch_id
                    )
                    session.add(history)
                    
                    matched_sku.price = new_price
                    
                    auto_updated.append({
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
                # 未匹配的SKU（新SKU）
                new_skus.append({
                    'type': 'NEW_SKU',
                    'raw_text': item.raw_text,
                    'brand': item.brand,
                    'series': item.series,
                    'spec': item.spec,
                    'color': item.color,
                    'price': item.price,
                    'suggestion': '标准表中不存在此SKU，请确认是否需要添加到标准表'
                })
        
        session.commit()
        
        return {
            "success": True,
            "batch_id": batch_id,
            "summary": {
                "total_input": len(parsed_items),
                "auto_updated": len(auto_updated),
                "need_confirm_keep": len(need_confirm_keep),
                "price_empty_remind": len(price_empty_remind),
                "new_sku": len(new_skus)
            },
            "auto_updated": auto_updated,
            "need_confirm_keep": need_confirm_keep,
            "price_empty_remind": price_empty_remind,
            "new_skus": new_skus
        }
        
    finally:
        matcher.close()
        session.close()


@app.post("/api/price/confirm")
async def confirm_price_updates(
    batch_id: str = Form(...),
    confirm_keep: str = Form("[]"),      # JSON数组，确认保留原价格的SKU
    confirm_fill: str = Form("[]"),      # JSON数组，确认填充空价格的SKU
    confirm_add_sku: str = Form("[]")    # JSON数组，确认添加的新SKU
):
    """
    确认价格更新
    """
    session = db.get_session()
    
    try:
        confirm_keep_list = json.loads(confirm_keep)
        confirm_fill_list = json.loads(confirm_fill)
        confirm_add_sku_list = json.loads(confirm_add_sku)
        
        updated_count = 0
        
        # 处理保留原价格确认（实际不需要更新，只是记录）
        for item in confirm_keep_list:
            sku_code = item.get('sku_code')
            # 记录日志
            print(f"确认保留价格: {sku_code}")
        
        # 处理填充空价格
        for item in confirm_fill_list:
            sku_code = item.get('sku_code')
            new_price = item.get('new_price')
            
            sku = session.query(StandardSKU).filter_by(sku_code=sku_code).first()
            if sku:
                history = PriceHistory(
                    sku_code=sku_code,
                    old_price=sku.price,
                    new_price=new_price,
                    source_type='CONFIRM_FILL',
                    source_content='确认填充空价格'
                )
                session.add(history)
                sku.price = new_price
                updated_count += 1
        
        # 处理添加新SKU（简化版，实际应该调用添加SKU接口）
        for item in confirm_add_sku_list:
            print(f"需要添加新SKU: {item}")
        
        session.commit()
        
        return {
            "success": True,
            "updated_count": updated_count,
            "message": f"已确认更新 {updated_count} 条SKU价格"
        }
        
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.post("/api/sku/import/csv")
async def import_skus_from_csv(file: UploadFile = File(...)):
    """
    从CSV导入标准SKU
    """
    try:
        temp_path = f"/tmp/{uuid.uuid4()}.csv"
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        result = sku_manager.import_from_csv(temp_path)
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


@app.get("/api/price/export")
async def export_current_prices():
    """
    导出当前价格表
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
    
    os.makedirs("data", exist_ok=True)
    init_db()
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
