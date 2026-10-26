"""Kompas MVP 0.2.1. Start with: streamlit run app.py"""
from __future__ import annotations

import streamlit as st
from kompas.core import SCENARIOS, get_question, save_answer, report_markdown
from kompas.examiner import assess_case, repeat_recommendations
from kompas.knowledge import KnowledgeRepository, TOPICS, information_response
from kompas.model import RuleBasedModel

st.set_page_config(page_title="Компас — AI-наставник", page_icon="🧭", layout="centered")
st.markdown("""
<style>
.block-container { max-width: 860px; padding-top: 2.4rem; }
[data-testid="stMetricValue"] {font-size: 1.6rem;}
</style>
""", unsafe_allow_html=True)

if "active_scenario" not in st.session_state:
    st.session_state.active_scenario = "history"
if "answers" not in st.session_state:
    st.session_state.answers = {code: {} for code in SCENARIOS}
if "attempts" not in st.session_state:
    st.session_state.attempts = {code: {} for code in SCENARIOS}
if "exam_results" not in st.session_state:
    st.session_state.exam_results = {code: {} for code in SCENARIOS}

with st.sidebar:
    st.title("🧭 Компас")
    st.caption("MVP 0.2.1 · Локальный режим без API-ключа")
    selected = st.selectbox(
        "Жизненный сценарий",
        options=list(SCENARIOS),
        format_func=lambda c: SCENARIOS[c].title,
        index=list(SCENARIOS).index(st.session_state.active_scenario),
    )
    st.session_state.active_scenario = selected
    if st.button("Начать сценарий заново", use_container_width=True):
        st.session_state.answers[selected] = {}
        st.session_state.attempts[selected] = {}
        st.session_state.exam_results[selected] = {}
        st.rerun()
    st.divider()
    st.info("Тестовый режим: фиксированные вопросы и проверяемые правила. Реальная языковая модель пока не подключена.")

scenario = SCENARIOS[st.session_state.active_scenario]
answers = st.session_state.answers[scenario.code]
attempts = st.session_state.attempts[scenario.code]
exam_results = st.session_state.exam_results[scenario.code]

st.title("🧭 Компас")
st.subheader(scenario.title)
st.write(scenario.description)
st.caption("Система помогает понять альтернативы и риски, но не выбирает жизненную траекторию за человека.")

mentor_tab, trainer_tab, sources_tab, tech_tab = st.tabs(["Наставник", "Тренажёр", "Источники", "О проекте"])

with mentor_tab:
    total = len(scenario.questions)
    st.progress(len(answers) / total)
    st.caption(f"Прохождение: {len(answers)} из {total} шагов")
    question = get_question(scenario.code, answers)
    if question is not None:
        st.markdown("### " + question.title)
        if question.help:
            st.caption(question.help)
        with st.form(f"question_{scenario.code}_{question.key}", clear_on_submit=False):
            if question.kind == "choice":
                response = st.radio("Выбери ответ", question.options, key=f"option_{scenario.code}_{question.key}")
            elif question.kind == "multi":
                response = st.multiselect("Выбери от 1 до 3 критериев", question.options, max_selections=3, key=f"multi_{scenario.code}_{question.key}")
            else:
                response = st.text_input("Твой ответ")
            submitted = st.form_submit_button("Продолжить →", type="primary")
        if submitted:
            try:
                st.session_state.answers[scenario.code] = save_answer(scenario.code, answers, question.key, response)
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    else:
        st.success("Маршрут пройден. Ни один университет не назначен «правильным» автоматически.")
        if scenario.code == "history":
            if answers.get("budget") in ("Пока не знаю", "Не хочу сообщать"):
                st.info("Бюджет неизвестен. СПбГУ, СГУ, РГГУ и МГУ остаются рассматриваемыми вариантами.")
            if answers.get("year") == "2027":
                st.warning("Для поступления в 2027 году требуются официальные правила именно 2027 года. Данные 2026 года — только справочные.")
        st.markdown("### Персональная карта вопросов")
        st.markdown(report_markdown(scenario.code, answers, attempts))
        st.download_button(
            "Скачать отчёт (.md)",
            data=report_markdown(scenario.code, answers, attempts).encode("utf-8"),
            file_name=f"kompas_{scenario.code}_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
        st.caption("Экспорт PDF запланирован для версии Lead. Здесь пока доступен Markdown.")

with trainer_tab:
    st.markdown("### Тренажёр решений")
    st.write("Это **детерминированная самопроверка**, не оценка свободного текста нейросетью. Ответы и ошибки учитываются только в текущем сеансе приложения.")
    for i, case in enumerate(scenario.cases):
        with st.expander(f"Кейс {i+1}. {case.title}", expanded=i == 0):
            st.write(case.prompt)
            with st.form(f"case_{scenario.code}_{i}"):
                user_choice = st.radio("Какой подход выберешь?", range(len(case.options)), format_func=lambda idx: case.options[idx], key=f"case_radio_{scenario.code}_{i}")
                check = st.form_submit_button("Проверить ответ")
            if check:
                result = assess_case(scenario.code, i, user_choice)
                st.session_state.attempts[scenario.code][i] = result.correct
                st.session_state.exam_results[scenario.code][i] = user_choice
            # Feedback survives a widget rerun within the current Streamlit session.
            if i in exam_results:
                result = assess_case(scenario.code, i, exam_results[i])
                if result.correct:
                    st.success(result.message)
                else:
                    st.warning(result.message)
                    st.caption("Категория ошибки: " + result.error_category)
                st.caption("Последняя попытка: " + ("верно" if result.correct else "нужно повторить"))
    st.divider()
    st.metric("Пройдено кейсов", f"{len(attempts)}/{len(scenario.cases)}")
    needs_repeat = repeat_recommendations(scenario.code, attempts)
    if needs_repeat:
        st.warning("Рекомендуется повторить: " + "; ".join(needs_repeat))

with sources_tab:
    st.markdown("### Контролируемый информационный режим")
    if scenario.code == "history":
        st.caption("Сведения берутся из локального реестра с официальными URL, датами и годом набора. Сайты не опрашиваются автоматически.")
        selected_topic = st.selectbox("Что изучить?", list(TOPICS), format_func=lambda code: TOPICS[code])
        year = answers.get("year")
        st.caption(f"Год поступления из анкеты: {year or 'пока не указан'}")
        try:
            repo = KnowledgeRepository.from_file()
            data = information_response(repo, selected_topic, year)
        except (OSError, ValueError) as exc:
            st.error(f"Не удалось прочитать проверенную базу знаний: {exc}")
        else:
            st.info(data.notice)
            for item in data.universities:
                st.markdown(f"#### {item.university}")
                if not item.verified:
                    st.write("Подтверждённых данных для выбранного раздела и года пока нет. Требуется проверка.")
                for fact in item.verified:
                    st.write(fact.statement)
                    st.caption(f"Проверено: {fact.retrieved_at}; актуальность записи до: {fact.valid_until}. Это не гарантия актуальности сайта в момент просмотра.")
                    st.markdown(f"[Открыть официальный источник]({fact.source_url})")
                if item.archive:
                    with st.expander("Архивные сведения — не использовать как текущие правила"):
                        for fact in item.archive:
                            st.write(f"Набор {fact.intake_year or 'не указан'}: {fact.statement}")
                            st.caption(f"Проверено: {fact.retrieved_at}; статус: устарело / не подходит к выбранному году.")
                            if fact.source_url:
                                st.markdown(f"[Источник архивной записи]({fact.source_url})")
            st.divider()
            st.markdown("**Вопрос для дальнейшего исследования**")
            st.write(RuleBasedModel().generate_followup({"topic": selected_topic}, ()).text)
            st.caption("Вопрос сформулирован локальными правилами, а не языковой моделью.")
    else:
        st.info("Для сценария пока нет проверенных записей в базе знаний. Сам сценарий и тренажёр доступны; факты не подставляются автоматически.")

with tech_tab:
    st.markdown("""
### Границы версии 0.2.1

- **Работает:** выбор из трёх жизненных сценариев; пошаговый маршрут; обработка неизвестного бюджета; пять кейсов Георгия; самопроверка с объяснением вариантов и категориями ошибок; временная память результатов; экспорт Markdown; локальная база проверенных ссылок; информационный режим с отделением архивных данных; интерфейс локального адаптера.
- **Пока не работает:** свободный диалог с LLM, семантическая проверка произвольных ответов, автоматическое обновление сайтов вузов, постоянная база профилей, адаптация между запусками, экспорт PDF, достоверный прогноз поступления.
- **Как подключим LLM:** заменим генератор вопросов и анализатор свободных ответов на отдельный API-адаптер. Контроль этапов диалога, исходных фактов и подтверждения источников останется в Python.

Проект не собирает настоящие персональные данные и по умолчанию ничего не записывает на диск. Ответы хранятся в сеансе Streamlit, пока он существует.
""")
