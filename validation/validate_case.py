#!/usr/bin/env python3
"""Offline validation of saved Agent_Allish records; not an agent executor."""
import argparse
import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:
    sys.exit("Install dependency: python -m pip install jsonschema>=4")

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = {
    "brief": ROOT / "validation/common_intake/brief.schema.json",
    "product": ROOT / "validation/product_strategy/contracts.json",
    "communication": ROOT / "validation/communication_strategy/contracts.json",
}
KINDS = {
    "brief.json": ("brief", None),
    "state.json": (None, "case_state"),
    "product_strategy_outline.json": ("product", "strategy_outline"),
    "communication_strategy_draft.json": ("communication", "strategy"),
    "communication_strategy.json": ("communication", "strategy"),
}

def schema_for(path):
    name = path.name
    if name == "brief.json":
        if path.parent.name == "product_strategy":
            return "product", "brief"
        if path.parent.name == "communication_strategy":
            return None, None
        return "brief", None
    if name == "state.json":
        return ("product" if path.parent.name == "product_strategy" else "communication"), "case_state"
    if name.endswith("_stage.json") or (name.startswith("C0") and name.endswith(".json") and "stages" in path.parts):
        return ("product" if "product_strategy" in path.parts else "communication"), "stage_record"
    if name.endswith(".json") and "methods" in path.parts:
        return ("product" if "product_strategy" in path.parts else "communication"), "method_record"
    return KINDS.get(name, (None, None))

def run(case_dir):
    errors = []
    schemas = {k: json.loads(p.read_text(encoding="utf-8")) for k, p in SCHEMAS.items()}
    for key, schema in schemas.items():
        Draft202012Validator.check_schema(schema)
    documents = []
    observed = set()
    for path in sorted(case_dir.rglob("*.json")):
        kind, definition = schema_for(path)
        if not kind:
            continue
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            schema = schemas[kind]
            if definition:
                if definition not in schema.get("$defs", {}):
                    errors.append(f"{path}: missing schema definition {definition}")
                    continue
                schema = {"$ref": f"#/$defs/{definition}", "$defs": schemas[kind]["$defs"],
                          "$schema": "https://json-schema.org/draft/2020-12/schema"}
            validator = Draft202012Validator(schema)
            for issue in validator.iter_errors(obj):
                errors.append(f"{path}: {list(issue.path)}: {issue.message}")
            documents.append((path, obj))
            observed.add(path.relative_to(case_dir).as_posix())
        except (OSError, ValueError) as exc:
            errors.append(f"{path}: {exc}")
    required = {"brief.json", "product_strategy/state.json", "communication_strategy/state.json"}
    for stage in range(1, 8):
        required.add(f"product_strategy/results/stages/{stage:02d}_stage.json")
    for stage in range(1, 7):
        required.add(f"communication_strategy/results/stages/C{stage:02d}.json")
    required.add("product_strategy/results/product_strategy_outline.json")
    # Communication final artifact has the module's actual persisted filename.
    if not ({"communication_strategy/results/communication_strategy.json",
             "communication_strategy/results/communication_strategy_draft.json"} & observed):
        errors.append(f"{case_dir}: missing mandatory communication strategy final artifact")
    for missing in sorted(required - observed):
        errors.append(f"{case_dir}: missing mandatory artifact {missing}")
    if not documents:
        errors.append(f"{case_dir}: no recognizable JSON artifacts")
    case_id = case_dir.name
    for path, obj in documents:
        if isinstance(obj, dict) and obj.get("case_id") != case_id:
            errors.append(f"{path}: case_id mismatch: {obj.get('case_id')} != {case_id}")
    brief = case_dir / "brief.json"
    if brief.exists():
        try:
            data = json.loads(brief.read_text(encoding="utf-8"))
            if data.get("interview_status") != "confirmed" or data.get("user_confirmed_brief") is not True:
                errors.append(f"{brief}: brief not confirmed by user")
        except (ValueError, OSError) as exc:
            errors.append(f"{brief}: cannot check confirmation: {exc}")
    return errors, len(documents)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_dir", type=Path)
    args = parser.parse_args()
    if not args.case_dir.is_dir():
        parser.error("case_dir must be an existing directory")
    try:
        errors, count = run(args.case_dir)
    except Exception as exc:
        sys.exit(f"Validator setup failed: {exc}")
    print(f"Checked {count} recognized JSON artifacts; errors: {len(errors)}")
    for error in errors:
        print("ERROR:", error)
    if not errors:
        print("Structural schema and mandatory file checks passed. NOT a full semantic, provenance, approval or runtime verification.")
    sys.exit(1 if errors else 0)

if __name__ == "__main__":
    main()
