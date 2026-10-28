"""Validated, local, citation-first knowledge store for the demo.

The repository never downloads content at runtime. A verification record is an
editorial assertion about an official URL checked on a known date, not a promise
that the page is still current when the app is subsequently opened.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

Verification = Literal["verified", "stale", "unverified"]
Topic = Literal["programs", "admission", "costs"]
UNIVERSITIES = ("СПбГУ", "СГУ", "РГГУ", "МГУ")
TOPICS: dict[str, str] = {
    "programs": "Программы по истории",
    "admission": "Условия поступления",
    "costs": "Расходы и проживание",
}
OFFICIAL_DOMAINS = ("spbu.ru", "sgu.ru", "rsuh.ru", "msu.ru")
DEFAULT_DATA = Path(__file__).resolve().parent / "data" / "facts.json"


@dataclass(frozen=True)
class Fact:
    fact_id: str
    subject_type: str
    university: str
    program: str | None
    topic: Topic
    statement: str
    value: str | int | float | None
    intake_year: int | None
    source_url: str | None
    retrieved_at: date | None
    valid_until: date | None
    verification_status: Verification
    notes: str

    @classmethod
    def from_dict(cls, item: dict) -> "Fact":
        mandatory = ("fact_id", "subject_type", "university", "program", "topic",
                     "statement", "value", "intake_year", "source_url", "retrieved_at",
                     "valid_until", "verification_status", "notes")
        if any(key not in item for key in mandatory):
            raise ValueError("Неполная запись факта")
        try:
            checked = date.fromisoformat(item["retrieved_at"]) if item["retrieved_at"] else None
            valid = date.fromisoformat(item["valid_until"]) if item["valid_until"] else None
        except (TypeError, ValueError) as exc:
            raise ValueError("Некорректная дата источника") from exc
        if (not isinstance(item["fact_id"], str) or not item["fact_id"]
            or not isinstance(item["statement"], str) or not item["statement"].strip()):
            raise ValueError("Нужны идентификатор и утверждение")
        if item["university"] not in UNIVERSITIES or item["topic"] not in TOPICS:
            raise ValueError("Неизвестный вуз или раздел")
        if item["verification_status"] not in ("verified", "stale", "unverified"):
            raise ValueError("Неизвестный статус проверки")
        year = item["intake_year"]
        if year is not None and (type(year) is not int or not 2000 <= year <= 2100):
            raise ValueError("Некорректный год набора")
        if item["topic"] == "admission" and year is None:
            raise ValueError("Для правил приёма обязателен год набора")
        url = item["source_url"]
        if url is not None:
            parsed = urlsplit(url)
            host = (parsed.hostname or "").lower()
            if parsed.scheme != "https" or not any(host == root or host.endswith("." + root) for root in OFFICIAL_DOMAINS):
                raise ValueError("Нужна HTTPS-ссылка официального вуза")
        if item["verification_status"] == "verified":
            if not url or checked is None or valid is None or valid < checked:
                raise ValueError("Подтверждённый факт требует источника и дат")
        return cls(
            fact_id=item["fact_id"], subject_type=item["subject_type"],
            university=item["university"], program=item["program"],
            topic=item["topic"], statement=item["statement"], value=item["value"],
            intake_year=year, source_url=url, retrieved_at=checked,
            valid_until=valid, verification_status=item["verification_status"],
            notes=item["notes"],
        )


class KnowledgeRepository:
    def __init__(self, facts: list[Fact]):
        identifiers = [fact.fact_id for fact in facts]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Повторяющиеся ID фактов")
        self.facts = tuple(facts)

    @classmethod
    def from_file(cls, path: Path = DEFAULT_DATA) -> "KnowledgeRepository":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("База знаний должна быть JSON-массивом")
        return cls([Fact.from_dict(record) for record in data])

    def find(self, *, university: str, topic: Topic) -> tuple[Fact, ...]:
        if university not in UNIVERSITIES or topic not in TOPICS:
            raise ValueError("Неизвестный фильтр")
        return tuple(f for f in self.facts if f.university == university and f.topic == topic)


def effective_status(fact: Fact, *, as_of: date, intake_year: int | None) -> Verification:
    """Older/different admission years must not become current facts."""
    if fact.verification_status != "verified":
        return fact.verification_status
    if fact.retrieved_at is None or fact.valid_until is None:
        return "unverified"
    if not fact.retrieved_at <= as_of <= fact.valid_until:
        return "stale"
    if fact.topic == "admission" and (intake_year is None or fact.intake_year != intake_year):
        return "stale"
    return "verified"


@dataclass(frozen=True)
class UniversityInformation:
    university: str
    verified: tuple[Fact, ...]
    archive: tuple[Fact, ...]


@dataclass(frozen=True)
class InformationResponse:
    topic: Topic
    intake_year: int | None
    universities: tuple[UniversityInformation, ...]
    notice: str


def information_response(
    repository: KnowledgeRepository,
    topic: Topic,
    year: str | None,
    *,
    as_of: date | None = None,
) -> InformationResponse:
    if topic not in TOPICS:
        raise ValueError("Неизвестный информационный раздел")
    intake_year = int(year) if year and year.isdecimal() and len(year) == 4 else None
    current = as_of or date.today()
    result = []
    for university in UNIVERSITIES:
        verified, archive = [], []
        for fact in repository.find(university=university, topic=topic):
            status = effective_status(fact, as_of=current, intake_year=intake_year)
            if status == "verified":
                verified.append(fact)
            elif status == "stale":
                archive.append(fact)
            # Unverified statements are intentionally never presented as facts.
        result.append(UniversityInformation(university, tuple(verified), tuple(archive)))
    notice = ("Правила приёма требуют отдельной проверки для выбранного года. "
              "Материалы других кампаний показаны только как архивные."
              if topic == "admission" else
              "Сведения о программах не подтверждают условия поступления на будущий год."
              if topic == "programs" else
              "Стоимость обучения, переезда и проживания неизвестна: отсутствие данных не означает нулевую цену.")
    return InformationResponse(topic, intake_year, tuple(result), notice)
