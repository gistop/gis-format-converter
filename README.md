# GIS数据格式转换（gis-format-converter）

> 把 GIS/遥感数据从格式 A 转成格式 B，转完给你**核对结论** + **地图预览**。

一个 [WorkBuddy](https://www.workbuddy.cn) 技能：矢量与栅格数据的格式转换（矢量↔矢量、栅格↔栅格）。转换后对话流输出要素数/字段/坐标系核对表，并在网页地图上预览成果（卫星底图、图层样式与透明度实时可调）。

## 功能特性

- **固定流程**：摸底 → 转换 → 校验 → 预览，每步有明确产物，杜绝"转完不看结果"
- **自动重投影**：GeoJSON 强制 WGS84；UTM / CGCS2000 / Web 墨卡托互转
- **坐标纠偏**：GCJ-02（高德/腾讯）↔ WGS84，POI 表/轨迹偏移修正
- **栅格处理**：重采样、波段提取/合并
- **核对结论**：转换后对话流给行数/字段/坐标系/范围对照表
- **地图预览**：卫星底图自动分档——轻量数据走腾讯地图 GL JS，大数据（≥10MB 或 ≥2 万要素）自动切 MapLibre WebGL；顶栏「图层样式」面板支持点/线/面分区调颜色与透明度，栅格预览带透明度滑杆
- **引导态**：@ 技能但没说需求时，先输出能力矩阵卡片再反问，普通用户零门槛

## 支持格式

**矢量**（geopandas + pyogrio）：GeoJSON、Shapefile、KML/KMZ、GPX、CSV（经纬度表）、GPKG、TopoJSON、WKT、ArcGIS REST

**栅格**（rasterio + rioxarray）：GeoTIFF、COG、ENVI（.dat+.hdr）、HDF（.hdf/.h5）、IMG、PNG/JPG（世界文件配准）

## 安装

**WorkBuddy 内（推荐）**：技能市场搜索「GIS/RS数据格式转换」一键安装；或把本仓库的 `gis-format-converter/` 目录整体拷入 `~/.workbuddy/skills/`，重启即可。

**其他 Agent 平台**：`SKILL.md` 为通用 Agent Skills 格式，将目录拷入平台技能路径并按其约定加载，详见下方兼容性说明。

## 使用示例

```text
把这个 shp 转成 GeoJSON，转换完给我看下地图
把 Landsat 的 HDF 影像转成 GeoTIFF，重投影到 WGS84
把高德导出的 POI 表转成 shp，顺便纠偏成 WGS84
```

## 兼容性说明

| 能力 | WorkBuddy 内 | 其他平台 |
|---|---|---|
| 格式转换核心（转换/重投影/纠偏/重采样） | ✅ 开箱即用 | ✅ 相同（需 Python 环境） |
| 环境自检 + 国内镜像补装 | ✅ `scripts/env_check.py` 自动 | ✅ 相同 |
| 地图预览 · 腾讯卫星底图 | ✅ 运行时本地代理，零 key | ⚠️ 需自行申请腾讯位置服务 key，替换 `assets/preview_tmap.html` 中的代理占位符 |
| 成果交付（文件卡片 + 右侧预览） | ✅ present_files 流程 | ⚠️ 按平台习惯改为输出文件路径 |

**依赖**：Python 3.9+；geopandas + pyogrio（矢量）、rasterio + rioxarray（栅格）。首次使用运行 `python scripts/env_check.py` 自动探测缺失包并走清华镜像安装。

## 目录结构

```text
gis-format-converter/
├── SKILL.md                    # 主流程：判型 → 环境 → 摸底 → 转换 → 校验 → 预览
├── scripts/
│   ├── env_check.py            # 四件套环境探测，--fix 自动镜像补装
│   └── make_preview.py         # 预览生成：矢量自动分档 + 栅格降采样叠加
├── assets/
│   ├── preview_tmap.html       # 标准档模板（腾讯卫星底图 + 图层样式面板）
│   └── preview_maplibre.html   # 性能档模板（MapLibre WebGL，扛大数据）
└── references/
    ├── capability-matrix.md    # 能力矩阵（引导态输出源）
    ├── vector-formats.md       # 矢量格式逐格式手册
    ├── raster-formats.md       # 栅格格式逐格式手册
    ├── gcj02.md                # 火星坐标纠偏说明
    └── install.md              # 环境安装指南（conda/pip 分支）
```

## License

[MIT](LICENSE) © 地理精灵
