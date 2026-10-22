"""Kompas MVP 0.1. Start with: streamlit run app.py"""
from __future__ import annotations

import streamlit as st
from kompas.core import SCENARIOS, get_question, save_answer, evaluate_case, report_markdown

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

with st.sidebar:
    st.title("🧭 Компас")
    st.caption("MVP 0.1 · Демо без API-ключа")
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
        st.rerun()
    st.divider()
    st.info("Тестовый режим: фиксированные вопросы и проверяемые правила. Реальная языковая модель пока не подключена.")

scenario = SCENARIOS[st.session_state.active_scenario]
answers = st.session_state.answers[scenario.code]
attempts = st.session_state.attempts[scenario.code]

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
                is_correct, feedback = evaluate_case(scenario.code, i, user_choice)
                st.session_state.attempts[scenario.code][i] = is_correct
                if is_correct:
                    st.success(feedback)
                else:
                    st.warning(feedback)
            if i in attempts:
                st.caption("Последняя попытка: " + ("верно" if attempts[i] else "нужно повторить"))
    st.divider()
    st.metric("Пройдено кейсов", f"{len(attempts)}/{len(scenario.cases)}")
    needs_repeat = [scenario.cases[i].title for i, good in attempts.items() if not good]
    if needs_repeat:
        st.warning("Рекомендуется повторить: " + "; ".join(needs_repeat))

with sources_tab:
    st.markdown("### База знаний: демонстрационные источники")
    if scenario.code == "history":
        st.markdown("""
| Университет | Что подтверждено | Источник | Статус на 2027 |
|---|---|---|---|
| СГУ | Есть направление 46.03.01 «История», очная форма | [СГУ — институт](https://sgu.ru/struktura/imimo) | Требует обновления правил |
| СПбГУ | В материалах приёма 2026 указаны программы по истории | [СПбГУ — списки 2026](https://cabinet.spbu.ru/Lists/ForeignersLists/bak/list_8c1eaa86-c0d3-47e0-83d8-736e6d3f1e86.html) | Требует обновления правил |
| МГУ | Выбран Георгием для сравнения | Ещё не заполнено | Требуется проверка |
| РГГУ | Выбран Георгием для сравнения | Ещё не заполнено | Требуется проверка |
""")
        st.warning("В MVP нет актуальных проходных баллов, стоимости общежитий, мест и расчёта вероятности зачисления. Программа не должна их придумывать.")
    else:
        st.info("Для этого сценария источники предстоит подобрать и документировать. Сейчас работает только структура обсуждения и самопроверка.")

with tech_tab:
    st.markdown("""
### Границы версии 0.1

- **Работает:** выбор из трёх жизненных сценариев; пошаговый маршрут; обработка неизвестного бюджета; пять кейсов Георгия; самопроверка; временная память ошибок; экспорт Markdown.
- **Пока не работает:** свободный диалог с LLM, семантическая проверка произвольных ответов, автоматическое обновление сайтов вузов, постоянная база профилей, экспорт PDF, достоверный прогноз поступления.
- **Как подключим LLM:** заменим генератор вопросов и анализатор свободных ответов на отдельный API-адаптер. Контроль этапов диалога, исходных фактов и подтверждения источников останется в Python.

Проект не собирает настоящие персональные данные и по умолчанию ничего не записывает на диск. Ответы хранятся в сеансе Streamlit, пока он существует.
""")
