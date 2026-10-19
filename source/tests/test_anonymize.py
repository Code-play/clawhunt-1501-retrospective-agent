"""确定性假名化测试：稳定性、可复现、PII 拒绝。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from retrospective_agent.anonymize import (  # noqa: E402
    AnonymizationError,
    Pseudonymizer,
    assert_no_pii,
)
from retrospective_agent.events import Event, load_events  # noqa: E402

SAMPLES = ROOT / "samples" / "process_events.jsonl"


def make_event(**overrides):
    base = {
        "event_id": "EVT-X",
        "timestamp": "2026-03-02T09:00:00Z",
        "actor": "Chen Wei",
        "actor_role": "sre",
        "action": "deploy",
        "outcome": "success",
        "service": "payment",
        "source_type": "deploy_pipeline",
        "source_ref": "PR-1",
        "customer": "Northwind Retail",
        "attributes": {},
        "text": "",
    }
    base.update(overrides)
    return Event(**base)


class TestPseudonymizer(unittest.TestCase):
    def test_01_stable_across_instances(self):
        a = Pseudonymizer().alias("PERSON", "Chen Wei")
        b = Pseudonymizer().alias("PERSON", "Chen Wei")
        self.assertEqual(a, b)
        self.assertTrue(a.startswith("PERSON-"))

    def test_02_different_inputs_differ(self):
        pz = Pseudonymizer()
        self.assertNotEqual(pz.alias("PERSON", "Chen Wei"), pz.alias("PERSON", "Li Na"))

    def test_03_field_roles_are_separated(self):
        pz = Pseudonymizer()
        self.assertNotEqual(pz.alias("PERSON", "X"), pz.alias("CUST", "X"))

    def test_04_anonymize_event_keeps_structure(self):
        pz = Pseudonymizer()
        ev = make_event()
        anon = pz.anonymize_event(ev)
        self.assertTrue(anon.actor.startswith("PERSON-"))
        self.assertTrue(anon.customer.startswith("CUST-"))
        self.assertTrue(anon.source_ref.startswith("REF-"))
        self.assertTrue(anon.event_id.startswith("EVT-"))
        self.assertEqual(anon.action, ev.action)
        self.assertEqual(anon.timestamp, ev.timestamp)

    def test_05_reproduces_whole_stream(self):
        pz = Pseudonymizer()
        once = [e.event_id for e in pz.anonymize_events(load_events(SAMPLES))]
        twice = [e.event_id for e in pz.anonymize_events(load_events(SAMPLES))]
        self.assertEqual(once, twice)

    def test_06_pii_in_text_rejected(self):
        with self.assertRaises(AnonymizationError):
            assert_no_pii(make_event(text="联系 someone@example.com"))

    def test_07_clean_event_passes(self):
        assert_no_pii(make_event(text="正常的运维记录"))  # 不抛异常即通过


if __name__ == "__main__":
    unittest.main(verbosity=2)
