"""Общие функции скриптов: конфиг, пути, вызов Divine (LSLib)."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def enable_utf8_stdout():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except AttributeError:
            pass


def config():
    cfg = json.loads((ROOT / "config" / "tools.json").read_text(encoding="utf-8"))
    local = ROOT / "config" / "tools.local.json"
    if not local.exists():
        sys.exit("Нет config/tools.local.json — скопируйте tools.local.example.json и поправьте пути.")
    cfg["local"] = json.loads(local.read_text(encoding="utf-8"))
    return cfg


def save_config_section(key, value):
    """Перезаписывает один раздел tools.json (например, найденные идентификаторы Альфиры)."""
    path = ROOT / "config" / "tools.json"
    cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg[key] = value
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve(rel):
    p = Path(rel)
    return p if p.is_absolute() else ROOT / p


def game_data_dir(cfg=None):
    cfg = cfg or config()
    return resolve(cfg["paths"]["game_data"])


def divine(*args, check=True):
    """Divine требует абсолютных путей; все Path приводятся к строкам Windows."""
    exe = config()["local"]["divine_path"]
    cmd = [exe, "-g", "bg3", *[str(a) for a in args]]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        sys.exit(f"Divine упал ({r.returncode}):\n{' '.join(cmd)}\n{r.stdout}\n{r.stderr}")
    return r.stdout


def game_pak(rel):
    return Path(config()["local"]["game_dir"]) / "Data" / rel
