#!/usr/bin/env python3
"""Optional developer QA for communication module contracts (not a runtime dependency).

Usage (from repository root):
    python -m pip install jsonschema pyyaml
    python validation/communication_strategy/tests/validate_contracts.py
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
import yaml

ROOT = Path(__file__).resolve().parents[3]
COMM = ROOT / "validation/communication_strategy"
INTAKE = ROOT / "validation/common_intake"
PRODUCT = ROOT / "validation/product_strategy"
checker = FormatChecker()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


contract = load(COMM / "contracts.json")
brief_schema = load(INTAKE / "brief.schema.json")
product_contract = load(PRODUCT / "contracts.json")
for schema in (contract, brief_schema, product_contract):
    Draft202012Validator.check_schema(schema)


def valid(schema, item) -> bool:
    return Draft202012Validator(schema, format_checker=checker).is_valid(item)


def require(cond: bool, message: str):
    if not cond:
        raise AssertionError(message)


def enforce_interop(request):
    """Cross-document checks required of the executor; JSON Schema cannot compare fields."""
    assert valid(contract["$defs"]["module_request"] | {"$defs": contract["$defs"]}, request)
    if request["action"] != "start_case":
        return
    brief = request["confirmed_brief"]
    require(valid(brief_schema, brief), "Full source brief invalid")
    require(request["case_id"] == brief["case_id"], "Request/brief case_id mismatch")
    outline = request["product_strategy_outline"]
    if outline is not None:
        require(valid(product_contract["$defs"]["strategy_outline"] | {"$defs": product_contract["$defs"]}, outline), "Product outline invalid")
        require(outline["case_id"] == request["case_id"], "Product case_id mismatch")


def check_paths(state, method_record, stage_record, strategy):
    prefix = f'cases/{state["case_id"]}/communication_strategy/'
    for path in [state["brief_ref"], *state["result_refs"]["method_results"], *state["result_refs"]["stage_results"],
                 *strategy["stage_result_refs"]]:
        require(path.startswith(prefix), "Path escapes communication namespace: " + path)
    require(method_record["method_id"] == "M01" and method_record["home_stage"] == "C01", "Unexpected test method")
    require(stage_record["stage_id"] == "C01", "Unexpected test stage")


def main():
    good = {
        "start_case": load(INTAKE / "examples/communication_start_case.request.json"),
        "run_next_stage": load(COMM / "examples/run_next_stage.request.json"),
        "approve_stage": load(COMM / "examples/approve_stage.request.json"),
        "attach_human_data": load(COMM / "examples/attach_human_data.request.json"),
        "update_brief": load(COMM / "examples/update_brief.request.json"),
        "module_response": load(COMM / "examples/run_next_stage.response.json"),
        "method_record": load(COMM / "examples/method_M01.partial.json"),
        "stage_record": load(COMM / "examples/stage_C01.partial.json"),
        "case_state": load(COMM / "examples/case_state.awaiting_parent.json"),
        "strategy": load(COMM / "examples/communication_strategy.draft.json"),
    }
    for name, item in good.items():
        require(valid(contract, item), f"Invalid positive sample: {name}")
    enforce_interop(good["start_case"])
    require(valid(brief_schema, good["update_brief"]["updated_brief"]), "Invalid updated brief")
    original = load(INTAKE / "examples/brief.confirmed.example.json")
    require(good["start_case"]["confirmed_brief"] == original, "Source brief modified during mapping")

    registry = yaml.safe_load((COMM / "method_routing.yaml").read_text(encoding="utf-8"))
    method = good["method_record"]
    require(registry["method_registry"][method["method_id"]]["stage"] == method["home_stage"], "Method in wrong stage")
    require(method["method_file"].endswith(registry["method_registry"][method["method_id"]]["file"]), "Wrong YAML file")
    method_yaml = yaml.safe_load((ROOT / method["method_file"]).read_text(encoding="utf-8"))
    required_native = set(method_yaml["outputs"]["required"])
    require(required_native <= set(method["native_result"]), "Native result missing YAML output fields")

    check_paths(good["case_state"], method, good["stage_record"], good["strategy"])
    require(good["module_response"]["state_revision"] == good["case_state"]["revision"], "Response revision mismatch")
    require(good["module_response"]["stage_id"] == good["stage_record"]["stage_id"], "Response stage mismatch")
    for artifact in good["module_response"]["artifacts"]:
        require(artifact["path"].startswith(f'cases/{original["case_id"]}/communication_strategy/'), "Artifact escapes namespace")

    negatives = []
    def bad(source, mutate):
        obj = copy.deepcopy(source)
        mutate(obj)
        negatives.append(obj)

    start = good["start_case"]
    bad(start, lambda x: x.pop("confirmed_brief"))
    bad(start, lambda x: x.update(confirmed_brief=None))
    bad(start, lambda x: x.update(action="invalid"))
    bad(start, lambda x: x.update(unexpected_key="not allowed"))
    bad(start, lambda x: x["confirmed_brief"].update(interview_status="collecting"))
    bad(start, lambda x: x["confirmed_brief"].update(user_confirmed_brief=False))
    bad(start, lambda x: x.pop("product_strategy_outline"))
    bad(start, lambda x: x.update(expected_revision=1))
    bad(good["approve_stage"], lambda x: x.update(parent_approval=False))
    bad(good["attach_human_data"], lambda x: x.update(data_artifacts=[]))
    bad(good["module_response"], lambda x: x["artifacts"][0].pop("content"))
    bad(good["module_response"], lambda x: x.update(status="blocked", errors=[]))
    bad(good["module_response"], lambda x: x.update(status="needs_human_data", data_requests=[]))
    bad(good["module_response"], lambda x: x.update(status="awaiting_parent", stage_id=None))
    bad(good["method_record"], lambda x: x.update(status="awaiting_data", data_requests=[]))
    bad(good["method_record"], lambda x: x.update(status="completed", native_result=None))
    bad(good["stage_record"], lambda x: x.update(stage_id="C07"))
    bad(good["case_state"], lambda x: x["stage_states"].pop("C06"))
    bad(good["case_state"], lambda x: x.update(brief_ref="cases/demo_maintenance_saas/state.json"))
    bad(good["strategy"], lambda x: x.update(alternatives=x["alternatives"][:2]))
    bad(good["strategy"], lambda x: x.update(alternatives=[a for a in x["alternatives"] if a["alternative_type"] != "status_quo"] + [dict(alternative_type="other",description="Third option")]))
    bad(good["strategy"], lambda x: x.update(stage_result_refs=x["stage_result_refs"][:5]))
    bad(good["strategy"], lambda x: x.update(source_brief_revision=0))
    for index, item in enumerate(negatives, 1):
        require(not valid(contract, item), f"Invalid fixture accepted by schema: #{index}")

    wrong_brief = copy.deepcopy(start)
    wrong_brief["confirmed_brief"]["case_id"] = "different_case"
    require(valid(contract, wrong_brief), "Cross-object mismatch must be handled by executor")
    try:
        enforce_interop(wrong_brief)
    except AssertionError:
        pass
    else:
        raise AssertionError("Cross-document case_id mismatch not rejected")

    print(f"PASS: {len(good)} positive, {len(negatives)} negative schema checks; "
          "full source/product validation, YAML-native requirements, paths and cross-document identity.")


if __name__ == "__main__":
    main()
