"""Editorial rubrics, negative answers, repeat hints and report regressions."""
import unittest
from unittest.mock import patch

from kompas.core import SCENARIOS, evaluate_case, report_markdown
from kompas.examiner import (
    RUBRICS, CaseRubric, ERROR_CATEGORIES, assess_case,
    repeat_recommendations, validate_rubrics,
)


class ExaminerTests(unittest.TestCase):
    def test_every_scenario_has_three_to_five_cases_with_complete_rubrics(self):
        validate_rubrics()
        for code, scenario in SCENARIOS.items():
            self.assertTrue(3 <= len(scenario.cases) <= 5, code)
            for i, case in enumerate(scenario.cases):
                rubric = RUBRICS[(code, i)]
                self.assertIn(rubric.category_code, ERROR_CATEGORIES)
                self.assertEqual(set(rubric.incorrect_reasons), set(range(len(case.options))) - {case.correct})

    def test_every_wrong_choice_yields_specific_explanation_and_category(self):
        for code, scenario in SCENARIOS.items():
            for i, case in enumerate(scenario.cases):
                for selected in range(len(case.options)):
                    with self.subTest(code=code, case=i, selected=selected):
                        result = assess_case(code, i, selected)
                        self.assertEqual(result.correct, selected == case.correct)
                        self.assertIn("Принцип:", result.message)
                        if result.correct:
                            self.assertIsNone(result.error_category_code)
                            self.assertEqual(result.recommended_case_indices, ())
                        else:
                            self.assertIn(RUBRICS[(code, i)].incorrect_reasons[selected], result.message)
                            self.assertEqual(result.error_category_code, RUBRICS[(code, i)].category_code)
                            self.assertEqual(result.recommended_case_indices[0], i)

    def test_invalid_choice_rejected_cleanly(self):
        for value in (-1, 3, None, "1", 0.0, True):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "Неизвестный вариант"):
                    assess_case("history", 0, value)

    def test_invalid_scenario_and_case_rejected_cleanly(self):
        for scenario, idx in (("missing", 0), ("history", -1), ("history", 999), ("history", True)):
            with self.subTest(scenario=scenario, idx=idx):
                with self.assertRaises(ValueError):
                    assess_case(scenario, idx, 0)

    def test_invalid_rubrics_are_detected(self):
        original = RUBRICS[("history", 0)]
        for bad in (CaseRubric("unknown", {0: "reason", 2: "reason"}),
                    CaseRubric("tradeoffs", {0: "reason"}),
                    CaseRubric("tradeoffs", {0: "", 2: "reason"})):
            with self.subTest(bad=bad):
                with patch.dict(RUBRICS, {("history", 0): bad}):
                    with self.assertRaises(ValueError):
                        validate_rubrics()
        self.assertIs(RUBRICS[("history", 0)], original)

    def test_recommendations_by_shared_category_and_respect_success(self):
        suggestions = repeat_recommendations("history", {2: False, 3: True})
        self.assertEqual(len(suggestions), 1)
        self.assertIn("Год поступления", suggestions[0])
        self.assertEqual(repeat_recommendations("history", {0: True}), ())
        new = repeat_recommendations("history", {2: False})
        self.assertEqual(len(new), 2)
        self.assertIn("Подготовка к испытаниям", new[1])

    def test_reject_invalid_attempt_history(self):
        for history in ({-1: False}, {100: True}, {0: "нет"}, {True: False}):
            with self.subTest(history=history):
                with self.assertRaises(ValueError):
                    repeat_recommendations("history", history)

    def test_report_includes_categories_and_legacy_api_is_intact(self):
        correct, text = evaluate_case("internship", 0, 1)
        self.assertTrue(correct)
        self.assertIn("Принцип", text)
        correct, text = evaluate_case("internship", 0, 0)
        self.assertFalse(correct)
        self.assertIn("Устное обещание", text)
        report = report_markdown("history", {"year": "2027"}, {2: False, 3: True})
        self.assertIn("Проверка фактов и обещаний", report)
        self.assertNotIn("Повторить (по категориям ошибок): Подготовка к испытаниям", report)
        self.assertIn("Пройдено кейсов: 2", report)


if __name__ == "__main__":
    unittest.main()
