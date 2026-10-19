"""证据白名单。

复盘结论只能建立在被授权的来源之上。本模块把白名单做成硬约束：
不在 allowed_source_types 里的来源，一律拒绝，并给出可解释的原因
（列出被拒来源与当前白名单），拒绝项会如实出现在报告里。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .events import Event


class EvidencePolicyError(ValueError):
    """白名单配置非法。"""


@dataclass(frozen=True)
class EvidenceRef:
    """一条可被引用的证据：证据 ID + 时间戳 + 来源，缺一不可。"""

    evidence_id: str
    timestamp: str
    source_type: str
    source_ref: str
    action: str
    summary: str

    def __post_init__(self) -> None:
        if not self.evidence_id:
            raise ValueError("EvidenceRef.evidence_id 不能为空")
        if not self.timestamp:
            raise ValueError("EvidenceRef.timestamp 不能为空 —— 证据必须带时间戳")
        if not self.source_type:
            raise ValueError("EvidenceRef.source_type 不能为空")


@dataclass(frozen=True)
class RejectedEvidence:
    """被白名单拒绝的来源。"""

    evidence_id: str
    timestamp: str
    source_type: str
    reason: str


@dataclass(frozen=True)
class EvidencePolicy:
    """证据来源白名单。"""

    allowed_source_types: tuple[str, ...]

    @classmethod
    def load(cls, path: str | Path) -> "EvidencePolicy":
        p = Path(path)
        if not p.is_file():
            raise EvidencePolicyError(f"证据白名单配置不存在：{p}")
        data = json.loads(p.read_text(encoding="utf-8"))
        allowed = data.get("allowed_source_types")
        if not isinstance(allowed, dict) or not allowed:
            raise EvidencePolicyError("allowed_source_types 必须是非空对象")
        return cls(allowed_source_types=tuple(sorted(allowed.keys())))

    def is_allowed(self, source_type: str) -> bool:
        return source_type in self.allowed_source_types

    def reject_reason(self, source_type: str) -> str:
        return (
            f"来源类型 '{source_type}' 不在证据白名单内"
            f"（允许：{', '.join(self.allowed_source_types)}）"
        )


def _summarize(event: Event) -> str:
    parts = [f"{event.action}/{event.outcome}", f"service={event.service}"]
    for key in sorted(event.attributes):
        parts.append(f"{key}={event.attributes[key]}")
    return "; ".join(parts)


def collect_evidence(events: list[Event], policy: EvidencePolicy) -> tuple[list[EvidenceRef], list[RejectedEvidence]]:
    """按白名单把事件分成 采纳证据 / 拒绝证据，保持输入顺序（调用前已排序）。"""
    accepted: list[EvidenceRef] = []
    rejected: list[RejectedEvidence] = []
    for event in events:
        if policy.is_allowed(event.source_type):
            accepted.append(
                EvidenceRef(
                    evidence_id=event.event_id,
                    timestamp=event.timestamp,
                    source_type=event.source_type,
                    source_ref=event.source_ref,
                    action=event.action,
                    summary=_summarize(event),
                )
            )
        else:
            rejected.append(
                RejectedEvidence(
                    evidence_id=event.event_id,
                    timestamp=event.timestamp,
                    source_type=event.source_type,
                    reason=policy.reject_reason(event.source_type),
                )
            )
    return accepted, rejected
