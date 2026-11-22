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

    def test_in_progress_case_does_not_require_future_stages(self):
        with tempfile.TemporaryDirectory() as temp:
            case = Path(temp) / "example"
            case.mkdir()
            errors, count = validator.run(case, require_complete=False)
            self.assertEqual(count, 0)
            self.assertFalse(any("mandatory artifact" in e and "stages" in e for e in errors))
            self.assertFalse(any("mandatory communication strategy" in e for e in errors))

    def test_communication_approval_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            case = Path(temp) / "example"
            stage_dir = case / "communication_strategy/results/stages"
            stage_dir.mkdir(parents=True)
            (stage_dir / "C01.json").write_text(json.dumps({"version": 3}))
            state = {"stage_states": {"C01": "accepted"}, "approval_evidence": {
                "C01": {"approval_origin": "mock", "message_ref": "test",
                        "stage_version": 3, "case_id": "example", "stage_id": "C01"}}}
            errors = validator.check_approval_evidence(case, state, "communication_strategy")
            self.assertTrue(any("without live_user approval" in e for e in errors))
            state["approval_evidence"]["C01"]["approval_origin"] = "live_user"
            self.assertEqual(validator.check_approval_evidence(case, state, "communication_strategy"), [])

    def test_integration_rejects_fabricated_approval_in_partial_case(self):
        """Exercise run(), not just the approval helper, on a dating-app fixture."""
        with tempfile.TemporaryDirectory() as temp:
            case = Path(temp) / "dating_no_likes"
            stages = case / "product_strategy/results/stages"
            stages.mkdir(parents=True)
            (stages / "01_stage.json").write_text(json.dumps({
                "case_id": "dating_no_likes", "stage_id": "S01",
                "version": 2, "fields": {"concept": "No likes, direct dates"}
            }), encoding="utf-8")
            state_path = case / "product_strategy/state.json"
            state = {
                "case_id": "dating_no_likes",
                "stage_states": {"S01": "awaiting_parent_approval"}
            }
            state_path.write_text(json.dumps(state), encoding="utf-8")
            errors, _ = validator.run(case, require_complete=False)
            self.assertFalse(any("accepted without" in e for e in errors))
            state["stage_states"]["S01"] = "accepted"
            state_path.write_text(json.dumps(state), encoding="utf-8")
            errors, _ = validator.run(case, require_complete=False)
            self.assertTrue(any("accepted without approval evidence" in e for e in errors))
            state["approval_evidence"] = {"S01": {
                "approval_origin": "mock", "message_ref": "simulated-user",
                "stage_version": 2, "case_id": "dating_no_likes", "stage_id": "S01"
            }}
            state_path.write_text(json.dumps(state), encoding="utf-8")
            errors, _ = validator.run(case, require_complete=False)
            self.assertTrue(any("without live_user approval" in e for e in errors))
            state["approval_evidence"]["S01"].update({
                "approval_origin": "live_user", "stage_version": 1
            })
            state_path.write_text(json.dumps(state), encoding="utf-8")
            errors, _ = validator.run(case, require_complete=False)
            self.assertTrue(any("approval version mismatch" in e for e in errors))

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
