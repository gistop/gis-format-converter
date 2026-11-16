# GCJ-02 / BD-09 火星坐标纠偏

## 背景：三种坐标系

| 坐标系 | 俗称 | 谁在用 |
|---|---|---|
| WGS84 | 地球坐标 / GPS 坐标 | GPS 设备、OSM、国际地图、GeoJSON/KML/GPX 规范 |
| GCJ-02 | 火星坐标 | 高德、腾讯地图、谷歌中国 —— 国内合法地图数据的强制坐标系 |
| BD-09 | 百度坐标 | 百度地图（GCJ-02 再加密一次） |

**关键认识**：GCJ-02/BD-09 不是坐标系（没有 EPSG 代码），是加密算法。`to_crs` 处理不了它们
（会报错或原样带过），必须用本节的纠偏公式做数值变换。这是纯数学、零依赖，不涉及 GDAL。

## 判别数据是哪个坐标系

| 数据来源 | 坐标系 |
|---|---|
| 高德 / 腾讯地图 API 或导出 | GCJ-02 |
| 百度地图 API 或导出 | BD-09 |
| GPS 轨迹仪 / 手机 GPS 原始记录 | WGS84 |
| OSM / 国际数据源 | WGS84 |
| 政务测绘矢量成果 | 按 WGS84 处理（CGCS2000 与 WGS84 差异可忽略） |

经验判别法：把数据叠到 OSM 底图上，中国境内的点**整体偏移 100~700 米**（境外的点不偏）→ 是 GCJ-02；
再叠加一个固定小量 → BD-09。`gdf.total_bounds` 也能粗判：坐标落在中国境外却是国内业务数据，大概率坐标系错了。

## 纠偏代码（保存为 coord_gcj.py，一次写好反复用）

```python
"""GCJ-02/BD-09 ↔ WGS84 纠偏。纯 numpy 实现，可整几何矢量化。"""
import numpy as np

_A = 6378245.0                  # 克拉索夫斯基椭球长半轴
_EE = 0.00669342162296594323    # 第一偏心率平方

def _delta(lng, lat):
    dlng = (300.0 + lng + 2.0*lat + 0.1*lng*lng + 0.1*lng*lat + 0.1*np.sqrt(np.abs(lng))
            + (20.0*np.sin(6.0*lng*np.pi) + 20.0*np.sin(2.0*lng*np.pi))*2.0/3.0
            + (20.0*np.sin(lng*np.pi) + 40.0*np.sin(lng/3.0*np.pi))*2.0/3.0
            + (150.0*np.sin(lng/12.0*np.pi) + 300.0*np.sin(lng/30.0*np.pi))*2.0/3.0)
    dlat = (-100.0 + 2.0*lng + 3.0*lat + 0.2*lat*lat + 0.1*lng*lat + 0.2*np.sqrt(np.abs(lng))
            + (20.0*np.sin(6.0*lng*np.pi) + 20.0*np.sin(2.0*lng*np.pi))*2.0/3.0
            + (20.0*np.sin(lat*np.pi) + 40.0*np.sin(lat/3.0*np.pi))*2.0/3.0
            + (160.0*np.sin(lat/12.0*np.pi) + 320.0*np.sin(lat*np.pi/30.0))*2.0/3.0)
    return dlng, dlat

def _wgs2gcj(lng, lat):
    dlng, dlat = _delta(lng - 105.0, lat - 35.0)   # 平移基准，不可省
    radlat = lat / 180.0 * np.pi
    magic = 1 - _EE * np.sin(radlat) ** 2
    sqrtmagic = np.sqrt(magic)
    dlat = (dlat * 180.0) / ((_A * (1 - _EE)) / (magic * sqrtmagic) * np.pi)
    dlng = (dlng * 180.0) / (_A / sqrtmagic * np.cos(radlat) * np.pi)
    return lng + dlng, lat + dlat

def _in_china(lng, lat):
    return (lng >= 72.004) & (lng <= 137.8347) & (lat >= 0.8293) & (lat <= 55.8271)

def gcj2wgs(lng, lat):
    """GCJ-02 → WGS84（高德/腾讯数据纠偏），迭代逼近，误差 <0.1 米。"""
    lng = np.atleast_1d(np.asarray(lng, dtype=float))
    lat = np.atleast_1d(np.asarray(lat, dtype=float))
    wlng, wlat = lng.copy(), lat.copy()
    inside = _in_china(lng, lat)                   # 境外坐标不偏移
    for _ in range(6):
        glng, glat = _wgs2gcj(wlng[inside], wlat[inside])
        wlng[inside] += lng[inside] - glng
        wlat[inside] += lat[inside] - glat
    return wlng, wlat

def wgs2gcj(lng, lat):
    """WGS84 → GCJ-02（把标准数据发布到高德/腾讯）。"""
    lng = np.atleast_1d(np.asarray(lng, dtype=float))
    lat = np.atleast_1d(np.asarray(lat, dtype=float))
    out_lng, out_lat = lng.copy(), lat.copy()
    inside = _in_china(lng, lat)
    out_lng[inside], out_lat[inside] = _wgs2gcj(lng[inside], lat[inside])
    return out_lng, out_lat

_X_PI = np.pi * 3000.0 / 180.0

def gcj2bd(lng, lat):
    z = np.sqrt(lng**2 + lat**2) + 0.00002 * np.sin(lat * _X_PI)
    theta = np.arctan2(lat, lng) + 0.000003 * np.cos(lng * _X_PI)
    return z * np.cos(theta) + 0.0065, z * np.sin(theta) + 0.006

def bd2gcj(lng, lat):
    x, y = lng - 0.0065, lat - 0.006
    z = np.sqrt(x**2 + y**2) - 0.00002 * np.sin(y * _X_PI)
    theta = np.arctan2(y, x) - 0.000003 * np.cos(x * _X_PI)
    return z * np.cos(theta), z * np.sin(theta)
```

## 接到 GeoDataFrame 上（配合 shapely）

```python
import numpy as np
import shapely
from coord_gcj import gcj2wgs, wgs2gcj, gcj2bd, bd2gcj

def apply_coord(gdf, fn):
    """fn(lng, lat) -> (lng, lat)，矢量化作用于整列几何。"""
    def f(x, y):
        ox, oy = fn(np.asarray(x, dtype=float), np.asarray(y, dtype=float))
        return np.asarray(ox), np.asarray(oy)
    return gdf.set_geometry([shapely.ops.transform(f, g) for g in gdf.geometry])

# 用法：gdf = apply_coord(gdf, gcj2wgs)   # 高德/腾讯 → WGS84，之后照常 to_file
```

## 方向速查

| 你有的数据 | 你要的坐标 | 用的函数 |
|---|---|---|
| 高德/腾讯 (GCJ-02) | WGS84 | `gcj2wgs` |
| WGS84 | 高德/腾讯 | `wgs2gcj` |
| 百度 (BD-09) | WGS84 | `bd2gcj` 后再 `gcj2wgs` |
| WGS84 | 百度 | `wgs2gcj` 后再 `gcj2bd` |

## 典型完整流程

**高德导出的 POI（CSV，GBK，GCJ-02）→ 前端 GeoJSON（WGS84）**：

```python
import pandas as pd
import geopandas as gpd
from coord_gcj import gcj2wgs

df = pd.read_csv("pois.csv", encoding="gbk")
gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df["lng"], df["latitude"]), crs="EPSG:4326")
gdf = apply_coord(gdf, gcj2wgs)
gdf.to_file("pois_wgs84.geojson", driver="GeoJSON")
```

## 精度与注意

- 公式为公开经验拟合：正向（wgs2gcj/gcj2bd）直接套公式，反向（gcj2wgs）迭代逼近，误差 <0.1 米；整体偏移量级 100~700 米（北京约 550 米）。
- 若纠偏后偏移达到 100 公里级，说明方向选反了或源数据是经纬度互换——先 `gdf.total_bounds` 核对。
- 境外坐标自动跳过（公式只在境内有意义）。
- 不用于测绘用途。
