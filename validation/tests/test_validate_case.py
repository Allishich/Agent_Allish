"""Regression checks for the offline case validator. Run: python -m unittest discover -s validation/tests"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "validate_case.py"
spec = importlib.util.spec_from_file_location("case_validator", SCRIPT)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class CaseValidatorTests(unittest.TestCase):
    def test_stage_paths(self):
        case = Path("cases/example")
        self.assertEqual(validator.schema_for(case / "communication_strategy/results/stages/C01.json"),
                         ("communication", "stage_record"))
        self.assertEqual(validator.schema_for(case / "product_strategy/results/stages/01_stage.json"),
                         ("product", "stage_record"))
        self.assertEqual(validator.schema_for(case / "communication_strategy/results/methods/M01.json"),
                         ("communication", "method_record"))

    def test_approval_evidence_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            case = Path(temp) / "example"
            stage_dir = case / "product_strategy/results/stages"
            stage_dir.mkdir(parents=True)
            (stage_dir / "01_stage.json").write_text(json.dumps({"version": 2}))
            state = {"stage_states": {"S01": "accepted"}}
            errors = validator.check_approval_evidence(case, state, "product_strategy")
            self.assertTrue(any("without approval evidence" in e for e in errors))
            state["approval_evidence"] = {"S01": {
                "approval_origin": "mock", "message_ref": "mock-1",
                "stage_version": 2, "case_id": "example", "stage_id": "S01"}}
            errors = validator.check_approval_evidence(case, state, "product_strategy")
            self.assertTrue(any("without live_user approval" in e for e in errors))
            state["approval_evidence"]["S01"]["approval_origin"] = "live_user"
            state["approval_evidence"]["S01"]["stage_version"] = 1
            errors = validator.check_approval_evidence(case, state, "product_strategy")
            self.assertTrue(any("approval version mismatch" in e for e in errors))
            state["approval_evidence"]["S01"]["stage_version"] = 2
            self.assertEqual(validator.check_approval_evidence(case, state, "product_strategy"), [])

    def test_empty_case_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            case = Path(temp) / "example"
            case.mkdir()
            errors, count = validator.run(case)
            self.assertEqual(count, 0)
            self.assertTrue(any("missing mandatory artifact" in e for e in errors))
            self.assertTrue(any("missing mandatory communication strategy" in e for e in errors))

    def test_unconfirmed_brief_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            case = Path(temp) / "example"
            case.mkdir()
            (case / "brief.json").write_text(json.dumps({
                "case_id": "example", "interview_status": "collecting",
                "user_confirmed_brief": False
            }))
            errors, _ = validator.run(case)
            self.assertTrue(any("brief not confirmed" in e for e in errors))

    def test_wrong_case_id_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            case = Path(temp) / "example"
            case.mkdir()
            (case / "brief.json").write_text(json.dumps({"case_id": "other"}))
            errors, _ = validator.run(case)
            self.assertTrue(any("case_id mismatch" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
