"""Formatos de respuesta del dominio de incidentes (lo que ve el cliente)."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.domains.incidents import service


def to_number(value: Decimal | None) -> float | None:
    # Pydantic serializa Decimal como texto; el cliente espera números.
    return None if value is None else float(value)


class RuleCount(BaseModel):
    rule: str
    label: str
    count: int


class InvalidRecord(BaseModel):
    incident_id: str
    row: int
    rules: list[str]


class CodeCount(BaseModel):
    code: str
    count: int
    percentage: float | None


class ScoreCount(BaseModel):
    score: int
    label: str
    count: int
    percentage: float | None


class Satisfaction(BaseModel):
    closed_cases: int
    scored_cases: int
    average: float | None
    distribution: list[ScoreCount]


class AnalysisResponse(BaseModel):
    source_file: str
    analyzed_at: datetime
    total_records: int
    valid_records: int
    invalid_records: int
    # Incluye siempre todas las reglas, aunque estén en 0.
    invalid_breakdown: list[RuleCount]
    invalid_records_detail: list[InvalidRecord]
    categories: list[CodeCount]
    statuses: list[CodeCount]
    satisfaction: Satisfaction

    @classmethod
    def from_summary(cls, summary: dict, source_file: str, analyzed_at: datetime) -> "AnalysisResponse":
        valid = summary["valid"]
        scored = summary["scored_cases"]
        return cls(
            source_file=source_file,
            analyzed_at=analyzed_at,
            total_records=summary["total"],
            valid_records=valid,
            invalid_records=summary["invalid"],
            invalid_breakdown=[
                RuleCount(rule=key, label=label, count=summary["rules"][key]) for key, label in service.RULES
            ],
            invalid_records_detail=[InvalidRecord(**detail) for detail in summary["invalid_details"]],
            categories=[
                CodeCount(code=code, count=count, percentage=to_number(service.percentage(count, valid)))
                for code, count in summary["categories"].items()
            ],
            statuses=[
                CodeCount(code=code, count=count, percentage=to_number(service.percentage(count, valid)))
                for code, count in summary["statuses"].items()
            ],
            satisfaction=Satisfaction(
                closed_cases=summary["closed_cases"],
                scored_cases=scored,
                average=to_number(service.rounded_average(summary)),
                distribution=[
                    ScoreCount(
                        score=score,
                        label=service.SCORE_LABELS[score],
                        count=count,
                        percentage=to_number(service.percentage(count, scored)),
                    )
                    for score, count in summary["scores"].items()
                ],
            ),
        )
