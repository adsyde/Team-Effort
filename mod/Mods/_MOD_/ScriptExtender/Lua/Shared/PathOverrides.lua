-- Подмена диалогов игры нашими копиями (сервер и клиент). Список генерирует scripts/companion_lines.py.
-- Класть файлы по пути игры (Mods/GustavDev/...) в пак нельзя: вторая папка Mods/* без meta.lsx
-- идёт по алфавиту раньше нашей, и мод пропадает из списка.
Ext.Require("Shared/Overrides.lua")

for from, to in pairs(TE.DialogOverrides or {}) do
    Ext.IO.AddPathOverride(from, to)
end
