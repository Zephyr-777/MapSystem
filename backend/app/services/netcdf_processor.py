import xarray as xr
import numpy as np
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

class NetCDFProcessor:
    """
    处理 NetCDF 文件，提取元数据并生成数据切片
    """
    
    @staticmethod
    def extract_metadata(file_path: Path) -> Dict[str, Any]:
        """
        读取 .nc 文件并提取维度和变量信息
        """
        try:
            with xr.open_dataset(file_path) as ds:
                # 提取维度
                dims = {k: int(v) for k, v in ds.dims.items()}
                
                # 提取坐标信息 (用于确定范围)
                coords = {}
                for coord_name, coord_val in ds.coords.items():
                    coords[coord_name] = {
                        "min": float(coord_val.min()),
                        "max": float(coord_val.max()),
                        "size": int(coord_val.size),
                        "units": coord_val.attrs.get("units", "")
                    }
                
                # 提取变量
                variables = []
                for var_name, var_val in ds.data_vars.items():
                    # 过滤掉坐标变量 (通常已经在 coords 中)
                    if var_name in ds.coords:
                        continue
                        
                    variables.append({
                        "name": var_name,
                        "long_name": var_val.attrs.get("long_name", var_name),
                        "units": var_val.attrs.get("units", ""),
                        "dims": list(var_val.dims),
                        "shape": list(var_val.shape),
                        "dtype": str(var_val.dtype)
                    })
                
                # 尝试确定空间范围 (bbox)
                extent = None
                # 常见经纬度变量名
                lon_names = ['lon', 'longitude', 'x']
                lat_names = ['lat', 'latitude', 'y']
                
                lon_var = next((k for k in ds.coords if k.lower() in lon_names), None)
                lat_var = next((k for k in ds.coords if k.lower() in lat_names), None)
                
                if lon_var and lat_var:
                    min_x = float(ds[lon_var].min())
                    max_x = float(ds[lon_var].max())
                    min_y = float(ds[lat_var].min())
                    max_y = float(ds[lat_var].max())
                    extent = [min_x, min_y, max_x, max_y]
                
                return {
                    "dims": dims,
                    "coords": coords,
                    "variables": variables,
                    "extent": extent,
                    "global_attrs": {k: str(v) for k, v in ds.attrs.items()}
                }
        except Exception as e:
            print(f"Error processing NetCDF: {e}")
            raise e

    @staticmethod
    def get_data_slice(
        file_path: Path, 
        variable: str, 
        time_index: int = 0, 
        depth_index: int = 0
    ) -> Dict[str, Any]:
        """
        获取指定变量在特定时间/深度的切片数据 (用于前端可视化)
        返回: GeoJSON Point Collection (带值) 或 简单的 Grid JSON
        """
        try:
            with xr.open_dataset(file_path) as ds:
                if variable not in ds.data_vars:
                    raise ValueError(f"Variable {variable} not found")
                
                da = ds[variable]
                
                # 处理切片索引
                # 假设维度顺序通常是 (time, depth, lat, lon) 或 (lat, lon)
                # 我们需要根据实际维度名来切片
                
                sel_dict = {}
                
                # 查找时间维度
                time_dim = next((d for d in da.dims if 'time' in d.lower() or d == 't'), None)
                if time_dim:
                    # 确保索引在范围内
                    idx = min(time_index, da.sizes[time_dim] - 1)
                    sel_dict[time_dim] = ds[time_dim].values[idx]
                
                # 查找深度/垂直维度
                depth_dim = next((d for d in da.dims if 'depth' in d.lower() or 'lev' in d.lower() or d == 'z'), None)
                if depth_dim:
                    idx = min(depth_index, da.sizes[depth_dim] - 1)
                    sel_dict[depth_dim] = ds[depth_dim].values[idx]
                
                # 执行切片
                slice_da = da.sel(**sel_dict, method='nearest') if sel_dict else da
                
                # 确保剩下的是 2D (lat, lon)
                if len(slice_da.dims) != 2:
                    # 如果还有多余维度，取第0个
                    # 这是一个简化的处理，实际可能需要更复杂的逻辑
                    while len(slice_da.dims) > 2:
                        slice_da = slice_da.isel({slice_da.dims[0]: 0})
                
                # 获取经纬度网格
                lon_names = ['lon', 'longitude', 'x']
                lat_names = ['lat', 'latitude', 'y']
                
                lon_dim = next((d for d in slice_da.dims if d.lower() in lon_names), None)
                lat_dim = next((d for d in slice_da.dims if d.lower() in lat_names), None)
                
                if not lon_dim or not lat_dim:
                    raise ValueError("Could not identify lat/lon dimensions")
                
                # 转换为 DataFrame 或直接提取值
                # 为了前端性能，我们可能需要降采样或直接返回 Grid 数据
                # 这里返回简单的 Grid JSON: { lats: [], lons: [], values: [[...]] }
                
                # 处理 NaN
                vals = slice_da.values
                vals = np.where(np.isnan(vals), None, vals)
                
                return {
                    "variable": variable,
                    "units": da.attrs.get("units", ""),
                    "lons": slice_da[lon_dim].values.tolist(),
                    "lats": slice_da[lat_dim].values.tolist(),
                    "values": vals.tolist(),
                    "min": float(np.nanmin(slice_da.values)),
                    "max": float(np.nanmax(slice_da.values))
                }
                
        except Exception as e:
            print(f"Error getting slice: {e}")
            raise e
