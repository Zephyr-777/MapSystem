# 智能问答系统技术详解

## 一、系统概述

本系统的智能问答功能允许用户使用自然语言查询地质数据，无需学习 SQL 或 GIS 专业术语。系统核心是将用户的自然语言问题自动转换为数据库查询语句，并返回精准的结果。

**核心能力**：

- ✅ 自然语言理解：理解"北京附近"、"最近一周"等模糊表达
- ✅ 空间关系解析：自动识别地理位置和空间范围
- ✅ 语义搜索：理解同义词和相关概念
- ✅ 智能排序：按相关性对结果进行排序

---

## 二、自然语言转 SQL 的完整过程

### 2.1 转换流程概览

```
用户输入
   ↓
[自然语言理解层] - Qwen3.5 大语言模型
   ↓
生成的 SQL 语句
   ↓
[安全检查层] - SQL 注入防护
   ↓
[数据库执行层] - PostgreSQL + PostGIS
   ↓
查询结果
   ↓
[语义重排序层] - 向量相似度计算
   ↓
最终结果返回给用户
```

### 2.2 详细转换步骤

#### **步骤 1：构建系统提示词（System Prompt）**

系统提示词是指导大模型理解任务的关键，它定义了：

- 数据库表结构
- 字段含义
- 查询规则
- 输出格式

```python
system_prompt = """
You are a PostgreSQL + PostGIS expert. Convert natural language queries to SQL.

Table Schema:
geo_assets (
    id INTEGER PRIMARY KEY,
    name VARCHAR,              -- 数据名称
    file_type VARCHAR,         -- 文件类型：DEM, Shapefile, GeoTIFF, NetCDF 等
    description VARCHAR,       -- 数据描述
    created_at TIMESTAMP,      -- 创建时间
    extent GEOMETRY(Polygon, 4326),  -- 空间范围（多边形）
    extent_min_x FLOAT,        -- 最小经度
    extent_min_y FLOAT,        -- 最小纬度
    extent_max_x FLOAT,        -- 最大经度
    extent_max_y FLOAT         -- 最大纬度
);

Rules:
1. Return ONLY the SQL query. No markdown, no explanation.
2. Use ST_Intersects or ST_Contains for spatial queries if 'extent' is valid.
3. If spatial query is complex or ambiguous, fallback to bounding box filter
   using extent_min_x/y etc.
4. Always select * from geo_assets.
5. Limit results to 20 if not specified.
"""
```

#### **步骤 2：调用大语言模型**

将用户问题和系统提示词一起发送给 Qwen3.5 模型：

```python
def _generate_sql(self, query: str) -> str:
    response = self.client.chat.completions.create(
        model="qwen3.5-flash",  # 使用通义千问快速响应模型
        messages=[
            {"role": "system", "content": system_prompt},  # 系统指令
            {"role": "user", "content": f"Query: {query}\nSQL:"}  # 用户问题
        ],
        temperature=0.1  # 低温度参数，确保输出稳定
    )
    return response.choices[0].message.content.strip()
```

#### **步骤 3：实际转换示例**

**示例 1：简单属性查询**

用户输入：`"查找所有的 DEM 数据"`

模型生成的 SQL：

```sql
SELECT * FROM geo_assets
WHERE file_type = 'DEM'
LIMIT 20
```

**示例 2：时间范围查询**

用户输入：`"查找最近一周上传的矢量数据"`

模型生成的 SQL：

```sql
SELECT * FROM geo_assets
WHERE file_type IN ('Shapefile', 'GeoJSON', 'WKT')
  AND created_at >= NOW() - INTERVAL '7 days'
LIMIT 20
```

**示例 3：空间位置查询**

用户输入：`"显示北京附近的 DEM 数据"`

模型生成的 SQL（使用空间函数）：

```sql
SELECT * FROM geo_assets
WHERE file_type = 'DEM'
  AND ST_Intersects(
    extent,
    ST_MakeEnvelope(115.7, 39.4, 117.4, 41.6, 4326)
  )
LIMIT 20
```

**示例 4：文本描述查询**

用户输入：`"查询包含'断层'描述的地质点"`

模型生成的 SQL：

```sql
SELECT * FROM geo_assets
WHERE description ILIKE '%断层%'
LIMIT 20
```

**示例 5：组合查询**

用户输入：`"查找青藏高原最近一个月的 GeoTIFF 数据"`

模型生成的 SQL：

```sql
SELECT * FROM geo_assets
WHERE file_type = 'GeoTIFF'
  AND created_at >= NOW() - INTERVAL '1 month'
  AND (
    ST_Intersects(extent, tibetan_plateau_polygon) OR
    (extent_min_x BETWEEN 73 AND 105 AND extent_min_y BETWEEN 26 AND 40)
  )
LIMIT 20
```

#### **步骤 4：SQL 清理和安全检查**

从模型返回的 SQL 可能包含 markdown 标记或其他格式问题，需要清理：

````python
# 清理 markdown 代码块标记
cleaned_sql = sql_query.replace("```sql", "").replace("```", "").strip()

# 安全检查：防止 SQL 注入和危险操作
dangerous_keywords = ["drop", "delete", "update", "insert", "alter", "truncate"]
if any(kw in cleaned_sql.lower() for kw in dangerous_keywords):
    print(f"Unsafe SQL blocked: {cleaned_sql}")
    # 降级到简单的 LIKE 搜索
    return self._fallback_search(query)
````

#### **步骤 5：执行 SQL 查询**

使用 SQLAlchemy 执行生成的 SQL：

```python
from sqlalchemy import text

try:
    # 使用 text() 包装原始 SQL
    result_proxy = self.db.execute(text(cleaned_sql))

    # 获取所有结果（以字典形式）
    results = result_proxy.mappings().all()

    # 提取 ID 列表
    ids = [row['id'] for row in results if 'id' in row]

    # 使用 ORM 查询完整对象
    assets = self.db.query(GeoAsset).filter(GeoAsset.id.in_(ids)).all()

except Exception as e:
    print(f"SQL Execution failed: {e}")
    # 降级到简单搜索
    return self._fallback_search(query)
```

---

## 三、PostgreSQL + PostGIS 数据库详解

### 3.1 PostgreSQL 是什么？

**PostgreSQL** 是一个强大的开源关系型数据库管理系统（RDBMS），特点包括：

- ✅ 支持复杂查询和事务（ACID 兼容）
- ✅ 支持自定义数据类型和函数
- ✅ 优秀的扩展性（通过插件）
- ✅ 对 GIS 空间数据的原生支持（通过 PostGIS 扩展）

### 3.2 PostGIS 是什么？

**PostGIS** 是 PostgreSQL 的空间数据库扩展，它添加了：

- 空间数据类型（点、线、面、几何体）
- 空间函数（计算距离、相交、包含等）
- 空间索引（加速空间查询）

### 3.3 数据库能存储什么？

#### **A. 属性数据（传统关系型数据）**

存储在 `geo_assets` 表中的常规字段：

| 字段名         | 数据类型  | 说明           | 示例值                           |
| -------------- | --------- | -------------- | -------------------------------- |
| `id`           | INTEGER   | 主键，唯一标识 | 1, 2, 3                          |
| `name`         | VARCHAR   | 数据名称       | "四川省 DEM 数据"                |
| `file_type`    | VARCHAR   | 文件类型       | "DEM", "Shapefile", "GeoTIFF"    |
| `description`  | VARCHAR   | 描述文本       | "四川省 30 米分辨率数字高程模型" |
| `created_at`   | TIMESTAMP | 创建时间       | 2025-03-16 10:30:00              |
| `extent_min_x` | FLOAT     | 最小经度       | 102.5                            |
| `extent_min_y` | FLOAT     | 最小纬度       | 28.3                             |
| `extent_max_x` | FLOAT     | 最大经度       | 108.7                            |
| `extent_max_y` | FLOAT     | 最大纬度       | 34.2                             |

**用途**：存储数据的元信息，用于快速筛选和展示。

#### **B. 空间数据（几何图形）**

存储在 `extent` 字段中的空间几何对象：

**1. 几何类型（Geometry Types）**

```sql
-- 点（Point）：表示一个位置
SELECT ST_GeomFromText('POINT(116.4 39.9)', 4326);
-- 北京的位置

-- 线（LineString）：表示路径或边界
SELECT ST_GeomFromText('LINESTRING(116.4 39.9, 121.5 31.2)', 4326);
-- 从北京到上海的线

-- 面（Polygon）：表示区域
SELECT ST_GeomFromText('POLYGON((116.0 39.5, 117.0 39.5, 117.0 40.5, 116.0 40.5, 116.0 39.5))', 4326);
-- 北京市的近似范围

-- 多点（MultiPoint）、多线（MultiLineString）、多面（MultiPolygon）
-- 用于表示多个分离的几何对象
```

**2. 空间参考系统（SRID）**

- `4326`：WGS84 坐标系，GPS 使用的经纬度系统（最常用）
- `3857`：Web Mercator 投影，Google Maps、OpenStreetMap 使用
- `32650`：UTM 投影，适合局部区域的高精度测量

**3. 实际存储示例**

```sql
-- 插入一个带有空间范围的数据
INSERT INTO geo_assets (
    name,
    file_type,
    description,
    extent,  -- 空间几何字段
    extent_min_x, extent_min_y, extent_max_x, extent_max_y
) VALUES (
    '四川省 DEM',
    'GeoTIFF',
    '四川省 30 米分辨率数字高程模型',
    ST_GeomFromText(
        'POLYGON((102.5 28.3, 108.7 28.3, 108.7 34.2, 102.5 34.2, 102.5 28.3))',
        4326
    ),
    102.5, 28.3, 108.7, 34.2
);
```

### 3.4 空间查询函数详解

#### **A. 空间关系判断**

**1. ST_Intersects(geom1, geom2)** - 判断是否相交

最常用的空间函数，判断两个几何体是否有重叠部分。

```sql
-- 查询与给定区域相交的所有数据
SELECT * FROM geo_assets
WHERE ST_Intersects(
    extent,  -- 数据库中的空间字段
    ST_GeomFromText('POLYGON((116.0 39.5, 117.0 39.5, 117.0 40.5, 116.0 40.5, 116.0 39.5))', 4326)
);

-- 实际应用场景：查询北京市范围内的所有地质数据
```

**2. ST_Contains(geom1, geom2)** - 判断是否包含

判断 geom1 是否完全包含 geom2。

```sql
-- 查询完全包含给定区域的数据
SELECT * FROM geo_assets
WHERE ST_Contains(
    extent,
    ST_GeomFromText('POINT(116.4 39.9)', 4326)  -- 北京市中心点
);
```

**3. ST_Within(geom1, geom2)** - 判断是否在内部

判断 geom1 是否完全在 geom2 内部。

```sql
-- 查询完全在给定区域内的数据
SELECT * FROM geo_assets
WHERE ST_Within(
    extent,
    ST_GeomFromText('POLYGON((102.5 28.3, 108.7 28.3, 108.7 34.2, 102.5 34.2, 102.5 28.3))', 4326)
);
```

**4. ST_Distance(geom1, geom2)** - 计算距离

计算两个几何体之间的距离（单位：米）。

```sql
-- 查询距离北京市中心 100 公里内的所有数据
SELECT *,
       ST_Distance(
           extent,
           ST_GeomFromText('POINT(116.4 39.9)', 4326)
       ) as distance_meters
FROM geo_assets
WHERE ST_Distance(
    extent,
    ST_GeomFromText('POINT(116.4 39.9)', 4326)
) < 100000  -- 100 公里
ORDER BY distance_meters;
```

#### **B. 空间构造函数**

**1. ST_MakeEnvelope(minx, miny, maxx, maxy, SRID)** - 创建矩形范围

最常用的快速创建查询框的函数。

```sql
-- 创建北京市的近似边界框
SELECT ST_MakeEnvelope(115.7, 39.4, 117.4, 41.6, 4326);

-- 实际应用：查询北京附近的数据
SELECT * FROM geo_assets
WHERE ST_Intersects(
    extent,
    ST_MakeEnvelope(115.7, 39.4, 117.4, 41.6, 4326)
);
```

**2. ST_Buffer(geom, radius)** - 创建缓冲区

围绕几何体创建一个指定半径的缓冲区。

```sql
-- 查询长江沿线 50 公里范围内的所有地质数据
SELECT * FROM geo_assets
WHERE ST_Intersects(
    extent,
    ST_Buffer(
        ST_GeomFromText('LINESTRING(...)', 4326),  -- 长江路径
        50000  -- 50 公里缓冲区
    )
);
```

**3. ST_Union(geom1, geom2)** - 合并几何体

将多个几何体合并为一个。

```sql
-- 合并多个相邻的区域
SELECT ST_Union(
    ST_GeomFromText('POLYGON((...))', 4326),
    ST_GeomFromText('POLYGON((...))', 4326)
);
```

#### **C. 空间提取函数**

**1. ST_X(point)** 和 **ST_Y(point)** - 提取坐标

```sql
-- 提取点的经纬度
SELECT ST_X(geom), ST_Y(geom) FROM stations;
```

**2. ST_Area(geom)** - 计算面积

```sql
-- 计算每个数据覆盖的面积（平方米）
SELECT name, ST_Area(extent::geography) as area_sqm
FROM geo_assets;
```

**3. ST_Centroid(geom)** - 获取几何中心

```sql
-- 获取每个数据的中心点坐标
SELECT name, ST_AsText(ST_Centroid(extent)) as center_point
FROM geo_assets;
```

### 3.5 完整查询示例

#### **示例 1：查询特定区域的数据**

```sql
-- 查询四川省范围内的所有地质数据
SELECT
    id,
    name,
    file_type,
    description,
    ST_AsText(extent) as boundary_wkt
FROM geo_assets
WHERE ST_Intersects(
    extent,
    ST_GeomFromText(
        'POLYGON((102.5 28.3, 108.7 28.3, 108.7 34.2, 102.5 34.2, 102.5 28.3))',
        4326
    )
);
```

#### **示例 2：组合查询（空间 + 属性 + 时间）**

```sql
-- 查询青藏高原地区最近一个月上传的 DEM 数据
SELECT * FROM geo_assets
WHERE file_type = 'DEM'
  AND created_at >= NOW() - INTERVAL '1 month'
  AND ST_Intersects(
      extent,
      ST_GeomFromText(
          'POLYGON((73 26, 105 26, 105 40, 73 40, 73 26))',
          4326
      )
  )
ORDER BY created_at DESC
LIMIT 20;
```

#### **示例 3：距离排序查询**

```sql
-- 查询距离上海市中心最近的前 10 个数据
SELECT
    id,
    name,
    file_type,
    ST_Distance(
        extent::geography,
        ST_GeomFromText('POINT(121.4737 31.2304)', 4326)::geography
    ) as distance_meters
FROM geo_assets
ORDER BY distance_meters
LIMIT 10;
```

#### **示例 4：空间连接查询**

```sql
-- 查询每个省份有多少个地质数据
SELECT
    provinces.name as province_name,
    COUNT(geo_assets.id) as asset_count
FROM provinces
LEFT JOIN geo_assets
    ON ST_Intersects(provinces.boundary, geo_assets.extent)
GROUP BY provinces.name
ORDER BY asset_count DESC;
```

---

## 四、语义重排序（Semantic Reranking）

### 4.1 为什么需要重排序？

SQL 查询返回的结果可能不够精准。例如：

- 用户搜索："地震数据"
- SQL 返回：所有包含"地震"关键词的数据
- 但有些数据描述为"earthquake"或"seismic"，字面不匹配

**解决方案**：使用向量嵌入和余弦相似度进行语义重排序。

### 4.2 重排序流程

```python
async def _semantic_rerank(self, assets: List[GeoAsset], query: str):
    # 1. 获取查询的向量嵌入
    query_emb = self._get_embedding(query)  # 如 [0.123, -0.456, 0.789, ...]

    # 2. 获取所有结果的向量嵌入
    docs = [f"{a.name} {a.description or ''}" for a in assets]
    doc_embs = [self._get_embedding(d) for d in docs]

    # 3. 计算余弦相似度
    similarities = cosine_similarity([query_emb], doc_embs)[0]

    # 4. 按相似度排序
    scored_assets = list(zip(assets, similarities))
    scored_assets.sort(key=lambda x: x[1], reverse=True)

    return [a for a, s in scored_assets]
```

### 4.3 向量嵌入是什么？

**向量嵌入（Embedding）** 是将文本转换为高维向量的技术，使得语义相似的文本在向量空间中距离更近。

**示例**：

```
"地震" → [0.123, -0.456, 0.789, 0.234, ...]
"earthquake" → [0.125, -0.453, 0.791, 0.232, ...]
"洪水" → [0.567, 0.123, -0.345, 0.678, ...]
```

可以看到，"地震"和"earthquake"的向量非常接近，而"洪水"的向量则相差较远。

### 4.4 余弦相似度计算

**余弦相似度** 用于衡量两个向量的相似程度，值域为 [-1, 1]：

- 1：完全相同
- 0：无关
- -1：完全相反

```python
from sklearn.metrics.pairwise import cosine_similarity

# 计算查询向量与所有文档向量的相似度
similarities = cosine_similarity([query_emb], doc_embs)[0]

# 结果示例：[0.92, 0.87, 0.45, 0.23]
# 表示第一个文档与查询最相似
```

---

## 五、完整数据流示例

### 用户查询："查找北京附近的 DEM 数据"

#### **步骤 1：前端发送请求**

```typescript
// SmartSearchBox.vue
const response = await geoDataApi.smartSearch("查找北京附近的 DEM 数据");
```

#### **步骤 2：后端接收并生成 SQL**

```python
# GET /api/geodata/smart-search?q=查找北京附近的 DEM 数据

# 1. 调用大模型生成 SQL
sql = llm_generate("""
Query: 查找北京附近的 DEM 数据
SQL:
""")

# 生成的 SQL:
# SELECT * FROM geo_assets
# WHERE file_type = 'DEM'
#   AND ST_Intersects(extent, ST_MakeEnvelope(115.7, 39.4, 117.4, 41.6, 4326))
# LIMIT 20
```

#### **步骤 3：执行 SQL 查询**

```python
# 执行 SQL
result_proxy = db.execute(text(sql))
results = result_proxy.mappings().all()

# 提取 ID 并查询完整对象
ids = [row['id'] for row in results]
assets = db.query(GeoAsset).filter(GeoAsset.id.in_(ids)).all()
```

#### **步骤 4：语义重排序**

```python
# 计算每个结果与查询的语义相似度
reranked_assets = await semantic_rerank(assets, "查找北京附近的 DEM 数据")
```

#### **步骤 5：返回结果**

```json
{
  "data": [
    {
      "id": 1,
      "name": "北京市 DEM 数据",
      "file_type": "DEM",
      "description": "北京市 30 米分辨率数字高程模型",
      "extent": {...},
      "relevance_score": 0.95
    },
    {
      "id": 5,
      "name": "华北平原地形图",
      "file_type": "DEM",
      "description": "包含北京地区的高程数据",
      "extent": {...},
      "relevance_score": 0.87
    }
  ],
  "total": 2
}
```

---

## 六、技术亮点总结

### 6.1 创新点

1. **零学习成本**：用户无需学习 SQL 或 GIS 术语
2. **语义理解**：理解同义词、模糊表达、空间关系
3. **智能排序**：结合空间关系和语义相关性
4. **安全可靠**：SQL 注入防护、错误降级处理

### 6.2 技术栈

| 层级       | 技术                 | 作用                   |
| ---------- | -------------------- | ---------------------- |
| 大语言模型 | Qwen3.5-flash        | 自然语言理解，SQL 生成 |
| 嵌入模型   | text-embedding-v2    | 文本向量化             |
| 数据库     | PostgreSQL + PostGIS | 空间数据存储和查询     |
| 相似度计算 | scikit-learn         | 余弦相似度             |
| Web 框架   | FastAPI              | RESTful API            |

### 6.3 性能优化

- **空间索引**：使用 GIST 索引加速空间查询
- **缓存机制**：缓存常用查询结果
- **降级策略**：AI 失败时自动切换到简单搜索
- **批量处理**：批量计算向量嵌入，减少 API 调用

---

## 七、面试回答模板

### 问题："请介绍一下你的智能问答功能"

**回答**：

> "我的毕设项目实现了一个基于大语言模型的地质数据智能问答系统。它的核心价值是让用户能够用自然语言直接查询地质数据，而不需要学习 SQL 或 GIS 专业术语。
>
> **技术实现上分为三个层次**：
>
> **第一层是自然语言理解**。我使用通义千问 Qwen3.5 大模型，通过精心设计的系统提示词，让模型理解数据库结构，然后将用户的自然语言问题转换为 SQL 查询语句。比如用户说'查找北京附近的 DEM 数据'，模型会自动生成包含空间查询函数的 SQL。
>
> **第二层是数据库查询**。我使用 PostgreSQL 配合 PostGIS 扩展来存储空间数据。PostGIS 提供了强大的空间函数，比如 ST_Intersects 可以判断两个区域是否相交，ST_MakeEnvelope 可以快速创建查询范围。这些函数使得空间查询变得非常高效。
>
> **第三层是语义优化**。考虑到单纯的关键词匹配可能不够精准，我还实现了语义重排序。通过计算查询和结果的向量嵌入，使用余弦相似度来评估相关性，确保最相关的结果排在前面。
>
> **这个功能的亮点在于**：
>
> - 用户完全不需要技术背景，说人话就能查询
> - 支持空间关系理解，比如'附近'、'范围内'
> - 支持时间和属性的组合查询
> - 有完善的安全机制，防止 SQL 注入
>
> 我觉得这个功能体现了我的跨学科整合能力，将大语言模型、空间数据库和语义理解技术有机结合，解决了传统 GIS 系统查询门槛高的痛点。"

---

## 八、常见问题解答

### Q1: 为什么选择 PostgreSQL + PostGIS 而不是 MongoDB 或 MySQL？

**A**: PostgreSQL + PostGIS 是开源 GIS 领域的黄金组合：

- PostGIS 提供了最完整的空间函数支持（100+ 个空间函数）
- 空间索引性能优异（GIST 索引）
- 支持复杂的空间数据类型
- 成熟的社区和文档支持
- MySQL 的空间功能相对较弱，MongoDB 的地理空间查询不如 PostGIS 专业

### Q2: 大模型生成的 SQL 不准确怎么办？

**A**: 有多层保障：

1. **系统提示词优化**：明确告知模型表结构和查询规则
2. **安全检查**：拦截 DROP、DELETE 等危险操作
3. **异常处理**：SQL 执行失败时自动降级到简单的 LIKE 搜索
4. **温度参数**：设置 temperature=0.1 确保输出稳定

### Q3: 语义重排序会不会影响性能？

**A**: 确实会增加延迟，因此：

- 默认关闭重排序，仅在结果较多时启用
- 批量计算向量嵌入，减少 API 调用次数
- 限制重排序的结果数量（前 20 条）
- 可以考虑本地部署嵌入模型，减少网络延迟

### Q4: 如何处理中文地名的空间解析？

**A**: 当前实现使用预定义的坐标范围（如北京的经纬度框）。更高级的方案：

- 集成地理编码 API（如高德、百度地图 API）
- 建立地名 - 坐标映射数据库
- 使用 NLP 技术识别地名实体并解析

### Q5: 智能问答与传统搜索有什么区别？

**A**:
| 维度 | 传统关键词搜索 | 智能语义搜索 |
|------|--------------|-------------|
| **输入方式** | 精确关键词 | 自然语言句子 |
| **匹配逻辑** | 字面匹配（LIKE） | 语义理解 + 向量相似度 |
| **空间查询** | 需要手动输入坐标 | "北京附近" 自动解析 |
| **结果排序** | 按时间/名称 | 按语义相关性 |
| **示例** | "DEM Sichuan" | "我想看四川的高程数据" |

### Q6: 系统如何处理复杂的空间查询？

**A**: 系统采用多层策略：

1. **简单空间关系**：使用 `ST_Intersects` 判断相交
2. **距离查询**：使用 `ST_Distance` 计算距离
3. **缓冲区查询**：使用 `ST_Buffer` 创建缓冲区
4. **复杂区域**：使用 `ST_Union` 合并多个几何体
5. **降级策略**：复杂查询失败时使用边界框过滤

---

## 九、系统架构与实现细节

### 9.1 前端交互组件

智能问答功能的前端入口是 `SmartSearchBox.vue` 组件，提供以下功能：

**用户界面**：

```vue
<template>
  <div class="smart-search">
    <el-input
      v-model="searchQuery"
      placeholder="用自然语言描述您要找的数据..."
      @keyup.enter="handleSearch"
      :prefix-icon="Search"
      clearable
    >
      <template #append>
        <el-button @click="handleSearch" :loading="loading">
          <el-icon><MagicStick /></el-icon> 智能搜索
        </el-button>
      </template>
    </el-input>

    <!-- 搜索建议 -->
    <div v-if="suggestions.length" class="search-suggestions">
      <el-tag
        v-for="sug in suggestions"
        :key="sug"
        @click="
          searchQuery = sug;
          handleSearch();
        "
      >
        {{ sug }}
      </el-tag>
    </div>
  </div>
</template>
```

**预设搜索建议**：

```typescript
const suggestions = ref<string[]>([
  "查找最近一周上传的矢量数据",
  "显示北京附近的 DEM 数据",
  "查询包含'断层'描述的地质点",
]);
```

**搜索处理逻辑**：

```typescript
const handleSearch = async () => {
  if (!searchQuery.value.trim()) return;

  loading.value = true;
  try {
    // 调用后端智能搜索接口
    const response = await geoDataApi.smartSearch(searchQuery.value);
    const results = Array.isArray(response)
      ? response
      : (response as any).data || [];

    if (results.length === 0) {
      ElMessage.info("未找到匹配的数据");
    } else {
      ElMessage.success(`智能检索到 ${results.length} 条数据`);
      emit("search-result", results);
    }
  } catch (error) {
    console.error(error);
    ElMessage.error("智能搜索服务暂不可用");
  } finally {
    loading.value = false;
  }
};
```

### 9.2 后端 API 接口

**接口定义** (`/api/geodata/smart-search`)：

```python
@router.get("/smart-search", response_model=GeoDataListResponse)
async def smart_search(
    q: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    基于自然语言的智能搜索 (NL2SQL + 语义排序)
    """
    if not q:
        return GeoDataListResponse(data=[], total=0)

    # 创建搜索引擎实例
    engine = SemanticSearchEngine(db)

    # 执行搜索
    assets = await engine.search(q)

    # 构建返回结果
    data_list = []
    for asset in assets:
        full_path = settings.STORAGE_DIR / asset.file_path
        exists = full_path.exists()

        extent = None
        if asset.extent_min_x is not None:
            extent = [asset.extent_min_x, asset.extent_min_y,
                     asset.extent_max_x, asset.extent_max_y]

        center_x = asset.center_x
        center_y = asset.center_y
        if center_x is None and extent:
            center_x = (extent[0] + extent[2]) / 2
            center_y = (extent[1] + extent[3]) / 2

        data_list.append(GeoDataItem(
            id=asset.id,
            name=asset.name,
            type=asset.file_type,
            uploadTime=asset.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            extent=extent,
            srid=asset.srid,
            exists=exists,
            center_x=center_x,
            center_y=center_y,
            description=asset.description,
            source="internal"
        ))

    return GeoDataListResponse(data=data_list, total=len(data_list))
```

### 9.3 核心服务类

**SemanticSearchEngine 类结构**：

```python
class SemanticSearchEngine:
    def __init__(self, db: Session):
        self.db = db
        # 使用 DashScope API
        self.api_key = os.getenv("DASHSCOPE_API_KEY", "sk-xxx")
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"

        # 模型配置
        self.model_name = "qwen3.5-flash"

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        ) if self.api_key else None

        # 系统提示词
        self.system_prompt = """..."""

    async def search(self, query: str) -> List[GeoAsset]:
        """执行语义搜索：NL -> SQL -> 执行 -> 重排序"""
        # 1. NL2SQL 转换
        sql_query = self._generate_sql(query)

        # 2. 安全检查
        cleaned_sql = self._sanitize_sql(sql_query)

        # 3. 执行 SQL
        results = self._execute_sql(cleaned_sql)

        # 4. 语义重排序（可选）
        reranked_assets = await self._semantic_rerank(results, query)

        return reranked_assets

    def _generate_sql(self, query: str) -> str:
        """调用大模型生成 SQL"""
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Query: {query}\nSQL:"}
            ],
            temperature=0.1
        )
        return response.choices[0].message.content.strip()

    def _get_embedding(self, text: str) -> List[float]:
        """获取文本的向量嵌入"""
        response = self.client.embeddings.create(
            input=text,
            model="text-embedding-v2"
        )
        return response.data[0].embedding
```

### 9.4 数据流转全过程

```
┌─────────────────────────────────────────────────────────────┐
│                     用户输入查询                              │
│            "查找北京附近的 DEM 数据"                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  前端：SmartSearchBox.vue                                   │
│  - 捕获用户输入                                             │
│  - 发送 HTTP GET 请求                                        │
│  - 显示加载状态                                             │
└─────────────────────┬───────────────────────────────────────┘
                      │ GET /api/geodata/smart-search?q=...
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  后端：smart_search() API                                   │
│  - 验证用户认证                                             │
│  - 创建 SemanticSearchEngine 实例                           │
│  - 调用 search() 方法                                        │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 1: NL2SQL 转换                                         │
│  - 构建 system prompt                                       │
│  - 调用 Qwen3.5-flash 模型                                   │
│  - 生成 SQL 语句                                             │
│                                                              │
│  生成的 SQL:                                                │
│  SELECT * FROM geo_assets                                   │
│  WHERE file_type = 'DEM'                                    │
│    AND ST_Intersects(extent,                                │
│      ST_MakeEnvelope(115.7, 39.4, 117.4, 41.6, 4326))       │
│  LIMIT 20                                                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 2: SQL 安全检查                                        │
│  - 清理 markdown 标记                                         │
│  - 检查危险关键词（DROP, DELETE 等）                          │
│  - 如果检测到危险操作，降级为简单 LIKE 搜索                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 3: 执行 SQL 查询                                       │
│  - 使用 SQLAlchemy 执行 SQL                                  │
│  - 获取结果 ID 列表                                          │
│  - 使用 ORM 查询完整对象                                    │
│                                                              │
│  数据库：PostgreSQL + PostGIS                               │
│  - extent 字段存储空间几何（Polygon, 4326）                 │
│  - 使用 GIST 空间索引加速查询                               │
│  - ST_Intersects 判断空间相交关系                           │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 4: 语义重排序（可选）                                  │
│  - 获取查询的向量嵌入                                        │
│  - 获取所有结果的向量嵌入                                    │
│  - 计算余弦相似度                                            │
│  - 按相似度降序排列                                          │
│                                                              │
│  示例相似度：[0.95, 0.87, 0.45, 0.23]                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 5: 构建返回结果                                        │
│  - 转换为 GeoDataItem 列表                                   │
│  - 计算中心点坐标                                            │
│  - 检查文件是否存在                                          │
│  - 格式化时间戳                                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  返回 JSON 响应                                               │
│  {                                                          │
│    "data": [                                                │
│      {                                                      │
│        "id": 1,                                             │
│        "name": "北京市 DEM 数据",                             │
│        "type": "DEM",                                       │
│        "extent": [115.7, 39.4, 117.4, 41.6],               │
│        "description": "30 米分辨率数字高程模型",              │
│        "uploadTime": "2025-03-10 14:30:00"                 │
│      }                                                      │
│    ],                                                       │
│    "total": 1                                               │
│  }                                                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  前端处理响应                                                │
│  - 显示成功消息："智能检索到 1 条数据"                        │
│  - 在地图上高亮显示结果                                     │
│  - 更新侧边栏列表                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 十、数据库表结构详解

### 10.1 geo_assets 表完整定义

```sql
CREATE TABLE geo_assets (
    -- 主键
    id SERIAL PRIMARY KEY,

    -- 基本属性
    name VARCHAR(255) NOT NULL,              -- 数据名称
    file_type VARCHAR(50) NOT NULL,          -- 文件类型
    file_path VARCHAR(500) NOT NULL,         -- 文件存储路径
    file_size BIGINT,                        -- 文件大小（字节）
    description TEXT,                        -- 数据描述

    -- 空间信息
    extent GEOMETRY(Polygon, 4326),          -- 空间范围（多边形）
    extent_min_x FLOAT,                      -- 最小经度
    extent_min_y FLOAT,                      -- 最小纬度
    extent_max_x FLOAT,                      -- 最大经度
    extent_max_y FLOAT,                      -- 最大纬度
    srid INTEGER DEFAULT 4326,               -- 空间参考 ID
    center_x FLOAT,                          -- 中心点经度
    center_y FLOAT,                          -- 中心点纬度

    -- 元数据
    created_at TIMESTAMP DEFAULT NOW(),      -- 创建时间
    updated_at TIMESTAMP DEFAULT NOW(),      -- 更新时间
    uploaded_by INTEGER,                     -- 上传者 ID

    -- 索引
    CONSTRAINT unique_name UNIQUE (name)
);

-- 创建空间索引（加速空间查询）
CREATE INDEX idx_geo_assets_extent ON geo_assets USING GIST (extent);

-- 创建属性索引（加速属性查询）
CREATE INDEX idx_geo_assets_file_type ON geo_assets (file_type);
CREATE INDEX idx_geo_assets_created_at ON geo_assets (created_at);
CREATE INDEX idx_geo_assets_name ON geo_assets (name);
```

### 10.2 空间数据示例

**插入一个 DEM 数据**：

```sql
INSERT INTO geo_assets (
    name, file_type, file_path, description,
    extent, extent_min_x, extent_min_y, extent_max_x, extent_max_y,
    center_x, center_y
) VALUES (
    '四川省 DEM 数据',
    'GeoTIFF',
    '/data/dem/sichuan_dem.tif',
    '四川省 30 米分辨率数字高程模型',
    ST_GeomFromText(
        'POLYGON((102.5 28.3, 108.7 28.3, 108.7 34.2, 102.5 34.2, 102.5 28.3))',
        4326
    ),
    102.5, 28.3, 108.7, 34.2,
    105.6, 31.25
);
```

**查询示例**：

```sql
-- 查询所有 DEM 数据
SELECT id, name, description
FROM geo_assets
WHERE file_type = 'DEM';

-- 查询四川省范围内的数据
SELECT id, name, file_type
FROM geo_assets
WHERE ST_Intersects(
    extent,
    ST_GeomFromText(
        'POLYGON((102.5 28.3, 108.7 28.3, 108.7 34.2, 102.5 34.2, 102.5 28.3))',
        4326
    )
);

-- 查询最近一周上传的数据
SELECT id, name, created_at
FROM geo_assets
WHERE created_at >= NOW() - INTERVAL '7 days';

-- 组合查询：四川省最近一个月的 DEM 数据
SELECT id, name, description, created_at
FROM geo_assets
WHERE file_type = 'DEM'
  AND created_at >= NOW() - INTERVAL '1 month'
  AND ST_Intersects(
      extent,
      ST_GeomFromText(
          'POLYGON((102.5 28.3, 108.7 28.3, 108.7 34.2, 102.5 34.2, 102.5 28.3))',
          4326
      )
  )
ORDER BY created_at DESC;
```

---

## 十一、技术选型对比

### 11.1 大语言模型选型

| 模型               | 优点                       | 缺点             | 适用场景         |
| ------------------ | -------------------------- | ---------------- | ---------------- |
| **Qwen3.5-flash**  | 速度快，成本低，中文理解好 | 复杂推理能力略弱 | 简单 NL2SQL 转换 |
| **GPT-4**          | 理解能力强，准确率高       | 成本高，延迟大   | 复杂查询理解     |
| **Claude 3**       | 长文本处理好               | 中文支持一般     | 文档分析         |
| **本地部署 LLaMA** | 数据隐私好，无 API 调用    | 需要 GPU 资源    | 敏感数据场景     |

**本系统选择 Qwen3.5-flash 的原因**：

- ✅ 中文理解能力强
- ✅ API 成本低
- ✅ 响应速度快（适合实时查询）
- ✅ 支持 OpenAI 兼容接口，集成简单

### 11.2 数据库选型

| 数据库                   | 空间功能   | 性能       | 易用性     | 成本      |
| ------------------------ | ---------- | ---------- | ---------- | --------- |
| **PostgreSQL + PostGIS** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐   | 免费      |
| **MySQL**                | ⭐⭐⭐     | ⭐⭐⭐⭐   | ⭐⭐⭐⭐⭐ | 免费      |
| **MongoDB**              | ⭐⭐⭐     | ⭐⭐⭐⭐   | ⭐⭐⭐⭐   | 免费/付费 |
| **Oracle Spatial**       | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐     | 昂贵      |

**选择 PostgreSQL + PostGIS 的原因**：

- ✅ 最完整的空间函数支持（100+ 函数）
- ✅ 优秀的空间索引性能（GIST 索引）
- ✅ 开源免费，社区活跃
- ✅ 成熟的 GIS 生态系统

### 11.3 向量嵌入模型

| 模型                       | 维度 | 中文支持   | 速度 | 成本         |
| -------------------------- | ---- | ---------- | ---- | ------------ |
| **text-embedding-v2**      | 1536 | ⭐⭐⭐⭐⭐ | 快   | 低           |
| **text-embedding-3-large** | 3072 | ⭐⭐⭐⭐⭐ | 中   | 中           |
| **BGE-Large**              | 1024 | ⭐⭐⭐⭐⭐ | 快   | 免费（本地） |
| **m3e-base**               | 768  | ⭐⭐⭐⭐⭐ | 快   | 免费（本地） |

---

## 十二、性能优化策略

### 12.1 查询优化

**1. 空间索引优化**

```sql
-- 确保 extent 字段有 GIST 索引
CREATE INDEX idx_geo_assets_extent ON geo_assets USING GIST (extent);

-- 查询前使用边界框预过滤（利用索引）
SELECT * FROM geo_assets
WHERE extent_min_x <= 117.4
  AND extent_max_x >= 115.7
  AND extent_min_y <= 41.6
  AND extent_max_y >= 39.4
  AND ST_Intersects(extent, ST_MakeEnvelope(115.7, 39.4, 117.4, 41.6, 4326));
```

**2. 组合索引**

```sql
-- 为常用查询创建组合索引
CREATE INDEX idx_file_type_created
ON geo_assets (file_type, created_at);
```

**3. 查询分析**

```sql
-- 使用 EXPLAIN ANALYZE 分析查询性能
EXPLAIN ANALYZE
SELECT * FROM geo_assets
WHERE ST_Intersects(extent, ST_MakeEnvelope(115.7, 39.4, 117.4, 41.6, 4326));
```

### 12.2 缓存策略

**1. SQL 生成缓存**

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=1000)
def cached_generate_sql(query_hash: str) -> str:
    """缓存已生成的 SQL，避免重复调用大模型"""
    # 实现略
    pass

def generate_sql(query: str) -> str:
    query_hash = hashlib.md5(query.encode()).hexdigest()
    return cached_generate_sql(query_hash)
```

**2. 查询结果缓存**

```python
import redis
import json

redis_client = redis.Redis()

def get_cached_results(cache_key: str):
    """从 Redis 获取缓存的查询结果"""
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    return None

def cache_results(cache_key: str, results, ttl=300):
    """缓存查询结果，5 分钟过期"""
    redis_client.setex(
        cache_key,
        ttl,
        json.dumps(results, default=str)
    )
```

### 12.3 批量处理

**批量计算向量嵌入**

```python
def batch_get_embeddings(texts: List[str], batch_size=10):
    """批量获取向量嵌入，减少 API 调用次数"""
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.embeddings.create(
            input=batch,
            model="text-embedding-v2"
        )
        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)

    return all_embeddings
```

---

## 十三、安全与容错

### 13.1 SQL 注入防护

**1. 使用参数化查询**

```python
# ❌ 错误：直接拼接 SQL
sql = f"SELECT * FROM geo_assets WHERE name = '{user_input}'"

# ✅ 正确：使用参数化查询
from sqlalchemy import text
sql = text("SELECT * FROM geo_assets WHERE name = :name")
result = db.execute(sql, {"name": user_input})
```

**2. 危险操作拦截**

```python
def sanitize_sql(sql: str) -> str:
    """检查并拦截危险 SQL 操作"""
    dangerous_keywords = [
        "drop", "delete", "update", "insert",
        "alter", "truncate", "create", "grant", "revoke"
    ]

    sql_lower = sql.lower()
    for keyword in dangerous_keywords:
        if keyword in sql_lower:
            print(f"Unsafe SQL blocked: {sql}")
            return None

    return sql
```

### 13.2 错误降级策略

**多级降级机制**：

```python
async def search(self, query: str):
    try:
        # Level 1: 完整智能搜索（NL2SQL + 重排序）
        sql = self._generate_sql(query)
        results = self._execute_sql(sql)
        reranked = await self._semantic_rerank(results, query)
        return reranked

    except LLMError:
        # Level 2: 降级为简单 LIKE 搜索
        print("LLM failed, falling back to LIKE search")
        return self._fallback_search(query)

    except DatabaseError:
        # Level 3: 返回空结果
        print("Database error")
        return []
```

### 13.3 限流与配额

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("/smart-search")
@limiter.limit("10/minute")  # 每分钟最多 10 次请求
async def smart_search(request, q: str):
    # 实现限流
    pass
```

---

## 十四、测试与评估

### 14.1 功能测试

**测试用例示例**：

```python
import pytest

class TestSmartSearch:

    def test_simple_query(self):
        """测试简单属性查询"""
        query = "查找所有的 DEM 数据"
        results = search_engine.search(query)
        assert all(r.file_type == 'DEM' for r in results)

    def test_spatial_query(self):
        """测试空间查询"""
        query = "北京附近的数据"
        results = search_engine.search(query)
        assert len(results) > 0

    def test_time_query(self):
        """测试时间查询"""
        query = "最近一周上传的数据"
        results = search_engine.search(query)
        # 验证结果都在一周内
        one_week_ago = datetime.now() - timedelta(days=7)
        assert all(r.created_at >= one_week_ago for r in results)

    def test_combined_query(self):
        """测试组合查询"""
        query = "四川省最近一个月的 DEM 数据"
        results = search_engine.search(query)
        # 验证所有条件都满足
        assert all(r.file_type == 'DEM' for r in results)
```

### 14.2 性能测试

```python
import time

def benchmark_search():
    """性能基准测试"""
    test_queries = [
        "查找 DEM 数据",
        "北京附近的数据",
        "最近一周上传的矢量数据",
        "四川省的地形图"
    ]

    for query in test_queries:
        start = time.time()
        results = search_engine.search(query)
        elapsed = time.time() - start

        print(f"Query: {query}")
        print(f"  Results: {len(results)}")
        print(f"  Time: {elapsed:.2f}s")
        print()
```

### 14.3 准确率评估

**评估指标**：

- **准确率（Precision）**：返回结果中相关的比例
- **召回率（Recall）**：所有相关结果中被返回的比例
- **F1 分数**：准确率和召回率的调和平均

```python
def evaluate_search(test_cases):
    """评估搜索准确率"""
    precisions = []
    recalls = []

    for query, expected_ids in test_cases:
        results = search_engine.search(query)
        result_ids = set(r.id for r in results)

        # 计算准确率和召回率
        relevant = result_ids.intersection(expected_ids)
        precision = len(relevant) / len(result_ids) if result_ids else 0
        recall = len(relevant) / len(expected_ids) if expected_ids else 0

        precisions.append(precision)
        recalls.append(recall)

    avg_precision = sum(precisions) / len(precisions)
    avg_recall = sum(recalls) / len(recalls)
    f1_score = 2 * (avg_precision * avg_recall) / (avg_precision + avg_recall)

    print(f"平均准确率：{avg_precision:.2f}")
    print(f"平均召回率：{avg_recall:.2f}")
    print(f"F1 分数：{f1_score:.2f}")
```

---

## 十五、未来改进方向

### 15.1 功能增强

1. **多轮对话支持**
   - 支持上下文理解
   - 示例：
     - 用户："查找 DEM 数据"
     - 系统：返回结果
     - 用户："只要四川省的"
     - 系统：理解"四川省的"指的是 DEM 数据

2. **地理编码集成**
   - 自动解析中文地名
   - 示例："查找长江流域的数据" → 自动获取长江流域的多边形范围

3. **可视化查询构建**
   - 在地图上框选区域
   - 自动生成空间查询

4. **查询建议与自动补全**
   - 根据用户输入提供建议
   - 示例：输入"查找" → 建议"查找 DEM 数据"、"查找 Shapefile 数据"

### 15.2 性能优化

1. **本地部署嵌入模型**
   - 减少 API 调用延迟
   - 降低使用成本

2. **查询缓存优化**
   - 智能缓存热门查询
   - 缓存过期策略优化

3. **分布式架构**
   - 读写分离
   - 数据库分片

### 15.3 智能化提升

1. **查询意图识别**
   - 分类查询类型（空间、属性、时间）
   - 针对性优化

2. **个性化推荐**
   - 基于用户历史行为推荐数据
   - 相似数据推荐

3. **自动摘要与标签**
   - 为数据生成摘要
   - 自动打标签

---

## 十六、总结

### 16.1 核心技术总结

本系统的智能问答功能整合了以下关键技术：

1. **大语言模型（Qwen3.5）**：理解自然语言，生成 SQL 查询
2. **PostgreSQL + PostGIS**：存储空间数据，执行空间查询
3. **向量嵌入与语义相似度**：实现语义重排序，提升相关性
4. **FastAPI + Vue3**：提供高性能 API 和友好的用户界面

### 16.2 创新点

- ✅ **零学习成本**：用户无需学习 SQL 或 GIS 术语
- ✅ **语义理解**：理解同义词、模糊表达、空间关系
- ✅ **多模态支持**：可扩展支持图像、音频等多模态数据
- ✅ **安全可靠**：SQL 注入防护、错误降级处理

### 16.3 应用价值

- **降低 GIS 使用门槛**：让非专业用户也能轻松查询空间数据
- **提升数据发现效率**：快速找到所需数据，减少搜索时间
- **促进数据共享**：智能化的数据管理促进地质数据共享

---

**文档版本**: v2.0  
**最后更新**: 2025-03-16  
**作者**: 毕业设计项目  
**联系方式**: [你的邮箱]

---

## 附录 A：常用 SQL 速查表

### 空间查询函数

| 函数                           | 说明                 | 示例                                        |
| ------------------------------ | -------------------- | ------------------------------------------- |
| `ST_Intersects(a, b)`          | 判断 a 和 b 是否相交 | `WHERE ST_Intersects(extent, geom)`         |
| `ST_Contains(a, b)`            | 判断 a 是否包含 b    | `WHERE ST_Contains(extent, point)`          |
| `ST_Within(a, b)`              | 判断 a 是否在 b 内   | `WHERE ST_Within(point, polygon)`           |
| `ST_Distance(a, b)`            | 计算 a 和 b 的距离   | `ORDER BY ST_Distance(extent, point)`       |
| `ST_MakeEnvelope(x1,y1,x2,y2)` | 创建矩形范围         | `ST_MakeEnvelope(115.7, 39.4, 117.4, 41.6)` |
| `ST_Buffer(geom, radius)`      | 创建缓冲区           | `ST_Buffer(line, 1000)`                     |
| `ST_Area(geom)`                | 计算面积             | `ST_Area(extent::geography)`                |
| `ST_Centroid(geom)`            | 获取中心点           | `ST_Centroid(extent)`                       |

### 几何构造函数

| 函数                         | 说明           | 示例                                         |
| ---------------------------- | -------------- | -------------------------------------------- |
| `ST_GeomFromText(wkt, srid)` | WKT 转几何对象 | `ST_GeomFromText('POINT(116.4 39.9)', 4326)` |
| `ST_AsText(geom)`            | 几何对象转 WKT | `ST_AsText(extent)`                          |
| `ST_Point(x, y)`             | 创建点         | `ST_Point(116.4, 39.9)`                      |
| `ST_LineFromText(wkt)`       | 创建线         | `ST_LineFromText('LINESTRING(...)')`         |
| `ST_PolyFromText(wkt)`       | 创建面         | `ST_PolyFromText('POLYGON(...)')`            |

---

## 附录 B：常见问题排查

### 问题 1：SQL 生成失败

**现象**：智能搜索返回空结果或报错

**排查步骤**：

1. 检查 API Key 是否正确
2. 查看后端日志中的 SQL 生成过程
3. 验证系统提示词是否清晰
4. 尝试简化查询语句

**解决方案**：

```python
# 检查 LLM 客户端
if not self.client:
    print("LLM client not initialized")
    return self._fallback_search(query)
```

### 问题 2：空间查询结果为空

**现象**：明明有数据，但空间查询返回空

**排查步骤**：

1. 检查 extent 字段是否有值
2. 验证 SRID 是否一致（都使用 4326）
3. 使用 `ST_Intersects` 替代 `ST_Contains`

**解决方案**：

```sql
-- 检查数据
SELECT id, name, ST_AsText(extent) FROM geo_assets;

-- 使用边界框预过滤
SELECT * FROM geo_assets
WHERE extent_min_x <= ? AND extent_max_x >= ?
  AND extent_min_y <= ? AND extent_max_y >= ?;
```

### 问题 3：查询速度慢

**现象**：智能搜索响应时间超过 5 秒

**排查步骤**：

1. 检查是否有空间索引
2. 查看是否启用了缓存
3. 分析 SQL 执行计划

**解决方案**：

```sql
-- 创建空间索引
CREATE INDEX idx_geo_assets_extent ON geo_assets USING GIST (extent);

-- 分析查询
EXPLAIN ANALYZE SELECT ...;
```

---

**END**
