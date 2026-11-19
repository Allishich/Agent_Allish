# Research data for Agent_Allish

Начните с [START_HERE.md](START_HERE.md). В каталоге находится автономная копия 43 статистических наборов (один крупный набор разбит на 8 CSV-частей), 29 паспортов, навигация AI_CONTEXT, исходные каталоги и QA.

Репозиторные пути записаны в [AI_CONTEXT/manifest.json](AI_CONTEXT/manifest.json). Для поиска по вопросам используйте [AI_CONTEXT/routing.json](AI_CONTEXT/routing.json), для ограничений — [AI_CONTEXT/data_rules.md](AI_CONTEXT/data_rules.md).

Проверка: `python research_data/tools/validate_package.py`. Восстановление крупного CSV: `python research_data/tools/reconstruct_large_csv.py`.

**Исходные файлы и другие каталоги репозитория не менялись.** Этот пакет предлагается через отдельный PR для проверки Алиной.
