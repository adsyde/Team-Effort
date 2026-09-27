#!/usr/bin/env python3
"""Реплики спутников: копия варианта «только для <спутника>» с говорящим — самим спутником.

В диалогах игры уникальный вариант спутника — это выбор героя (TagQuestion/ActiveRoll, speaker = 1)
с условием «у слота 1 есть тег REALLY_<ИМЯ>». Для героя-не-происхождения он скрыт. Рядом кладём копию:
  - speaker = слот спутника в этом диалоге;
  - все условия и флаги узла на слоте 1 переносятся на слот спутника (они описывают говорящего);
  - плюс «у слота 1 нет REALLY_<ИМЯ>», чтобы у героя-происхождения вариант не двоился.
Дети и тексты те же. Варианты игрока в игре не озвучены, фаз в таймлайне у них нет — таймлайн не трогаем.

Что копировать — data/companion_lines.json (scripts/research/select_lines.py). Диалоги берутся из
паков игры (кэш build/cache/<пак>), результат — mod/Mods/_MOD_/Story/DialogsBinary/Overrides/<путь>.lsf.lsx
(контент игры, в git не входит). В игре подменяет Lua: Ext.IO.AddPathOverride.

  python scripts/companion_lines.py
"""
import copy
import json
import shutil
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

from common import ROOT, config, divine, enable_utf8_stdout

enable_utf8_stdout()

NS = uuid.UUID("c226c99d-720c-4611-98c9-9ba1fe6df481")    # UUID мода: копии получают одни и те же id
DATA = ROOT / "data/companion_lines.json"
CACHE = ROOT / "build/cache"
OVERRIDES = ROOT / "mod/Mods/_MOD_/Story/DialogsBinary/Overrides"
MANIFEST = ROOT / "mod/Mods/_MOD_/ScriptExtender/Lua/Shared/Overrides.lua"


def attr(node, name):
    for a in node.findall("attribute"):
        if a.get("id") == name:
            return a
    return None


def kids(node, name):
    for c in node.findall("children/node"):
        if c.get("id") == name:
            yield c


def flag(tag, value, slot):
    f = ET.Element("node", {"id": "flag", "key": "UUID"})
    ET.SubElement(f, "attribute", {"id": "UUID", "type": "FixedString", "value": tag})
    ET.SubElement(f, "attribute", {"id": "value", "type": "bool", "value": "True" if value else "False"})
    ET.SubElement(f, "attribute", {"id": "paramval", "type": "int32", "value": str(slot)})
    return f


def retarget(node, slot, tag):
    """Условия и флаги узла со слота 1 — на слот спутника; плюс «слот 1 — не он»."""
    for key in ("checkflags", "setflags"):
        for block in kids(node, key):
            for fg in kids(block, "flaggroup"):
                for f in kids(fg, "flag"):
                    pv = attr(f, "paramval")
                    if pv is not None and pv.get("value") == "1":
                        pv.set("value", str(slot))
    checks = next(kids(node, "checkflags"))
    tag_group = next(fg for fg in kids(checks, "flaggroup") if attr(fg, "type").get("value") == "Tag")
    tag_group.find("children").append(flag(tag, False, 1))


def patch(tree, wanted, tag_of):
    """wanted: {uuid узла: (спутник, слот)}. Возвращает список добавленных (спутник, оригинал, копия)."""
    dialog = tree.getroot().find("region/node")
    nodes_root = next(kids(dialog, "nodes")).find("children")
    nodes = [n for n in nodes_root.findall("node") if n.get("id") == "node"]
    by_id = {attr(n, "UUID").get("value"): n for n in nodes}
    roots = [r for r in nodes_root.findall("node") if r.get("id") == "RootNodes"]
    added = []
    for orig_id, (comp, slot) in wanted.items():
        n = by_id.get(orig_id)
        if n is None or attr(n, "speaker").get("value") != "1":
            raise SystemExit(f"узел {orig_id} не найден или уже не вариант героя — пересоберите data/")
        new_id = str(uuid.uuid5(NS, f"{orig_id}:{slot}"))
        new = copy.deepcopy(n)
        attr(new, "UUID").set("value", new_id)
        attr(new, "speaker").set("value", str(slot))
        for a in new.iter("attribute"):
            if a.get("id") == "LineId":
                a.set("value", str(uuid.uuid5(NS, f"{a.get('value')}:{slot}")))
        retarget(new, slot, tag_of[comp])
        nodes_root.insert(list(nodes_root).index(n) + 1, new)
        for p in nodes:     # ссылка на копию — у всех родителей, сразу после оригинала
            lst = next(kids(p, "children"), None)
            lst = lst.find("children") if lst is not None else None
            for i, c in enumerate(list(lst) if lst is not None else []):
                if attr(c, "UUID").get("value") == orig_id:
                    ref = copy.deepcopy(c)
                    attr(ref, "UUID").set("value", new_id)
                    lst.insert(i + 1, ref)
                    break
        for r in roots:     # корневой вариант — копия тоже корневая
            if attr(r, "RootNodes").get("value") == orig_id:
                ref = copy.deepcopy(r)
                attr(ref, "RootNodes").set("value", new_id)
                nodes_root.insert(list(nodes_root).index(r) + 1, ref)
        added.append((comp, orig_id, new_id))
    return added


def cached(pak, inner):
    root = CACHE / Path(pak).stem
    if not root.exists():
        game = Path(config()["local"]["game_dir"]) / "Data" / pak
        divine("-a", "extract-package", "-s", game, "-d", root, "-x", "*/Story/DialogsBinary/*")
    lsf = root / inner
    lsx = lsf.with_name(lsf.name + ".lsx")
    if not lsx.exists():
        divine("-a", "convert-resource", "-s", lsf, "-d", lsx)
    return lsx


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    if OVERRIDES.exists():
        shutil.rmtree(OVERRIDES)
    overrides, count = {}, 0
    for entry in data["dialogs"]:
        inner = entry["dialog"]
        tree = ET.parse(cached(entry["pak"], inner))
        wanted = {n["node"]: (n["companion"], n["slot"]) for n in entry["nodes"]}
        count += len(patch(tree, wanted, data["tags"]))
        rel = inner.split("/Story/DialogsBinary/", 1)[1]
        out = OVERRIDES / (rel + ".lsx")          # X.lsf.lsx → при сборке X.lsf
        out.parent.mkdir(parents=True, exist_ok=True)
        tree.write(out, encoding="utf-8", xml_declaration=True)
        overrides[inner] = "Mods/_MOD_/Story/DialogsBinary/Overrides/" + rel
    lines = ["-- Сгенерировано scripts/companion_lines.py. Подмена диалогов игры нашими копиями.",
             "TE.DialogOverrides = {"]
    lines += [f'    ["{k}"] = "{v}",' for k, v in sorted(overrides.items())]
    lines += ["}", ""]
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"реплики спутников: {count} копий в {len(overrides)} диалогах")


if __name__ == "__main__":
    main()
