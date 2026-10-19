"""结论 → 改进项。

每条改进项都必须至少回溯到一条结论；结论的证据即改进项的证据。
这样"改进项"不是凭空冒出来的待办，而是能从 事实→证据→结论 一路查回来。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .evidence import EvidenceRef
from .findings import Conclusion


class TraceabilityError(ValueError):
    """改进项无法回溯到结论。"""


@dataclass(frozen=True)
class Improvement:
    action_id: str
    rule_id: str
    statement: str
    rationale: str
    owner_role: str
    priority: str
    conclusion_ids: tuple[str, ...]
    evidence: tuple[EvidenceRef, ...]

    def __post_init__(self) -> None:
        if not self.conclusion_ids:
            raise TraceabilityError(f"改进项 {self.action_id} 没有回溯到任何结论，拒绝产出")
        if not self.evidence:
            raise TraceabilityError(f"改进项 {self.action_id} 没有任何证据，拒绝产出")


def build_improvements(
    conclusions: list[Conclusion], rules: list[dict[str, Any]]
) -> list[Improvement]:
    by_id = {r["rule_id"]: r for r in rules}
    improvements: list[Improvement] = []
    for i, conclusion in enumerate(conclusions, start=1):
        rule = by_id[conclusion.rule_id]
        spec = rule.get("action")
        if not spec:
            continue
        improvements.append(
            Improvement(
                action_id=f"A-{i:02d}",
                rule_id=conclusion.rule_id,
                statement=spec["statement"],
                rationale=f"由结论 {conclusion.conclusion_id} 支撑（该结论挂 {len(conclusion.evidence)} 条证据）",
                owner_role=spec.get("owner_role", "unassigned"),
                priority=spec.get("priority", "medium"),
                conclusion_ids=(conclusion.conclusion_id,),
                evidence=conclusion.evidence,
            )
        )
    return improvements


def trace_improvement(improvement: Improvement, conclusions: list[Conclusion]) -> list[EvidenceRef]:
    """回溯一条改进项：改进项 -> 结论 -> 证据。返回全部证据（去重、确定性排序）。"""
    by_id = {c.conclusion_id: c for c in conclusions}
    chain: dict[str, EvidenceRef] = {}
    for cid in improvement.conclusion_ids:
        conclusion = by_id.get(cid)
        if conclusion is None:
            raise TraceabilityError(f"改进项 {improvement.action_id} 引用了不存在的结论 {cid}")
        for ref in conclusion.evidence:
            chain[ref.evidence_id] = ref
    if not chain:
        raise TraceabilityError(f"改进项 {improvement.action_id} 回溯后没有任何证据")
    return [chain[k] for k in sorted(chain, key=lambda k: (chain[k].timestamp, k))]
