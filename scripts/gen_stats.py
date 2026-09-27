#!/usr/bin/env python3
"""Генерирует статусы помощи отряда, настройки MCM и все тексты мода (EN и RU).

  mod/Public/_MOD_/Stats/Generated/Data/TE_SkillAssist.txt
  mod/Mods/_MOD_/MCM_blueprint.json
  mod/Mods/_MOD_/Localization/English/TeamEffort_en.xml
  mod/Mods/_MOD_/Localization/Russian/TeamEffort_ru.xml

На каждый навык — MAX_BONUS статусов TE_SKILLASSIST_<Навык>_<N> с Boosts Skill(<Навык>, N) и общим
StackId: одновременно висит только один статус навыка. Список навыков и MAX_BONUS должны совпадать
с Lua/Server/SkillAssist.lua. Термины RU сверены по loca игры: «Отряд», «Проверка навыка», «Ловкость рук».

Тексты — одна таблица TEXT (как в AutoStackMerge): игра сама выбирает язык. Хэндлы строк хранятся
в data/handles.json и между сборками не меняются. В текстах MCM нет символов – — … “ ” ‘ ’ №:
MCM рисует их шрифтом ImGui.

  python scripts/gen_stats.py
"""
import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HANDLES = ROOT / "data/handles.json"
MOD_UUID = "c226c99d-720c-4611-98c9-9ba1fe6df481"
SKILLS = [
    "Athletics", "Acrobatics", "SleightOfHand", "Stealth",
    "Arcana", "History", "Investigation", "Nature", "Religion",
    "AnimalHandling", "Insight", "Medicine", "Perception", "Survival",
    "Deception", "Intimidation", "Performance", "Persuasion",
]
MAX_BONUS = 30

# ключ: (English, Русский)
TEXT = {
    "status_name": ("Party Know-How", "Опыт отряда"),
    "status_desc": ("The most skilled member of your party lends their experience to this check.",
                    "Самый умелый в отряде помогает вам в этой проверке навыка."),
    "mod_name": ("Team Effort", "Общими силами"),
    "mod_desc": ("The whole party pitches in: companions lend their skills to checks and speak their own "
                 "unique dialogue lines.",
                 "Весь отряд в деле: спутники помогают в проверках навыков и говорят свои уникальные реплики."),
    "tab_general": ("General", "Основное"),
    "sec_checks": ("Party help with checks", "Помощь отряда в проверках"),
    "dialogue_assist_name": ("In conversations", "В беседах"),
    "dialogue_assist_desc": (
        "At the start of a conversation each speaker gets a bonus to skills up to the level of the best party "
        "member. The bonus is removed when the conversation ends.",
        "В начале беседы каждый говорящий получает бонус к навыкам до уровня лучшего в отряде. "
        "После беседы бонус снимается."),
    "tool_assist_name": ("Locks and traps", "Замки и ловушки"),
    "tool_assist_desc": (
        "Picking a lock or disarming a trap gets a Sleight of Hand bonus up to the level of the best party member.",
        "Взлом замка и обезвреживание ловушки получают бонус к Ловкости рук до уровня лучшего в отряде."),
    "sec_lines": ("Companion lines", "Реплики спутников"),
    "companion_lines_name": ("Companion lines in conversations", "Реплики спутников в беседах героя"),
    "companion_lines_desc": (
        "Unique dialogue options of companions (for example Shadowheart) appear in the main character's "
        "conversations, and the companion says them.",
        "Уникальные варианты ответа спутников (например, Шэдоухарт) видны в беседах героя, "
        "и говорит их сам спутник."),
    "sec_debug": ("Debug", "Отладка"),
    "debug_log_name": ("Detailed log", "Подробный журнал"),
    "debug_log_desc": ("Write skill comparisons to the Script Extender console.",
                       "Писать сравнение навыков в консоль Script Extender."),
}
# хэндлы, выданные до data/handles.json (статус уже в игре под ними)
LEGACY = {"status_name": "h839d0d66g0497g4e70g8ccdgcc5aa7806629",
          "status_desc": "h77a9cf58ge1feg4585ga1edg39e32ee4c1f0"}
FORBIDDEN = "–—…“”‘’№"


def handles():
    h = json.loads(HANDLES.read_text(encoding="utf-8")) if HANDLES.exists() else {}
    for key in TEXT:
        if key not in h:
            u = uuid.uuid4().hex
            h[key] = LEGACY.get(key) or f"h{u[:8]}g{u[8:12]}g{u[12:16]}g{u[16:20]}g{u[20:]}"
    HANDLES.parent.mkdir(parents=True, exist_ok=True)
    HANDLES.write_text(json.dumps(h, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return h


def blueprint(h):
    def setting(sid, default):
        return {"Id": sid, "Name": TEXT[sid + "_name"][0], "Description": TEXT[sid + "_desc"][0],
                "Handles": {"NameHandle": h[sid + "_name"], "DescriptionHandle": h[sid + "_desc"]},
                "Type": "checkbox", "Default": default}

    def section(sec_id, key, settings):
        return {"SectionId": sec_id, "SectionName": TEXT[key][0], "Handles": {"NameHandle": h[key]},
                "Settings": settings}

    return {
        "SchemaVersion": 11,
        "ModName": TEXT["mod_name"][0],
        "Handles": {"NameHandle": h["mod_name"], "DescriptionHandle": h["mod_desc"]},
        "ModUUID": MOD_UUID,
        "Tabs": [{
            "TabName": TEXT["tab_general"][0], "Handles": {"NameHandle": h["tab_general"]}, "TabId": "general",
            "Sections": [
                section("checks", "sec_checks", [setting("dialogue_assist", True), setting("tool_assist", True)]),
                section("lines", "sec_lines", [setting("companion_lines", True)]),
                section("debug", "sec_debug", [setting("debug_log", False)]),
            ],
        }],
    }


def stats(h):
    out = [
        'new entry "TE_SKILLASSIST_BASE"',
        'type "StatusData"',
        'data "StatusType" "BOOST"',
        f'data "DisplayName" "{h["status_name"]};1"',
        f'data "Description" "{h["status_desc"]};1"',
        'data "Icon" "Action_Help"',
        'data "StatusPropertyFlags" "DisableOverhead;DisablePortraitIndicator;DisableCombatlog"',
        "",
    ]
    for skill in SKILLS:
        for n in range(1, MAX_BONUS + 1):
            out += [
                f'new entry "TE_SKILLASSIST_{skill}_{n}"',
                'type "StatusData"',
                'data "StatusType" "BOOST"',
                'using "TE_SKILLASSIST_BASE"',
                f'data "StackId" "TE_SKILLASSIST_{skill}"',
                f'data "Boosts" "Skill({skill}, {n})"',
                "",
            ]
    # Замки и ловушки (Lua/Server/ToolAssist.lua): игра снимает статус сама по окончании взлома.
    out += [
        'new entry "TE_TOOLASSIST_BASE"',
        'type "StatusData"',
        'data "StatusType" "BOOST"',
        'using "TE_SKILLASSIST_BASE"',
        'data "RemoveEvents" "OnLockpickingFinished;OnDisarmingFinished"',
        "",
    ]
    for n in range(1, MAX_BONUS + 1):
        out += [
            f'new entry "TE_TOOLASSIST_SleightOfHand_{n}"',
            'type "StatusData"',
            'data "StatusType" "BOOST"',
            'using "TE_TOOLASSIST_BASE"',
            'data "StackId" "TE_TOOLASSIST_SleightOfHand"',
            f'data "Boosts" "Skill(SleightOfHand, {n})"',
            "",
        ]
    return "\n".join(out)


def loca(h, idx):
    esc = lambda t: t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    rows = "".join(f'  <content contentuid="{h[k]}" version="1">{esc(v[idx])}</content>\n' for k, v in TEXT.items())
    return f'<?xml version="1.0" encoding="utf-8"?>\n<contentList>\n{rows}</contentList>\n'


def write(rel, text):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")
    print(rel)


def main():
    bad = {k: c for k, v in TEXT.items() for t in v for c in t if c in FORBIDDEN}
    if bad:
        raise SystemExit(f"символы, которые MCM не рисует: {bad}")
    h = handles()
    write("mod/Public/_MOD_/Stats/Generated/Data/TE_SkillAssist.txt", stats(h))
    write("mod/Mods/_MOD_/MCM_blueprint.json", json.dumps(blueprint(h), ensure_ascii=False, indent=4) + "\n")
    for i, lang in enumerate(("English", "Russian")):
        write(f"mod/Mods/_MOD_/Localization/{lang}/TeamEffort_{lang[:2].lower()}.xml", loca(h, i))


if __name__ == "__main__":
    main()
