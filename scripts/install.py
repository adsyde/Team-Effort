#!/usr/bin/env python3
"""Ставит собранный мод в игру: копирует пак в Mods и включает его в порядок загрузки профиля
(основа — установщик AlfiraSecondVerse).

BG3 Mod Manager Redux хранит порядок основного профиля сам и при экспорте перезаписывает
modsettings.lsx, поэтому для Public мод прописывается сразу в трёх местах:
modsettings.lsx, <BG3MM>/Data/CurrentOrders/*.json, <BG3MM>/Orders/LastExported.json.
Перед записью делаются .bak-копии. Игра и менеджер модов должны быть закрыты.
Нужен Script Extender.

  python scripts/install.py                    # основной профиль
  python scripts/install.py --remove-conflicts # и выключить моды, которые делают то же самое
  python scripts/install.py --uninstall
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from common import config, enable_utf8_stdout, resolve

enable_utf8_stdout()

BG3 = Path(os.environ["LOCALAPPDATA"]) / "Larian Studios" / "Baldur's Gate 3"
MODS = BG3 / "Mods"
PROFILES = BG3 / "PlayerProfiles"
MAIN_PROFILE = "Public"

# Моды, которые делают то же самое: вместе с нашим их включать нельзя
CONFLICTS = {
    "6e49e906-f0de-9abb-d7e1-b361e22be6a2": "Best in Party Skills",
    "81db9dfa-b4a6-41f0-b31c-ac7e0f7a7476": "Use highest modifier - SE Toggle",
}


def running(name):
    return name.lower() in subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()


def backup(p):
    shutil.copy2(p, p.with_name(p.name + time.strftime(".%Y%m%d-%H%M%S.bak")))


def node(folder, name, uuid, ver):
    return f'''            <node id="ModuleShortDesc">
              <attribute id="Folder" type="LSString" value="{folder}" />
              <attribute id="MD5" type="LSString" value="" />
              <attribute id="Name" type="LSString" value="{name}" />
              <attribute id="PublishHandle" type="uint64" value="0" />
              <attribute id="UUID" type="guid" value="{uuid}" />
              <attribute id="Version64" type="int64" value="{ver}" />
            </node>
'''


def drop_node(text, uuid):
    i = text.find(f'value="{uuid}"')
    if i < 0:
        return text
    a = text.rindex('<node id="ModuleShortDesc">', 0, i)
    a = text.rindex("\n", 0, a) + 1
    b = text.index("</node>", i) + len("</node>\n")
    return text[:a] + text[b:]


def active_uuids(text):
    return set(re.findall(r'id="UUID" type="(?:guid|FixedString)" value="([^"]+)"', text))


def mm_order_files(cfg):
    mm = Path(cfg["local"].get("bg3mm_dir", "C:/Games/BG3MM"))
    files = list((mm / "Data" / "CurrentOrders").glob("*.json")) + [mm / "Orders" / "LastExported.json"]
    return [f for f in files if f.exists()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--profile", default=MAIN_PROFILE, help="папка профиля в PlayerProfiles (по умолчанию Public)")
    ap.add_argument("--clone-mods-from", metavar="ПРОФИЛЬ",
                    help="взять порядок модов из другого профиля (для нового тестового профиля)")
    ap.add_argument("--remove-conflicts", action="store_true",
                    help="выключить в профиле моды, которые тоже дают бонусы отряда к проверкам")
    ap.add_argument("--copy-save", metavar="ПАПКА",
                    help="скопировать сохранение из Public/Savegames/Story в профиль")
    args = ap.parse_args()
    cfg = config()
    mod = cfg["mod"]
    for exe in ("bg3", "Redux"):
        if running(exe):
            sys.exit(f"Запущен {exe} — закройте игру и менеджер модов и повторите.")

    profile_dir = PROFILES / args.profile
    if not profile_dir.is_dir():
        sys.exit(f"Нет профиля {profile_dir} — создайте его в игре (главное меню → Профиль).")
    settings = profile_dir / "modsettings.lsx"
    main_profile = args.profile == MAIN_PROFILE

    if args.clone_mods_from:
        src = PROFILES / args.clone_mods_from / "modsettings.lsx"
        if settings.exists():
            backup(settings)
        shutil.copy2(src, settings)
        print(f"Порядок модов взят из профиля {args.clone_mods_from}.")

    folder = f'{mod["name"]}_{mod["uuid"]}'
    pak = resolve(cfg["paths"]["dist"]) / f'{mod["name"]}.pak'
    from build_pak import version64
    ver = version64(mod["version"])

    s = settings.read_text(encoding="utf-8")
    found = {u: n for u, n in CONFLICTS.items() if u in active_uuids(s)}
    if found and not args.uninstall:
        if not args.remove_conflicts:
            sys.exit("В профиле включены моды, которые делают то же самое:\n  " + "\n  ".join(found.values())
                     + "\nВместе с нашим их включать нельзя: бонусы сложатся. Запустите с --remove-conflicts.")
        for u in found:
            s = drop_node(s, u)
        print("Выключены в профиле: " + ", ".join(found.values()))

    if not args.clone_mods_from:
        backup(settings)
    s = drop_node(s, mod["uuid"])
    if not args.uninstall:
        if not pak.exists():
            sys.exit(f"Нет {pak} — сначала python scripts/build_pak.py")
        shutil.copy2(pak, MODS / pak.name)
        mods_block = s.index('<node id="Mods">')
        end = s.index("</children>", mods_block)
        end = s.rindex("\n", 0, end) + 1
        s = s[:end] + node(folder, mod["display_name"], mod["uuid"], ver) + s[end:]
    settings.write_text(s, encoding="utf-8")

    touched = 0
    if main_profile:
        for f in mm_order_files(cfg):
            backup(f)
            d = json.loads(f.read_text(encoding="utf-8-sig"))
            d["Order"] = [m for m in d["Order"] if m["UUID"] != mod["uuid"] and m["UUID"] not in found]
            if not args.uninstall:
                d["Order"].append({"UUID": mod["uuid"], "Name": mod["display_name"]})
            f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            touched += 1

    if args.copy_save:
        src = PROFILES / MAIN_PROFILE / "Savegames" / "Story" / args.copy_save
        dst = profile_dir / "Savegames" / "Story" / args.copy_save
        if not src.is_dir():
            sys.exit(f"Нет сохранения {src}")
        shutil.copytree(src, dst, dirs_exist_ok=True)
        print(f"Сохранение скопировано: {args.copy_save}")

    what = "Убран из порядка" if args.uninstall else f"Установлен {pak.name}"
    print(f"{what} — профиль {args.profile}: modsettings" + (f" + {touched} файла менеджера" if touched else ""))


if __name__ == "__main__":
    main()
