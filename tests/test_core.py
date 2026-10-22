import unittest
from kompas.core import SCENARIOS, get_question, save_answer, evaluate_case, report_markdown


class TestKompas(unittest.TestCase):
    def test_three_scenarios(self):
        self.assertEqual(set(SCENARIOS), {"history", "internship", "onboarding"})
        self.assertEqual(len(SCENARIOS["history"].cases), 5)
        self.assertTrue(all(len(s.cases) >= 3 for s in SCENARIOS.values()))

    def test_main_route_complete(self):
        vals = ["2027", "Археология", "Наука и исследования", "Нужно разобраться с испытаниями", "Пока не знаю", ["Научная среда", "Стоимость жизни"]]
        answers = {}
        for val in vals:
            q = get_question("history", answers)
            self.assertIsNotNone(q)
            answers = save_answer("history", answers, q.key, val)
        self.assertIsNone(get_question("history", answers))
        report = report_markdown("history", answers)
        self.assertIn("Бюджет неизвестен", report)
        for uni in ("СПбГУ", "СГУ", "РГГУ", "МГУ"):
            self.assertIn(uni, report)
        self.assertNotIn("100% поступление", report)

    def test_answer_validation(self):
        with self.assertRaises(ValueError):
            save_answer("history", {}, "year", "2020")
        with self.assertRaises(ValueError):
            save_answer("history", {}, "priorities", ["Несуществующий критерий"])
        with self.assertRaises(ValueError):
            save_answer("history", {}, "priorities", [])
        with self.assertRaises(ValueError):
            save_answer("history", {}, "priorities", ["Научная среда"] * 4)

    def test_case_grading_and_retry_hint(self):
        good, info = evaluate_case("history", 0, 1)
        self.assertTrue(good)
        self.assertIn("Принцип", info)
        bad, info = evaluate_case("history", 0, 0)
        self.assertFalse(bad)
        report = report_markdown("history", {}, {0: False, 1: True})
        self.assertIn("Престиж ≠ соответствие", report)

    def test_all_cases_valid(self):
        for s in SCENARIOS.values():
            for i, c in enumerate(s.cases):
                self.assertTrue(0 <= c.correct < len(c.options))
                correct, _ = evaluate_case(s.code, i, c.correct)
                self.assertTrue(correct)


if __name__ == "__main__":
    unittest.main()
