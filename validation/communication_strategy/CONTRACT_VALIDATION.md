# Проверка протокола Communication Strategy v0.1

## Что проверяется

Файл `contracts.json` — JSON Schema Draft 2020-12 с **корневым `oneOf`**. При проверке всего документа явно выбирается один из типов:

| Тип | Путь к схеме | Особенности |
| --- | --- | --- |
| Запрос | `#/$defs/module_request` | Только семь поддерживаемых действий; обязательные поля по действию |
| Ответ | `#/$defs/module_response` | Статус, запрос и ревизия, артефакты, ограничения, ошибки, следующие действия |
| Метод | `#/$defs/method_record` | M01–M12, C01–C06, `native_result`, ссылки, источник, версия |
| Этап | `#/$defs/stage_record` | Этап C01–C06, методы, доказательства, результат/ограничения |
| Состояние | `#/$defs/case_state` | Строго C01–C06, статусы методов, ревизия, история результатов |
| Стратегия | `#/$defs/strategy` | Шесть ссылок на этапы, минимум три альтернативы, включая `status_quo` |

Поля, не предусмотренные типом, запрещены на уровне оболочки (`additionalProperties:false`). `native_result` намеренно остаётся гибким: его обязательное содержание определяет **исходная** `methods/Mxx.yaml#outputs.required`, а не общая оболочка.

## Критические условия

- `start_case`: полный подтверждённый `confirmed_brief`, `product_strategy_outline` (объект или `null`), `expected_revision=0`.
- `run_next_stage`, `approve_stage`, `attach_human_data`, `update_brief`: `expected_revision` локального состояния.
- `approve_stage`: `stage_id` и фактическое `parent_approval=true`. Несогласованный результат не объявлять согласованным.
- `attach_human_data`: `method_id` и хотя бы один `data_artifacts` с разрешённым источником.
- `update_brief`: подтверждённый `updated_brief`, без перезаписи исходного файла `common_intake`.
- `module_response.status=blocked`: непустой `errors`. `status=awaiting_parent`: `awaiting_parent_confirmation=true` и конкретный `stage_id`. `needs_human_data`: непустой `data_requests`.
- Любой `artifacts[].saved=false` требует присутствующего `content`. `saved=true` — только после фактически подтверждённой записи.
- `method_record.status=completed` требует `native_result`-объекта; `awaiting_data` — непустого `data_requests`.
- `case_state` включает шесть статусов C01–C06 и **отдельные** `source_brief_revision` и `revision`.
- `strategy` остаётся draft, даже если все этапы выполнены; полнота полей не делает выводы доказанными.

## Сквозные инварианты, которые не обеспечивает одна JSON Schema

Исполнитель и/или принимающая платформа **дополнительно** проверяют:

1. Совпадение `case_id` в запросе, `confirmed_brief`, продуктовом `strategy_outline`, `case_state`, результатах и артефактах.
2. Полный исходный бриф по `validation/common_intake/brief.schema.json`, продуктовый каркас — по `validation/product_strategy/contracts.json#/$defs/strategy_outline`; их происхождение и доступность.
3. Актуальность `expected_revision` относительно **коммуникационного** `case_state.revision`; `brief.revision` является отдельным счётчиком.
4. Разрешение путей только в `cases/{case_id}/communication_strategy/`, не в `product_strategy/` и не в общем `brief.json`.
5. Соответствие `method_id` родному Cxx по `method_routing.yaml`; соответствие полей `native_result` YAML-методике.
6. Наличие реального согласия пользователя и подтверждённого сохранения. Схема не умеет проверять эти события.
7. Фактическую достоверность документов и источников. Валидный JSON не является доказательством рынка.

## Воспроизводимые разработческие проверки

В каталоге `examples/` находятся **синтетические** примеры всех типов. Действующий `start_case` — в `validation/common_intake/examples/communication_start_case.request.json`.

При наличии Python, `jsonschema` и `PyYAML` можно локально выполнить **необязательный для работы агента** набор проверок:

```bash
python -m pip install jsonschema pyyaml
python validation/communication_strategy/tests/validate_contracts.py
```

Тест проверяет положительные объекты, негативные варианты, полную схему исходного брифа, независимую схему продуктового каркаса, родной этап метода и границы путей. Реальный LLM-вызов, файловое сохранение и источники тест не проверяет.

Нельзя считать отсутствие запуска теста доказательством его прохождения. Примеры показывают **форматы**, а не реальные завершённые исследования.
