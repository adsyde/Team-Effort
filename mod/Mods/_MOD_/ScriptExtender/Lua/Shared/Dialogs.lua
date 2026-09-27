-- Правленые диалоги (сервер и клиент): какой вариант включить, решает DialogKit по включённым модам и
-- порядку загрузки. Файлы DialogKit.lua и DialogKitManifest.lua кладёт сборка (scripts/dialogs.py).
local DialogKit = Ext.Require("Shared/DialogKit.lua")
Ext.Require("Shared/DialogKitManifest.lua")

DialogKit.Apply("c226c99d-720c-4611-98c9-9ba1fe6df481", DialogKitManifest, function(fmt, ...)
    _P("[TeamEffort] DialogKit: " .. string.format(fmt, ...))
end)
