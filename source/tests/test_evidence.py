"""证据白名单测试：非白名单来源必须被拒绝并给出可解释原因。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from retrospective_agent.anonymize import Pseudonymizer  # noqa: E402
from retrospective_agent.events import load_events  # noqa: E402
from retrospective_agent.evidence import EvidencePolicy, collect_evidence  # noqa: E402

WHITELIST = ROOT / "config" / "evidence_whitelist.json"
SAMPLES = ROOT / "samples" / "process_events.jsonl"


class TestEvidenceWhitelist(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = EvidencePolicy.load(WHITELIST)
        cls.events = Pseudonymizer().anonymize_events(load_events(SAMPLES))
        cls.accepted, cls.rejected = collect_evidence(cls.events, cls.policy)

    def test_01_policy_is_loaded(self):
        self.assertIn("incident_log", self.policy.allowed_source_types)
        self.assertTrue(self.policy.is_allowed("ticket_system"))
        self.assertFalse(self.policy.is_allowed("unverified_hearsay"))

    def test_02_non_whitelisted_rejected(self):
        bad = {r.source_type for r in self.rejected}
        self.assertIn("unverified_hearsay", bad)
        self.assertIn("manager_note", bad)

    def test_03_rejection_reason_explains(self):
        for r in self.rejected:
            self.assertIn(r.source_type, r.reason)
            self.assertIn("不在证据白名单内", r.reason)

    def test_04_rejected_never_accepted(self):
        accepted_ids = {r.evidence_id for r in self.accepted}
        for r in self.rejected:
            self.assertNotIn(r.evidence_id, accepted_ids)

    def test_05_every_ref_has_id_and_timestamp(self):
        for r in self.accepted:
            self.assertTrue(r.evidence_id)
            self.assertTrue(r.timestamp)

    def test_06_split_is_complete(self):
        self.assertEqual(len(self.accepted) + len(self.rejected), len(self.events))


if __name__ == "__main__":
    unittest.main(verbosity=2)
