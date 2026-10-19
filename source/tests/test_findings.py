"""事实→结论 的强制依据测试，以及阈值/证据不足的行为。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from retrospective_agent.cli import build_retrospective, load_ruleset  # noqa: E402
from retrospective_agent.events import Event  # noqa: E402
from retrospective_agent.evidence import EvidencePolicy, EvidenceRef, collect_evidence  # noqa: E402
from retrospective_agent.anonymize import Pseudonymizer  # noqa: E402
from retrospective_agent.events import load_events  # noqa: E402
from retrospective_agent.findings import (  # noqa: E402
    Conclusion,
    GroundingError,
    build_conclusions,
    build_facts,
)

CONFIG = ROOT / "config"
SAMPLES = ROOT / "samples" / "process_events.jsonl"


def make_event(event_id, action="deploy", outcome="success", severity=None):
    attrs = {"severity": severity} if severity else {}
    return Event(
        event_id=event_id,
        timestamp="2026-03-02T09:00:00Z",
        actor="PERSON-1",
        actor_role="sre",
        action=action,
        outcome=outcome,
        service="payment",
        source_type="incident_log",
        source_ref="REF-1",
        attributes=attrs,
    )


class TestGrounding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = EvidencePolicy.load(CONFIG / "evidence_whitelist.json")
        cls.ruleset = load_ruleset(CONFIG / "retrospective_rules.json")

    def test_01_conclusion_without_evidence_rejected(self):
        with self.assertRaises(GroundingError):
            Conclusion(
                conclusion_id="C-99",
                rule_id="R-X",
                statement="没有证据的结论",
                evidence=(),
                fact_ids=(),
                confidence=0.9,
            )

    def test_02_reported_conclusions_are_grounded(self):
        for scenario in self.ruleset["scenarios"]:
            retro = build_retrospective(load_events(SAMPLES), self.policy, self.ruleset, scenario)
            self.assertTrue(retro.conclusions)
            for c in retro.conclusions:
                self.assertTrue(c.evidence, f"{c.conclusion_id} 无证据")
                for ref in c.evidence:
                    self.assertTrue(ref.evidence_id)
                    self.assertTrue(ref.timestamp)

    def test_03_below_threshold_rule_is_skipped(self):
        events = [make_event("E1"), make_event("E2")]
        emap = {
            e.event_id: EvidenceRef(e.event_id, e.timestamp, e.source_type, "REF-1", e.action, "s")
            for e in events
        }
        rule = {
            "rule_id": "R-HIGH",
            "filter": {"action": ["deploy"]},
            "aggregate": {"op": "count"},
            "min_value": 99,
            "min_evidence": 1,
            "fact_template": "v={value}",
        }
        facts, skipped = build_facts(events, emap, [rule])
        self.assertEqual(facts, [])
        self.assertEqual(len(skipped), 1)
        self.assertIn("未达阈值", skipped[0]["reason"])

    def test_04_insufficient_evidence_rule_is_skipped(self):
        events = [make_event("E1")]
        emap = {
            e.event_id: EvidenceRef(e.event_id, e.timestamp, e.source_type, "REF-1", e.action, "s")
            for e in events
        }
        rule = {
            "rule_id": "R-NEED3",
            "filter": {"action": ["deploy"]},
            "aggregate": {"op": "count"},
            "min_value": 0,
            "min_evidence": 3,
            "fact_template": "v={value}",
        }
        facts, skipped = build_facts(events, emap, [rule])
        self.assertEqual(facts, [])
        self.assertIn("证据不足", skipped[0]["reason"])

    def test_05_fact_evidence_sorted_deterministically(self):
        events = [make_event("E2"), make_event("E1")]
        emap = {
            e.event_id: EvidenceRef(e.event_id, e.timestamp, e.source_type, "REF-1", e.action, "s")
            for e in events
        }
        rule = {
            "rule_id": "R-CNT",
            "filter": {"action": ["deploy"]},
            "aggregate": {"op": "count"},
            "min_value": 1,
            "min_evidence": 1,
            "fact_template": "v={value}",
            "conclusion_template": "c={value}",
        }
        facts, _ = build_facts(events, emap, [rule])
        ids = [r.evidence_id for r in facts[0].evidence]
        self.assertEqual(ids, ["E1", "E2"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
