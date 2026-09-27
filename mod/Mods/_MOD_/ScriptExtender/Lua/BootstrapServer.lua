TE = TE or {}
TE.Debug = false

function TE.Log(fmt, ...)
    if TE.Debug or (TE.Setting and TE.Setting("debug_log")) then
        _P("[TeamEffort] " .. string.format(fmt, ...))
    end
end

-- В консоли Script Extender: !te_debug — включить/выключить подробный журнал.
Ext.RegisterConsoleCommand("te_debug", function()
    TE.Debug = not TE.Debug
    _P("[TeamEffort] журнал " .. (TE.Debug and "включён" or "выключен"))
end)

Ext.Require("Shared/Dialogs.lua")
Ext.Require("Server/Settings.lua")
Ext.Require("Server/SkillAssist.lua")
Ext.Require("Server/ToolAssist.lua")
