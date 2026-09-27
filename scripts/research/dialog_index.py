#!/usr/bin/env python3
"""Индекс диалогов игры для второй части: узлы, говорящие, условия. Кэш — build/research/index.pkl.

Для каждого диалога: слоты говорящих (что в них: группа «Игроки» или конкретный персонаж) и узлы
(конструктор, говорящий, дети, теги в checkflags/setflags с номером слота).

  python scripts/research/dialog_index.py        # построить (≈10 мин на 9220 диалогов)
"""
import glob, json, os, pickle, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GD = (ROOT / "../AlfiraCompanion/game-data").resolve()
CACHE = ROOT / "build/research/index.pkl"
PLAYERS = "e0d1ff71-04a8-4340-ae64-9684d846eb83"
COMPANIONS = {
    "3ed74f06-3c60-42dc-83f6-f034cb47c679": "SHADOWHEART", "c7c13742-bacd-460a-8f65-f864fe41f255": "ASTARION",
    "ad9af97d-75da-406a-ae13-7071c563f604": "GALE", "58a69333-40bf-8358-1d17-fff240d7fb12": "LAEZEL",
    "c774d764-4a17-48dc-b470-32ace9ce447d": "WYLL", "2c76687d-93a2-477b-8b18-8a14b549304c": "KARLACH",
    "91b6b200-7d00-4d62-8dc9-99e8339dfa1a": "JAHEIRA", "0de603c5-42e2-4811-9dad-f652de080eba": "MINSC",
    "25721313-0c15-4935-8176-9f134385451b": "MINTHARA", "7628bc0e-52b8-42a7-856a-13a6fd413323": "HALSIN",
}


def v(o, k, d=None):
    x = o.get(k)
    return x.get("value", d) if isinstance(x, dict) else d


def flags(node, key):
    out = []
    for cf in node.get(key) or []:
        for g in cf.get("flaggroup") or []:
            t = g["type"]["value"]
            for fl in g.get("flag") or []:
                out.append((t, fl["UUID"]["value"], v(fl, "paramval"), v(fl, "value")))
    return out


def tag_names():
    names = {}
    for p in glob.glob(str(GD / "*/Public/*/Tags/*.lsx")) + glob.glob(str(GD / "*/Public/*/Flags/*.lsx")):
        m = re.search(r'id="Name"[^>]*value="([^"]*)"', open(p, encoding="utf-8").read())
        if m:
            names[os.path.basename(p)[:-4]] = m.group(1)
    return names


def parse(path):
    d = json.load(open(path, encoding="utf-8-sig"))
    dlg = d["save"]["regions"]["dialog"]
    slots = {}
    for sl in dlg.get("speakerlist") or []:
        for s in sl.get("speaker") or []:
            slots[int(v(s, "index"))] = v(s, "list", "")
    nodes = {}
    for group in dlg.get("nodes") or []:
        for n in group.get("node") or []:
            uid = v(n, "UUID")
            kids = [v(c, "UUID") for ch in n.get("children") or [] for c in ch.get("child") or []]
            texts = []
            for tt in n.get("TaggedTexts") or []:
                for t in tt.get("TaggedText") or []:
                    for tx in t.get("TagTexts") or []:
                        for x in tx.get("TagText") or []:
                            texts.append(x["TagText"].get("handle"))
            nodes[uid] = dict(c=v(n, "constructor"), sp=v(n, "speaker"), kids=kids, texts=texts,
                              check=flags(n, "checkflags"), set=flags(n, "setflags"),
                              skill=v(n, "Skill"), roots=None)
    roots = [v(r, "RootNodes") for rn in dlg.get("nodes") or [] for r in rn.get("RootNodes") or []]
    return dict(slots=slots, nodes=nodes, roots=roots)


def build():
    files = glob.glob(str(GD / "*/Mods/*/Story/Dialogs/**/*.lsj"), recursive=True)
    index = {}
    for i, f in enumerate(files):
        try:
            index[os.path.relpath(f, GD)] = parse(f)
        except Exception as e:
            print("skip", f, e, file=sys.stderr)
        if i % 1000 == 0:
            print(i, len(files))
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    pickle.dump(dict(index=index, tags=tag_names()), open(CACHE, "wb"))
    return index


def load():
    return pickle.load(open(CACHE, "rb"))


if __name__ == "__main__":
    build()
    print("ok", CACHE)
