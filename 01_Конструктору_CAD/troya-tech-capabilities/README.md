# troya-tech-capabilities — скилл «Технологические возможности TROYA»

Эталонная папка скилла. Формат `SKILL.md` + `references/` + `scripts/` + `data/` понимают Claude Code, Antigravity и Codex.

## Установка и обновление

```
python scripts/install.py
```

Копирует папку в `~/.claude/skills`, `~/.gemini/config/skills` (Antigravity) и `~/.codex/skills`.

## Для других инструментов (ChatGPT, Cursor, Copilot, DeepSeek и т. п.)

- Инструменты с правилами проекта (Cursor, Windsurf, Copilot): добавьте `SKILL.md` в правила проекта
  или положите рядом `AGENTS.md` со ссылкой на эту папку. В папке «Технологические возможности» такой `AGENTS.md` уже есть.
- Чат-ассистенты без доступа к диску: приложите `SKILL.md`, `references/machines.md` и `data/dfm_rules.csv`
  (при вопросах по трубе — ещё `data/tube_capabilities.json`) и попросите следовать `SKILL.md`.

## Состав

| Файл | Что внутри |
|---|---|
| `SKILL.md` | порядок оценки технологичности, краткие пределы, ловушки |
| `references/machines.md` | подробные характеристики станков |
| `references/report-template.md` | шаблон отчёта о технологичности |
| `data/equipment.csv` | реестр оборудования (из ОС.xls, без стоимости) |
| `data/tube_capabilities.json` | труборез, трубогибы, оснастка (R, L1, L2) |
| `data/dfm_rules.csv` | правила для КД с кодами и статусом достоверности |
| `data/gaps.csv` | чего не хватает: что запросить у технологов и механиков |
| `scripts/check_tube.py` | проверка трубной детали: труборез + гибка + оснастка |
| `scripts/build_registry.py` | ОС.xls → equipment.csv + Excel для инженеров |
| `scripts/make_xlsx.py` | сборка Excel (вызывается из build_registry.py) |
| `scripts/install.py` | раскладка скилла по инструментам |

Зависимости: Python 3.10+, `openpyxl`, `xlrd` (только для чтения ОС.xls).
