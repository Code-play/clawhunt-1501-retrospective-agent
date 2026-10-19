"""确定性假名化。

把事件里可以直接识别人/单据的字段，替换成稳定假名：
  - 人员姓名      -> PERSON-xxxxxxxx
  - 客户名称      -> CUST-xxxxxxxx
  - 工单/流水线号 -> REF-xxxxxxxx
  - 事件 ID       -> EVT-xxxxxxxx

"稳定"指同一原文永远映射到同一假名（由固定盐 + SHA-256 前 8 位决定），
因此多次复跑、跨报告都能对齐；没有密钥无法反查原文。
自由文本里若残留邮箱/手机号/身份证号等可识别信息，直接拒绝处理。
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from typing import Any

from .events import Event

DEFAULT_SALT = "clawhunt-1501-retrospective"

# 假名前缀 -> 需要假名化的字段
FIELD_KINDS: tuple[tuple[str, str], ...] = (
    ("actor", "PERSON"),
    ("customer", "CUST"),
    ("source_ref", "REF"),
    ("event_id", "EVT"),
)

_PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("邮箱", re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")),
    ("手机号", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    ("身份证号", re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")),
)


class AnonymizationError(ValueError):
    """事件中残留了可识别的个人信息，拒绝处理。"""


@dataclass(frozen=True)
class Pseudonymizer:
    """确定性假名生成器。"""

    salt: str = DEFAULT_SALT
    length: int = 8

    def alias(self, kind: str, value: str) -> str:
        if value is None or not str(value).strip():
            return ""
        digest = hashlib.sha256(f"{self.salt}|{kind}|{value}".encode("utf-8")).hexdigest()
        return f"{kind}-{digest[: self.length]}"

    def anonymize_event(self, event: Event) -> Event:
        updates: dict[str, Any] = {}
        for field_name, kind in FIELD_KINDS:
            updates[field_name] = self.alias(kind, getattr(event, field_name))
        return replace(event, **updates)

    def anonymize_events(self, events: list[Event]) -> list[Event]:
        return [self.anonymize_event(e) for e in events]


def assert_no_pii(event: Event) -> None:
    """自由文本里出现可识别信息即拒绝。"""
    haystack = "\n".join([event.text, event.actor, event.customer, event.source_ref])
    for label, pattern in _PII_PATTERNS:
        m = pattern.search(haystack)
        if m:
            raise AnonymizationError(
                f"事件 {event.event_id} 的自由文本中出现疑似{label}：{m.group(0)[:4]}***，拒绝处理"
            )
