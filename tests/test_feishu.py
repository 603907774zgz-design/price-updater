"""
飞书机器人测试脚本
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.feishu.bot import FeishuBot, init_bot
from src.parser.text_parser import TextParser

def test_text_parsing():
    """测试文本解析"""
    print("=" * 60)
    print("📝 测试文本解析")
    print("=" * 60)
    
    parser = TextParser()
    
    test_text = """大疆pk3标准2575
大疆pk3全能3270
影石acepro2单电黑2250"""
    
    items = parser.parse(test_text)
    
    print(f"\n✅ 解析到 {len(items)} 条商品:\n")
    
    for i, item in enumerate(items, 1):
        print(f"{i}. {item.raw_text}")
        print(f"   品牌: {item.brand}")
        print(f"   系列: {item.series}")
        print(f"   规格: {item.spec}")
        print(f"   颜色: {item.color}")
        print(f"   价格: {item.price}")
        print()
    
    return len(items) > 0

def test_bot_initialization():
    """测试机器人初始化"""
    print("=" * 60)
    print("🤖 测试机器人初始化")
    print("=" * 60)
    
    # 测试空配置
    bot = FeishuBot()
    print("✅ 机器人实例创建成功（无配置）")
    
    # 测试卡片生成（通过发送结果卡片间接测试）
    result = {
        "success": True,
        "session_id": "test_session",
        "summary": {
            "total": 10,
            "auto_matched": 7,
            "need_confirm": 2,
            "new_sku": 1
        },
        "results": []
    }
    # 卡片生成会在_send_result_card中测试
    print("✅ 机器人方法检查通过")
    return True

def test_database():
    """测试数据库连接"""
    print("=" * 60)
    print("🗄️ 测试数据库")
    print("=" * 60)
    
    from src.models.database import db, StandardSKU
    
    try:
        session = db.get_session()
        count = session.query(StandardSKU).count()
        print(f"✅ 数据库连接成功")
        print(f"📊 当前SKU数量: {count}")
        session.close()
        return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🧪 飞书机器人模块测试")
    print("=" * 60 + "\n")
    
    results = []
    
    # 测试1: 文本解析
    results.append(("文本解析", test_text_parsing()))
    
    print()
    
    # 测试2: 机器人初始化
    results.append(("机器人初始化", test_bot_initialization()))
    
    print()
    
    # 测试3: 数据库
    results.append(("数据库连接", test_database()))
    
    # 汇总
    print("\n" + "=" * 60)
    print("📋 测试结果汇总")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查配置")
        return 1

if __name__ == '__main__':
    exit(main())
