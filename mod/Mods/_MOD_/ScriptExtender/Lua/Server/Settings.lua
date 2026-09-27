-- Настройки MCM (MCM_blueprint.json, генерирует scripts/gen_stats.py). Без MCM — значения по умолчанию.
-- «Реплики спутников» — это глобальный флаг TE_CompanionLines_Enabled: копии вариантов в диалогах
-- видны, только пока он стоит, поэтому выключаются без перезапуска.

local MOD_UUID = "c226c99d-720c-4611-98c9-9ba1fe6df481"
local FLAG = "TE_CompanionLines_Enabled_018440f2-8807-53d4-b844-1cde8a1c4e30"
local NULL = "NULL_00000000-0000-0000-0000-000000000000"
local DEFAULTS = {
    dialogue_assist = true,
    tool_assist = true,
    companion_lines = true,
    debug_log = false,
}

function TE.Setting(id)
    local ok, v = pcall(function()
        return Mods.BG3MCM.MCMAPI:GetSettingValue(id, MOD_UUID)
    end)
    if ok and v ~= nil then
        return v
    end
    return DEFAULTS[id]
end

local function syncCompanionLines()
    if TE.Setting("companion_lines") then
        Osi.SetFlag(FLAG, NULL, 0, 1)
    else
        Osi.ClearFlag(FLAG, NULL, 0, 1)
    end
end

Ext.Osiris.RegisterListener("LevelGameplayStarted", 2, "after", syncCompanionLines)

pcall(function()
    Ext.ModEvents.BG3MCM["MCM_Setting_Saved"]:Subscribe(function(data)
        if data and data.modUUID == MOD_UUID and data.settingId == "companion_lines" then
            syncCompanionLines()
        end
    end)
end)
