# Техническая проверка v0.1

## Проверки

- Все YAML-файлы должны разбираться как YAML; все JSON — как JSON.
- `examples/brief.confirmed.example.json` должен проходить `brief.schema.json`.
- `examples/communication_context.draft.json` должен проходить `communication_context.schema.json`.
- `examples/product_start_case.request.json` должен проходить **действующую** `validation/product_strategy/contracts.json` v0.2; для этого используется JSON Schema 2020-12 из существующего продуктового комплекта.
- Отрицательные проверки: неподтверждённый бриф со статусом `confirmed`, пустой `decision_question`, неизвестный ключ на верхнем уровне, неотмеченное поле `user_confirmed_brief` должны отклоняться.
- `examples/communication_context.draft.json` по-прежнему остаётся историческим примером с `proposed_not_approved`; **не** использовать его в качестве активного входа.
- Новый `examples/communication_start_case.request.json` должен проходить `validation/communication_strategy/contracts.json#/$defs/module_request`; вложенный `confirmed_brief` независимо проходит `brief.schema.json`, а переданный продуктовый каркас — `validation/product_strategy/contracts.json#/$defs/strategy_outline`.
- При `start_case` отклонять отсутствие `confirmed_brief`, `null`, незавершённый или неподтверждённый бриф и отсутствие поля `product_strategy_outline` (его значение может быть `null`). Совпадение `case_id` разных документов проверять исполнителем; стандартная JSON Schema не обеспечивает сравнение значений разных путей.
- Для всех объектов коммуникационного модуля теперь действует корневой `oneOf` в `contracts.json`: `module_request`, `module_response`, `method_record`, `stage_record`, `case_state`, `strategy`. Доступны синтетические образцы и негативные проверки `validation/communication_strategy/tests/validate_contracts.py`. Межобъектное совпадение `case_id` и контроль ревизии остаются обязанностью исполнителя.

## Границы технических проверок

Схемы проверяют структуру и типы, **не** семантическую истинность, исследовательскую состоятельность или полноту источников. Проверка соответствия значения в `field_provenance.field_path` реально существующему пути и сохранения `discovery.md` требует хоста/исполнителя. Сама LLM, прочитав JSON Schema, не эквивалентна машинному валидатору.

Данные в `examples/` синтетические, не фактические сведения о рынке и не результаты реального исследования.

## Результат проверки образцов (21 ноября 2026)

Формальные JSON Schema проверены по Draft 2020-12; валидны примеры подтверждённого брифа, незавершённого интервью, продукта `start_case` по существующему `contracts.json`, чернового коммуникационного контекста. Шесть отрицательных случаев для подтверждённого брифа отклонены. Оба YAML корректно разобраны. Проверка проводится только локально при подготовке комплекта; в конечной LLM-среде валидатор может отсутствовать.
