from pathlib import Path
from PIL import Image
import re

class ParserService:
    @staticmethod
    def parse_tfw_file(tfw_path: Path) -> dict:
        """解析 .tfw 文件"""
        try:
            with open(tfw_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if len(lines) < 6:
                raise ValueError(f".tfw 文件格式错误：需要6行，实际只有{len(lines)}行")
            
            return {
                'pixel_width': float(lines[0].strip()),
                'rotation_a': float(lines[1].strip()),
                'rotation_b': float(lines[2].strip()),
                'pixel_height': float(lines[3].strip()),
                'upper_left_x': float(lines[4].strip()),
                'upper_left_y': float(lines[5].strip())
            }
        except Exception as e:
            raise ValueError(f"解析 .tfw 文件失败: {str(e)}")

    @staticmethod
    def parse_prj_file(prj_path: Path) -> int:
        """解析 .prj 文件，返回 EPSG 代码"""
        try:
            with open(prj_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            epsg_match = re.search(r'AUTHORITY\["EPSG",\s*"(\d+)"\]', content, re.IGNORECASE)
            if epsg_match:
                return int(epsg_match.group(1))
            
            lower_content = content.lower()
            if '+proj=merc' in lower_content or 'pseudo-mercator' in lower_content or 'web mercator' in lower_content:
                return 3857
            
            if 'wgs 84' in lower_content or 'wgs_1984' in lower_content:
                if 'projcs' not in content:
                    return 4326
            
            return 4326
        except Exception as e:
            print(f"解析 .prj 失败: {e}, 使用默认 EPSG:4326")
            return 4326

    @staticmethod
    def get_image_size(tif_path: Path) -> tuple:
        try:
            with Image.open(tif_path) as img:
                return img.size
        except Exception as e:
            raise ValueError(f"读取图像尺寸失败: {str(e)}")

    @staticmethod
    def calculate_extent(tfw_data: dict, width: int, height: int) -> dict:
        pixel_width = tfw_data['pixel_width']
        pixel_height = tfw_data['pixel_height']
        upper_left_x = tfw_data['upper_left_x']
        upper_left_y = tfw_data['upper_left_y']
        
        min_x = upper_left_x
        max_y = upper_left_y
        max_x = upper_left_x + (width * pixel_width)
        min_y = upper_left_y + (height * pixel_height)
        
        return {
            'min_x': min_x,
            'min_y': min_y,
            'max_x': max_x,
            'max_y': max_y
        }
