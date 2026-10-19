"""报告可溯源测试：改进项可回溯结论，渲染包含依据链。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from retrospective_agent.actions import (  # noqa: E402
    Improvement,
    TraceabilityError,
    trace_improvement,
)
from retrospective_agent.cli import build_retrospective, load_ruleset  # noqa: E402
from retrospective_agent.events import load_events  # noqa: E402
from retrospective_agent.evidence import EvidencePolicy, EvidenceRef  # noqa: E402
from retrospective_agent.report import render  # noqa: E402

CONFIG = ROOT / "config"
SAMPLES = ROOT / "samples" / "process_events.jsonl"
TEMPLATE = CONFIG / "report_template.md"


class TestReportTraceability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = EvidencePolicy.load(CONFIG / "evidence_whitelist.json")
        cls.ruleset = load_ruleset(CONFIG / "retrospective_rules.json")
        cls.reports = [
            build_retrospective(load_events(SAMPLES), cls.policy, cls.ruleset, s)
            for s in cls.ruleset["scenarios"]
        ]

    def test_01_two_reports_produced(self):
        self.assertEqual(len(self.reports), 2)
        self.assertEqual({r.scenario_id for r in self.reports}, {"incident_retro", "release_retro"})

    def test_02_every_improvement_traces_to_evidence(self):
        for retro in self.reports:
            for a in retro.improvements:
                chain = trace_improvement(a, retro.conclusions)
                self.assertTrue(chain)
                for ref in chain:
                    self.assertTrue(ref.evidence_id and ref.timestamp)

    def test_03_improvement_without_conclusion_rejected(self):
        ref = EvidenceRef("E1", "2026-03-02T09:00:00Z", "incident_log", "REF-1", "deploy", "s")
        with self.assertRaises(TraceabilityError):
            Improvement("A-X", "R-X", "s", "r", "sre", "high", (), (ref,))

    def test_04_improvement_without_evidence_rejected(self):
        with self.assertRaises(TraceabilityError):
            Improvement("A-X", "R-X", "s", "r", "sre", "high", ("C-01",), ())

    def test_05_render_contains_chain_ids(self):
        text = "\n".join(render(r, TEMPLATE) for r in self.reports)
        for retro in self.reports:
            for c in retro.conclusions:
                self.assertIn(c.conclusion_id, text)
                for ref in c.evidence:
                    self.assertIn(ref.evidence_id, text)
            for a in retro.improvements:
                self.assertIn(a.action_id, text)

    def test_06_render_no_unfilled_placeholder(self):
        text = "\n".join(render(r, TEMPLATE) for r in self.reports)
        self.assertNotIn("{{", text)

    def test_07_render_is_deterministic(self):
        first = render(self.reports[0], TEMPLATE)
        second = render(self.reports[0], TEMPLATE)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main(verbosity=2)
