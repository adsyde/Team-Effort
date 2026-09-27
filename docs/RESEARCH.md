# Исследование (2026-09-27)

Всё ниже проверено по распакованным пакам игры (`../AlfiraCompanion/game-data`, Patch 8 Hotfix 9)
и по распакованным модам других авторов. Их файлы изучаем, но не копируем.

## Проверки навыков в беседах

- Бросок делает узел диалога `ActiveRoll`: поля `RollType` (`SkillCheck`…), `Skill`, `Ability`,
  `DifficultyClassID`, `Advantage`. Бросает `speaker` — слот говорящего: из 3329 таких узлов 2444 — слот 1
  (герой), 787 — слоты 2–5, 98 — слот 0. `RollTargetSpeaker` — против кого бросок.
  Флаги `ExcludeSpeakerOptionalBonuses` / `ExcludeCompanionsOptionalBonuses` управляют
  необязательными бонусами (например, «Наставление» от спутника).
- **Сменить бросающего нельзя** — только того, кто ведёт беседу. Поэтому передаём число:
  временный бонус `Skill(<Навык>, N)`.
- Игроки беседы: `DialogGetInvolvedPlayer(inst, i)`, i = 1… (игра заполняет ими
  `DB_DialogPlayers(inst, игрок, i)` в `Shared/__AAA_FirstGoal.txt`).
- Сигнатуры запросов (из `story_header.div`): `CalculatePassiveSkill(GUIDSTRING, STRING, out INTEGER)`,
  `HasSkill(CHARACTER, STRING, out INTEGER)`, `RemoveStatus(GUIDSTRING, STRING, GUIDSTRING)`,
  `DialogStarted/DialogEnded(DIALOGRESOURCE, INTEGER)`.

### Чужие моды на эту тему

| Мод | Как устроен |
|---|---|
| Best in Party Skills (imCioco, Nexus 20091, v2.6.0.7, 2026-05) | Чистый Osiris. На `DialogStarted` сравнивает `CalculatePassiveSkill` героя со спутниками (`IsInPartyWith`) и вешает статус `<НАВЫК>_BUFF_<СПУТНИК>` с `Skill(X, 1)` и флагом `MultiplyEffectsByDuration`; длительность = разница × 6 с. Снимает на `DialogEnded`. Перенос преимущества закомментирован. Отдельно — замки, ловушки, карманы, скрытность (переключатели). |
| Use highest modifier (PlainOldCookies, Nexus 2171, v1.13, 2023) | То же на Lua (`Osi.HasSkill`), статусы на каждого спутника. |

Наш вариант: бессрочный статус на каждое значение (`PV_SKILLASSIST_<Навык>_<N>`, 1–30, общий
StackId), снимается в конце беседы и при загрузке уровня. Так бонус не зависит от того, тикает ли
длительность статуса во время беседы.

## Уникальные реплики спутников

- Вариант «только для Шэдоухарт» — обычный ответ героя (`TagQuestion`) с условием
  «у говорящего есть тег `REALLY_SHADOWHEART`» (`checkflags` → `flaggroup type=Tag`, `paramval` = слот).
  Реплики озвучены актёром спутника и переведены в loca игры.
- Сколько таких узлов (все 9220 диалогов): Карлах 252, Астарион 184, Уилл 179, Лаэзель 175,
  Шэдоухарт 172, Гейл 128, Джахейра 14, Минтара 14, Хальсин 7, Минск 7 — всего 1132;
  с Тёмным Соблазном (`REALLY_DARK_URGE`, 586) — 397 файлов. Слот в условии: 1 — в 1425 случаях,
  2–28 — в остальных.
- Такими же тегами на слоте 1 закрыты варианты по классу и расе (`PALADIN`, `BARD`, `TIEFLING`…).
- Готового мода «выбрать реплику спутника» не нашли. Близкие:
  - **More Reactive Companions** (LightningLarryL) — Lua: на `AutomatedDialogStarted` для
    автоматических сценок (`_PAD_`, `_VB_`, не `GLO_`/`ORI_`) останавливает сценку и запускает
    её заново (`QRY_StartDialog_Fixed`) со случайным спутником в 12 м как говорящим.
    Выбора в меню нет.
  - **Swap Origin And Companion** (Nexus 9486) — меняет героя и спутника местами на всю игру
    (ломает лагерь и палатки).
  - **Everyone In Dialogue** (Nexus 3206) — статус, с которым персонаж участвует в беседах издалека.
