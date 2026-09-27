PV = PV or {}
PV.Debug = false

function PV.Log(fmt, ...)
    if PV.Debug then
        _P("[PartyVoices] " .. string.format(fmt, ...))
    end
end

-- В консоли Script Extender: !pv_debug — включить/выключить подробный журнал.
Ext.RegisterConsoleCommand("pv_debug", function()
    PV.Debug = not PV.Debug
    _P("[PartyVoices] журнал " .. (PV.Debug and "включён" or "выключен"))
end)

Ext.Require("Server/SkillAssist.lua")
