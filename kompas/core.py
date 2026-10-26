"""Deterministic, key-free dialogue orchestrator for the Kompas prototype.

The goal here is *product logic*, not a simulation pretending to be an LLM.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

QuestionKind = Literal["choice", "multi", "text"]


@dataclass(frozen=True)
class Question:
    key: str
    title: str
    kind: QuestionKind
    options: tuple[str, ...] = ()
    help: str = ""


@dataclass(frozen=True)
class TrainingCase:
    title: str
    prompt: str
    options: tuple[str, ...]
    correct: int
    principle: str
    feedback: str


@dataclass(frozen=True)
class Scenario:
    code: str
    title: str
    description: str
    questions: tuple[Question, ...]
    cases: tuple[TrainingCase, ...]


HISTORY = Scenario(
    code="history",
    title="Георгий: выбор вуза",
    description="17 лет, Саратов; история; СПбГУ, СГУ, РГГУ, МГУ. Финансовые возможности неизвестны.",
    questions=(
        Question("year", "В каком году планируешь поступать?", "choice", ("2027", "2028", "Пока не решил"), "Правила приёма нужно проверять для выбранного года."),
        Question("interest", "Что особенно привлекает тебя в истории?", "choice", ("История России", "Всеобщая история", "Археология", "Пока не определился")),
        Question("goal", "Какую траекторию ты сейчас рассматриваешь?", "choice", ("Наука и исследования", "Преподавание", "Музеи и архивы", "Хочу разобраться")),
        Question("exam", "Что известно о подготовке к поступлению?", "choice", ("Подготовка идёт, баллы пока неизвестны", "Есть пробные результаты", "Нужно разобраться с испытаниями", "Предпочту не отвечать"), "Здесь не вычисляется вероятность поступления без проверенных данных."),
        Question("budget", "Насколько понятен бюджет переезда?", "choice", ("Есть деньги на переезд и проживание", "Бюджет ограничен", "Пока не знаю", "Не хочу сообщать"), "Точный доход семьи не нужен."),
        Question("priorities", "Выбери до трёх главных критериев", "multi", ("Содержание программы", "Научная среда", "Стоимость жизни", "Вероятность поступления", "Комфорт и переезд", "Репутация вуза")),
    ),
    cases=(
        TrainingCase("Престиж ≠ соответствие", "МГУ известнее СГУ. Что следует из этого?", ("МГУ однозначно лучше для любого историка", "Нужно сравнить программы и личные приоритеты", "СГУ всегда лучше, так как рядом"), 1, "Не подменять качество конкретной программы общим престижем.", "Сначала посмотри учебные планы, научные интересы и возможности, значимые лично тебе."),
        TrainingCase("Неизвестный бюджет", "Георгий не знает семейный бюджет. Что делать?", ("Исключить все варианты с переездом", "Предположить, что денег хватит", "Сохранить варианты, собрать данные по расходам и обсудить диапазоны"), 2, "Не трактовать неизвестность как невозможность.", "Неизвестные расходы нужно пометить как вопросы для проверки, а не оценивать нулём."),
        TrainingCase("Год поступления", "Известны условия поступления в 2026 году, а Георгий поступает в 2027-м. Как поступить?", ("Выдать требования 2026 года как окончательные", "Пометить данные 2026 как справочные и запросить условия 2027", "Сказать, что поступать невозможно"), 1, "Не переносить правила прошлого года автоматически.", "Источник должен содержать год и дату проверки; будущие условия требуют обновления."),
        TrainingCase("Подготовка к испытаниям", "Сайт вуза упоминает дополнительное испытание. Что делать?", ("Сверить актуальность требования и включить подготовку в план", "Игнорировать, если хорошие результаты ЕГЭ", "Придумать проходной балл"), 0, "Проверять требования конкретной программы и года.", "Поступление определяется официальными условиями и реальными результатами, а не общими ожиданиями."),
        TrainingCase("Мнения окружающих", "Друзья зовут в Москву, родители — остаться дома. Как сравнить выбор?", ("Повторить решение друзей", "Подчиниться родителям без обсуждения", "Выделить собственные критерии и обсудить ограничения"), 2, "Уважать автономию пользователя.", "Мнения семьи и друзей можно учитывать как факторы, но не вместо собственных целей."),
    ),
)

INTERNSHIP = Scenario(
    code="internship",
    title="Первая стажировка",
    description="Пользователь выбирает первую стажировку и проверяет условия предложения.",
    questions=(
        Question("year", "На каком этапе обучения ты находишься?", "choice", ("Школа", "Колледж", "Вуз", "После выпуска")),
        Question("interest", "Какая область привлекает?", "choice", ("IT", "Гуманитарные исследования", "Бизнес и аналитика", "Пока не знаю")),
        Question("goal", "Что наиболее важно в первой стажировке?", "choice", ("Опыт", "Доход", "Наставник", "Найти сферу интересов")),
        Question("budget", "Какие условия ты можешь принять?", "choice", ("Только оплачиваемая", "Готов рассмотреть учебную практику", "Пока не знаю")),
        Question("priorities", "Выбери до трёх критериев", "multi", ("Оплата", "Навыки", "Наставничество", "График", "Безопасность условий", "Перспективы")),
    ),
    cases=(
        TrainingCase("Обещание трудоустройства", "Компания обещает работу после стажировки без условий. Как действовать?", ("Считать гарантию доказанной", "Уточнить письменные условия и порядок отбора", "Немедленно оплатить доступ"), 1, "Проверять обещания и условия.", "Проси конкретные условия и подтверждения, а не полагайся на рекламное обещание."),
        TrainingCase("Перегрузка", "График стажировки конфликтует с учёбой. Что делать?", ("Игнорировать конфликт", "Сравнить ценность и нагрузку, обсудить гибкий график", "Бросить учёбу немедленно"), 1, "Учитывать реальные ограничения.", "Компромиссы должны быть явными, а не скрытыми."),
        TrainingCase("Платный отбор", "За интервью просят заплатить. Что делать?", ("Сразу перевести деньги", "Скрыть предложение от всех", "Проверить организацию и отказаться от подозрительных платежей"), 2, "Обращать внимание на риск мошенничества.", "Проверь работодателя, его контакты и прозрачность условий."),
    ),
)

ONBOARDING = Scenario(
    code="onboarding",
    title="Первый месяц на работе",
    description="Пользователь учится адаптироваться в коллективе и обсуждать рабочие сложности.",
    questions=(
        Question("year", "Какой сейчас у тебя опыт?", "choice", ("Первая неделя", "Первый месяц", "Пока только готовлюсь")),
        Question("goal", "Что тревожит сильнее?", "choice", ("Неясные задачи", "Обратная связь", "Объём работы", "Общение в команде")),
        Question("interest", "С кем легче обсудить проблему?", "choice", ("Наставник", "Руководитель", "Коллега", "Пока не знаю")),
        Question("budget", "Какая поддержка доступна?", "choice", ("Есть наставник", "Есть руководитель", "Пока никого нет")),
        Question("priorities", "Выбери до трёх приоритетов", "multi", ("Обучение", "Понятные задачи", "Баланс времени", "Коммуникация", "Обратная связь")),
    ),
    cases=(
        TrainingCase("Неясное задание", "Руководитель дал расплывчатую задачу. Что делать?", ("Уточнить результат, критерии и срок", "Молча сделать что угодно", "Не приступать и ничего не говорить"), 0, "Прояснять критерии результата.", "Хороший вопрос на старте экономит время на переделках."),
        TrainingCase("Ошибка новичка", "Ты допустил ошибку. Что лучше предпринять?", ("Скрыть", "Описать последствия и предложить исправление", "Обвинить коллегу"), 1, "Прозрачная работа с ошибками.", "Сообщи о проблеме и подготовь варианты исправления."),
        TrainingCase("Нет обратной связи", "Тебе месяц не дают обратную связь. Что делать?", ("Уточнить ожидания и договориться о встрече", "Считать, что всё идеально", "Уволиться без разговора"), 0, "Активно запрашивать обратную связь.", "Уточнение критериев помогает учиться и снижает неопределённость."),
    ),
)

SCENARIOS: dict[str, Scenario] = {s.code: s for s in (HISTORY, INTERNSHIP, ONBOARDING)}


def get_question(scenario_code: str, answers: dict) -> Question | None:
    """First unanswered step; no LLM allowed to skip a mandatory question."""
    for question in SCENARIOS[scenario_code].questions:
        if question.key not in answers:
            return question
    return None


def save_answer(scenario_code: str, answers: dict, key: str, value: str | list[str]) -> dict:
    scenario = SCENARIOS[scenario_code]
    question = next((q for q in scenario.questions if q.key == key), None)
    if question is None:
        raise ValueError("Неизвестное поле анкеты")
    if key in answers:
        raise ValueError("Поле уже заполнено; используйте сброс для нового прохождения")
    expected = get_question(scenario_code, answers)
    if expected is None or expected.key != key:
        raise ValueError("Этапы сценария необходимо проходить по порядку")
    if question.kind == "choice" and value not in question.options:
        raise ValueError("Ответ должен быть выбран из вариантов")
    if question.kind == "multi" and (not isinstance(value, list) or not 1 <= len(value) <= 3 or any(v not in question.options for v in value) or len(set(value)) != len(value)):
        raise ValueError("Выберите от одного до трёх вариантов")
    if question.kind == "text" and (not isinstance(value, str) or not value.strip() or len(value) > 1000):
        raise ValueError("Ответ не должен быть пустым")
    return {**answers, key: value}


def evaluate_case(scenario_code: str, case_index: int, selected_index: int) -> tuple[bool, str]:
    """Backward-compatible adapter; detailed assessment lives in examiner.py."""
    from .examiner import assess_case

    outcome = assess_case(scenario_code, case_index, selected_index)
    return outcome.correct, outcome.message


def report_markdown(scenario_code: str, answers: dict, attempts: dict[int, bool] | None = None) -> str:
    scenario = SCENARIOS[scenario_code]
    lines = [f"# Компас — {scenario.title}", "", "**Режим:** демонстрационный, без LLM и без автоматической проверки актуальности вузов.", "", "## Ответы пользователя"]
    for q in scenario.questions:
        value = answers.get(q.key, "Не указано")
        if isinstance(value, list):
            value = ", ".join(value)
        lines.append(f"- **{q.title}** {value}")
    lines += ["", "## Что ещё проверить"]
    if scenario_code == "history":
        lines += [
            "- Правила приёма, набор экзаменов и дополнительные испытания именно на выбранный год.",
            "- Учебные планы, научные направления, практики в СПбГУ, СГУ, РГГУ, МГУ.",
            "- Наличие общежития, расходы, возможности поддержки, способы подачи документов.",
            "- Собственные приоритеты: не отождествлять престиж с соответствием программы.",
        ]
        if answers.get("budget") in ("Пока не знаю", "Не хочу сообщать"):
            lines += ["- **Бюджет неизвестен:** ни один вуз из-за этого автоматически не исключается."]
    elif scenario_code == "internship":
        lines += ["- Проверить компанию и официальное описание стажировки.", "- Сравнить оплату, график, наставничество и ожидаемые навыки."]
    else:
        lines += ["- Обсудить ожидания и критерии результата с наставником или руководителем.", "- Согласовать следующую встречу для обратной связи."]
    if scenario_code == "history":
        # The default report is independently verifiable, even when downloaded.
        from datetime import date
        from .knowledge import KnowledgeRepository, information_response

        info = information_response(KnowledgeRepository.from_file(), "programs", answers.get("year"), as_of=date.today())
        lines += ["", "## Проверенные сведения о программах", "Данные проверены по официальным страницам; не заменяют правила приёма на выбранный год."]
        for item in info.universities:
            if item.verified:
                for fact in item.verified:
                    lines.append(f"- **{item.university}:** {fact.statement} [Официальный источник]({fact.source_url}) (проверено: {fact.retrieved_at.isoformat()}; актуальность до: {fact.valid_until.isoformat()}).")
            else:
                lines.append(f"- **{item.university}:** сведения требуют повторной проверки.")
        lines += ["", "## Статус правил приёма"]
        year = answers.get("year", "Пока не определён")
        lines.append(f"Правила поступления на выбранный год ({year}) должны быть подтверждены отдельно для каждого вуза; архивные условия 2026 года нельзя автоматически переносить на другие годы.")
    if attempts:
        lines += ["", "## Самопроверка", f"Пройдено кейсов: {len(attempts)}. Корректных ответов: {sum(attempts.values())}."]
        from .examiner import repeat_recommendations
        repeat = repeat_recommendations(scenario_code, attempts)
        if repeat:
            lines.append("Повторить (по категориям ошибок): " + "; ".join(repeat))
    lines += ["", "## Важное ограничение", "Этот отчёт — учебная карта вопросов, а не решение о поступлении или трудоустройстве. Все сведения необходимо подтверждать официальными источниками соответствующего года."]
    return "\n".join(lines)
