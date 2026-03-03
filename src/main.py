"""
主程序入口
集成飞书机器人
"""
import os
import sys
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Optional
import uvicorn
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.models.database import init_db, db
from src.feishu.bot import feishu_router, init_bot
from src.parser.text_parser import TextParser
from src.matcher.sku_matcher import SKUMatcher, ExtractedItem
from src.utils.excel_handler import ExcelHandler
import uuid
import json

# 创建FastAPI应用
app = FastAPI(
    title="价格智能更新系统",
    description="基于OCR和NLP的价格自动识别与更新",
    version="1.0.0"
)

# 注册路由
app.include_router(feishu_router)

# 全局处理器
text_parser = TextParser()
excel_handler = ExcelHandler()


@app.on_event("startup")
async def startup_event():
    """启动时初始化"""
    # 初始化数据库
    os.makedirs("data", exist_ok=True)
    init_db()
    
    # 初始化飞书机器人
    app_id = os.getenv("FEISHU_APP_ID", "")
    app_secret = os.getenv("FEISHU_APP_SECRET", "")
    encrypt_key = os.getenv("FEISHU_ENCRYPT_KEY", "")
    
    if app_id and app_secret:
        init_bot(app_id, app_secret, encrypt_key)
        print(f"✅ 飞书机器人已初始化 (App ID: {app_id[:8]}...)")
    else:
        print("⚠️ 飞书机器人未配置 (缺少FEISHU_APP_ID或FEISHU_APP_SECRET)")


@app.get("/")
def root():
    """根路径"""
    return {
        "message": "价格智能更新系统 API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "ok"}


@app.post("/api/price/update/text")
async def update_price_from_text(
    text: str = Form(...),
    user_id: str = Form("anonymous")
):
    """
    从文本更新价格（API方式）
    """
    try:
        # 解析文本
        parsed_items = text_parser.parse(text)
        
        if not parsed_items:
            return {
                "success": False,
                "message": "未识别到有效的价格信息"
            }
        
        # 匹配SKU
        result = await _process_parsed_items(parsed_items, user_id, text)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _process_parsed_items(parsed_items: List, user_id: str, source_content: str):
    """匹配SKU并保存"""
    session = db.get_session()
    matcher = SKUMatcher()
    
    try:
        # 创建更新会话
        session_id = str(uuid.uuid4())
        from src.models.database import UpdateSession, PendingUpdate, PriceHistory
        
        update_session = UpdateSession(
            session_id=session_id,
            user_id=user_id,
            total_items=len(parsed_items)
        )
        session.add(update_session)
        
        # 处理每个商品项
        auto_matched = 0
        need_confirm = 0
        new_sku_count = 0
        
        results = []
        
        for item in parsed_items:
            # 获取候选SKU
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
            extracted.match_score = score
            
            if matched_sku:
                extracted.matched_sku = matched_sku
                
                if score >= 90:
                    extracted.match_status = 'MATCHED'
                    auto_matched += 1
                    
                    # 自动确认，直接更新价格
                    if item.price:
                        history = PriceHistory(
                            sku_code=matched_sku.sku_code,
                            old_price=matched_sku.price,
                            new_price=item.price,
                            source_type='API',
                            source_content=item.raw_text,
                            updated_by=user_id
                        )
                        session.add(history)
                        matched_sku.price = item.price
                        
                elif score >= 75:
                    extracted.match_status = 'NEED_CONFIRM'
                    need_confirm += 1
                else:
                    extracted.match_status = 'LOW_CONFIDENCE'
                    need_confirm += 1
            else:
                extracted.match_status = 'NO_MATCH'
                new_sku_count += 1
            
            # 保存到待审核表
            pending = PendingUpdate(
                session_id=session_id,
                sku_code=matched_sku.sku_code if matched_sku else None,
                raw_text=item.raw_text,
                extracted_brand=item.brand,
                extracted_series=item.series,
                extracted_spec=item.spec,
                extracted_color=item.color,
                extracted_price=item.price,
                is_preactivated=item.is_preactivated,
                match_score=score,
                match_status='PENDING' if extracted.match_status in ['NEED_CONFIRM', 'LOW_CONFIDENCE', 'NO_MATCH'] else 'CONFIRMED',
                matched_sku_code=matched_sku.sku_code if matched_sku else None
            )
            session.add(pending)
            
            results.append({
                'raw_text': item.raw_text,
                'price': item.price,
                'matched_sku': matched_sku.sku_code if matched_sku else None,
                'match_score': score,
                'status': extracted.match_status
            })
        
        # 更新会话统计
        update_session.auto_matched = auto_matched
        update_session.need_confirm = need_confirm
        update_session.new_sku_count = new_sku_count
        
        session.commit()
        
        return {
            "success": True,
            "session_id": session_id,
            "summary": {
                "total": len(parsed_items),
                "auto_matched": auto_matched,
                "need_confirm": need_confirm,
                "new_sku": new_sku_count
            },
            "results": results
        }
        
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        matcher.close()
        session.close()


@app.get("/api/price/export/{session_id}")
async def export_result(session_id: str):
    """导出更新结果Excel"""
    try:
        file_path = excel_handler.generate_update_excel(session_id)
        
        return FileResponse(
            file_path,
            filename=f"price_update_{session_id}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sku/search")
async def search_sku(keyword: str, category: Optional[str] = None):
    """搜索SKU"""
    session = db.get_session()
    
    try:
        from src.models.database import StandardSKU
        from sqlalchemy import or_
        
        query = session.query(StandardSKU)
        
        if category:
            query = query.filter(StandardSKU.category == category)
        
        query = query.filter(
            or_(
                StandardSKU.sku_code.contains(keyword),
                StandardSKU.series.contains(keyword),
                StandardSKU.title.contains(keyword),
                StandardSKU.spec.contains(keyword),
                StandardSKU.color.contains(keyword)
            )
        )
        
        results = query.limit(20).all()
        
        return {
            "success": True,
            "data": [sku.to_dict() for sku in results]
        }
        
    finally:
        session.close()


@app.get("/api/sku/list")
async def list_skus(category: Optional[str] = None, limit: int = 100, offset: int = 0):
    """列出SKU"""
    session = db.get_session()
    
    try:
        from src.models.database import StandardSKU
        
        query = session.query(StandardSKU)
        
        if category:
            query = query.filter(StandardSKU.category == category)
        
        total = query.count()
        results = query.limit(limit).offset(offset).all()
        
        return {
            "success": True,
            "total": total,
            "data": [sku.to_dict() for sku in results]
        }
        
    finally:
        session.close()


if __name__ == "__main__":
    # 启动服务
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"🚀 启动价格更新系统...")
    print(f"📡 服务地址: http://{host}:{port}")
    print(f"📚 API文档: http://{host}:{port}/docs")
    
    # 如果默认端口被占用，尝试其他端口
    import socket
    for try_port in [port, 8000, 8001, 8002]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('0.0.0.0', try_port))
            sock.close()
            if result != 0:  # 端口可用
                port = try_port
                break
        except:
            pass
    
    print(f"🚀 最终使用端口: {port}")
    uvicorn.run(app, host=host, port=port)
