#!/usr/bin/env python3
"""Сверка вариантов «all» (DialogKit) после сборки: в каждом — все узлы игры, все новые узлы Team Effort
и партнёра, и ничего сверх; узлы обоих модов не изменены (кроме добавленных детей), порядок детей и корней
сохранён, слоты и UUID диалога совпадают.

Нужны свежие сборки обоих модов: Team Effort — `scripts/build_pak.py` (mod/), партнёр — своя сборка
DialogKit (для SuccubusPlus — `make_mod.py`, каталог `build_dk/`).

  python scripts/check_all.py [каталог own-варианта партнёра]
"""
import copy
import sys
import xml.etree.ElementTree as ET

from common import ROOT, config, enable_utf8_stdout, resolve

enable_utf8_stdout()
cfg = config()
sys.path.insert(0, str(resolve(cfg["dialogkit"]["path"])))
from dialogkit import lsx  # noqa: E402
from dialogkit.patch import Dialog  # noqa: E402

ALL = ROOT / "mod/Mods/_MOD_/DialogKit/all"
TE = ROOT / "mod/Mods/_MOD_/Story/DialogsBinary"
PARTNER = resolve(sys.argv[1] if len(sys.argv) > 1 else "../SuccubusPlus/build_dk/Mods/_MOD_/Story/DialogsBinary")
FILES = resolve(cfg["dialogkit"]["cache"]) / "files/Gustav/Mods"
GAME = [FILES / m / "Story/DialogsBinary" for m in ("GustavDev", "Gustav")]


def load(p):
    return Dialog(lsx.load(p))


def stripped(n):
    n = copy.deepcopy(n)
    h = lsx.kid(n, "children")
    if h is not None:
        n.find("children").remove(h)
    return ET.tostring(n)


def subseq(a, b):
    it = iter(b)
    return all(x in it for x in a)


def root_ids(d):
    return [a.get("value") for r in d.roots() for a in r.findall("attribute")]


def slots(d):
    return {i: ET.tostring(s) for i, s in d.slots().items()}


def check(rel):
    g = load(next(d / rel for d in GAME if (d / rel).exists()))
    mods = {"TE": load(TE / rel), "партнёр": load(PARTNER / rel)}
    al = load(ALL / rel)
    errs, expect, new = [], set(g.by_id), {}
    for name, m in mods.items():
        if set(g.by_id) - set(m.by_id):
            errs.append(f"{name}: в own-варианте пропал узел игры")
        new[name] = set(m.by_id) - set(g.by_id)
        expect |= new[name]
    if set(al.by_id) != expect:
        errs.append(f"узлы: лишних {len(set(al.by_id) - expect)}, нет {len(expect - set(al.by_id))}")
    for name, m in mods.items():
        for nid, n in m.by_id.items():
            a = al.by_id.get(nid)
            if a is None:
                continue
            if stripped(a) != stripped(n):
                errs.append(f"{name} {nid}: узел изменён")
            if not subseq(m.children_of(n), al.children_of(a)):
                errs.append(f"{name} {nid}: дети не сохранены")
        if not subseq(root_ids(m), root_ids(al)):
            errs.append(f"{name}: корни не сохранены")
        if any(slots(al).get(i) != s for i, s in slots(m).items()):
            errs.append(f"{name}: слоты не совпадают")
        if lsx.value(m.root, "UUID") != lsx.value(al.root, "UUID"):
            errs.append(f"{name}: UUID диалога разный")
    for nid, a in al.by_id.items():
        known = set().union(*(m.children_of(m.by_id[nid]) for m in mods.values() if nid in m.by_id))
        if set(al.children_of(a)) - known:
            errs.append(f"{nid}: дети ниоткуда")
    print(f"{rel.as_posix()}: игра {len(g.by_id)}, +TE {len(new['TE'])}, +партнёр {len(new['партнёр'])}, "
          f"all {len(al.by_id)} — {'OK' if not errs else 'ОШИБКИ'}")
    for e in errs[:10]:
        print("   ", e)
    return not errs


if __name__ == "__main__":
    files = sorted(ALL.rglob("*.lsf.lsx")) if ALL.exists() else []
    if not files:
        print("вариантов «all» нет")
    sys.exit(0 if all([check(f.relative_to(ALL)) for f in files]) else 1)
