"""Provider-neutral LLM boundary and an entirely offline implementation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class FollowupResponse:
    text: str
    used_fact_ids: tuple[str, ...] = ()
    mode: str = "rules"


@dataclass(frozen=True)
class FreeAnswerFeedback:
    assessed: bool
    text: str
    mode: str = "rules"


class LanguageModel(Protocol):
    def generate_followup(self, context: dict, allowed_facts: tuple) -> FollowupResponse: ...

    def evaluate_free_answer(self, case: object, answer: str, rubric: object) -> FreeAnswerFeedback: ...


class RuleBasedModel:
    """Predictable fallback; it does not simulate semantic evaluation."""

    def generate_followup(self, context: dict, allowed_facts: tuple = ()) -> FollowupResponse:
        topic = context.get("topic", "programs")
        questions = {
            "programs": "Какой профиль истории тебе интереснее и какие учебные планы следует сравнить?",
            "admission": "На какой год ты поступаешь и какие официальные испытания ещё требуется проверить?",
            "costs": "Какой диапазон расходов на переезд и проживание приемлем, если ты готов его обсуждать?",
        }
        return FollowupResponse(questions.get(topic, "Какой информации не хватает для решения?"))

    def evaluate_free_answer(self, case: object, answer: str, rubric: object) -> FreeAnswerFeedback:
        return FreeAnswerFeedback(False, "Свободный текст пока не оценивается. Для самопроверки выбери вариант в тренажёре.")
