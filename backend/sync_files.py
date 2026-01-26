#!/usr/bin/env python3
"""
地质文件同步脚本

功能：
1. 扫描 backend/storage 文件夹下的所有 .tif 文件
2. 解析同名的 .tfw 文件（World File），读取坐标信息和分辨率
3. 计算 extent（空间范围矩形）
4. 将信息存入 MySQL 的 geo_assets 表
5. 如果数据库里已经有了同名文件，则更新元数据
"""

import sys
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models import GeoAsset
from PIL import Image
import os
from dotenv import load_dotenv

load_dotenv()

# 获取 storage 目录路径
STORAGE_DIR = Path(__file__).parent / "storage"


def parse_tfw_file(tfw_path: Path) -> dict:
    """
    解析 .tfw 文件（World File 格式）
    
    .tfw 文件格式（6行）：
    Line 1: pixel width (x方向分辨率)
    Line 2: rotation parameter (通常是0)
    Line 3: rotation parameter (通常是0)
    Line 4: pixel height (y方向分辨率，通常是负值)
    Line 5: x-coordinate of upper-left corner (左上角x坐标)
    Line 6: y-coordinate of upper-left corner (左上角y坐标)
    
    Returns:
        dict: 包含解析结果的字典
    """
    try:
        with open(tfw_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if len(lines) < 6:
            raise ValueError(f".tfw 文件格式错误：需要6行，实际只有{len(lines)}行")
        
        # 解析每行数据
        pixel_width = float(lines[0].strip())
        rotation_a = float(lines[1].strip())
        rotation_b = float(lines[2].strip())
        pixel_height = float(lines[3].strip())  # 通常是负值
        upper_left_x = float(lines[4].strip())
        upper_left_y = float(lines[5].strip())
        
        return {
            'pixel_width': pixel_width,
            'pixel_height': pixel_height,
            'rotation_a': rotation_a,
            'rotation_b': rotation_b,
            'upper_left_x': upper_left_x,
            'upper_left_y': upper_left_y
        }
    except Exception as e:
        raise ValueError(f"解析 .tfw 文件失败: {str(e)}")


def get_image_size(tif_path: Path) -> tuple:
    """
    获取 .tif 图像的宽度和高度
    
    Returns:
        tuple: (width, height)
    """
    try:
        with Image.open(tif_path) as img:
            return img.size  # (width, height)
    except Exception as e:
        raise ValueError(f"读取图像尺寸失败: {str(e)}")


def calculate_extent(tfw_data: dict, width: int, height: int) -> dict:
    """
    根据 .tfw 数据和图像尺寸计算 extent（空间范围矩形）
    
    Args:
        tfw_data: 从 .tfw 文件解析的数据
        width: 图像宽度（像素）
        height: 图像高度（像素）
    
    Returns:
        dict: 包含 extent 的字典 {min_x, min_y, max_x, max_y}
    """
    pixel_width = tfw_data['pixel_width']
    pixel_height = tfw_data['pixel_height']  # 通常是负值
    upper_left_x = tfw_data['upper_left_x']
    upper_left_y = tfw_data['upper_left_y']
    
    # 计算 extent
    # 左上角坐标已经在 tfw_data 中给出
    min_x = upper_left_x
    max_y = upper_left_y
    
    # 右下角坐标
    max_x = upper_left_x + (width * pixel_width)
    min_y = upper_left_y + (height * pixel_height)  # pixel_height 通常是负值，所以这里是减法
    
    return {
        'min_x': min_x,
        'min_y': min_y,
        'max_x': max_x,
        'max_y': max_y
    }


def sync_geo_files(db: Session):
    """
    同步地质文件到数据库
    
    Args:
        db: 数据库会话
    """
    if not STORAGE_DIR.exists():
        print(f"错误：存储目录不存在: {STORAGE_DIR}")
        return
    
    # 扫描所有 .tif 文件
    tif_files = list(STORAGE_DIR.glob("*.tif")) + list(STORAGE_DIR.glob("*.TIF"))
    
    if not tif_files:
        print(f"未找到 .tif 文件在目录: {STORAGE_DIR}")
        return
    
    print(f"找到 {len(tif_files)} 个 .tif 文件")
    
    success_count = 0
    error_count = 0
    update_count = 0
    create_count = 0
    
    for tif_path in tif_files:
        try:
            file_name = tif_path.name
            file_path = str(tif_path)
            
            print(f"\n处理文件: {file_name}")
            
            # 查找对应的 .tfw 文件
            tfw_path = tif_path.with_suffix('.tfw') or tif_path.with_suffix('.TFW')
            
            if not tfw_path.exists():
                # 尝试查找大写的 .TFW
                tfw_path = STORAGE_DIR / f"{tif_path.stem}.TFW"
            
            if not tfw_path.exists():
                print(f"  警告: 未找到对应的 .tfw 文件，跳过 {file_name}")
                # 仍然保存文件信息，但没有 extent
                extent_min_x = extent_min_y = extent_max_x = extent_max_y = None
                width = height = None
                resolution_x = resolution_y = None
            else:
                print(f"  找到 .tfw 文件: {tfw_path.name}")
                
                # 解析 .tfw 文件
                tfw_data = parse_tfw_file(tfw_path)
                
                # 获取图像尺寸
                width, height = get_image_size(tif_path)
                print(f"  图像尺寸: {width} x {height}")
                
                # 计算 extent
                extent = calculate_extent(tfw_data, width, height)
                extent_min_x = extent['min_x']
                extent_min_y = extent['min_y']
                extent_max_x = extent['max_x']
                extent_max_y = extent['max_y']
                
                resolution_x = tfw_data['pixel_width']
                resolution_y = abs(tfw_data['pixel_height'])
                
                print(f"  Extent: [{extent_min_x}, {extent_min_y}, {extent_max_x}, {extent_max_y}]")
                print(f"  分辨率: {resolution_x} x {resolution_y}")
            
            # 检查数据库中是否已存在
            existing_asset = db.query(GeoAsset).filter(GeoAsset.name == file_name).first()
            
            if existing_asset:
                # 更新现有记录
                existing_asset.file_path = file_path
                existing_asset.extent_min_x = extent_min_x
                existing_asset.extent_min_y = extent_min_y
                existing_asset.extent_max_x = extent_max_x
                existing_asset.extent_max_y = extent_max_y
                existing_asset.width = width
                existing_asset.height = height
                existing_asset.resolution_x = resolution_x
                existing_asset.resolution_y = resolution_y
                existing_asset.updated_at = datetime.now()
                
                db.commit()
                update_count += 1
                print(f"  ✓ 更新数据库记录")
            else:
                # 创建新记录
                new_asset = GeoAsset(
                    name=file_name,
                    file_path=file_path,
                    file_type="栅格",
                    extent_min_x=extent_min_x,
                    extent_min_y=extent_min_y,
                    extent_max_x=extent_max_x,
                    extent_max_y=extent_max_y,
                    width=width,
                    height=height,
                    resolution_x=resolution_x,
                    resolution_y=resolution_y
                )
                
                db.add(new_asset)
                db.commit()
                create_count += 1
                print(f"  ✓ 创建新数据库记录")
            
            success_count += 1
            
        except Exception as e:
            error_count += 1
            print(f"  ✗ 处理失败: {str(e)}")
            db.rollback()
    
    print(f"\n同步完成:")
    print(f"  成功: {success_count}")
    print(f"  创建: {create_count}")
    print(f"  更新: {update_count}")
    print(f"  错误: {error_count}")


def main():
    """主函数"""
    print("=" * 60)
    print("地质文件同步脚本")
    print("=" * 60)
    print(f"存储目录: {STORAGE_DIR.resolve()}")
    
    # 确保数据库表存在
    print("\n检查数据库表...")
    Base.metadata.create_all(bind=engine)
    print("✓ 数据库表已就绪")
    
    # 执行同步
    db = SessionLocal()
    try:
        sync_geo_files(db)
    except Exception as e:
        print(f"\n严重错误: {str(e)}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
