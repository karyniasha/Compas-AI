"""Explainable, deterministic multiple-choice examiner for the offline MVP.

The rubric is explicit editorial content, NOT an LLM judgement. Category codes
are stable keys for a future opt-in SQLite error history.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .core import SCENARIOS


ERROR_CATEGORIES: dict[str, str] = {
    "evidence": "Проверка фактов и обещаний",
    "uncertainty": "Работа с неопределённостью",
    "tradeoffs": "Сравнение альтернатив",
    "agency": "Самостоятельность выбора",
    "constraints": "Учёт ограничений",
    "communication": "Коммуникация и ответственность",
    "safety": "Безопасность решения",
}


@dataclass(frozen=True)
class CaseRubric:
    """Category and specific reasons for *every* wrong option index."""

    category_code: str
    incorrect_reasons: Mapping[int, str]


# Keys are (scenario_code, zero-based case index); option indexes are zero-based.
# A wrong option must have a meaningful explanation, never a fabricated fact.
RUBRICS: dict[tuple[str, int], CaseRubric] = {
    ("history", 0): CaseRubric("tradeoffs", {
        0: "Известность вуза сама по себе не доказывает, что его программа подходит твоим целям.",
        2: "Близость к дому важна, но не делает любой местный вариант безусловно лучшим.",
    }),
    ("history", 1): CaseRubric("uncertainty", {
        0: "Отсутствие сведений о бюджете не означает, что переезд невозможен.",
        1: "Предположение о достатке нельзя использовать как подтверждённый финансовый расчёт.",
    }),
    ("history", 2): CaseRubric("evidence", {
        0: "Правила прошлого года нельзя выдавать за окончательные требования следующего набора.",
        2: "Отсутствие опубликованных требований нового года не означает запрета на поступление.",
    }),
    ("history", 3): CaseRubric("evidence", {
        1: "Дополнительное испытание нельзя игнорировать только из-за результатов ЕГЭ.",
        2: "Неподтверждённый проходной балл создаёт ложное впечатление точности.",
    }),
    ("history", 4): CaseRubric("agency", {
        0: "Выбор друзей не заменяет сопоставления личных целей и возможностей.",
        1: "Совет родителей важен, но стоит обсудить причины и собственные критерии.",
    }),
    ("internship", 0): CaseRubric("evidence", {
        0: "Устное обещание не гарантирует трудоустройство без проверяемых условий.",
        2: "Требование оплатить доступ не подтверждает надёжность предложения и повышает риск потери денег.",
    }),
    ("internship", 1): CaseRubric("constraints", {
        0: "Игнорирование учёбы создаёт неучтённый риск перегрузки.",
        2: "Резкий отказ от учёбы несоразмерен конфликту графиков без сравнения альтернатив.",
    }),
    ("internship", 2): CaseRubric("safety", {
        0: "Перевод денег до проверки организации повышает риск мошенничества.",
        1: "Сокрытие сомнительного предложения лишает возможности проверить его с другими людьми.",
    }),
    ("onboarding", 0): CaseRubric("communication", {
        1: "Работа без согласованных критериев может привести к переделкам.",
        2: "Молчаливое бездействие не устраняет неопределённость задачи.",
    }),
    ("onboarding", 1): CaseRubric("communication", {
        0: "Скрытая ошибка может усилить последствия и помешать исправлению.",
        2: "Обвинение без разбора причин разрушает доверие и не исправляет результат.",
    }),
    ("onboarding", 2): CaseRubric("communication", {
        1: "Отсутствие замечаний ещё не означает, что ожидания руководителя выполнены.",
        2: "Увольнение без попытки прояснить ожидания исключает полезный способ разрешить проблему.",
    }),
}


@dataclass(frozen=True)
class CaseAssessment:
    correct: bool
    message: str
    criterion: str
    error_category_code: str | None
    error_category: str | None
    recommended_case_indices: tuple[int, ...]


def validate_rubrics() -> None:
    """Fail fast if the scenario content and its editorial rubrics diverge."""
    expected = {(code, i) for code, scenario in SCENARIOS.items() for i in range(len(scenario.cases))}
    if set(RUBRICS) != expected:
        raise ValueError("Рубрики не покрывают все кейсы или содержат лишние записи")
    for (code, i), rubric in RUBRICS.items():
        case = SCENARIOS[code].cases[i]
        if len(case.options) < 2 or not 0 <= case.correct < len(case.options):
            raise ValueError(f"Некорректный правильный вариант: {code}/{i}")
        if len(set(case.options)) != len(case.options) or any(not option.strip() for option in case.options):
            raise ValueError(f"Некорректные варианты ответа: {code}/{i}")
        if not case.principle.strip() or not case.feedback.strip() or not case.title.strip():
            raise ValueError(f"Неполное содержание кейса: {code}/{i}")
        if rubric.category_code not in ERROR_CATEGORIES:
            raise ValueError(f"Неизвестная категория ошибки: {code}/{i}")
        incorrect = set(range(len(case.options))) - {case.correct}
        if set(rubric.incorrect_reasons) != incorrect:
            raise ValueError(f"Не каждому неверному ответу задано объяснение: {code}/{i}")
        if any(not isinstance(reason, str) or not reason.strip() for reason in rubric.incorrect_reasons.values()):
            raise ValueError(f"Пустое объяснение ошибки: {code}/{i}")


def _case(scenario_code: str, case_index: int):
    if scenario_code not in SCENARIOS:
        raise ValueError("Неизвестный сценарий")
    if type(case_index) is not int or not 0 <= case_index < len(SCENARIOS[scenario_code].cases):
        raise ValueError("Неизвестный кейс")
    return SCENARIOS[scenario_code].cases[case_index]


def assess_case(scenario_code: str, case_index: int, selected_index: int) -> CaseAssessment:
    """Assess one explicit choice; arbitrary prose is deliberately not graded."""
    case = _case(scenario_code, case_index)
    if type(selected_index) is not int or not 0 <= selected_index < len(case.options):
        raise ValueError("Неизвестный вариант ответа")
    rubric = RUBRICS[(scenario_code, case_index)]
    if selected_index == case.correct:
        return CaseAssessment(
            correct=True,
            message=f"Верно. {case.feedback} Принцип: {case.principle}",
            criterion=case.principle,
            error_category_code=None,
            error_category=None,
            recommended_case_indices=(),
        )
    related = tuple(
        i for i, _ in enumerate(SCENARIOS[scenario_code].cases)
        if i != case_index and RUBRICS[(scenario_code, i)].category_code == rubric.category_code
    )
    return CaseAssessment(
        correct=False,
        message=(f"Пока нет. {rubric.incorrect_reasons[selected_index]} "
                 f"Как действовать: {case.feedback} Принцип: {case.principle}"),
        criterion=case.principle,
        error_category_code=rubric.category_code,
        error_category=ERROR_CATEGORIES[rubric.category_code],
        recommended_case_indices=(case_index, *related),
    )


def repeat_recommendations(scenario_code: str, attempts: Mapping[int, bool]) -> tuple[str, ...]:
    """Suggest wrong cases first, then not-yet-mastered cases of the same skill."""
    if scenario_code not in SCENARIOS:
        raise ValueError("Неизвестный сценарий")
    scenario = SCENARIOS[scenario_code]
    if any(type(i) is not int or not 0 <= i < len(scenario.cases) or type(v) is not bool for i, v in attempts.items()):
        raise ValueError("Некорректные данные попыток")
    wrong = sorted(i for i, correct in attempts.items() if not correct)
    suggested = list(wrong)
    for i in wrong:
        category = RUBRICS[(scenario_code, i)].category_code
        for j in range(len(scenario.cases)):
            if (j not in suggested and attempts.get(j) is not True
                    and RUBRICS[(scenario_code, j)].category_code == category):
                suggested.append(j)
    return tuple(f"{scenario.cases[i].title} — {ERROR_CATEGORIES[RUBRICS[(scenario_code, i)].category_code]}" for i in suggested)
