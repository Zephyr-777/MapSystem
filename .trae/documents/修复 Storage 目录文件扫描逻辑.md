## 修复 Storage 目录文件扫描逻辑

### 问题分析
1. **物理路径与数据库不同步**：后端启动时未自动检查存储目录的物理文件与数据库记录的一致性
2. **SRID 字段处理不当**：部分记录可能缺少正确的坐标系统信息
3. **GET /api/geodata/list 缺少调试信息**：无法知道某些记录未返回的原因

### 解决方案

#### 1. 后端启动自检逻辑
- **文件**：`backend/main.py`
- **功能**：在 FastAPI 应用启动时，自动扫描 `/Users/mengzh/Desktop/vue-map/backend/storage` 目录
- **实现**：
  - 添加 `init_storage_sync` 函数，在应用初始化时调用
  - 扫描目录中的所有 `.tif` 文件
  - 对每个 TIF 文件，检查数据库中是否存在对应记录
  - 若不存在，调用 `process_and_save_geo_file` 自动解析并添加到数据库

#### 2. 增强数据库同步逻辑
- **文件**：`backend/utils_geo.py`
- **功能**：确保 SRID 字段被正确填充
- **实现**：
  - 确保 `process_and_save_geo_file` 函数总是解析 `.prj` 文件并设置 `srid` 字段
  - 改进 `parse_prj_file` 函数，确保准确识别 EPSG:3857 和其他坐标系统
  - 确保解析出的坐标系统信息与坐标值一起保存

#### 3. 改进 GET /api/geodata/list 接口
- **文件**：`backend/routers/geodata.py`
- **功能**：添加调试日志，显示文件存在性检查结果
- **实现**：
  - 对每个数据库记录，构建完整文件路径
  - 打印 `os.path.exists(full_path)` 的结果
  - 记录详细日志，说明为何某些记录未返回（权限问题、路径拼写错误等）
  - 确保所有文件存在性检查都有明确的日志输出

### 实现步骤

1. **修改 `backend/main.py`**：
   - 导入 `utils_geo.process_and_save_geo_file` 函数
   - 添加 `init_storage_sync` 函数
   - 在应用初始化前调用该函数

2. **优化 `backend/utils_geo.py`**：
   - 确保 `process_and_save_geo_file` 函数总是设置 `srid` 字段
   - 改进日志输出，显示 SRID 识别结果

3. **增强 `backend/routers/geodata.py`**：
   - 在 `get_geodata_list` 函数中添加文件存在性检查日志
   - 对每个记录，打印完整路径和存在性结果
   - 记录详细的错误信息，如权限问题或路径错误

### 预期效果
- 后端启动时自动同步存储目录与数据库
- 所有物理文件都有对应的数据库记录，且 SRID 字段正确填充
- GET /api/geodata/list 接口提供详细的调试信息，便于排查问题
- 确保坐标系统信息（SRID）与坐标值一起保存，不会丢失

### 测试建议
1. 清空数据库中的 `geo_assets` 表
2. 确保存储目录中有 TIF 文件及其对应的 .prj 和 .tfw 文件
3. 启动后端服务，检查是否自动添加所有文件到数据库
4. 调用 GET /api/geodata/list 接口，检查日志输出
5. 验证返回的记录中 SRID 字段正确填充