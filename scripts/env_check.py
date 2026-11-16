#!/usr/bin/env python3
"""环境探测：检查 GIS/RS 四件套（geopandas/pyogrio/rasterio/rioxarray）。

用法：python env_check.py [--fix]
  --fix  输出缺失包后自动用清华镜像安装（pip），装完自动复检。

逻辑：
  1. 逐包 import + 版本探测（装过 != 能用，import 成功才算数）
  2. 输出 JSON：{"python": ..., "is_conda": ..., "pkgs": {name: {"ok", "ver", "err"}}, "missing": [...]}
  3. --fix 时只装 missing 里的包（国内镜像优先），再复检一次
"""
import json
import subprocess
import sys

MIRROR = "https://pypi.tuna.tsinghua.edu.cn/simple"
PKGS = {
    "geopandas": "0.14",
    "pyogrio": "0.10",
    "rasterio": "1.3",
    "rioxarray": "0.15",
}


def probe():
    result = {"python": sys.version.split()[0], "is_conda": None, "pkgs": {}, "missing": []}
    try:
        import os
        result["is_conda"] = os.path.exists(os.path.join(sys.prefix, "conda-meta"))
    except Exception:
        result["is_conda"] = False
    for name, min_ver in PKGS.items():
        try:
            mod = __import__(name)
            ver = getattr(mod, "__version__", "unknown")
            result["pkgs"][name] = {"ok": True, "ver": ver, "min": min_ver}
        except Exception as e:
            result["pkgs"][name] = {"ok": False, "ver": None, "err": str(e).splitlines()[0][:200], "min": min_ver}
            result["missing"].append(name)
    return result


def fix(result):
    """只装缺失包，国内镜像。conda 环境下提示改用 conda 但仍尝试 pip（wheel 通常兼容）。"""
    if not result["missing"]:
        print("Nothing to fix.")
        return
    pkgs = " ".join(result["missing"])
    if result["is_conda"]:
        print(f"[hint] 当前是 conda 环境（{sys.prefix}）。若 pip 安装后 import 失败，"
              f"改用: conda install -c conda-forge {pkgs}")
    cmd = [sys.executable, "-m", "pip", "install", "-i", MIRROR, *result["missing"]]
    print("[fix] " + " ".join(cmd))
    rc = subprocess.call(cmd)
    if rc != 0:
        print("[fix] pip 安装失败，exit", rc)
        sys.exit(rc)


if __name__ == "__main__":
    r = probe()
    if "--fix" in sys.argv and r["missing"]:
        fix(r)
        r = probe()  # 复检
    print(json.dumps(r, ensure_ascii=False, indent=2))
    if r["missing"]:
        print(f"[env_check] 缺失/损坏: {', '.join(r['missing'])} —— 按 references/install.md 处理", file=sys.stderr)
        sys.exit(1)
    print("[env_check] 四件套全部可用 ✓")
