#!/usr/bin/env python3
"""Правленые диалоги Team Effort через DialogKit (../DialogKit, config/tools.json → dialogkit).

Патчи — data/patches/**/*.json (формат dialogkit/1; реплики спутников пишет
scripts/research/select_lines.py). Сборка кладёт в mod/:
  Mods/_MOD_/Story/DialogsBinary/<путь>.lsf.lsx      вариант «own» (свои правки поверх игры)
  Mods/_MOD_/DialogKit/<вариант>/<путь>.lsf.lsx      «all» (с партнёрами), «own@<UUID>»/«all@<UUID>» (на базе мода)
  Public/_MOD_/Timeline/Generated/<имя>.lsf.lsx (+_Scene.lsf), Public/_MOD_/DialogKit/<вариант>/…
  Public/_MOD_/Content/…/[PAK]_DialogKit/…           банки диалогов и таймлайнов (подмена как у модов игры)
  Mods/_MOD_/ScriptExtender/Lua/Shared/DialogKit.lua и DialogKitManifest.lua — выбор варианта при загрузке.
Всё это — контент игры, в git не входит (.gitignore).

  python scripts/dialogs.py
"""
import shutil
import sys
from pathlib import Path

from common import ROOT, config, enable_utf8_stdout, resolve

enable_utf8_stdout()

GENERATED = [
    "mod/Mods/_MOD_/Story/DialogsBinary",
    "mod/Mods/_MOD_/DialogKit",
    "mod/Public/_MOD_/DialogKit",
    "mod/Public/_MOD_/Timeline",
    "mod/Public/_MOD_/Content/Assets/Dialogs/[PAK]_DialogKit",
    "mod/Public/_MOD_/Content/Generated/[PAK]_DialogKit",
]
LUA = ROOT / "mod/Mods/_MOD_/ScriptExtender/Lua/Shared"


def main():
    cfg = config()
    dk = cfg["dialogkit"]
    sys.path.insert(0, str(resolve(dk["path"])))
    from dialogkit.build import Project, lua_manifest
    from dialogkit.game import Game

    local = cfg["local"]
    game = Game(local["divine_path"], local["game_dir"], resolve(dk["cache"]))
    for rel in GENERATED:
        p = ROOT / rel
        if p.exists():
            shutil.rmtree(p)
    bases = []
    for b in dk.get("bases", []):
        try:
            game.pak_path(b["source"])
            bases.append(b)
        except FileNotFoundError:
            print(f"  база {b['name']} не установлена — варианты на её основе не собираются")
    partners = [dict(p, patches=str(resolve(p["patches"]))) for p in dk.get("partners", [])]
    for p in partners:
        if not Path(p["patches"]).exists():
            print(f"  у партнёра {p['name']} нет патчей ({p['patches']}) — вариантов «all» не будет")
    project = Project(game, cfg["mod"]["uuid"], [resolve(d) for d in dk["patches"]], ROOT / "mod",
                      partners=partners, bases=bases)
    manifest = project.build()
    LUA.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(resolve(dk["path"]) / "dialogkit/lua/DialogKit.lua", LUA / "DialogKit.lua")
    (LUA / "DialogKitManifest.lua").write_text(lua_manifest(manifest, cfg["mod"]["uuid"]), encoding="utf-8",
                                               newline="\n")
    variants = sum(len(e["variants"]) for e in manifest)
    print(f"диалоги DialogKit: {len(manifest)} диалогов, {variants} вариантов"
          f" (с партнёрами {sum(1 for e in manifest if e['partners'])}, на базе модов "
          f"{sum(1 for e in manifest if e['bases'])})")
    return manifest


if __name__ == "__main__":
    main()
