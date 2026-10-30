import unittest
from datetime import datetime
from types import SimpleNamespace

from ai.ocr import parse_medicine_text
from ai.safety import decide_safety


class PipelineTests(unittest.TestCase):
    def classifier(self, label="Crocin", unknown=False):
        return {"label": label if not unknown else "unknown", "confidence": 94, "margin": 30, "is_unknown": unknown, "reason": "below_calibrated_acceptance_threshold" if unknown else None}

    def ocr(self, text="Crocin 500 mg EXP 08/2027", confidence=.95):
        return parse_medicine_text(text, confidence)

    def quality(self, failed=False):
        return {"retake_required": failed, "reasons": ["image_is_blurry"] if failed else []}

    def prescription(self):
        return SimpleNamespace(medicine_name="Crocin", time="morning,night")

    def test_expiry_parser_normalizes_to_last_day(self):
        parsed = self.ocr("Crocin 500 mg Batch No AB-123 EXP 08/2027")
        self.assertEqual(parsed["expiry_date"], "2027-08-31")
        self.assertEqual(parsed["batch_number"], "AB-123")

    def test_low_quality_prevents_positive_result(self):
        result = decide_safety(self.classifier(), self.ocr(), self.quality(True), [self.prescription()])
        self.assertEqual(result["status"], "RETAKE_REQUIRED")

    def test_expiry_overrides_other_evidence(self):
        result = decide_safety(self.classifier(), self.ocr("Crocin EXP 08/2024"), self.quality(), [self.prescription()])
        self.assertEqual(result["status"], "EXPIRED")

    def test_cnn_ocr_conflict_requires_manual_verification(self):
        result = decide_safety(self.classifier("Crocin"), self.ocr("Dolo 650 EXP 08/2027"), self.quality(), [self.prescription()])
        self.assertEqual(result["status"], "MANUAL_VERIFICATION")

    def test_unknown_requires_manual_verification(self):
        result = decide_safety(self.classifier(unknown=True), self.ocr(), self.quality(), [self.prescription()])
        self.assertEqual(result["status"], "MANUAL_VERIFICATION")

    def test_known_but_different_medicine_is_wrong_medicine(self):
        result = decide_safety(self.classifier("Dolo 650"), self.ocr("Dolo 650 EXP 08/2027"), self.quality(), [self.prescription()])
        self.assertEqual(result["status"], "WRONG_MEDICINE")

    def test_advisory_match_requires_all_evidence(self):
        result = decide_safety(self.classifier(), self.ocr(), self.quality(), [self.prescription()], datetime(2026, 10, 22, 9))
        self.assertEqual(result["status"], "ADVISORY_MATCH")


if __name__ == "__main__": unittest.main()
