"""渲染 Markdown 复盘报告。

模板来自 config/report_template.md，占位符形如 {{facts}}。
渲染是纯字符串替换，确定性、无副作用。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .actions import Improvement, trace_improvement
from .evidence import EvidenceRef, RejectedEvidence
from .findings import Conclusion, Fact


@dataclass
class Retrospective:
    scenario_id: str
    title: str
    window_from: str
    window_to: str
    events_total: int
    evidence_index: list[EvidenceRef]
    rejected: list[RejectedEvidence]
    facts: list[Fact]
    conclusions: list[Conclusion]
    improvements: list[Improvement]
    skipped: list[dict[str, Any]] = field(default_factory=list)


def _ev_label(ref: EvidenceRef) -> str:
    return f"`{ref.evidence_id}`@{ref.timestamp}"


def _render_facts(retro: Retrospective) -> str:
    lines: list[str] = []
    if not retro.facts:
        lines.append("_无达到阈值的事实。_")
    for fact in retro.facts:
        lines.append(f"**{fact.fact_id}**（规则 `{fact.rule_id}`）：{fact.statement}")
        lines.append("  证据：" + "、".join(_ev_label(e) for e in fact.evidence))
        lines.append("")
    if retro.skipped:
        lines.append("未构成事实/结论的规则（可解释）：")
        for s in retro.skipped:
            lines.append(f"- `{s['rule_id']}`：{s['reason']}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _render_evidence_table(retro: Retrospective) -> str:
    rows = [
        "| 证据 ID | 时间戳 | 来源类型 | 来源单据 | 摘要 |",
        "|---|---|---|---|---|",
    ]
    for ref in retro.evidence_index:
        rows.append(
            f"| `{ref.evidence_id}` | {ref.timestamp} | {ref.source_type} | "
            f"`{ref.source_ref}` | {ref.summary} |"
        )
    return "\n".join(rows)


def _render_conclusions(retro: Retrospective) -> str:
    lines: list[str] = []
    if not retro.conclusions:
        lines.append("_无有依据的结论。_")
    for c in retro.conclusions:
        lines.append(f"**{c.conclusion_id}**（置信度 {c.confidence:.2f}）：{c.statement}")
        lines.append(
            f"  依据事实 {'、'.join('`' + f + '`' for f in c.fact_ids)}；"
            f"证据 {'、'.join(_ev_label(e) for e in c.evidence)}"
        )
        lines.append("")
    return "\n".join(lines).rstrip()


def _render_improvements(retro: Retrospective) -> str:
    lines: list[str] = []
    if not retro.improvements:
        lines.append("_无改进项。_")
    for a in retro.improvements:
        lines.append(
            f"**{a.action_id}**［{a.priority}］{a.statement}"
        )
        lines.append(
            f"  负责角色：{a.owner_role}；回溯结论：{a.conclusion_ids[0]}；"
            f"{a.rationale}"
        )
        lines.append("")
    return "\n".join(lines).rstrip()


def _render_rejected(retro: Retrospective) -> str:
    if not retro.rejected:
        return "_无。所有来源均在白名单内。_"
    rows = [
        "| 证据 ID | 时间戳 | 来源类型 | 拒绝原因 |",
        "|---|---|---|---|",
    ]
    for r in retro.rejected:
        rows.append(f"| `{r.evidence_id}` | {r.timestamp} | {r.source_type} | {r.reason} |")
    return "\n".join(rows)


def _render_trace(retro: Retrospective) -> str:
    lines: list[str] = []
    facts_by_id = {f.fact_id: f for f in retro.facts}
    conclusions_by_id = {c.conclusion_id: c for c in retro.conclusions}
    for a in retro.improvements:
        evidence = trace_improvement(a, retro.conclusions)
        conclusion = conclusions_by_id[a.conclusion_ids[0]]
        fact = facts_by_id[conclusion.fact_ids[0]]
        chain = (
            f"{a.action_id} → {conclusion.conclusion_id} → {fact.fact_id} → "
            + "、".join(_ev_label(e) for e in evidence)
        )
        lines.append(f"- {chain}")
    return "\n".join(lines) if lines else "_无。_"


def render(retro: Retrospective, template_path: str | Path) -> str:
    template = Path(template_path).read_text(encoding="utf-8")
    mapping = {
        "title": retro.title,
        "scenario_id": retro.scenario_id,
        "window_from": retro.window_from,
        "window_to": retro.window_to,
        "events_total": str(retro.events_total),
        "evidence_accepted": str(len(retro.evidence_index)),
        "evidence_rejected": str(len(retro.rejected)),
        "facts": _render_facts(retro),
        "evidence_table": _render_evidence_table(retro),
        "conclusions": _render_conclusions(retro),
        "improvements": _render_improvements(retro),
        "rejected": _render_rejected(retro),
        "trace": _render_trace(retro),
    }
    for key, value in mapping.items():
        template = template.replace("{{" + key + "}}", value)
    return template if template.endswith("\n") else template + "\n"
