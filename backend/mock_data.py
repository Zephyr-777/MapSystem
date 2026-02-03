import sys
import os
import random
from datetime import datetime

# 将当前目录添加到 sys.path 以便导入 'app'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.geo_asset import GeoAsset

def generate_mock_data():
    db = SessionLocal()
    categories = ['TIF', 'SHP', 'MDB']
    
    # 中国经纬度大致范围
    # 经度 (Lon): 73°E - 135°E
    # 纬度 (Lat): 18°N - 54°N
    
    print("开始生成 500 条模拟地质资产数据...")
    
    try:
        for i in range(500):
            lon = random.uniform(73, 135)
            lat = random.uniform(18, 54)
            
            # 随机生成一个小范围的边界框
            size = random.uniform(0.05, 0.2)
            min_x, min_y = lon - size, lat - size
            max_x, max_y = lon + size, lat + size
            
            category = random.choice(categories)
            # 确保名称唯一，加入时间戳或随机数
            timestamp = int(datetime.now().timestamp() * 1000)
            name = f"MOCK_{category}_{i}_{timestamp % 10000}_{random.randint(100, 999)}"
            
            asset = GeoAsset(
                name=name,
                file_path=f"/storage/mock/{name}.{category.lower()}",
                # 根据分类设置主类型
                file_type="栅格" if category == 'TIF' else "矢量",
                sub_type=category,
                srid=4326,
                extent_min_x=min_x,
                extent_min_y=min_y,
                extent_max_x=max_x,
                extent_max_y=max_y,
                center_x=lon,
                center_y=lat,
                is_sidecar=False,
                created_at=datetime.now()
            )
            
            db.add(asset)
            
            if (i + 1) % 100 == 0:
                db.flush()
                print(f"已处理 {i + 1} 条数据...")
        
        db.commit()
        print(f"成功生成 500 条模拟数据。")
        
    except Exception as e:
        print(f"发生错误: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    generate_mock_data()
