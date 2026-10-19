"""事实 → 结论。

- 事实（Fact）：对事件流做的中性量化观察，自带 >=1 条证据引用。
- 结论（Conclusion）：对事实的解读，强制挂 >=1 条证据 ID + 时间戳；
  没有证据的结论无法被构造出来（抛 GroundingError），这是"强制有依据"
  在数据结构层面的落地，而不是文档约定。

规则从 config/retrospective_rules.json 读取：过滤 + 聚合 + 阈值 + 文案模板。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .events import Event
from .evidence import EvidenceRef


class GroundingError(ValueError):
    """结论缺少证据引用。"""


@dataclass(frozen=True)
class Fact:
    fact_id: str
    rule_id: str
    statement: str
    evidence: tuple[EvidenceRef, ...]
    metric: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Conclusion:
    conclusion_id: str
    rule_id: str
    statement: str
    evidence: tuple[EvidenceRef, ...]
    fact_ids: tuple[str, ...]
    confidence: float

    def __post_init__(self) -> None:
        if not self.evidence:
            raise GroundingError(
                f"结论 {self.conclusion_id} 没有任何证据引用，拒绝产出"
            )
        for ref in self.evidence:
            if not ref.evidence_id or not ref.timestamp:
                raise GroundingError(
                    f"结论 {self.conclusion_id} 的证据缺少 ID 或时间戳，拒绝产出"
                )


def match_event(event: Event, criteria: dict[str, list[Any]] | None) -> bool:
    """criteria 形如 {'action': ['deploy'], 'attributes.severity': ['high']}。"""
    if not criteria:
        return True
    for key, allowed in criteria.items():
        if event.get(key) not in allowed:
            return False
    return True


def _aggregate(matched: list[Event], agg: dict[str, Any]) -> dict[str, Any]:
    op = agg.get("op")
    if op == "count":
        return {"op": "count", "value": float(len(matched)), "total": len(matched)}
    if op == "ratio":
        numerator = [e for e in matched if match_event(e, agg.get("numerator"))]
        value = (len(numerator) / len(matched)) if matched else 0.0
        return {
            "op": "ratio",
            "value": value,
            "total": len(matched),
            "ratio_numerator": len(numerator),
        }
    if op == "avg":
        field_name = agg.get("field")
        values = [float(e.get(field_name)) for e in matched if e.get(field_name) is not None]
        value = (sum(values) / len(values)) if values else 0.0
        return {"op": "avg", "value": value, "total": len(matched), "n": len(values)}
    raise ValueError(f"未知聚合操作：{op!r}")


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{round(value, 3):g}"
    return str(value)


def _groups(matched: list[Event], group_by: str | None) -> dict[str, int]:
    if not group_by:
        return {}
    counts: dict[str, int] = {}
    for e in matched:
        key = str(e.get(group_by))
        counts[key] = counts.get(key, 0) + 1
    return counts


def build_facts(
    events: list[Event],
    evidence_map: dict[str, EvidenceRef],
    rules: list[dict[str, Any]],
) -> tuple[list[Fact], list[dict[str, Any]]]:
    """按规则产出事实；未达阈值/证据不足的规则进入 skipped（可解释）。"""
    facts: list[Fact] = []
    skipped: list[dict[str, Any]] = []
    serial = 0

    for rule in rules:
        matched = [e for e in events if match_event(e, rule.get("filter"))]
        metric = _aggregate(matched, rule["aggregate"])
        value = metric["value"]

        if len(matched) < int(rule.get("min_evidence", 1)):
            skipped.append(
                {
                    "rule_id": rule["rule_id"],
                    "title": rule.get("title", ""),
                    "reason": f"证据不足：命中 {len(matched)} 条，低于下限 {rule.get('min_evidence', 1)}",
                }
            )
            continue
        if value < float(rule.get("min_value", 0)):
            skipped.append(
                {
                    "rule_id": rule["rule_id"],
                    "title": rule.get("title", ""),
                    "reason": f"未达阈值：实际 {_fmt(value)}，阈值 {_fmt(rule.get('min_value', 0))}",
                }
            )
            continue

        serial += 1
        fill = dict(metric)
        fill["value"] = _fmt(value)
        fill["groups"] = ", ".join(
            f"{k}={v}" for k, v in sorted(_groups(matched, rule.get("group_by")).items())
        ) or "-"
        evidence = tuple(sorted((evidence_map[e.event_id] for e in matched), key=lambda r: (r.timestamp, r.evidence_id)))
        facts.append(
            Fact(
                fact_id=f"F-{serial:02d}",
                rule_id=rule["rule_id"],
                statement=rule["fact_template"].format(**fill),
                evidence=evidence,
                metric=metric,
            )
        )
    return facts, skipped


def build_conclusions(facts: list[Fact], rules: list[dict[str, Any]]) -> list[Conclusion]:
    """每条事实 -> 一条结论；结论继承事实的全部证据引用。"""
    by_id = {r["rule_id"]: r for r in rules}
    conclusions: list[Conclusion] = []
    for i, fact in enumerate(facts, start=1):
        rule = by_id[fact.rule_id]
        fill = {k: _fmt(v) for k, v in fact.metric.items() if k != "value"}
        fill["value"] = _fmt(fact.metric["value"])
        statement = rule["conclusion_template"].format(**fill)
        conclusions.append(
            Conclusion(
                conclusion_id=f"C-{i:02d}",
                rule_id=fact.rule_id,
                statement=statement,
                evidence=fact.evidence,
                fact_ids=(fact.fact_id,),
                confidence=float(rule.get("confidence", 0.6)),
            )
        )
    return conclusions
