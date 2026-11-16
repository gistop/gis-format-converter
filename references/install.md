# 安装指南（国内镜像优先）

技术栈四件套：**geopandas + pyogrio（矢量）、rasterio + rioxarray（栅格）**。
rasterio/pyogrio 的 wheel 内置 GDAL 二进制，无需编译，macOS/Linux/Windows 通用。

## 安装铁律（按序执行）

1. **先探测，缺啥装啥**——运行 `scripts/env_check.py`，只安装缺失或损坏的包，不要盲目全量安装。
2. **pip 安装一律走国内镜像**（清华 TUNA）：

```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple geopandas pyogrio rasterio rioxarray
```

3. **装完必须复检**——再跑一次 `scripts/env_check.py`，全部 `OK` 才进入转换流程。

## venv 方式（推荐，干净隔离）

```bash
python3 -m venv ~/.venvs/gis
~/.venvs/gis/bin/pip install -i https://pypi.tuna.tsinghua.edu.cn/simple geopandas pyogrio rasterio rioxarray
```

之后所有命令用 `~/.venvs/gis/bin/python` 执行。Windows（Git Bash）路径同理；PowerShell 下是 `~/.venvs/gis/Scripts/python.exe`。

## 平台说明

### Windows
- win_amd64 官方 wheel 齐全，pip 直接装通常一次成功。
- **经典坑**：pip 显示已安装但 `import rasterio` 报 DLL 加载失败——多为 pip/conda 混装或 PATH 里有残留 GDAL。解法：卸载后重装（`pip uninstall rasterio -y && pip install -i 镜像 rasterio`），仍失败就换 venv 隔离。
- 若机器在用 conda 且环境里有 GDAL：**优先 conda 装**（`conda install -c conda-forge geopandas pyogrio rasterio rioxarray`，走 conda 国内镜像见下），避免 pip/conda 混装 DLL 冲突。

### macOS
- 系统 Python 直接 pip 可能报 `externally-managed-environment`（PEP 668），用 venv 绕开。
- arm64（Apple Silicon）wheel 齐全，无需编译。

### Linux
- venv + pip 即可；wheel 不编译，极少缺系统依赖。

## conda 国内镜像（仅 conda 用户需要）

```bash
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge
conda install geopandas pyogrio rasterio rioxarray
```

## 常用备选镜像

| 镜像 | pip 参数 |
|---|---|
| 清华 TUNA（默认） | `-i https://pypi.tuna.tsinghua.edu.cn/simple` |
| 阿里云 | `-i https://mirrors.aliyun.com/pypi/simple/` |
| 中科大 | `-i https://mirrors.ustc.edu.cn/pypi/simple` |

## 版本要求

| 包 | 最低版本 | 说明 |
|---|---|---|
| geopandas | 0.14 | pyogrio 作为 IO 引擎所需 |
| pyogrio | 0.10 | 建议 0.10+，0.11.x 实测稳定 |
| rasterio | 1.3 | 1.3.10+ 对 COG 写出支持好 |
| rioxarray | 0.15 | 依赖 xarray，重投影用 |

## 可选附加

```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple topojson   # 仅 TopoJSON 写出（纯 Python，很小）
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple matplotlib # 仅栅格图例渲染备选
```

## 装完之后

回到 SKILL.md 工作流第 1 步复检，通过后继续。
