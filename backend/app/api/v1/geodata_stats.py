
from sqlalchemy import func
from datetime import datetime, timedelta

@router.get("/stats")
async def get_geodata_stats(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """获取数据统计信息"""
    # 1. 矢量 vs 栅格 比例
    # 假设 file_type '矢量' 或 sub_type 包含 '矢量'
    # 假设 file_type '栅格' 或 sub_type 包含 '影像'
    
    # 简单起见，按 file_type 分组
    type_counts = db.query(
        GeoAsset.file_type, 
        func.count(GeoAsset.id)
    ).filter(
        GeoAsset.is_sidecar == False
    ).group_by(GeoAsset.file_type).all()
    
    # 格式化为 ECharts pie data
    pie_data = [{"name": t[0] or "未知", "value": t[1]} for t in type_counts]
    
    # 2. 最近一周上传数量
    end_date = datetime.now()
    start_date = end_date - timedelta(days=6)
    
    daily_counts = db.query(
        func.date(GeoAsset.updated_at).label('date'),
        func.count(GeoAsset.id)
    ).filter(
        GeoAsset.is_sidecar == False,
        GeoAsset.updated_at >= start_date
    ).group_by(
        func.date(GeoAsset.updated_at)
    ).all()
    
    # 补全日期 (即使某天没有数据也要显示 0)
    date_map = {t[0].strftime("%Y-%m-%d"): t[1] for t in daily_counts if t[0]}
    
    bar_categories = []
    bar_values = []
    
    for i in range(7):
        d = start_date + timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        bar_categories.append(d.strftime("%m-%d"))
        bar_values.append(date_map.get(d_str, 0))
        
    return {
        "pie": pie_data,
        "bar": {
            "categories": bar_categories,
            "values": bar_values
        }
    }
