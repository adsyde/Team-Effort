#!/usr/bin/env python3
"""Реплики спутников: копия варианта «только для <спутника>» с говорящим — самим спутником.

В диалогах игры уникальный вариант спутника — это ответ героя (TagQuestion, speaker = 1) с условием
«у слота 1 есть тег REALLY_<ИМЯ>». Для героя-не-происхождения он скрыт. Мы добавляем рядом копию:
  speaker = слот спутника в этом диалоге,
  условие: у слота спутника есть REALLY_<ИМЯ>, у слота 1 — нет (иначе у героя-происхождения вариант двоится).
Дети и тексты — те же. Варианты игрока в игре не озвучены и в таймлайне фаз не имеют, поэтому
таймлайн не трогаем.

Исходник — бинарный диалог игры (DialogsBinary/*.lsf → lsx), результат — mod/Mods/_MOD_/Story/
DialogsBinary/Overrides/<тот же путь>.lsf.lsx; в игре его подставляет Lua (Ext.IO.AddPathOverride).

  python scripts/companion_lines.py            # прототип: TWN_Hospital_Surgeon, Шэдоухарт
"""
import copy
import json
import subprocess
import sys
import tempfile
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

from common import ROOT, config, divine, enable_utf8_stdout

enable_utf8_stdout()

NS = uuid.UUID("c226c99d-720c-4611-98c9-9ba1fe6df481")    # UUID мода: копии получают одни и те же id
PLAYERS = "e0d1ff71-04a8-4340-ae64-9684d846eb83"   # группа говорящих «Игроки»
COMPANIONS = {                                     # персонаж → тег REALLY_<ИМЯ>
    "3ed74f06-3c60-42dc-83f6-f034cb47c679": ("SHADOWHEART", "642d2aee-e3df-47e3-9f47-bbcd441bb9e0"),
}
PROTOTYPE = [("Gustav.pak", "Mods/GustavDev/Story/DialogsBinary/Act2/Town/TWN_Hospital_Surgeon.lsf")]
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


def patch(tree):
    """Добавляет копии вариантов спутников. Возвращает список (спутник, uuid оригинала, uuid копии)."""
    dialog = tree.getroot().find("region/node")
    slots = {}
    for sl in kids(dialog, "speakerlist"):
        for s in kids(sl, "speaker"):
            slots[attr(s, "list").get("value")] = int(attr(s, "index").get("value"))
    nodes_root = next(kids(dialog, "nodes")).find("children")
    nodes = [n for n in nodes_root.findall("node") if n.get("id") == "node"]
    tag_to_comp = {t: (c, name) for c, (name, t) in COMPANIONS.items()}
    added = []
    for n in nodes:
        if attr(n, "constructor").get("value") != "TagQuestion" or attr(n, "speaker").get("value") != "1":
            continue
        checks = next(kids(n, "checkflags"), None)
        if checks is None:
            continue
        comp = None
        for fg in kids(checks, "flaggroup"):
            if attr(fg, "type").get("value") != "Tag":
                continue
            for f in kids(fg, "flag"):
                t = attr(f, "UUID").get("value")
                if t in tag_to_comp and attr(f, "value").get("value") == "True" and attr(f, "paramval").get("value") == "1":
                    comp = (tag_to_comp[t], f)
        if not comp or comp[0][0] not in slots:
            continue   # спутника нет среди говорящих этого диалога — такие случаи позже (этап 3)
        (char, name), orig_flag = comp
        slot = slots[char]
        new = copy.deepcopy(n)
        new_id = str(uuid.uuid5(NS, f"{attr(n, 'UUID').get('value')}:{slot}"))
        attr(new, "UUID").set("value", new_id)
        attr(new, "speaker").set("value", str(slot))
        for lid in new.iter("attribute"):
            if lid.get("id") == "LineId":
                lid.set("value", str(uuid.uuid5(NS, f"{lid.get('value')}:{slot}")))
        # условие: вместо «слот 1 — <спутник>» ставим «слот спутника — он, слот 1 — нет»
        nchecks = next(kids(new, "checkflags"))
        for fg in kids(nchecks, "flaggroup"):
            for f in kids(fg, "flag"):
                if attr(f, "UUID").get("value") == attr(orig_flag, "UUID").get("value") and attr(f, "paramval").get("value") == "1":
                    attr(f, "paramval").set("value", str(slot))
                    fg.find("children").append(flag(attr(f, "UUID").get("value"), False, 1))
        nodes_root.insert(list(nodes_root).index(n) + 1, new)
        # ссылка на копию — у всех родителей, сразу после оригинала
        orig_id = attr(n, "UUID").get("value")
        for p in nodes:
            ch = next(kids(p, "children"), None)
            if ch is None or ch.find("children") is None:
                continue
            lst = ch.find("children")
            for i, c in enumerate(list(lst)):
                if attr(c, "UUID").get("value") == orig_id:
                    ref = copy.deepcopy(c)
                    attr(ref, "UUID").set("value", new_id)
                    lst.insert(i + 1, ref)
                    break
        added.append((name, orig_id, new_id))
    return added


def extract(pak, inner, tmp):
    game = Path(config()["local"]["game_dir"]) / "Data" / pak
    divine("-a", "extract-package", "-s", game, "-d", tmp, "-x", inner)
    lsf = Path(tmp) / inner
    lsx = lsf.with_suffix(".lsf.lsx")
    divine("-a", "convert-resource", "-s", lsf, "-d", lsx)
    return lsx


def main():
    overrides = {}
    with tempfile.TemporaryDirectory() as tmp:
        for pak, inner in PROTOTYPE:
            tree = ET.parse(extract(pak, inner, tmp))
            added = patch(tree)
            rel = inner.split("/Story/DialogsBinary/", 1)[1]
            out = OVERRIDES / (rel + ".lsx")          # X.lsf.lsx → при сборке X.lsf
            out.parent.mkdir(parents=True, exist_ok=True)
            tree.write(out, encoding="utf-8", xml_declaration=True)
            overrides[inner] = "Mods/_MOD_/Story/DialogsBinary/Overrides/" + rel
            for name, a, b in added:
                print(f"{rel}: {name} {a} → {b}")
    lines = ["-- Сгенерировано scripts/companion_lines.py. Подмена диалогов игры нашими копиями.",
             "TE.DialogOverrides = {"]
    lines += [f'    ["{k}"] = "{v}",' for k, v in sorted(overrides.items())]
    lines += ["}", ""]
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(MANIFEST.relative_to(ROOT))


if __name__ == "__main__":
    main()
