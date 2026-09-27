-- Замки и ловушки: взлом воровскими инструментами и обезвреживание ловушки — проверка «Ловкости рук»
-- (так в описании инструментов в игре). Тот, кто взламывает, получает бонус до уровня лучшего в отряде:
-- статус TE_TOOLASSIST_SleightOfHand_<N>. Игра снимает его сама (RemoveEvents OnLockpickingFinished;
-- OnDisarmingFinished), здесь — ещё раз на остановке и при загрузке уровня.

local SKILL = "SleightOfHand"
local active = {}   -- [персонаж] = статус

local function status(bonus)
    return string.format("TE_TOOLASSIST_%s_%d", SKILL, bonus)
end

local function stop(char)
    if active[char] then
        TE.ClearStatuses(char, { active[char] })
        active[char] = nil
    end
end

local function start(char)
    stop(char)
    local bonus, who = TE.BestHelper(char, SKILL)
    if bonus then
        active[char] = status(bonus)
        Osi.ApplyStatus(char, active[char], -1, 1, who)
    end
end

Ext.Osiris.RegisterListener("RequestCanLockpick", 3, "before", function(char) start(char) end)
Ext.Osiris.RegisterListener("RequestCanDisarmTrap", 3, "before", function(char) start(char) end)
Ext.Osiris.RegisterListener("StoppedLockpicking", 2, "after", function(char) stop(char) end)
Ext.Osiris.RegisterListener("StoppedDisarmingTrap", 2, "after", function(char) stop(char) end)

Ext.Osiris.RegisterListener("LevelGameplayStarted", 2, "after", function()
    active = {}
    local all = {}
    for n = 1, TE.MaxBonus do
        all[#all + 1] = status(n)
    end
    for _, row in pairs(Osi.DB_Players:Get(nil) or {}) do
        TE.ClearStatuses(row[1], all)
    end
end)
