"""
飞书表格同步模块
从飞书多维表格读取标准SKU数据
"""
import requests
import os
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

class FeishuTableSync:
    """飞书表格同步器"""
    
    def __init__(self, app_token: str = None, table_id: str = None):
        self.app_token = app_token or os.getenv("FEISHU_APP_TOKEN")
        self.table_id = table_id or os.getenv("FEISHU_TABLE_ID")
        self.app_id = os.getenv("FEISHU_APP_ID")
        self.app_secret = os.getenv("FEISHU_APP_SECRET")
        self.base_url = "https://open.feishu.cn/open-apis"
        self.tenant_access_token = None
    
    def get_tenant_access_token(self) -> str:
        """获取tenant_access_token"""
        if self.tenant_access_token:
            return self.tenant_access_token
        
        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        resp = requests.post(url, json=data)
        result = resp.json()
        
        if result.get("code") == 0:
            self.tenant_access_token = result["tenant_access_token"]
            return self.tenant_access_token
        else:
            raise Exception(f"获取token失败: {result}")
    
    def read_table_records(self, view_id: str = None, page_size: int = 500) -> List[Dict]:
        """
        读取表格记录
        
        Returns:
            记录列表，每条记录包含字段值
        """
        token = self.get_tenant_access_token()
        
        all_records = []
        page_token = None
        
        while True:
            url = f"{self.base_url}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            params = {
                "page_size": page_size
            }
            if view_id:
                params["view_id"] = view_id
            if page_token:
                params["page_token"] = page_token
            
            resp = requests.get(url, headers=headers, params=params)
            result = resp.json()
            
            if result.get("code") != 0:
                raise Exception(f"读取表格失败: {result}")
            
            data = result.get("data", {})
            records = data.get("items", [])
            
            for record in records:
                fields = record.get("fields", {})
                record_data = {
                    "record_id": record.get("record_id"),
                    **fields
                }
                all_records.append(record_data)
            
            # 检查是否还有更多数据
            page_token = data.get("page_token")
            has_more = data.get("has_more", False)
            
            if not has_more or not page_token:
                break
        
        return all_records
    
    def sync_to_local_db(self):
        """
        同步飞书表格数据到本地数据库
        """
        from src.models.database import db, StandardSKU
        
        print("🔄 开始从飞书表格同步数据...")
        
        # 读取飞书表格数据
        records = self.read_table_records()
        print(f"📊 从飞书读取到 {len(records)} 条记录")
        
        session = db.get_session()
        
        try:
            count = 0
            updated = 0
            
            for record in records:
                # 解析字段
                sku_code = record.get("sku编码", "")
                if not sku_code:
                    continue
                
                category = record.get("商品分类", "")
                series = record.get("商品系列", "")
                title = record.get("商品标题", "")
                spec = record.get("商品规格", "")
                color = record.get("商品颜色", "")
                
                # 解析价格
                price = None
                price_value = record.get("商品行情价", "")
                if price_value:
                    try:
                        if isinstance(price_value, (int, float)):
                            price = int(price_value)
                        elif isinstance(price_value, str):
                            price = int(float(price_value))
                    except:
                        price = None
                
                # 检测预激活
                is_preactivated = "预激活" in title or "预激活" in spec
                
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
                    updated += 1
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
                
                # 每100条提交一次
                if (count + updated) % 100 == 0:
                    session.commit()
                    print(f"  已处理 {count + updated} 条...")
            
            session.commit()
            
            print(f"✅ 同步完成!")
            print(f"  新增: {count} 条")
            print(f"  更新: {updated} 条")
            print(f"  总计: {count + updated} 条")
            
            return count + updated
            
        except Exception as e:
            session.rollback()
            print(f"❌ 同步失败: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            session.close()


if __name__ == '__main__':
    # 测试同步
    sync = FeishuTableSync()
    sync.sync_to_local_db()
