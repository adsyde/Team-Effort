-- Проверки навыков в беседе: каждый игрок беседы получает бонус до уровня лучшего в отряде.
--
-- В диалоге бросает говорящий (узел ActiveRoll, поле speaker), заменить бросающего нельзя.
-- Поэтому передаём не бросок, а число: статус PV_SKILLASSIST_<Навык>_<N> с Boosts Skill(<Навык>, N),
-- где N — разница между лучшим в отряде и говорящим. Статусы генерирует scripts/gen_stats.py.
-- Статус бессрочный и снимается в конце беседы, а при загрузке уровня — подчищается на всякий случай.

local SKILLS = {
    "Athletics", "Acrobatics", "SleightOfHand", "Stealth",
    "Arcana", "History", "Investigation", "Nature", "Religion",
    "AnimalHandling", "Insight", "Medicine", "Perception", "Survival",
    "Deception", "Intimidation", "Performance", "Persuasion",
}
local MAX_BONUS = 30    -- столько статусов на навык создаёт gen_stats.py
local NULL = "NULL_00000000-0000-0000-0000-000000000000"

local byInstance = {}   -- [инстанс беседы] = { [uuid игрока] = { статусы } }

local function uuid(guid)
    return string.sub(guid, -36)
end

local function name(char)
    local handle = Osi.GetDisplayName(char)
    return handle and Osi.ResolveTranslatedString(handle) or char
end

local function status(skill, bonus)
    return string.format("PV_SKILLASSIST_%s_%d", skill, bonus)
end

-- Сравниваем пассивные значения навыков, как Best in Party Skills: в них уже учтены
-- характеристика, мастерство, компетентность и бонусы вещей. Что именно даёт движок
-- (и есть ли там +5 за преимущество) — проверяем в игре командой pv_debug.
local function skillValue(char, skill)
    return Osi.CalculatePassiveSkill(char, skill) or 0
end

local function helpersOf(char)
    local out = {}
    for _, row in pairs(Osi.DB_Players:Get(nil) or {}) do
        local m = row[1]
        if uuid(m) ~= uuid(char) and Osi.IsInPartyWith(m, char) == 1 and Osi.IsDead(m) ~= 1 then
            out[#out + 1] = m
        end
    end
    return out
end

local function clear(char, statuses)
    for _, s in ipairs(statuses) do
        Osi.RemoveStatus(char, s, NULL)
    end
end

local function assist(char)
    local helpers = helpersOf(char)
    local applied = {}
    for _, skill in ipairs(SKILLS) do
        local own = skillValue(char, skill)
        local best, who = own, nil
        for _, m in ipairs(helpers) do
            local v = skillValue(m, skill)
            if v > best then
                best, who = v, m
            end
        end
        if who then
            local s = status(skill, math.min(best - own, MAX_BONUS))
            Osi.ApplyStatus(char, s, -1, 1, who)
            applied[#applied + 1] = s
            PV.Log("%s, %s: %d (HasSkill %s); лучший %s: %d → %s", name(char), skill, own,
                tostring(Osi.HasSkill(char, skill)), name(who), best, s)
        end
    end
    return applied
end

Ext.Osiris.RegisterListener("DialogStarted", 2, "after", function(_, inst)
    local players = {}
    for i = 1, Osi.DialogGetNumberOfInvolvedPlayers(inst) or 0 do
        local char = Osi.DialogGetInvolvedPlayer(inst, i)
        if char and Osi.IsCharacter(char) == 1 and not players[uuid(char)] then
            players[uuid(char)] = { char = char, statuses = assist(char) }
        end
    end
    byInstance[inst] = players
end)

Ext.Osiris.RegisterListener("DialogEnded", 2, "after", function(_, inst)
    for _, p in pairs(byInstance[inst] or {}) do
        clear(p.char, p.statuses)
    end
    byInstance[inst] = nil
end)

-- Беседа могла оборваться без DialogEnded (вылет, выход в меню): снимаем все наши статусы.
Ext.Osiris.RegisterListener("LevelGameplayStarted", 2, "after", function()
    byInstance = {}
    local all = {}
    for _, skill in ipairs(SKILLS) do
        for n = 1, MAX_BONUS do
            all[#all + 1] = status(skill, n)
        end
    end
    for _, row in pairs(Osi.DB_Players:Get(nil) or {}) do
        clear(row[1], all)
    end
end)
