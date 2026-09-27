# Team Effort («Общими силами»)

Мод для Baldur's Gate 3 (Patch 8 Hotfix 9). Нужен [Script Extender](https://github.com/Norbyte/bg3se).

Весь отряд участвует в деле, а не только тот, кто ведёт беседу.

- **Помощь в проверках** (0.1.0, проверяется). В начале беседы каждый говорящий получает бонус
  «Опыт отряда» к навыкам — до уровня лучшего в отряде. После беседы бонус снимается.
  То же при взломе замков и обезвреживании ловушек («Ловкость рук»). Дальше в плане: карманы, скрытность.
- **Реплики спутников** (в работе, прототип). Уникальные варианты ответа спутников (например, Шэдоухарт)
  видны в беседе героя, и говорит их сам спутник. Как и все варианты игрока в BG3, они без озвучки.

Не включайте вместе с Best in Party Skills и Use highest modifier: бонусы сложатся.

## Сборка

```
python scripts/build_pak.py    # dist/TeamEffort.pak
python scripts/install.py      # в игру; BG3 и BG3 Mod Manager закрыты
```

Пути к Divine и игре — в `config/tools.local.json` (образец — `tools.local.example.json`).

---

*Team Effort* — BG3 mod: party members lend their skills to checks and speak their own unique
dialogue lines (unvoiced, like all player lines) in the main character's conversations. Requires Script Extender.
