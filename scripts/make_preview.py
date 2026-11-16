#!/usr/bin/env python3
"""地图预览生成器：自动分档，用户无感。

用法：
  矢量：python make_preview.py vector <输出GeoJSON路径> [--title "标题"]
  栅格：python make_preview.py raster <输入栅格路径> [--title "标题"] [--max-side 2048]

分档规则（矢量，硬编码）：
  GeoJSON < 10MB 且要素数 < 20000  → 标准档 preview_tmap.html
                                       （腾讯 GL JS 卫星底图，WorkBuddy 本地 key 代理零 key，
                                        数据 WGS84 自动 GCJ-02 显示纠偏，顶栏可切卫星/矢量）
  否则                              → 性能档 preview_maplibre.html
                                       （MapLibre WebGL 扛大数据；天地图底图需 key，
                                        未配 key 时仅数据层）

栅格：
  降采样 PNG（默认最长边 2048px，2%-98% 分位拉伸）+ 按地理范围 ImageOverlay，输出单 HTML
  （天地图底图，key 可用 --tdt-key 传入；默认占位符 = 仅影像层）

输出：<输出GeoJSON同名>_preview.html（矢量）或 <输入栅格同名>_preview.html（栅格）
      并打印 JSON：{"html": 路径, "tier": "tmap|maplibre|raster", ...统计}
模板位置：与本脚本同级的 ../assets/
底图合规：腾讯地图/天地图（白名单源）；禁止接入 OSM/Mapbox/Google 等境外底图。
"""
import base64
import io
import json
import os
import sys

SIZE_LIMIT_MB = 10.0
FEATURE_LIMIT = 20000
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = {
    "tmap": os.path.join(HERE, "..", "assets", "preview_tmap.html"),
    "maplibre": os.path.join(HERE, "..", "assets", "preview_maplibre.html"),
}

DEFAULT_TDT_KEY = "请在 https://console.tianditu.gov.cn 申请天地图 key 后替换本占位符"


def build_vector(geojson_path, title, tdt_key=None):
    with open(geojson_path, "r", encoding="utf-8") as f:
        data_txt = f.read()
    size_mb = os.path.getsize(geojson_path) / 1024 / 1024
    n_feat = 0
    try:
        gj = json.loads(data_txt)
        n_feat = len(gj.get("features", []))
    except Exception as e:
        print(f"[warn] GeoJSON 解析失败，按性能档处理: {e}", file=sys.stderr)
        tier = "maplibre"
    else:
        tier = "tmap" if (size_mb < SIZE_LIMIT_MB and n_feat < FEATURE_LIMIT) else "maplibre"

    with open(TEMPLATES[tier], "r", encoding="utf-8") as f:
        html = f.read()
    html = html.replace("__TITLE__", title)
    html = html.replace("__GEOJSON_DATA__", data_txt)
    if tdt_key is not None:  # 仅性能档（MapLibre/天地图）使用
        html = html.replace("__TDT_KEY__", tdt_key)
    out = os.path.splitext(geojson_path)[0] + "_preview.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    return {"html": os.path.abspath(out), "tier": tier, "geojson_mb": round(size_mb, 2),
            "features": n_feat, "limits": {"size_mb": SIZE_LIMIT_MB, "features": FEATURE_LIMIT}}


def build_raster(raster_path, title, tdt_key, max_side):
    import numpy as np
    import rasterio
    from rasterio.warp import calculate_default_transform, reproject, Resampling

    with rasterio.open(raster_path) as src:
        # 决定预览读法：多波段取前3波段做 RGB，单波段灰度
        bands = min(src.count, 3)
        # 降采样读
        scale = min(max_side / src.width, max_side / src.height, 1.0)
        out_h = max(1, int(src.height * scale))
        out_w = max(1, int(src.width * scale))
        data = src.read(out_shape=(bands, out_h, out_w), resampling=Resampling.bilinear)

        # 转 WGS84 范围（预览用；EPSG:4326 直接用，否则重投影采样）
        if src.crs and src.crs.to_epsg() == 4326:
            west, south, east, north = src.bounds
        else:
            from rasterio.transform import array_bounds
            from rasterio.crs import CRS
            t, w, h = calculate_default_transform(src.crs, CRS.from_epsg(4326),
                                                   src.width, src.height, *src.bounds)
            west, south, east, north = array_bounds(h, w, t)

    # 归一化到 0-255（按 2%~98% 分位拉伸，避免极值压扁）
    arr = data.astype(np.float64)
    out_bands = []
    for i in range(arr.shape[0]):
        band = arr[i]
        valid = band[np.isfinite(band)]
        if valid.size == 0:
            out_bands.append(np.zeros((out_h, out_w), dtype=np.uint8))
            continue
        lo, hi = np.percentile(valid, 2), np.percentile(valid, 98)
        if hi <= lo:
            hi = lo + 1
        b = np.clip((band - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8)
        out_bands.append(b)
    if len(out_bands) == 1:
        rgb = np.stack([out_bands[0]] * 3)
    elif len(out_bands) == 2:
        rgb = np.stack([out_bands[0], out_bands[1], np.zeros_like(out_bands[0])])
    else:
        rgb = np.stack(out_bands[:3])

    # PNG 编码（PIL 若不可用则退回 rasterio 写内存 GTiff→PNG 的简化路径：这里统一用 PIL）
    from PIL import Image
    img = Image.fromarray(rgb.transpose(1, 2, 0), "RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    png_b64 = base64.b64encode(buf.getvalue()).decode()

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{title}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  * {{ box-sizing: border-box; }}
  html, body {{ margin:0; padding:0; height:100%;
    font-family: system-ui, "Segoe UI", "Microsoft YaHei", sans-serif; }}
  .bar {{ height:48px; display:flex; align-items:center; gap:12px; padding:0 16px;
    background:#fff; border-bottom:1px solid #e5e7eb; box-shadow:0 1px 2px rgba(0,0,0,.05); }}
  .bar .title {{ font-size:14px; font-weight:600; color:#111827;
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:40%; }}
  .bar .meta {{ font-size:12px; color:#6b7280; display:flex; gap:8px; align-items:center;
    white-space:nowrap; overflow:hidden; flex:1; }}
  .row {{ display:flex; align-items:center; gap:8px; margin:0; font-size:11px; color:#4b5563; }}
  .row label {{ flex:none; }}
  .row input[type=range] {{ width:110px; height:3px; accent-color:#111827; }}
  .row .val {{ width:34px; text-align:right; color:#9ca3af; font-variant-numeric:tabular-nums; }}
  #map {{ width:100%; height:calc(100vh - 48px); background:#333; }}
</style>
</head>
<body>
<header class="bar">
  <div class="title">{title}</div>
  <div class="meta" id="meta"></div>
  <div class="row"><label>透明度</label>
    <input type="range" id="opacity" min="0" max="100" step="1" value="100"><span class="val" id="opacityv"></span>
  </div>
</header>
<div id="map"></div>
<script>
var TDT_KEY = "{tdt_key}";
var hasKey = TDT_KEY && TDT_KEY.indexOf("请") !== 0 && TDT_KEY.indexOf("PLEASE") === -1 && TDT_KEY !== "";
var map = L.map("map");
if (hasKey) {{
  L.tileLayer("https://t{{s}}.tianditu.gov.cn/vec_w/{{z}}/{{x}}/{{y}}?tk=" + TDT_KEY,
    {{ subdomains:["0","1","2","3","4","5","6","7"], maxZoom:18, attribution:"天地图" }}).addTo(map);
}}
var bounds = [[{south:.6f}, {west:.6f}], [{north:.6f}, {east:.6f}]];
var overlay = L.imageOverlay("data:image/png;base64,{png_b64}", bounds, {{ opacity: 1.0 }}).addTo(map);
map.fitBounds(bounds);
var opEl = document.getElementById("opacity"), opVal = document.getElementById("opacityv");
opEl.addEventListener("input", function () {{
  var v = parseFloat(opEl.value);
  opVal.textContent = v + "%";
  overlay.setOpacity(v / 100);
}});
opVal.textContent = "100%";
var meta = '<span>栅格 {{out_w}}×{{out_h}}</span><span>2%-98% 拉伸</span><span>WGS84</span>';
if (!hasKey) meta += '<span style="color:#b45309">底图未配置 · 仅影像层</span>';
document.getElementById("meta").innerHTML = meta;
</script>
</body>
</html>
"""
    out = os.path.splitext(raster_path)[0] + "_preview.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    return {"html": os.path.abspath(out), "tier": "raster", "preview_px": [out_w, out_h],
            "bounds_wgs84": [round(west, 6), round(south, 6), round(east, 6), round(north, 6)]}


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    mode = sys.argv[1]
    path = sys.argv[2]
    title = "GIS/RS 预览"
    tdt_key = DEFAULT_TDT_KEY
    tdt_key_used = False
    max_side = 2048
    args = sys.argv[3:]
    i = 0
    while i < len(args):
        if args[i] == "--title":
            title = args[i + 1]; i += 2
        elif args[i] == "--tdt-key":
            tdt_key = args[i + 1]; tdt_key_used = True; i += 2
        elif args[i] == "--max-side":
            max_side = int(args[i + 1]); i += 2
        else:
            i += 1

    if mode == "vector":
        result = build_vector(path, title, tdt_key if tdt_key_used else None)
    elif mode == "raster":
        result = build_raster(path, title, tdt_key, max_side)
    else:
        print("mode 必须是 vector 或 raster", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
