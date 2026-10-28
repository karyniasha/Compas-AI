"""Knowledge and safe offline information-mode regression tests."""
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest

from kompas.knowledge import (
    DEFAULT_DATA, UNIVERSITIES, Fact, KnowledgeRepository,
    effective_status, information_response,
)
from kompas.model import RuleBasedModel
from kompas.core import SCENARIOS, get_question, report_markdown, save_answer

DATE = date(2026, 10, 22)


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.repository = KnowledgeRepository.from_file()

    def test_four_universities_have_cited_programs(self):
        response = information_response(self.repository, "programs", "2027", as_of=DATE)
        self.assertEqual(tuple(u.university for u in response.universities), UNIVERSITIES)
        for university in response.universities:
            self.assertGreaterEqual(len(university.verified), 1, university.university)
            for fact in university.verified:
                self.assertTrue(fact.source_url.startswith("https://"))
                self.assertIsNotNone(fact.retrieved_at)
                self.assertIsNotNone(fact.valid_until)
                self.assertIsNone(fact.value)  # No made-up prices, scores, or places.

    def test_old_admission_year_is_not_current(self):
        response = information_response(self.repository, "admission", "2027", as_of=DATE)
        self.assertFalse(any(u.verified for u in response.universities))
        self.assertTrue(any(u.archive for u in response.universities))
        old = information_response(self.repository, "admission", "2026", as_of=DATE)
        self.assertTrue(any(u.verified for u in old.universities))

    def test_stale_after_expiry(self):
        fact = self.repository.find(university="СГУ", topic="programs")[0]
        self.assertEqual(effective_status(fact, as_of=date(2027, 1, 1), intake_year=2027), "stale")
        self.assertFalse(any(u.verified for u in information_response(
            self.repository, "programs", "2027", as_of=date(2027, 1, 1)
        ).universities))

    def test_unverified_and_missing_prices_do_not_become_zero(self):
        costs = information_response(self.repository, "costs", "2027", as_of=DATE)
        self.assertFalse(any(u.verified or u.archive for u in costs.universities))
        self.assertIn("неизвестна", costs.notice)
        raw = json.loads(DEFAULT_DATA.read_text(encoding="utf-8"))[0]
        raw["verification_status"] = "unverified"
        raw["source_url"] = None
        raw["retrieved_at"] = None
        raw["valid_until"] = None
        artificial = KnowledgeRepository([Fact.from_dict(raw)])
        hidden = information_response(artificial, "programs", "2027", as_of=DATE)
        self.assertFalse(any(u.verified or u.archive for u in hidden.universities))

    def test_verified_requires_dates_and_official_url(self):
        raw = json.loads(DEFAULT_DATA.read_text(encoding="utf-8"))[0]
        for field, invalid in (("source_url", "https://spbu.ru.evil.example/fact"),
                               ("source_url", "http://spbu.ru/fact"),
                               ("source_url", None),
                               ("retrieved_at", None),
                               ("valid_until", "2020-01-01")):
            with self.subTest(field=field, invalid=invalid):
                changed = {**raw, field: invalid}
                with self.assertRaises(ValueError):
                    Fact.from_dict(changed)

    def test_reject_duplicate_ids_and_bad_json_shape(self):
        fact = self.repository.facts[0]
        with self.assertRaises(ValueError):
            KnowledgeRepository([fact, fact])
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "facts.json"
            file.write_text('{}', encoding="utf-8")
            with self.assertRaises(ValueError):
                KnowledgeRepository.from_file(file)

    def test_report_mentions_checked_url_and_warning(self):
        report = report_markdown("history", {"year": "2027", "budget": "Пока не знаю"})
        self.assertIn("проверено: 2026-10-22", report)
        self.assertIn("https://sgu.ru/struktura/imimo", report)
        self.assertIn("нельзя автоматически переносить", report)
        self.assertIn("Бюджет неизвестен", report)

    def test_local_adapter_does_not_evaluate_prose(self):
        model = RuleBasedModel()
        self.assertEqual(model.generate_followup({"topic": "admission"}, ()).mode, "rules")
        result = model.evaluate_free_answer(None, "МГУ лучше", None)
        self.assertFalse(result.assessed)
        self.assertNotIn("Верно", result.text)

    def test_scenario_out_of_order_and_duplicate_priority(self):
        with self.assertRaisesRegex(ValueError, "по порядку"):
            save_answer("history", {}, "budget", "Пока не знаю")
        answers = {}
        for val in ("2027", "Археология", "Наука и исследования", "Нужно разобраться с испытаниями", "Пока не знаю"):
            q = get_question("history", answers)
            answers = save_answer("history", answers, q.key, val)
        with self.assertRaises(ValueError):
            save_answer("history", answers, "priorities", ["Научная среда", "Научная среда"])

    def test_all_three_routes_can_complete_without_key(self):
        for code, scenario in SCENARIOS.items():
            with self.subTest(code=code):
                answers = {}
                while (q := get_question(code, answers)) is not None:
                    value = [q.options[0]] if q.kind == "multi" else q.options[0] if q.kind == "choice" else "Тест"
                    answers = save_answer(code, answers, q.key, value)
                self.assertEqual(len(answers), len(scenario.questions))
                self.assertIn("Компас", report_markdown(code, answers))


if __name__ == "__main__":
    unittest.main()
