#!/usr/bin/env python3
"""Реплики спутников: копия варианта «только для <спутника>» с говорящим — самим спутником.

В диалогах игры уникальный вариант спутника — это выбор героя (TagQuestion/ActiveRoll, speaker = 1)
с условием «у слота 1 есть тег REALLY_<ИМЯ>». Для героя-не-происхождения он скрыт. Рядом кладём копию:
  - speaker = слот спутника в этом диалоге;
  - все условия и флаги узла на слоте 1 переносятся на слот спутника (они описывают говорящего);
  - плюс «у слота 1 нет REALLY_<ИМЯ>», чтобы у героя-происхождения вариант не двоился.
Дети и тексты те же. Варианты игрока в игре не озвучены, фаз в таймлайне у них нет — таймлайн не трогаем.

Этап 3б: если спутника нет среди говорящих (entry["new_speakers"]), добавляем ему слот в диалог и
актёра в таймлайн сцены: номер говорящего (TimelineSpeakers) и запись актёра (TimelineActorData) —
копия записи другого спутника с новым номером, на свободном месте спутника в сцене (SceneActorType 4
в <имя>_Scene.lsx). Фаз для него нет: варианты игрока в таймлайне не играются.

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
TL_OVERRIDES = ROOT / "mod/Public/_MOD_/Timeline/Overrides"
COMPANION_SCENE_ACTOR = "4"   # тип места в сцене для спутников
# Глобальный флаг мода (mod/Public/_MOD_/Flags): копии видны, только пока он стоит. Ставит Lua по настройке
# MCM «Реплики спутников», поэтому их можно выключить без перезапуска.
ENABLED_FLAG = "018440f2-8807-53d4-b844-1cde8a1c4e30"
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
    glob = next((fg for fg in kids(checks, "flaggroup") if attr(fg, "type").get("value") == "Global"), None)
    if glob is None:
        glob = ET.SubElement(checks.find("children"), "node", {"id": "flaggroup", "key": "type"})
        ET.SubElement(glob, "attribute", {"id": "type", "type": "FixedString", "value": "Global"})
        ET.SubElement(glob, "children")
    f = ET.SubElement(glob.find("children"), "node", {"id": "flag", "key": "UUID"})
    ET.SubElement(f, "attribute", {"id": "UUID", "type": "FixedString", "value": ENABLED_FLAG})
    ET.SubElement(f, "attribute", {"id": "value", "type": "bool", "value": "True"})


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


def add_speakers(tree, dialog_name, new_speakers):
    """Новые слоты в speakerlist диалога. Возвращает {спутник: (индекс, SpeakerMappingId)}."""
    dialog = tree.getroot().find("region/node")
    lst = next(kids(dialog, "speakerlist")).find("children")
    donor = lst.findall("node")[-1]
    out = {}
    for comp, sp in sorted(new_speakers.items(), key=lambda x: x[1]["index"]):
        mapping = str(uuid.uuid5(NS, f"{dialog_name}:{comp}"))
        s = copy.deepcopy(donor)
        attr(s, "index").set("value", str(sp["index"]))
        attr(s, "list").set("value", sp["character"])
        attr(s, "SpeakerMappingId").set("value", mapping)
        lst.append(s)
        out[comp] = (sp["index"], mapping)
    return out


def patch_timeline(tl_tree, scene_lsx, added):
    """Актёры новых спутников в таймлайне. Возвращает список спутников, которым не нашлось места."""
    content = tl_tree.getroot().find("region[@id='TimelineContent']/node")
    speakers = next(kids(content, "TimelineSpeakers")).find("children")
    actors = next(kids(next(kids(content, "TimelineActorData")), "TimelineActorData")).find("children")
    scene = ET.parse(scene_lsx).getroot()
    places = sum(1 for a in scene.iter("node") if a.get("id") == "TLActor"
                 and (attr(a, "ActorType") is not None and attr(a, "ActorType").get("value") == COMPANION_SCENE_ACTOR))
    def value(o):
        return o.find("children/node")
    comp_actors = [o for o in actors.findall("node") if attr(value(o), "SceneActorType") is not None
                   and attr(value(o), "SceneActorType").get("value") == COMPANION_SCENE_ACTOR]
    def scene_index(o):   # 0 по умолчанию в файл не пишется
        a = attr(value(o), "SceneActorIndex")
        return int(a.get("value")) if a is not None else 0
    used = {scene_index(o) for o in comp_actors}
    failed = []
    for comp, (index, mapping) in added.items():
        free = [i for i in range(places) if i not in used]
        if not comp_actors or not free:
            failed.append(comp)
            continue
        used.add(free[0])
        sp = ET.SubElement(speakers, "node", {"id": "Object", "key": "MapKey"})
        ET.SubElement(sp, "attribute", {"id": "MapKey", "type": "int32", "value": str(index)})
        ET.SubElement(sp, "attribute", {"id": "MapValue", "type": "guid", "value": mapping})
        a = copy.deepcopy(comp_actors[0])
        attr(a, "MapKey").set("value", mapping)
        v = value(a)
        attr(v, "Speaker").set("value", str(index))
        if attr(v, "SceneActorIndex") is None:   # атрибуты — перед <children>
            v.insert(len(v.findall("attribute")),
                     ET.Element("attribute", {"id": "SceneActorIndex", "type": "int32", "value": "0"}))
        attr(v, "SceneActorIndex").set("value", str(free[0]))
        for snap in v.iter("node"):
            if snap.get("id") == "CompiledNodeSnapshots":
                cm = snap.find("children/node")
                if cm is not None and cm.find("children") is not None:
                    cm.remove(cm.find("children"))
        actors.append(a)
    return failed


def cached_timeline(pak, inner):
    """Таймлайн диалога: Mods/<модуль>/Story/DialogsBinary/.../X.lsf → Public/<модуль>/Timeline/Generated/X.lsf."""
    module = inner.split("/")[1]
    name = Path(inner).stem
    rel = f"Public/{module}/Timeline/Generated/{name}"
    root = CACHE / (Path(pak).stem + "_timelines")
    lsf = root / f"{rel}.lsf"
    if not lsf.exists():
        game = Path(config()["local"]["game_dir"]) / "Data" / pak
        divine("-a", "extract-package", "-s", game, "-d", root, "-x", f"{rel}*")
    lsx = lsf.with_name(lsf.name + ".lsx")
    if not lsx.exists():
        divine("-a", "convert-resource", "-s", lsf, "-d", lsx)
    return f"{rel}.lsf", lsx, root / f"{rel}_Scene.lsx"


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
    for d in (OVERRIDES, TL_OVERRIDES):
        if d.exists():
            shutil.rmtree(d)
    overrides, count, new_slots = {}, 0, 0
    for entry in data["dialogs"]:
        inner = entry["dialog"]
        tree = ET.parse(cached(entry["pak"], inner))
        wanted = {n["node"]: (n["companion"], n["slot"]) for n in entry["nodes"]}
        if entry.get("new_speakers"):
            added = add_speakers(tree, Path(inner).stem, entry["new_speakers"])
            tl_inner, tl_lsx, scene = cached_timeline(entry["pak"], inner)
            tl_tree = ET.parse(tl_lsx)
            failed = patch_timeline(tl_tree, scene, added)
            if failed:
                raise SystemExit(f"{inner}: нет места в сцене для {failed} — уберите диалог из NEW_SLOT_DIALOGS")
            tl_rel = tl_inner.split("/Timeline/Generated/", 1)[1]
            tl_out = TL_OVERRIDES / (tl_rel + ".lsx")
            tl_out.parent.mkdir(parents=True, exist_ok=True)
            tl_tree.write(tl_out, encoding="utf-8", xml_declaration=True)
            overrides[tl_inner] = "Public/_MOD_/Timeline/Overrides/" + tl_rel
            new_slots += len(added)
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
    print(f"реплики спутников: {count} копий, новых слотов {new_slots}, подменено файлов {len(overrides)}")


if __name__ == "__main__":
    main()
