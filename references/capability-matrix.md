# 能力矩阵（引导态专用）

用户 @ 了技能但没给任务、或问"能干嘛/支持哪些格式"时，读本文件输出能力卡片。
措辞原则：**用户视角**（说格式名和动作，不说 pyogrio/GDAL 等实现术语）。

---

## 能力卡片模板（按此结构输出，内容可按需精简）

**一句话定位**：把 GIS/遥感数据从格式 A 转成格式 B，转完给你**核对结论**（行数/字段/坐标系）+ **地图预览**（右侧网页打开，可调样式透明度）。

**矢量 ↔ 矢量**（点线面数据，如 POI、道路、行政区边界）：

| 转换 | 说明 |
|---|---|
| Shapefile ↔ GeoJSON | 最常见。GeoJSON 是网页通用格式；shp 是 ArcGIS/QGIS 通用格式 |
| KML/KMZ → GeoJSON / Shapefile | Google Earth 导出的数据转通用格式 |
| GPX → GeoJSON / Shapefile | GPS 轨迹/ waypoint 转通用格式 |
| CSV（含经纬度列）→ GeoJSON / Shapefile | Excel 表格转成地图数据 |
| GPKG ↔ GeoJSON / Shapefile | GeoPackage 单文件数据库，适合大打包 |
| TopoJSON / WKT → GeoJSON / Shapefile | 小众格式转通用格式 |
| ArcGIS 在线服务 → GeoJSON / Shapefile | 给个服务 URL 就能下载成文件 |

**栅格 ↔ 栅格**（影像/栅格数据，如卫星影像、DEM、土地利用栅格）：

| 转换 | 说明 |
|---|---|
| GeoTIFF ↔ COG | COG 是云优化格式，切片加载快 |
| ENVI(.dat+.hdr) → GeoTIFF / COG | ENVI/ERDAS 处理结果转通用格式 |
| HDF(.hdf/.h5) → GeoTIFF | Landsat/MODIS 等卫星产品转通用格式 |
| IMG(.img) → GeoTIFF / COG | ERDAS 格式转通用格式 |
| 带 世界文件的 PNG/JPG → GeoTIFF | 配准过的图片转标准栅格 |

**顺便能做**（转换时直接带上，不用另开口子）：
- 坐标系转换：UTM / WGS84 / CGCS2000 / Web 墨卡托 互转（转 GeoJSON 自动转 WGS84）
- GCJ-02（高德/腾讯）↔ WGS84 纠偏：POI 表、轨迹数据偏移修正
- 栅格重采样、波段提取/合并

**边界**（这些不做，主动给替代方案）：
- 矢量 → 栅格：需要说明意图（密度图？掩膜？），引导用户说清需求再单独处理
- 栅格 → 矢量：仅"栅格转等值线/面"类需求，需说明阈值参数
- CAD (dwg/dxf) 与 BIM：暂不支持，建议用户先在 QGIS 转 shp 再来
- 坐标纠偏只有经验公式精度（±1~2 米），测绘级精度需求建议用官方工具

**示例**（照着念就能用）：
1. "把 G:\data\xxx.shp 转成 geojson，转换完给我看下地图"
2. "把这份 Landsat 的 HDF 影像转成 GeoTIFF，重投影到 WGS84"
3. "把高德导出的 POI CSV 表转成 shp，顺便纠偏成 WGS84"

**结尾反问**：把文件路径发我（或直接拖文件进来），说一句想转成什么格式就行。

---

## 维护说明
- 新增格式支持时同步更新本表；用户视角措辞（格式名+动作），不写实现细节
- 本表同时是第 0 步判型的格式权威清单，SKILL.md 的格式表与本表保持一致
