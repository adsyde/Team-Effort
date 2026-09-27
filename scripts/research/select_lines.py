#!/usr/bin/env python3
"""Отбор вариантов спутников → патчи DialogKit data/patches/companion_lines/<диалог>.json (только id).

Берём вариант героя (TagQuestion или ActiveRoll, speaker = 1) с условием «у слота 1 есть тег
REALLY_<спутник>», если:
  - спутник уже среди говорящих этого диалога (есть слот с его персонажем);
  - дальше по ветке, до следующего выбора игрока, нет проверок тегов REALLY_* на слоте 1 и флагов
    Object на слоте 1 (иначе ветка ждёт, что говорит герой-происхождение, — это позже);
  - текст — не «мысль» целиком курсивом (решение автора 2026-09-27: такие пропускаем).
Диалог берётся из пака с наибольшим приоритетом (Patch8_HotFix9 > GustavX > Gustav > Shared).

Нужен индекс: python scripts/research/dialog_index.py. Тексты — кэш loca проекта Альфиры.

  python scripts/research/select_lines.py
"""
import collections
import json
import os
import pickle
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dialog_index as D  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
ROOT = D.ROOT
OUT = ROOT / "data/patches/companion_lines"
MOD = "c226c99d-720c-4611-98c9-9ba1fe6df481"
ENABLED_FLAG = "018440f2-8807-53d4-b844-1cde8a1c4e30"   # TE_CompanionLines_Enabled (настройка MCM)
PAK_PRIORITY = ["Patch8_HotFix9", "GustavX", "Gustav", "Shared"]
CHOICES = ("TagQuestion", "ActiveRoll")
THOUGHT = re.compile(r"^\s*<i>.*</i>\s*$", re.S)
# Этап 3б (прототип): диалоги, где спутника нет среди говорящих — добавляем ему слот и место в сцене.
# Пока только эти; остальные — после проверки в игре (docs/ROADMAP.md).
NEW_SLOT_DIALOGS = {"DEN_Stargazing", "DEN_Thieflings_Trainer"}


def binary_path(key):
    """Gustav\\Mods\\GustavDev\\Story\\Dialogs\\X.lsj → (Gustav, Mods/GustavDev/Story/DialogsBinary/X.lsf)"""
    pak, rest = key.replace("\\", "/").split("/", 1)
    return pak, rest.replace("/Story/Dialogs/", "/Story/DialogsBinary/", 1)[:-4] + ".lsf"


def successors(N, m):
    out = list(m["kids"])
    if m.get("jump"):
        out.append(m["jump"])
    if m.get("source") in N:
        out += N[m["source"]]["kids"]
    return [k for k in out if k in N]


def walk(N, n, really):
    """Ветка после варианта до следующего выбора игрока: (причина отказа или None, наборы следующих выборов)."""
    seen, stack, sets = set(), [n["kids"]], []
    while stack:
        level = [k for k in stack.pop() if k in N and k not in seen]
        choices = [k for k in level if N[k]["c"] in CHOICES]
        if choices:
            sets.append(choices)
        for k in level:
            seen.add(k)
            m = N[k]
            if m["c"] == "Nested Dialog":
                return "вложенный диалог", sets
            if any(t == "Tag" and fl in really and pv == 1 for t, fl, pv, val in m["check"]) or                     any(t == "Object" and pv == 1 for t, fl, pv, val in m["set"]):
                return "ветка ждёт героя-происхождение", sets
            if m["c"] not in CHOICES:
                stack.append(successors(N, m))
    return None, sets


def drop_dead_ends(N, nodes, really, skipped):
    """Убираем копии, после которых герою не из чего выбрать: весь следующий выбор — только для
    происхождения и сам не копируется. Повторяем, пока список не перестанет меняться."""
    def gated(k):
        return any(t == "Tag" and fl in really and pv == 1 and val for t, fl, pv, val in N[k]["check"])
    while True:
        ids = {x["node"] for x in nodes}
        keep = [x for x in nodes if not any(all(gated(k) and k not in ids for k in s) for s in x["_sets"])]
        skipped["тупик: дальше выбор только для происхождения"] += len(nodes) - len(keep)
        if len(keep) == len(nodes):
            for x in keep:
                del x["_sets"]
            return keep
        nodes = keep


def main():
    db = D.load()
    idx, tags = db["index"], db["tags"]
    loca = pickle.load(open(D.GD / "_cache.pkl", "rb"))["en"]
    really = {u: n[len("REALLY_"):] for u, n in tags.items() if n.startswith("REALLY_")}
    comp_tag = {name: u for u, name in really.items() if name in D.COMPANIONS.values()}

    latest = {}
    for key in idx:
        pak, inner = binary_path(key)
        if pak not in PAK_PRIORITY:
            continue
        if inner not in latest or PAK_PRIORITY.index(pak) < PAK_PRIORITY.index(latest[inner][0]):
            latest[inner] = (pak, key)

    picked, skipped = [], collections.Counter()
    for inner, (pak, key) in sorted(latest.items()):
        d = idx[key]
        N = d["nodes"]
        slot_of = {}
        for i, lst in d["slots"].items():
            for g in (lst or "").split(";"):
                if g in D.COMPANIONS:
                    slot_of.setdefault(D.COMPANIONS[g], i)
        nodes, new_speakers = [], {}
        allow_new = Path(inner).stem in NEW_SLOT_DIALOGS
        for u, n in N.items():
            if n["c"] not in CHOICES or n["sp"] != 1:
                continue
            comp = [really[fl] for t, fl, pv, val in n["check"]
                    if t == "Tag" and fl in comp_tag.values() and val and pv == 1]
            if not comp:
                continue
            comp = comp[0]
            if comp not in slot_of and not allow_new:
                skipped["спутника нет среди говорящих"] += 1
                continue
            texts = [loca.get(h, "") for h in n["texts"] if h]
            if texts and all(THOUGHT.match(t) for t in texts):
                skipped["мысль курсивом"] += 1
                continue
            dirty, sets = walk(N, n, really)
            if dirty:
                skipped[dirty] += 1
                continue
            if comp not in slot_of:     # этап 3б: новый слот в конце списка говорящих
                slot_of[comp] = max(d["slots"]) + 1 + len(new_speakers)
                new_speakers[comp] = {"index": slot_of[comp],
                                      "character": next(g for g, c in D.COMPANIONS.items() if c == comp)}
            nodes.append({"node": u, "companion": comp, "slot": slot_of[comp], "_sets": sets})
        nodes = drop_dead_ends(N, nodes, really, skipped)
        used = {x["companion"] for x in nodes}
        new_speakers = {c: v for c, v in new_speakers.items() if c in used}
        if nodes:
            entry = {"pak": f"{pak}.pak", "dialog": inner, "nodes": nodes}
            if new_speakers:
                entry["new_speakers"] = new_speakers
            picked.append(entry)

    total = collections.Counter(n["companion"] for p in picked for n in p["nodes"])
    import shutil, uuid
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for e in picked:
        stem = Path(e["dialog"]).stem
        ops = []
        for comp, sp in sorted(e.get("new_speakers", {}).items(), key=lambda x: x[1]["index"]):
            ops.append({"op": "add_speaker", "key": comp.lower(), "character": sp["character"], "index": sp["index"],
                        "mapping": str(uuid.uuid5(uuid.UUID(MOD), f"{stem}:{comp}")), "timeline": "companion"})
        for n in e["nodes"]:
            ops.append({"op": "add_node", "like": n["node"], "speaker": n["slot"], "move_slot": [1, n["slot"]],
                        "derive": {"ns": MOD, "tag": str(n["slot"])}, "_companion": n["companion"],
                        "conditions_add": [
                            {"type": "Tag", "flag": comp_tag[n["companion"]], "value": False, "slot": 1},
                            {"type": "Global", "flag": ENABLED_FLAG, "value": True}]})
        patch = {"format": "dialogkit/1", "id": "team-effort/companion-lines", "mod": MOD, "dialog": stem,
                 "_note": "Сгенерировано scripts/research/select_lines.py, руками не править. "
                          "Вариант героя «только для <спутника>» — копия, которую говорит сам спутник.",
                 "ops": ops}
        (OUT / f"{stem}.json").write_text(json.dumps(patch, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{sum(total.values())} вариантов в {len(picked)} диалогах:", dict(total.most_common()))
    print("пропущено:", dict(skipped))


if __name__ == "__main__":
    main()
