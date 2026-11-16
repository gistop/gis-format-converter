# 矢量格式逐格式转换手册

geopandas + pyogrio 路线。每节：读 → 写 → 坑。所有写法在 pyogrio 0.11 + geopandas 1.0（GDAL 3.10）实测过。

## 通用 API 总纲

两条铁律：
1. **转换前摸底，转换后校验**——geopandas 读入就是一张表，先看清楚再动手。
2. **坐标系永远是第一怀疑对象**——结果"位置不对"九成是 CRS 问题，一成是火星坐标（见 gcj02.md）。

```python
import geopandas as gpd
import pyogrio

# 摸底（必做）
pyogrio.list_layers("data.gpkg")      # 多图层文件列出 [(图层名, 几何类型), ...]
gdf = gpd.read_file("输入文件")
len(gdf)                              # 要素数
gdf.crs                               # 坐标系；None = 未标注
gdf.total_bounds                      # [minx, miny, maxx, maxy]
gdf.geom_type.value_counts()          # 几何类型分布
gdf.head()                            # 字段、属性、乱码检查
pyogrio.read_info("输入文件")         # 不读数据的元信息

# 读写（driver= 指定格式；gpkg/gpx 用 layer= 选层）
gdf = gpd.read_file("in.shp", encoding="gbk")
gdf.to_file("out.geojson", driver="GeoJSON")

# 坐标系
gdf = gdf.to_crs("EPSG:4326")         # 重投影
gdf = gdf.set_crs("EPSG:4490")        # 只补标注不换算（crs 为 None 且确定源坐标系时）

# 常见修复
import shapely
gdf["geometry"] = [g if g.geom_type == "MultiPolygon" else shapely.MultiPolygon([g])
                   for g in gdf.geometry]   # Polygon/MultiPolygon 混合写出报错时
gdf["geometry"] = shapely.force_2d(gdf.geometry)  # 去 Z 坐标
gdf = gdf[gdf.geometry.notna()]              # 丢弃空几何
```

常用 EPSG：WGS84=4326，CGCS2000=4490，北京54=4214，西安80=4610，Web 墨卡托=3857。
**GCJ-02/BD-09 不是坐标系**（无 EPSG 码），`to_crs` 无效，走 gcj02.md。

---

## 1. GeoJSON（.geojson）

前端地图的标准格式，规范坐标系 WGS84。

```python
gdf = gpd.read_file("in.geojson")
gdf.to_file("out.geojson", driver="GeoJSON")
```

- 写出前确认 `gdf.crs.to_epsg() == 4326`，不是就先 `to_crs("EPSG:4326")`——前端库普遍忽略 crs 声明，坐标系错了整体偏移。
- `.json` 扩展名也能读（靠内容识别）；产出给前端的文件统一用 `.geojson`。
- Polygon/MultiPolygon 混合写出报错 → 做 Multi 提升（见上文修复）。

## 2. Shapefile（.shp）

ArcGIS/QGIS/政务系统通用交换格式。**国内流传的 shp 属性表大多是 GBK 编码**，乱码占该格式问题的一半。

```python
gdf = gpd.read_file("in.shp")                    # 先直接读
gdf = gpd.read_file("in.shp", encoding="gbk")    # 属性乱码 → 显式 GBK（或 gb18030 超集）
gdf.to_file("out.shp", encoding="utf-8")         # 写 .cpg 标记，别人打开不乱码
```

坑：
- **字段名 10 字节截断**：超长字段名被截断并警告；重要字段先 `rename` 改短。
- datetime 只保留日期（时间丢弃）；字符串最长 254 字符；长文本改用 GPKG。
- 单文件 2GB 上限；大图层用 GPKG。
- shp 是"五件套"（.shp/.shx/.dbf/.prj/.cpg），分发整体拷贝。
- 没有 .prj 时 `gdf.crs` 为 None：确认真实坐标系后 `set_crs`。

## 3. KML / KMZ

Google Earth / 奥维常用。规范强制 WGS84。

```python
# 读
gdf = gpd.read_file("in.kml")
# KMZ 打不开就解压再读：
import zipfile, tempfile, os
with zipfile.ZipFile("in.kmz") as zf:
    kml_name = next(n for n in zf.namelist() if n.lower().endswith(".kml"))
    tmp = tempfile.mkdtemp()
    zf.extract(kml_name, tmp)
gdf = gpd.read_file(os.path.join(tmp, kml_name))

# 写：属性列必须先整理成 Name + Description 两列（不能省）
gdf = gdf.to_crs("EPSG:4326")
out = gdf.rename(columns={"名称": "Name", "描述": "Description"})
out[["Name", "Description", "geometry"]].to_file("out.kml", driver="KML")

# KMZ 写出：写 .kml 后自行 zip
with zipfile.ZipFile("out.kmz", "w", zipfile.ZIP_DEFLATED) as zf:
    zf.write("out.kml", "doc.kml")
```

坑：
- 基础 KML 驱动只读回 `Name`/`Description` 两列 + 几何，**ExtendedData 会被丢弃**（需要就用 ElementTree 自己解析，或 `pyogrio.list_drivers()` 查有无 LIBKML）。
- 写出时多余字段会变成垃圾输出；其他属性拼进 Description。
- 读回列名固定大写 `Name`/`Description`。
- 数据来自高德/腾讯且整体偏移几百米 → 是 GCJ-02，见 gcj02.md。

## 4. GPX

GPS 设备/户外软件（两步路、OruxMaps）格式。强制 WGS84，多图层。

```python
import pyogrio
pyogrio.list_layers("in.gpx")                    # waypoints / routes / tracks / ...
gdf = gpd.read_file("in.gpx", layer="tracks")    # 轨迹线
gdf = gpd.read_file("in.gpx", layer="waypoints") # 点
```

**写：不要用 `to_file(driver="GPX")`**（pyogrio 0.11 + GDAL 3.10 实测列错位 bug：name 值错进 `<ele>`、无报错）。GPX 写出一律用纯 XML 生成：

```python
import xml.etree.ElementTree as ET
import pandas as pd

def gdf_to_gpx(gdf, path):
    """Point→wpt，LineString→rte，MultiLineString→trk（每段一个 trkseg）。
    要求 gdf 已是 WGS84；name/desc/ele 字段写进 GPX。"""
    NS = "http://www.topografix.com/GPX/1/1"
    ET.register_namespace("", NS)
    root = ET.Element("gpx", {"version": "1.1", "creator": "geopandas", "xmlns": NS})

    def meta(row):
        return {k: str(row[k]) for k in ("name", "desc")
                if row.get(k) is not None and not pd.isna(row.get(k))}

    def latlon(c):
        return {"lat": "%.7f" % c[1], "lon": "%.7f" % c[0]}

    def ele_elem(parent, z):
        if z is not None:
            ET.SubElement(parent, "ele").text = "%.2f" % z

    for _, row in gdf.iterrows():
        g, m = row.geometry, meta(row)
        if g.geom_type == "Point":
            w = ET.SubElement(root, "wpt", latlon(g.coords[0]))
            ele_elem(w, g.z if g.has_z else (float(row["ele"]) if row.get("ele") is not None
                                             and not pd.isna(row.get("ele")) else None))
            for k in ("name", "desc"):
                if k in m:
                    ET.SubElement(w, k).text = m[k]
        elif g.geom_type == "LineString":
            rte = ET.SubElement(root, "rte")
            if "name" in m:
                ET.SubElement(rte, "name").text = m["name"]
            for c in g.coords:
                p = ET.SubElement(rte, "rtept", latlon(c))
                ele_elem(p, c[2] if len(c) > 2 else None)
        elif g.geom_type == "MultiLineString":
            trk = ET.SubElement(root, "trk")
            if "name" in m:
                ET.SubElement(trk, "name").text = m["name"]
            for part in g.geoms:
                seg = ET.SubElement(trk, "trkseg")
                for c in part.coords:
                    p = ET.SubElement(seg, "trkpt", latlon(c))
                    ele_elem(p, c[2] if len(c) > 2 else None)
        else:
            print("跳过不支持的几何:", g.geom_type)
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)

# 用法：gdf_to_gpx(gdf.to_crs("EPSG:4326"), "out.gpx")
```

## 5. CSV / 经纬度表

```python
import pandas as pd, geopandas as gpd

# 读：经纬度两列（列名可能是 lon/lng/longitude/x + lat/latitude/y）
df = pd.read_csv("in.csv", encoding="gbk")       # 编码按需：utf-8 / utf-8-sig / gbk
gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df["lng"], df["lat"]), crs="EPSG:4326")
# 或 WKT 文本列
gdf = gpd.GeoDataFrame(df, geometry=gpd.GeoSeries.from_wkt(df["wkt"]), crs="EPSG:4326")

# 写：lon/lat 两列 + BOM（Excel 中文不乱码）
out = pd.DataFrame({"lon": gdf.geometry.x, "lat": gdf.geometry.y})
out = pd.concat([out, gdf.drop(columns="geometry")], axis=1)
out.to_csv("out.csv", index=False, encoding="utf-8-sig")
```

坑：经纬度写反（纬度在前）会"成功"但坐标落海里——`total_bounds` 抽查。

## 6. GeoPackage（.gpkg）

现代通用格式：SQLite 单文件、多图层、无 2GB 限制、无字段名截断——**存档首选**。

```python
pyogrio.list_layers("in.gpkg")
gdf = gpd.read_file("in.gpkg", layer="cities")
gdf.to_file("out.gpkg", layer="cities", driver="GPKG")                  # 新建
rivers.to_file("out.gpkg", layer="rivers", driver="GPKG", mode="a")     # 追加图层
```

- 不带 mode 的写会整体重建文件（原图层全没）。
- 混合 Polygon/MultiPolygon 报错 → Multi 提升。

## 7. TopoJSON

pyogrio 驱动**只读**；写出用 topojson 包（`pip install topojson`）。

```python
gdf = gpd.read_file("in.topojson")          # 读
import topojson as tp
tp.Topology(gdf).to_json("out.topojson")    # 写（自动弧段共享，比 GeoJSON 小数倍）
```

- `.json` 文件头是 `"type": "Topology"` 即 TopoJSON。

## 8. WKT 文本

```python
# 读：一行一个 WKT（不要用 read_csv——几何里的逗号会当分隔符）
with open("in.wkt") as f:
    wkts = [line.strip() for line in f if line.strip()]
gdf = gpd.GeoDataFrame(geometry=gpd.GeoSeries.from_wkt(wkts), crs="EPSG:4326")

# 写：一行一个 WKT
with open("out.wkt", "w") as f:
    f.writelines(w + "\n" for w in gdf.geometry.to_wkt())
```

## 9. ArcGIS REST 服务（ESRI JSON）

```python
gdf = gpd.read_file("ESRIJSON:https://server/arcgis/rest/services/xxx/MapServer/0/query"
                    "?where=1%3D1&outFields=*&outSR=4326&f=json")
```

- URL 必须带 `f=json`；`where=1=1` 写成 `1%3D1`。数据量大有分页，需翻页拼接。

## 10. 格式选择建议

| 目标 | 推荐格式 |
|---|---|
| 网页前端 | GeoJSON（先 to_crs 4326） |
| ArcGIS/QGIS 存档 | GPKG（大）/ SHP（老系统兼容） |
| Google Earth / 奥维 | KML（记得改名 Name） |
| GPS 设备 / 户外软件 | GPX（用 §4 生成函数） |
| Excel / 爬虫 / 数据库 | CSV（lon/lat + utf-8-sig） |
| 减小前端体积 | TopoJSON |
