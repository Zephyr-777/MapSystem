import sys
import os

# 将当前目录添加到 sys.path 以便导入 'app'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.geo_asset import GeoAsset
from sqlalchemy import func

def inspect_data():
    db = SessionLocal()
    try:
        # 1. 统计总数
        total_count = db.query(func.count(GeoAsset.id)).scalar()
        print(f"--- 数据库统计 ---")
        print(f"总记录数: {total_count}")
        
        # 2. 按分类统计
        stats = db.query(GeoAsset.sub_type, func.count(GeoAsset.id)).group_by(GeoAsset.sub_type).all()
        print(f"\n--- 分类统计 ---")
        for sub_type, count in stats:
            print(f"{sub_type or 'Unknown'}: {count}")
            
        # 3. 查看最近生成的 10 条数据
        print(f"\n--- 最近生成的 10 条记录 ---")
        recent_assets = db.query(GeoAsset).order_by(GeoAsset.id.desc()).limit(10).all()
        
        header = f"{'ID':<5} | {'Name':<30} | {'Type':<6} | {'Center (Lon, Lat)':<25}"
        print(header)
        print("-" * len(header))
        
        for asset in recent_assets:
            center = f"({asset.center_x:.4f}, {asset.center_y:.4f})" if asset.center_x else "N/A"
            print(f"{asset.id:<5} | {asset.name[:30]:<30} | {asset.sub_type:<6} | {center:<25}")
            
    except Exception as e:
        print(f"查询出错: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_data()
