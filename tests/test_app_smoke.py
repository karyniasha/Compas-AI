"""Headless script smoke checks. Not a substitute for a browser/UI test."""
from contextlib import nullcontext
import os
import runpy
import sys
from pathlib import Path
import types
import unittest
from unittest.mock import patch

from kompas.core import SCENARIOS

ROOT = Path(__file__).resolve().parents[1]


class State(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class FakeStreamlit(types.ModuleType):
    def __init__(self, scenario="history", topic="programs", complete=False, submit_training=False):
        super().__init__("streamlit")
        self.sidebar = nullcontext()
        self.topic = topic
        self.output = []
        self.submit_training = submit_training
        self.session_state = State(
            active_scenario=scenario,
            answers={code: {} for code in SCENARIOS},
            attempts={code: {} for code in SCENARIOS},
        )
        if complete:
            questions = SCENARIOS[scenario].questions
            answers = {
                q.key: [q.options[0]] if q.kind == "multi" else q.options[0]
                for q in questions
            }
            if scenario == "history":
                answers["year"] = "2027"
                answers["budget"] = "Пока не знаю"
            self.session_state.answers[scenario] = answers

    def __getattr__(self, name):
        if name in ("form", "expander"):
            return lambda *args, **kwargs: nullcontext()
        if name == "tabs":
            return lambda labels: [nullcontext() for _ in labels]
        if name == "selectbox":
            return self.selectbox
        if name == "radio":
            return lambda label, options, **kwargs: list(options)[0]
        if name == "multiselect":
            return lambda *args, **kwargs: []
        if name == "button":
            return lambda *args, **kwargs: False
        if name == "form_submit_button":
            return lambda label, **kwargs: self.submit_training and label == "Проверить ответ"
        if name == "download_button":
            return lambda *args, **kwargs: False
        return lambda *args, **kwargs: self.output.append(str(args[0]) if args else name)

    def selectbox(self, label, options, **kwargs):
        if label == "Что изучить?":
            return self.topic
        return list(options)[kwargs.get("index", 0)]


class StreamlitSmokeTests(unittest.TestCase):
    def test_configured_api_key_does_not_enable_external_requests(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-only-placeholder", "OPENAI_MODEL": "test-model"}), \
                patch("kompas.llm_adapter.OpenAIResponsesModel.generate_followup") as remote, \
                patch("socket.socket.connect", side_effect=AssertionError("Unexpected network request")) as network:
            for scenario in SCENARIOS:
                result = self._render(scenario, complete=True)
                self.assertIn("Локальный режим", result)
                self.assertIn("не отправляются в LLM", result)
            remote.assert_not_called()
            network.assert_not_called()

    def _render(self, scenario, topic="programs", complete=False):
        stub = FakeStreamlit(scenario, topic, complete)
        with patch.dict(sys.modules, {"streamlit": stub}):
            runpy.run_path(str(ROOT / "app.py"), run_name="__main__")
        return "\n".join(stub.output)

    def test_all_scenario_initial_screens(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                result = self._render(scenario)
                self.assertIn("Компас", result)

    def test_completed_history_report_and_admission_sources(self):
        result = self._render("history", "admission", complete=True)
        self.assertIn("2027", result)
        self.assertIn("архив", result.lower())
        self.assertIn("Правила", result)

    def test_trainer_explains_and_keeps_result_during_rerun(self):
        stub = FakeStreamlit("history", complete=True, submit_training=True)
        with patch.dict(sys.modules, {"streamlit": stub}):
            runpy.run_path(str(ROOT / "app.py"), run_name="__main__")
            self.assertEqual(stub.session_state.exam_results["history"][0], 0)
            self.assertFalse(stub.session_state.attempts["history"][0])
            stub.submit_training = False
            stub.output.clear()
            runpy.run_path(str(ROOT / "app.py"), run_name="__main__")
        output = "\n".join(stub.output)
        self.assertIn("Известность вуза", output)
        self.assertIn("Категория ошибки", output)
        self.assertIn("Рекомендуется повторить", output)

    def test_completed_history_costs_does_not_invent_price(self):
        result = self._render("history", "costs", complete=True)
        self.assertIn("Стоимость", result)
        self.assertIn("Подтверждённых данных", result)


if __name__ == "__main__":
    unittest.main()
