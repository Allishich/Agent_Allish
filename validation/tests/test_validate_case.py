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
