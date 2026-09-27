#!/usr/bin/env python3
"""Генерирует статусы помощи отряда в проверках и их тексты.

  mod/Public/_MOD_/Stats/Generated/Data/TE_SkillAssist.txt
  mod/Mods/_MOD_/Localization/English/TeamEffort_en.xml
  mod/Mods/_MOD_/Localization/Russian/TeamEffort_ru.xml

На каждый навык — MAX_BONUS статусов TE_SKILLASSIST_<Навык>_<N> с Boosts Skill(<Навык>, N) и общим
StackId: одновременно висит только один статус навыка. Список навыков и MAX_BONUS должны совпадать
с Lua/Server/SkillAssist.lua. Термины RU сверены по loca игры: «Отряд», «Проверка навыка».

  python scripts/gen_stats.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = [
    "Athletics", "Acrobatics", "SleightOfHand", "Stealth",
    "Arcana", "History", "Investigation", "Nature", "Religion",
    "AnimalHandling", "Insight", "Medicine", "Perception", "Survival",
    "Deception", "Intimidation", "Performance", "Persuasion",
]
MAX_BONUS = 30
NAME = "h839d0d66g0497g4e70g8ccdgcc5aa7806629"
DESC = "h77a9cf58ge1feg4585ga1edg39e32ee4c1f0"
TEXTS = {
    "English": {
        NAME: "Party Know-How",
        DESC: "The most skilled member of your party lends their experience to this check.",
    },
    "Russian": {
        NAME: "Опыт отряда",
        DESC: "Самый умелый в отряде помогает вам в этой проверке навыка.",
    },
}


def stats():
    out = [
        'new entry "TE_SKILLASSIST_BASE"',
        'type "StatusData"',
        'data "StatusType" "BOOST"',
        f'data "DisplayName" "{NAME};1"',
        f'data "Description" "{DESC};1"',
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
    return "\n".join(out)


def loca(texts):
    rows = "".join(f'  <content contentuid="{h}" version="1">{t}</content>\n' for h, t in texts.items())
    return f'<?xml version="1.0" encoding="utf-8"?>\n<contentList>\n{rows}</contentList>\n'


def write(rel, text):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")
    print(rel)


def main():
    write("mod/Public/_MOD_/Stats/Generated/Data/TE_SkillAssist.txt", stats())
    for lang, texts in TEXTS.items():
        write(f"mod/Mods/_MOD_/Localization/{lang}/TeamEffort_{lang[:2].lower()}.xml", loca(texts))


if __name__ == "__main__":
    main()
