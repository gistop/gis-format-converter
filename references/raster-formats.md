# 栅格/遥感格式逐格式转换手册

rasterio + rioxarray 路线。每节：读 → 写 → 坑。写法基于 rasterio 1.3.x + rioxarray 0.15+（内置 GDAL）实测体系。

## 通用 API 总纲

```python
import rasterio
import rioxarray  # 导入即注册到 xarray

# 摸底（必做）
with rasterio.open("in.tif") as src:
    print(src.crs)             # 坐标系
    print(src.count)           # 波段数
    print(src.width, src.height)  # 尺寸（列数、行数）
    print(src.dtypes)          # 数据类型
    print(src.bounds)          # 范围
    print(src.res)             # 分辨率
    print(src.descriptions)    # 波段描述（多光谱常见）
    print(src.nodata)          # 无效值标记
    print(src.tags())          # 元数据

rasterio.drivers.raster_driver_registry()  # 需要时查看驱动
```

两条铁律（与矢量一致）：
1. **转换前摸底，转换后校验**——先看 CRS、波段、分辨率、nodata 再动手。
2. **nodata 是栅格的第一怀疑对象**——转换后"背景变黑/变白"，九成是 nodata 丢失或没写。

---

## 1. GeoTIFF（.tif / .tiff）

遥感事实标准。读写都稳。

```python
import rasterio

with rasterio.open("in.tif") as src:
    profile = src.profile.copy()           # 继承元数据模板
    data = src.read()                      # (bands, rows, cols) 数组

profile.update(driver="GTiff", count=data.shape[0],
               dtype=data.dtype, compress="deflate", predictor=2)
with rasterio.open("out.tif", "w", **profile) as dst:
    dst.write(data)
    dst.descriptions = src.descriptions    # 波段描述别丢
    dst.nodata = src.nodata                # nodata 别丢
```

坑：
- **nodata 必须显式写回**：`profile` 里带了通常没事，但 dtype 变化时（如 float→int）nodata 值可能失效，要同步更新。
- 巨大影像别 `src.read()` 全量进内存：用 `src.block_windows()` 分块或 `rasterio.windows.Window` 裁剪处理。
- 压缩选择：`deflate`（无损，通用）> `lzw`；`jpeg` 有损慎用。

## 2. COG（Cloud Optimized GeoTIFF）

云优化格式：内嵌金字塔 + tile 化，网页加载快。**网页预览/发布的推荐输出**。

```python
import rasterio
from rasterio.shutil import copy as rio_copy

# 方法一：rasterio shutil（源规范时最简单）
rio_copy("in.tif", "out_cog.tif", driver="GTiff",
         compress="deflate", COPY_SRC_OVERVIEWS=YES, TILED=YES, BLOCKXSIZE=512, BLOCKYSIZE=512)
```

```python
# 方法二：两步法（源没有金字塔时必走这条）
import rasterio
from rasterio.enums import Resampling

# 先建金字塔再 COPY_SRC_OVERVIEWS
with rasterio.open("in.tif") as src:
    # 1) 重写为 tiled tif
    ...
# 推荐直接用 rio-cogeo 工具（pip 装）：
# pip install rio-cogeo
# rio cogeo create in.tif out_cog.tif --cog-profile deflate
```

坑：
- `COPY_SRC_OVERVIEWS=YES` 必须全大写（GDAL Python 绑定要求，小写无效但不报错）。
- 无 pyramid 的源直接 copy 出来的不是合法 COG，网页加载照样慢——用 rio-cogeo 最稳。

## 3. ENVI（.dat/.hdr 分离头文件）

遥感经典格式。**转换时认 .dat（数据文件），.hdr 是它的头文件，两者必须成对存在**。

```python
with rasterio.open("in.dat") as src:      # 用 .dat 或 .img 打开，别直接开 .hdr
    data = src.read()
    profile = src.profile.copy()

profile.update(driver="GTiff", compress="deflate")
with rasterio.open("out.tif", "w", **profile) as dst:
    dst.write(data)
```

坑：
- 打开时用**数据文件路径**（.dat/.img），rasterio 自动找同目录 .hdr。
- 转出后分发单个 .tif 即可（头文件信息已内嵌）；反向转成 ENVI 时会自动生成 .dat + .hdr 一对。
- BSQ/BIL/BIP 存储顺序由 GDAL 处理，无需手动干预。

## 4. HDF-EOS / HDF4（.hdf，MODIS 等产品）

rasterio/GDAL 支持读，但 **pyogrio wheel（GDAL 3.x）默认编译含 HDF4 驱动；rasterio wheel 同样内置**。子数据集结构是核心概念。

```python
import rasterio

with rasterio.open("MOD021KM.A2026.hdf") as src:
    print(src.subdatasets)    # 列出子数据集：每个是一个可单独打开的"虚拟文件路径"
    # 形如 ['HDF4_EOS:EOS_GRID:"file.hdf":MOD_Grid_...:band_1', ...]

# 打开需要的子数据集
with rasterio.open(src.subdatasets[0]) as sub:
    data = sub.read(1)
    profile = sub.profile.copy()

profile.update(driver="GTiff")
with rasterio.open("band1.tif", "w", **profile) as dst:
    dst.write(data)
```

坑：
- **必须先 `subdatasets` 再选层**，直接 read 主文件会报错或拿到空数据（与矢量的 `list_layers` 同思路）。
- MODIS 的 Sinusoidal 投影（SINUSOIDAL）转 EPSG:4326 用 rioxarray 重投影（见下）。
- HDF5（.h5，部分新产品）同理：`subdatasets` 列出后逐个处理。

## 5. IMG（.img，ERDAS Imagine）

```python
with rasterio.open("in.img") as src:
    data = src.read()
    profile = src.profile.copy()
profile.update(driver="GTiff", compress="deflate")
with rasterio.open("out.tif", "w", **profile) as dst:
    dst.write(data)
```

- 老数据常见 .rrd 金字塔伴随文件，转换后不需要带走（GeoTIFF 内嵌）。

## 6. PNG / JPG（普通图像带地理参考）

GDAL 世界文件机制：.png + .pgw / .jpg + .jgw（世界文件）= 有地理参考的图像。

```python
# 带 .pgw 的 PNG → GeoTIFF
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS

with rasterio.open("in.png") as src:     # 读像素
    data = src.read()
    # 世界文件给的是仿射参数，rasterio 打开 png+pgw 会自动带上 transform
```

- rasterio 打开带世界文件的图像，transform 自动解析（前提：同目录同名 .pgw/.jgw 存在）。
- 无任何地理参考的纯图片：地理信息需用户口头给（范围/CRS），用 `from_bounds` 手工构造 transform 后写成 GeoTIFF。

## 7. 重投影（栅格版 to_crs）

rioxarray 是栅格重投影/裁剪最顺手的方式：

```python
import rioxarray
from rasterio.crs import CRS

rds = rioxarray.open_rasterio("in.tif")
rds_4326 = rds.rio.reproject("EPSG:4326")          # 重投影 + 自动重采样
rds_4326.rio.to_raster("out_4326.tif")

# 指定重采样方法（分类数据必须用最近邻，防止标签值被平均）
from rasterio.enums import Resampling
rds_4326 = rds.rio.reproject("EPSG:4326", resampling=Resampling.nearest)

# 重采样到指定分辨率
rds_30m = rds.rio.reproject(rds.rio.crs, resolution=0.0002778)   # ~30米
```

坑：
- **分类/标签波段必须 `Resampling.nearest`**（土地利用分类等），双线性会把类别平均成不存在的值。
- 连续数据（DEM、反射率）默认双线性没问题。
- 多波段一次性重投影，各波段共用同一网格，天然对齐。

## 8. 波段提取与合并

```python
# 提取单波段
with rasterio.open("in.tif") as src:
    band4 = src.read(4)
    profile = src.profile.copy()
profile.update(count=1)
with rasterio.open("band4.tif", "w", **profile) as dst:
    dst.write(band4, 1)

# 合并多波段（真彩色合成等）
import numpy as np
bands = []
for f in ["b4.tif", "b3.tif", "b2.tif"]:
    with rasterio.open(f) as src:
        bands.append(src.read(1))
        ref = src.profile
ref.update(count=3)
with rasterio.open("rgb.tif", "w", **ref) as dst:
    for i, b in enumerate(bands, 1):
        dst.write(b, i)
```

- 合并前核对各波段 **crs、transform、尺寸必须一致**（不一致先统一重投影/重采样到参考网格）。

## 9. 格式选择建议（转给谁用）

| 目标 | 推荐格式 |
|---|---|
| 网页预览 / 云端发布 | COG（金字塔内嵌，加载快） |
| GIS 软件存档 | GeoTIFF + deflate 压缩 |
| 老系统兼容 | IMG / ENVI |
| 普通展示 | PNG/JPG + 世界文件 |
| 减小体积 | deflate/LZW 无损压缩；容许有损再考虑 jpeg |

## 10. 栅格校验（转换后必做）

```python
with rasterio.open("out.tif") as dst:
    assert dst.count == 期望波段数
    assert dst.crs == 期望 CRS                # rasterio.crs.CRS.from_epsg(4326)
    assert dst.nodata == 期望nodata 或已处理
    assert dst.width > 0 and dst.height > 0
    # 抽样核对数值
    import numpy as np
    arr = dst.read(1, out_shape=(1, 256, 256))  # 降采样读一口看看
    print(arr.min(), arr.max(), arr.mean())
```
