import unittest

from ai.ocr import parse_printed_prescription


class PrintedPrescriptionParserTests(unittest.TestCase):
    def test_schedule_strength_and_course_are_extracted_from_one_row(self):
        draft = parse_printed_prescription([
            {"text": "Tab Zofer 4 mg 1-0-1 for 5 days", "confidence": 0.96},
        ])
        self.assertEqual(len(draft["candidates"]), 1)
        candidate = draft["candidates"][0]
        self.assertEqual(candidate["medicine_name"], "Zofer")
        self.assertEqual(candidate["strength"], "4 mg")
        self.assertEqual(candidate["tablets"], 1)
        self.assertEqual(candidate["time"], ["morning", "night"])
        self.assertEqual(candidate["frequency"], "Twice daily")
        self.assertEqual(candidate["course_days"], 5)

    def test_frequency_shorthand_does_not_invent_a_time(self):
        draft = parse_printed_prescription([
            {"text": "Cap Cetzine 10 mg BD after meals", "confidence": 0.94},
        ])
        candidate = draft["candidates"][0]
        self.assertEqual(candidate["frequency"], "Twice daily")
        self.assertEqual(candidate["time"], [])
        self.assertTrue(any("does not specify" in warning for warning in candidate["warnings"]))

    def test_explicit_dates_are_available_for_review(self):
        draft = parse_printed_prescription([
            {"text": "Start 01/11/2026 End 05/11/2026", "confidence": 0.98},
            {"text": "Tablet Dolo 650 mg 1-0-1", "confidence": 0.98},
        ])
        candidate = draft["candidates"][0]
        self.assertEqual(candidate["start_date"], "2026-11-01")
        self.assertEqual(candidate["end_date"], "2026-11-05")

    def test_empty_or_low_confidence_text_is_not_a_prescription(self):
        draft = parse_printed_prescription([{"text": "", "confidence": 0.0}])
        self.assertEqual(draft["candidates"], [])
        self.assertTrue(any("no printed text" in warning for warning in draft["warnings"]))


if __name__ == "__main__":
    unittest.main()
