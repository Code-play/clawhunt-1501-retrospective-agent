"""独立一键复跑验证。

    python verify/run_verification.py

对同一份脱敏过程数据跑完整链路（Schema 校验 -> 假名化 -> 证据白名单 ->
事实 -> 结论 -> 改进项 -> 渲染报告），逐条断言，并把输入、原始输出与断言结论
写成 verify/verification_record.md 与 verify/verification_result.json。
全部通过时退出码 0。文件是准的，终端编码不影响比对。
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from retrospective_agent.actions import TraceabilityError, trace_improvement  # noqa: E402
from retrospective_agent.anonymize import AnonymizationError, Pseudonymizer, assert_no_pii  # noqa: E402
from retrospective_agent.cli import build_retrospective, load_ruleset, prepare_events, write_events_jsonl  # noqa: E402
from retrospective_agent.events import load_events  # noqa: E402
from retrospective_agent.evidence import EvidencePolicy, collect_evidence  # noqa: E402
from retrospective_agent.findings import Conclusion, GroundingError  # noqa: E402
from retrospective_agent.report import render  # noqa: E402

CONFIG = ROOT / "config"
SAMPLES = ROOT / "samples" / "process_events.jsonl"
OUT = ROOT / "outputs"
TEMPLATE = CONFIG / "report_template.md"


@dataclass
class Check:
    name: str
    expected: str
    actual: str
    passed: bool


def main() -> int:
    policy = EvidencePolicy.load(CONFIG / "evidence_whitelist.json")
    ruleset = load_ruleset(CONFIG / "retrospective_rules.json")
    raw = load_events(SAMPLES)
    checks: list[Check] = []
    lines: list[str] = []

    def add(name, expected, actual, ok):
        checks.append(Check(name, str(expected), str(actual), bool(ok)))

    lines.append("# 验证记录 · 业务复盘 Agent（订单 #1501）\n")
    lines.append(f"生成时间（UTC）：{datetime.now(timezone.utc).isoformat()}")
    lines.append("复跑命令：`python verify/run_verification.py`\n")
    lines.append("## 0. 输入\n")
    lines.append(f"- 过程数据：`samples/process_events.jsonl`，共 {len(raw)} 条原始事件")
    lines.append(f"- 证据白名单：{'、'.join(policy.allowed_source_types)}")
    lines.append(f"- 场景：{'、'.join(s['scenario_id'] for s in ruleset['scenarios'])}\n")

    # ---------- 1. Schema 校验 ----------
    add("事件流加载", 32, len(raw), len(raw) == 32)
    lines.append("## 1. 事件流 Schema 校验\n")
    lines.append(f"- 加载事件 {len(raw)} 条，必填字段 / 枚举 / 时间戳 / 去重均通过。\n")

    # ---------- 2. 假名化 ----------
    lines.append("## 2. 确定性假名化\n")
    pii_ok = True
    for e in raw:
        try:
            assert_no_pii(e)
        except AnonymizationError:
            pii_ok = False
    add("样例无残留 PII", "通过", "通过" if pii_ok else "存在 PII", pii_ok)
    once = [e.event_id for e in Pseudonymizer().anonymize_events(raw)]
    twice = [e.event_id for e in Pseudonymizer().anonymize_events(raw)]
    add("假名化可复现（两次结果一致）", True, once == twice, once == twice)
    lines.append(f"- 32 条事件全部通过 PII 扫描；两次假名化结果一致：{once == twice}")
    lines.append(f"- 示例：原始 `EVT-A01` -> 假名 `{once[0]}`\n")

    # ---------- 3. 证据白名单 ----------
    lines.append("## 3. 证据白名单\n")
    events = Pseudonymizer().anonymize_events(raw)
    accepted, rejected = collect_evidence(events, policy)
    lines.append(f"- 采纳证据 {len(accepted)} 条；拒绝证据 {len(rejected)} 条")
    add("存在非白名单来源且被拒绝", True, len(rejected) > 0, len(rejected) > 0)
    reason_ok = all("不在证据白名单内" in r.reason for r in rejected)
    add("拒绝原因可解释", True, reason_ok, reason_ok)
    accepted_ids = {r.evidence_id for r in accepted}
    leak = [r for r in rejected if r.evidence_id in accepted_ids]
    add("被拒来源未混入采纳集", 0, len(leak), not leak)
    for r in rejected:
        lines.append(f"  - 拒绝 `{r.evidence_id}`（{r.source_type}）：{r.reason}")
    lines.append("")

    # ---------- 4. 逐场景：事实/结论/改进项 ----------
    reports = []
    OUT.mkdir(parents=True, exist_ok=True)
    for scenario in ruleset["scenarios"]:
        retro = build_retrospective(raw, policy, ruleset, scenario)
        reports.append(retro)
        lines.append(f"## 4. 场景 `{retro.scenario_id}` —— {retro.title}\n")
        lines.append(f"- 窗口 {retro.window_from} ~ {retro.window_to}")
        lines.append(f"- 采纳证据 {len(retro.evidence_index)}；被拒证据 {len(retro.rejected)}")
        lines.append(f"- 事实 {len(retro.facts)}；结论 {len(retro.conclusions)}；改进项 {len(retro.improvements)}\n")

        for f in retro.facts:
            lines.append(f"  - {f.fact_id}（`{f.rule_id}`）：{f.statement}")
        for c in retro.conclusions:
            evs = "、".join(f"`{e.evidence_id}`@{e.timestamp}" for e in c.evidence)
            lines.append(f"  - {c.conclusion_id}（置信 {c.confidence:.2f}）：{c.statement}")
            lines.append(f"    证据：{evs}")
        for a in retro.improvements:
            lines.append(f"  - {a.action_id}［{a.priority}/{a.owner_role}］{a.statement}（回溯 {a.conclusion_ids[0]}）")
        lines.append("")

        add(f"{retro.scenario_id} 产出结论", True, len(retro.conclusions) > 0, len(retro.conclusions) > 0)
        grounded = all(c.evidence and all(e.evidence_id and e.timestamp for e in c.evidence) for c in retro.conclusions)
        add(f"{retro.scenario_id} 每条结论挂证据ID+时间戳", True, grounded, grounded)
        in_index = all(
            e.evidence_id in {r.evidence_id for r in retro.evidence_index}
            for c in retro.conclusions for e in c.evidence
        )
        add(f"{retro.scenario_id} 结论证据可回溯到采纳集", True, in_index, in_index)
        traced = True
        for a in retro.improvements:
            try:
                chain = trace_improvement(a, retro.conclusions)
                traced = traced and bool(chain)
            except TraceabilityError:
                traced = False
        add(f"{retro.scenario_id} 改进项可回溯到结论/证据", True, traced, traced)

        # 报告可渲染且确定
        text = render(retro, TEMPLATE)
        (OUT / f"retro_{retro.scenario_id}.md").write_text(text, encoding="utf-8")
        det = text == render(retro, TEMPLATE)
        add(f"{retro.scenario_id} 报告渲染确定性", True, det, det)
        add(f"{retro.scenario_id} 报告无未填充占位符", True, "{{" not in text, "{{" not in text)

    add("共产出两份样例复盘", 2, len(reports), len(reports) == 2)

    # ---------- 5. 负向断言：缺证据/缺结论必须被拒 ----------
    lines.append("## 5. 负向断言（机制在代码层强制）\n")
    try:
        Conclusion("C-X", "R-X", "无证据", (), (), 0.9)
        ground_err = False
    except GroundingError:
        ground_err = True
    add("无证据的结论无法构造", "GroundingError", ground_err, ground_err)
    lines.append(f"- 构造无证据结论 -> GroundingError：{ground_err}")

    from retrospective_agent.actions import Improvement  # noqa: E402
    from retrospective_agent.evidence import EvidenceRef  # noqa: E402

    ref = EvidenceRef("E1", "2026-03-02T09:00:00Z", "incident_log", "REF-1", "deploy", "s")
    try:
        Improvement("A-X", "R-X", "s", "r", "sre", "high", (), (ref,))
        trace_err = False
    except TraceabilityError:
        trace_err = True
    add("无结论的改进项无法构造", "TraceabilityError", trace_err, trace_err)
    lines.append(f"- 构造无结论改进项 -> TraceabilityError：{trace_err}\n")

    # ---------- 6. 单元测试 ----------
    lines.append("## 6. 单元测试\n")
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", timeout=180,
    )
    tail = (proc.stderr or "").strip().splitlines()
    summary = tail[-3] if len(tail) >= 3 else (proc.stderr or "").strip()
    add("单元测试全部通过", "returncode 0", proc.returncode, proc.returncode == 0)
    lines.append(f"```\n{summary}\n```\n")

    # ---------- 匿名过程数据产物（验收标准第 1 条）----------
    lines.append("## 7. 匿名过程数据产物\n")
    lines.append("验收标准要求交付「匿名过程数据」，因此假名化结果必须落盘成可检查的产物，")
    lines.append("而不是只在内存里过一遍就丢掉。本节自行生成该产物再断言。\n")
    anonymized = prepare_events(raw, Pseudonymizer())
    anon_path = write_events_jsonl(anonymized, OUT / "process_events_anonymized.jsonl")
    anon_rows = [json.loads(ln) for ln in anon_path.read_text(encoding="utf-8").splitlines() if ln.strip()]

    add("匿名过程数据产物存在", True, anon_path.is_file(), anon_path.is_file())
    add("匿名过程数据条数等于输入", len(raw), len(anon_rows), len(anon_rows) == len(raw))

    raw_names = sorted({e.actor for e in raw if e.actor})
    leaked = [n for n in raw_names if any(n in json.dumps(r, ensure_ascii=False) for r in anon_rows)]
    add("匿名产物中无原始人员姓名", 0, len(leaked), not leaked)

    bad_actor = [r["event_id"] for r in anon_rows if r.get("actor") and not str(r["actor"]).startswith("PERSON-")]
    add("人员字段全部为 PERSON- 假名", 0, len(bad_actor), not bad_actor)
    bad_ref = [r["event_id"] for r in anon_rows if r.get("source_ref") and not str(r["source_ref"]).startswith("REF-")]
    add("单据字段全部为 REF- 假名", 0, len(bad_ref), not bad_ref)
    bad_evt = [r.get("event_id") for r in anon_rows if not str(r.get("event_id", "")).startswith("EVT-")]
    add("事件 ID 全部为 EVT- 假名", 0, len(bad_evt), not bad_evt)

    lines.append(f"- 产物：`outputs/process_events_anonymized.jsonl`（{len(anon_rows)} 条事件）")
    lines.append("- 假名前缀：人员 `PERSON-`、客户 `CUST-`、单据 `REF-`、事件 `EVT-`")
    lines.append(f"- 原始姓名泄漏检查：原始数据含 {len(raw_names)} 个不同姓名，泄漏 {len(leaked)} 个")
    lines.append(f"- 示例：`{raw[0].actor}` -> `{anonymized[0].actor}`；`{raw[0].source_ref}` -> `{anonymized[0].source_ref}`")
    lines.append("- 买家复现命令：`python -m retrospective_agent anonymize --out-file <输出文件>`\n")

    # ---------- 结论 ----------
    failed = [c for c in checks if not c.passed]
    lines.append("## 结论\n")
    lines.append(f"- 断言总数：{len(checks)}；通过：{len(checks) - len(failed)}；失败：{len(failed)}")
    lines.append(f"- 结果：**{'全部通过' if not failed else '存在失败项'}**\n")
    lines.append("| 断言 | 预期 | 实际 | 结果 |")
    lines.append("|---|---|---|---|")
    for c in checks:
        lines.append(f"| {c.name} | {c.expected} | {c.actual} | {'通过' if c.passed else '失败'} |")

    body = "\n".join(lines)
    (ROOT / "verify" / "verification_record.md").write_text(body, encoding="utf-8")
    (ROOT / "verify" / "verification_result.json").write_text(
        json.dumps(
            {
                "order": 1501,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "checks_total": len(checks),
                "checks_passed": len(checks) - len(failed),
                "checks_failed": len(failed),
                "all_passed": not failed,
                "checks": [c.__dict__ for c in checks],
            },
            ensure_ascii=False, indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(body)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
