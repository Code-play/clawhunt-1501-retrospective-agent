"""事件流 Schema：定义、加载与校验。

复盘的一切都建立在"事件"之上。事件必须先通过结构校验，才能进入
假名化、证据白名单与结论生成。校验不通过的事件不会被静默丢弃，
而是抛 EventSchemaError，让问题可见。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class EventSchemaError(ValueError):
    """事件不符合 Schema。"""


# 允许的取值域（可由需求扩展；越界即拒）
ALLOWED_ACTIONS: frozenset[str] = frozenset(
    {
        "incident_opened",
        "incident_resolved",
        "escalation",
        "deploy",
        "rollback",
        "review_requested",
        "review_completed",
        "ticket_opened",
        "ticket_closed",
        "postmortem_published",
    }
)
ALLOWED_OUTCOMES: frozenset[str] = frozenset({"success", "failure", "partial", "pending", "none"})
ALLOWED_ROLES: frozenset[str] = frozenset(
    {"oncall_engineer", "sre", "release_manager", "support_agent", "customer"}
)

REQUIRED_FIELDS: tuple[str, ...] = (
    "event_id",
    "timestamp",
    "actor",
    "actor_role",
    "action",
    "outcome",
    "service",
    "source_type",
    "source_ref",
)


def parse_ts(value: str) -> datetime:
    """解析 ISO8601 时间戳，统一到 UTC，便于确定性排序。"""
    if not isinstance(value, str) or not value.strip():
        raise EventSchemaError("timestamp 不能为空")
    raw = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise EventSchemaError(f"timestamp 不是合法 ISO8601：{value!r}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class Event:
    """一条过程事件。attributes 存放可量化的附加字段（如严重级别、检测时长）。"""

    event_id: str
    timestamp: str
    actor: str
    actor_role: str
    action: str
    outcome: str
    service: str
    source_type: str
    source_ref: str
    customer: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    text: str = ""

    @property
    def dt(self) -> datetime:
        return parse_ts(self.timestamp)

    def get(self, key: str) -> Any:
        """支持 'attributes.severity' 形式的取值；否则取顶层字段。"""
        if key.startswith("attributes."):
            return self.attributes.get(key.split(".", 1)[1])
        return getattr(self, key, None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "actor_role": self.actor_role,
            "action": self.action,
            "outcome": self.outcome,
            "service": self.service,
            "source_type": self.source_type,
            "source_ref": self.source_ref,
            "customer": self.customer,
            "attributes": dict(self.attributes),
            "text": self.text,
        }


def validate_event(raw: dict[str, Any], index: int = -1) -> Event:
    """校验单条原始事件，返回 Event；不合法则抛 EventSchemaError。"""
    where = f"第 {index} 条事件" if index >= 0 else "事件"
    if not isinstance(raw, dict):
        raise EventSchemaError(f"{where}必须是 JSON 对象")

    for key in REQUIRED_FIELDS:
        if key not in raw or raw[key] in (None, ""):
            raise EventSchemaError(f"{where}缺少必填字段 {key}")

    parse_ts(raw["timestamp"])

    if raw["action"] not in ALLOWED_ACTIONS:
        raise EventSchemaError(f"{where}的 action 非法：{raw['action']!r}")
    if raw["outcome"] not in ALLOWED_OUTCOMES:
        raise EventSchemaError(f"{where}的 outcome 非法：{raw['outcome']!r}")
    if raw["actor_role"] not in ALLOWED_ROLES:
        raise EventSchemaError(f"{where}的 actor_role 非法：{raw['actor_role']!r}")

    attributes = raw.get("attributes") or {}
    if not isinstance(attributes, dict):
        raise EventSchemaError(f"{where}的 attributes 必须是对象")

    return Event(
        event_id=str(raw["event_id"]),
        timestamp=str(raw["timestamp"]),
        actor=str(raw["actor"]),
        actor_role=str(raw["actor_role"]),
        action=str(raw["action"]),
        outcome=str(raw["outcome"]),
        service=str(raw["service"]),
        source_type=str(raw["source_type"]),
        source_ref=str(raw["source_ref"]),
        customer=str(raw.get("customer", "")),
        attributes=dict(attributes),
        text=str(raw.get("text", "")),
    )


def load_events(path: str | Path) -> list[Event]:
    """从 JSONL 加载事件流；校验每条并去重 event_id，按 (时间, ID) 确定性排序。"""
    p = Path(path)
    if not p.is_file():
        raise EventSchemaError(f"事件流文件不存在：{p}")

    events: list[Event] = []
    seen: set[str] = set()
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines()):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EventSchemaError(f"第 {i + 1} 行不是合法 JSON：{exc}") from exc
        event = validate_event(raw, index=i + 1)
        if event.event_id in seen:
            raise EventSchemaError(f"event_id 重复：{event.event_id}")
        seen.add(event.event_id)
        events.append(event)

    events.sort(key=lambda e: (e.dt, e.event_id))
    return events


def in_window(event: Event, start: str, end: str) -> bool:
    """半开区间 [start, end)。"""
    s, en = parse_ts(start), parse_ts(end)
    return s <= event.dt < en
