---
name: gis-format-converter
display_name: GIS数据格式转换
display_name_en: GIS/RS Format Converter
description: GIS/RS 数据格式转换：矢量与栅格数据的格式转换（矢量↔矢量、栅格↔栅格，不做矢量↔栅格互转）。矢量（GeoJSON、Shapefile、KML/KMZ、GPX、CSV、GPKG、TopoJSON、WKT、ArcGIS REST），栅格（GeoTIFF、COG、ENVI、HDF、IMG、PNG/JPG 世界文件），支持重投影（WGS84/CGCS2000/UTM/3857）、栅格重采样、波段提取合并、GCJ-02 纠偏，转换后给行数/字段/坐标核对结论并生成地图预览（卫星底图/MapLibre 自动分档，样式透明度可调）。凡用户提到 shp、geojson、kml、gpkg、gpx、tif、tiff、cog、envi、hdf、img、dem、遥感影像、卫星数据、波段、坐标系转换、火星坐标、重投影、ArcGIS/QGIS/ENVI/ERDAS 数据处理、矢量/栅格格式转换等场景，即使没说"格式转换"也应使用本技能。
description_zh: GIS/遥感数据格式转换：GeoJSON、SHP、KML、GPKG、GPX、GeoTIFF、COG、ENVI、HDF、IMG 等，含重投影、重采样、波段处理与 GCJ-02 纠偏，转换后自动出地图预览。
description_en: Convert GIS/RS vector and raster formats (GeoJSON, SHP, KML, GPKG, GPX, GeoTIFF, COG, ENVI, HDF, IMG) with reprojection, resampling, band handling, GCJ-02 correction, and automatic map preview.
examples_zh:
- "把这个 shp 转成 GeoJSON，转换完给我看下地图"
- "把 Landsat 的 HDF 影像转成 GeoTIFF，重投影到 WGS84"
- "把高德导出的 POI 表转成 shp，顺便纠偏成 WGS84"
examples_en:
- "Convert this shapefile to GeoJSON and show it on a map"
- "Reproject this Landsat HDF scene to WGS84 GeoTIFF"
- "Turn this UTM land-use raster into CGCS2000 COG"
version: 1.0.0
author: "地理精灵"
agent_created: true
---

# GIS数据格式转换

用 **geopandas + pyogrio（矢量）/ rasterio + rioxarray（栅格）** 完成 GIS/遥感数据格式转换。
转换的正确性和格式覆盖由 GDAL 保证，本 skill 不自研转换逻辑；核心价值是：摸底 → 转换 → 校验 → 预览的固定流程。

## 工作流程（按序执行，禁止跳步）

### 引导态（前置分支）：用户没给具体任务时，先引导、不进流程

**触发条件**（满足任一即进入，不执行后续第 0-5 步）：
- 消息里只有 @本技能，没有转换任务描述
- 用户在问"能干嘛 / 支持哪些格式 / 怎么用 / 帮助"

**动作**：读 `references/capability-matrix.md`，按其模板输出能力卡片，结构固定四段：
1. 一句话定位（"把 GIS/遥感数据从格式 A 转成格式 B，转完给核对结论 + 地图预览"）
2. 支持格式矩阵（矢量、栅格两张表，用户视角措辞）
3. 3 个可照着念的示例
4. 结尾反问："把文件路径发我（或直接拖文件进来），说一句想转成什么格式就行。"

用户答完后，按正常工作流（第 0 步起）执行。

### 第 0 步：数据类型判定

按输入扩展名/用户描述分两条线：

| 线 | 典型格式 | 走 |
|---|---|---|
| 矢量 | shp/geojson/kml/kmz/gpx/gpkg/csv/topojson/wkt/ArcGIS URL | 矢量流程（第 2-4 步 + vector-formats.md） |
| 栅格 | tif/tiff/cog/dat+hdr/hdf/h5/img/png+pgw/jpg+jgw | 栅格流程（第 2-4 步 + raster-formats.md） |
| 混合 | 都有 | 分别处理，最后统一汇报 |

### 第 1 步：环境检测（先探测，缺啥装啥，禁止盲目全量安装）

```bash
python scripts/env_check.py          # 探测四件套：geopandas/pyogrio/rasterio/rioxarray
```

- 全部 `OK` → 直接进第 2 步。
- 有缺失 → 读 `references/install.md`：**pip 一律走清华镜像**（`-i https://pypi.tuna.tsinghua.edu.cn/simple`），conda 环境优先 conda-forge（也走国内镜像）；装完**必须复检**再继续。
- 提示 conda 环境时注意：pip/conda 混装是 Windows DLL 报错的头号来源，能用 conda 装就别 pip。

### 第 2 步：摸底输入（必做，不要跳过）

**矢量**（详细 API 见 references/vector-formats.md 开头总纲）：

```python
import geopandas as gpd, pyogrio
pyogrio.list_layers("输入文件")     # 多图层文件（gpkg/gpx/kml/HDF 矢量层）必做
gdf = gpd.read_file("输入文件")
len(gdf); gdf.crs; gdf.total_bounds; gdf.geom_type.value_counts(); gdf.head()
```

**栅格**（详细 API 见 references/raster-formats.md 开头总纲）：

```python
import rasterio
with rasterio.open("输入文件") as src:
    src.crs; src.count; src.width, src.height; src.res; src.dtypes; src.nodata
    src.subdatasets      # HDF/NetCDF 等多子数据集格式必做，先列再选层
```

要点：
- 坐标系永远是第一怀疑对象：`crs` 为 None 时先确认真实坐标系再 `set_crs`，不要瞎猜。
- 中文属性乱码（shp/csv 国内常态）→ `encoding="gbk"`。
- 栅格 nodata 是第二怀疑对象：转换前后都要检查 nodata 是否保留。

### 第 3 步：执行转换

- **矢量**：`gpd.read_file` 进 → 处理（重投影 `to_crs`、纠偏见 gcj02.md、几何修复）→ `to_file(driver=)` 出。逐格式用法和坑查 `references/vector-formats.md` 对应小节。
- **栅格**：`rasterio.open` 读 → 处理（重投影 `rioxarray.rio.reproject`、重采样、波段提取/合并）→ 按 profile 写出。逐格式用法和坑查 `references/raster-formats.md` 对应小节。
- 特殊坑速查：GPX 写出禁用 `to_file`（列错位 bug），用 vector-formats.md §4 的纯 XML 函数；COG 优先 rio-cogeo；HDF 必须 subdatasets 选层；分类栅格重采样必须 `Resampling.nearest`。

### 第 4 步：校验输出（必做，结果进对话流）

读回输出文件逐项核对，并在对话流给用户**核对结论表**（这是本 skill 的固定交付物）：

```markdown
## 转换结论
| 项目 | 输入 | 输出 | 核对 |
|---|---|---|---|
| 要素数/像素数 | 1234 个要素 | 1234 个要素 | ✅ 一致 |
| 字段/波段 | 12 个字段（列出） | 12 个字段 | ✅ 无丢失 |
| 坐标系 | EPSG:4490 | EPSG:4326 | ✅ 已重投影 |
| 范围 | [73,18,135,54] | [73,18,135,54] | ✅ 落在预期区域 |
| 乱码/属性抽查 | 字段"名称" | 正常中文 | ✅ |
| nodata（栅格） | -9999 | -9999 | ✅ 保留 |
```

校验代码（矢量 assert 要素数一致 + crs + bounds + head 抽查；栅格 assert count/crs/nodata + 降采样读 min/max/mean），写法见两份 formats.md 的"校验"小节。任何 `[Warning]` 逐条看懂再交付。

### 第 5 步：地图预览（对话流给结论，右侧网页出图）

转换校验通过后，生成网页地图预览并用 present_files 打开：

```bash
# 矢量：输出为 GeoJSON（或先转一份临时 GeoJSON，WGS84）
python scripts/make_preview.py vector "输出.geojson" --title "文件名：N 个要素"

# 栅格：
python scripts/make_preview.py raster "输出.tif" --title "文件名：3 波段"
```

- **分档自动完成**（用户无感）：GeoJSON < 10MB 且要素数 < 20000 → 标准档（腾讯 GL JS 卫星底图，WorkBuddy 本地代理零 key，数据自动 GCJ-02 显示纠偏）；≥ 10MB 或超阈值 → 性能档（MapLibre WebGL 扛大数据，天地图底图需 key，未配 key 时仅数据层）。模板在 assets/。
- 栅格预览：降采样 PNG（默认最长边 2048px，2%-98% 分位拉伸）+ 按地理范围 ImageOverlay 摆放。
- **底图合规（红线）**：标准档走腾讯 GL JS 卫星底图（WorkBuddy 本地 key 代理，前端零 key，开箱即显）；性能档/栅格档用天地图（key 为占位符，未替换时仅数据层，不阻塞）。**禁止**接入 OSM/Mapbox/Google/ArcGIS Online 等境外底图源。数据坐标默认 WGS84，标准档模板内自动做 GCJ-02 显示纠偏（仅显示层，输出文件不动）。
- 生成后把 HTML 路径交给 present_files 在右侧打开。
- **交付动作（必做）**：预览打开后，再调用一次 present_files 呈现**转换产物本体**（geojson/shp/gpkg/tif 等），让用户拿到显性的文件卡片（可打开/另存），不要只在文字里报路径。输出文件一律写在**输入文件同目录**（同名换扩展名），方便用户寻找。

## 支持矩阵

**矢量**（详见 references/vector-formats.md）：

| 格式 | driver= | 读写 | 关键限制 |
|---|---|---|---|
| GeoJSON | GeoJSON | 读写 | 前端用前转 4326 |
| Shapefile | ESRI Shapefile | 读写 | 字段名 10 字节；2GB；GBK 乱码常发 |
| KML/KMZ | KML | 读写(受限) | 强制 WGS84；属性先整理成 Name/Description |
| GPX | （纯 XML 写出） | 读✓ 写⚠ | 写出禁用 to_file（bug），用 §4 函数 |
| CSV | （pandas） | 读写 | 几何靠 points_from_xy / wkt |
| GPKG | GPKG | 读写 | 多图层；mode="a" 追加 |
| TopoJSON | TopoJSON | 只读 | 写出用 topojson 包 |
| WKT | （shapely） | 读写 | from_wkt / to_wkt |
| ESRIJSON | ESRIJSON | 只读 | URL 带 f=json |

**栅格**（详见 references/raster-formats.md）：

| 格式 | 说明 | 关键点 |
|---|---|---|
| GeoTIFF | 事实标准 | deflate 压缩；nodata 显式写回 |
| COG | 网页发布推荐 | rio-cogeo 最稳；COPY_SRC_OVERVIEWS 全大写 |
| ENVI (.dat/.hdr) | 认 .dat 打开 | .dat+.hdr 成对；转出单 .tif 即可 |
| HDF/HDF-EOS | MODIS 等 | 必须 subdatasets 选层；Sinusoidal 用 rioxarray 重投影 |
| IMG | ERDAS | 常规 profile 改写 |
| PNG/JPG+世界文件 | 轻量发布 | .pgw/.jgw 同目录自动解析 |

**通用能力**：CRS 重投影（4326/4490/3857/UTM…）、栅格重采样（nearest/bilinear，分类必 nearest）、波段提取/合并、GCJ-02/BD-09 纠偏（references/gcj02.md）。

## 特殊场景索引

| 场景 | 处理方式 | 详见 |
|---|---|---|
| shp/CSV 属性乱码 | `encoding="gbk"` | vector-formats.md §2/§5 |
| 高德/腾讯/百度数据偏移几百米 | GCJ-02/BD-09 纠偏 | gcj02.md |
| 分类栅格重投影后出现奇怪值 | `Resampling.nearest` | raster-formats.md §7 |
| MODIS HDF 打不开/空数据 | 先 `src.subdatasets` 选层 | raster-formats.md §4 |
| 大影像内存不足 | block_windows 分块 / Window 裁剪 | raster-formats.md §1 |
| 多图层 gpkg 合并/拆分 | `layer=` + `mode="a"` | vector-formats.md §6 |

## 能力边界（对用户要诚实）

- 需要网络安装依赖（国内镜像；wheel 内置 GDAL，无需编译）；离线机器无解，除非已有环境。
- 栅格格式转换以 GDAL 驱动支持为准；私有/加密格式（如某些国产软件专有格式）不支持，建议先在源软件导出为通用品。
- 预览底图需天地图 key（占位符机制，无 key 时数据层照常显示）；境外区域数据建议直接用数据层查看。
- CAD（dwg/dxf）完整解析、数据库直连超范围，建议 QGIS/ogr2ogr。
- 纠偏公式为公开经验拟合（误差 <0.1 米），不用于测绘用途。
