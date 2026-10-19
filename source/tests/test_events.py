"""事件流 Schema 校验测试。"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from retrospective_agent.events import (  # noqa: E402
    EventSchemaError,
    load_events,
    parse_ts,
    validate_event,
)

SAMPLES = ROOT / "samples" / "process_events.jsonl"


class TestEventSchema(unittest.TestCase):
    def test_01_loads_and_sorts(self):
        events = load_events(SAMPLES)
        self.assertEqual(len(events), 32)
        stamps = [e.timestamp for e in events]
        self.assertEqual(stamps, sorted(stamps))

    def test_02_missing_field_rejected(self):
        raw = {
            "event_id": "E1",
            "timestamp": "2026-03-02T09:00:00Z",
            "actor": "A",
            "actor_role": "sre",
            "action": "deploy",
            "outcome": "success",
            "service": "payment",
            "source_type": "deploy_pipeline",
        }
        with self.assertRaises(EventSchemaError):
            validate_event(raw)  # 缺少 source_ref

    def test_03_invalid_action_rejected(self):
        raw = {
            "event_id": "E2",
            "timestamp": "2026-03-02T09:00:00Z",
            "actor": "A",
            "actor_role": "sre",
            "action": "teleport",
            "outcome": "success",
            "service": "payment",
            "source_type": "deploy_pipeline",
            "source_ref": "PR-1",
        }
        with self.assertRaises(EventSchemaError):
            validate_event(raw)

    def test_04_bad_timestamp_rejected(self):
        with self.assertRaises(EventSchemaError):
            parse_ts("not-a-timestamp")

    def test_05_duplicate_event_id_rejected(self):
        line = json.dumps(
            {
                "event_id": "DUP",
                "timestamp": "2026-03-02T09:00:00Z",
                "actor": "A",
                "actor_role": "sre",
                "action": "deploy",
                "outcome": "success",
                "service": "payment",
                "source_type": "deploy_pipeline",
                "source_ref": "PR-1",
            },
            ensure_ascii=False,
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "dup.jsonl"
            p.write_text(line + "\n" + line + "\n", encoding="utf-8")
            with self.assertRaises(EventSchemaError):
                load_events(p)

    def test_06_attributes_must_be_object(self):
        raw = {
            "event_id": "E3",
            "timestamp": "2026-03-02T09:00:00Z",
            "actor": "A",
            "actor_role": "sre",
            "action": "deploy",
            "outcome": "success",
            "service": "payment",
            "source_type": "deploy_pipeline",
            "source_ref": "PR-1",
            "attributes": ["bad"],
        }
        with self.assertRaises(EventSchemaError):
            validate_event(raw)


if __name__ == "__main__":
    unittest.main(verbosity=2)
