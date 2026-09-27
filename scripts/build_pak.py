#!/usr/bin/env python3
"""Собирает мод из mod/ в dist/TeamEffort.pak (основа — сборщик AlfiraSecondVerse).

mod/ повторяет раскладку пака; вместо папки модуля в путях пишется «_MOD_» —
сборщик подставит <name>_<uuid>, чтобы оно было записано ровно в одном месте.

Шаги: scripts/gen_stats.py и scripts/dialogs.py (DialogKit) → копия mod/ в build/pak с подстановкой _MOD_ → проверка локализации
(никаких <!-- --> — игра падает при запуске) → meta.lsx из config/tools.json → Divine create-package.

  python scripts/build_pak.py
  python scripts/build_pak.py --version 0.1.1
"""
import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

from common import config, divine, enable_utf8_stdout, resolve

enable_utf8_stdout()

# Каталоги, файлы в которых игра читает только в бинарном виде (.lsf).
# Остальные .lsx (meta.lsx, Story/*.txt, Localization/*.xml) кладутся как есть.
BINARY_DIRS = ("RootTemplates", "Flags", "Tags", "DialogsBinary", "Timeline", "Globals", "Levels", "Content",
               "DialogKit")
# Текстовые ресурсы, в которых _MOD_ заменяется на имя папки модуля.
TEXT_SUFFIXES = (".lsx", ".lsj", ".xml", ".lua")


def version64(text):
    major, minor, revision, build = ([int(p) for p in text.split(".")] + [0, 0, 0, 0])[:4]
    return (major << 55) | (minor << 47) | (revision << 31) | build


def meta_lsx(mod, folder, version):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="500"/>
    <region id="Config">
        <node id="root">
            <children>
                <node id="Conflicts"/>
                <node id="Dependencies">
                    <children>
                        <node id="ModuleShortDesc">
                            <attribute id="Folder" type="LSString" value="BG3MCM"/>
                            <attribute id="MD5" type="LSString" value=""/>
                            <attribute id="Name" type="LSString" value="Mod Configuration Menu"/>
                            <attribute id="PublishHandle" type="uint64" value="0"/>
                            <attribute id="UUID" type="FixedString" value="755a8a72-407f-4f0d-9a33-274ac0f0b53d"/>
                            <attribute id="Version64" type="int64" value="41799034041532416"/>
                        </node>
                    </children>
                </node>
                <node id="ModuleInfo">
                    <attribute id="Author" type="LSString" value="{mod["author"]}"/>
                    <attribute id="CharacterCreationLevelName" type="FixedString" value=""/>
                    <attribute id="Description" type="LSString" value="{mod["description"]}"/>
                    <attribute id="FileSize" type="uint64" value="0"/>
                    <attribute id="Folder" type="LSString" value="{folder}"/>
                    <attribute id="LobbyLevelName" type="FixedString" value=""/>
                    <attribute id="MD5" type="LSString" value=""/>
                    <attribute id="MenuLevelName" type="FixedString" value=""/>
                    <attribute id="Name" type="LSString" value="{mod["display_name"]}"/>
                    <attribute id="NumPlayers" type="uint8" value="4"/>
                    <attribute id="PhotoBooth" type="FixedString" value=""/>
                    <attribute id="PublishHandle" type="uint64" value="0"/>
                    <attribute id="StartupLevelName" type="FixedString" value=""/>
                    <attribute id="Tags" type="LSString" value=""/>
                    <attribute id="Type" type="FixedString" value="Add-on"/>
                    <attribute id="UUID" type="FixedString" value="{mod["uuid"]}"/>
                    <attribute id="Version64" type="int64" value="{version64(version)}"/>
                    <children>
                        <node id="PublishVersion">
                            <attribute id="Version64" type="int64" value="{version64(version)}"/>
                        </node>
                        <node id="Scripts"/>
                    </children>
                </node>
            </children>
        </node>
    </region>
</save>
'''


def main():
    cfg = config()
    mod = cfg["mod"]
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=mod["version"])
    ap.add_argument("--no-generate", action="store_true", help="не запускать gen_stats.py")
    args = ap.parse_args()

    if not args.no_generate:
        import gen_stats, dialogs
        gen_stats.main()
        dialogs.main()

    folder = f'{mod["name"]}_{mod["uuid"]}'
    src = resolve(cfg["paths"]["mod_src"])
    build = resolve(cfg["paths"]["build"]) / "pak"
    dist = resolve(cfg["paths"]["dist"])
    if build.exists():
        shutil.rmtree(build)
    twins = set()   # X.lsx рядом с X.lsf.lsx: настоящий lsx (например, _Scene.lsx таймлайна)

    files = [p for p in src.rglob("*") if p.is_file() and p.name not in (".gitkeep", "README.md")]
    if not files:
        sys.exit("mod/ пуст — собирать нечего.")
    errors = []
    for p in files:
        rel = p.relative_to(src).as_posix().replace("_MOD_", folder)
        out = build / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        data = p.read_bytes()
        if p.suffix == ".xml" and "/Localization/" in rel and b"<!--" in data:
            errors.append(f"{rel}: XML-комментарий в локализации роняет игру при запуске")
        if p.suffix in TEXT_SUFFIXES:
            data = data.replace(b"_MOD_", folder.encode())
        out.write_bytes(data)
    # Конвертация — после копирования: проверка локализации читает текстовые .lsx диалогов.
    for out in build.rglob("*.lsf.lsx"):
        twins.add(out.with_name(out.name[:-len(".lsf.lsx")] + ".lsx"))
    for out in sorted(build.rglob("*.ls[xj]")):
        rel = out.relative_to(build).as_posix()
        if out in twins:
            continue
        if out.suffix == ".lsj" and "/Story/Dialogs/" in rel:
            lsf = build / rel.replace("/Story/Dialogs/", "/Story/DialogsBinary/", 1)
            lsf = lsf.with_suffix(".lsf")
        elif out.suffix == ".lsx" and any(f"/{d}/" in f"/{rel}" for d in BINARY_DIRS):
            lsf = out.with_suffix(".lsf") if not out.name.endswith(".lsf.lsx") else out.with_suffix("")
        else:
            continue
        lsf.parent.mkdir(parents=True, exist_ok=True)
        divine("-a", "convert-resource", "-s", out, "-d", lsf)
        out.unlink()
    if errors:
        sys.exit("Сборка остановлена:\n  " + "\n  ".join(errors))

    meta = build / "Mods" / folder / "meta.lsx"
    meta.parent.mkdir(parents=True, exist_ok=True)
    meta.write_text(meta_lsx(mod, folder, args.version), encoding="utf-8")

    stray = {p.relative_to(build).parts[1] for p in build.glob("*/*") if p.is_dir()} - {folder}
    if stray:
        sys.exit(f"В паке лишние папки модулей {sorted(stray)}: всё должно лежать в _MOD_ (иначе мод пропадёт из списка).")

    dist.mkdir(parents=True, exist_ok=True)
    pak = dist / f'{mod["name"]}.pak'
    # Divine молча пропускает файлы, если в пути есть папка на «.» (например, .claude/worktrees):
    # тогда пакуем из временной копии.
    staged = build
    if any(part.startswith(".") for part in build.parts):
        staged = Path(tempfile.mkdtemp(prefix="te_pak_")) / "pak"
        shutil.copytree(build, staged)
    divine("-a", "create-package", "-s", staged, "-d", pak)
    if staged is not build:
        shutil.rmtree(staged.parent)
    listed = [l for l in divine("-a", "list-package", "-s", pak).splitlines() if "\t" in l]
    packed = sum(1 for p in build.rglob("*") if p.is_file())
    if len(listed) != packed:
        sys.exit(f"В паке {len(listed)} файлов из {packed}: Divine что-то пропустил.")
    for line in listed:
        print("  " + line.split("\t")[0])
    print(f"{pak}  ({pak.stat().st_size // 1024} КБ, {len(listed)} файлов, версия {args.version})")


if __name__ == "__main__":
    main()
