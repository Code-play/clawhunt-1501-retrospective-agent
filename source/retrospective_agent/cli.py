"""命令行入口。

    python -m retrospective_agent demo
    python -m retrospective_agent run --scenario incident_retro
    python -m retrospective_agent validate-events --events samples/process_events.jsonl

demo 一键复跑：用同一份脱敏过程数据，产出两份完整复盘报告（Markdown）
与一份运行日志，并打印"预期输出"摘要。全流程确定性，不联网、不调用模型 API。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from .actions import build_improvements
from .anonymize import Pseudonymizer, assert_no_pii
from .events import Event, in_window, load_events
from .evidence import EvidencePolicy, collect_evidence
from .findings import build_conclusions, build_facts, match_event
from .report import Retrospective, render

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = REPO_ROOT / "config"
DEFAULT_RULES = DEFAULT_CONFIG / "retrospective_rules.json"
DEFAULT_WHITELIST = DEFAULT_CONFIG / "evidence_whitelist.json"
DEFAULT_TEMPLATE = DEFAULT_CONFIG / "report_template.md"
DEFAULT_EVENTS = REPO_ROOT / "samples" / "process_events.jsonl"
DEFAULT_OUT = REPO_ROOT / "outputs"


class ConfigError(ValueError):
    """配置缺失或非法。"""


def load_ruleset(path: str | Path) -> dict:
    p = Path(path)
    if not p.is_file():
        raise ConfigError(f"复盘规则配置不存在：{p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not data.get("scenarios") or not data.get("rules"):
        raise ConfigError("retrospective_rules.json 需要 scenarios 与 rules")
    return data


def prepare_events(events: list[Event], pseudonymizer: Pseudonymizer) -> list[Event]:
    """先查残留 PII（拒绝），再做确定性假名化。"""
    for event in events:
        assert_no_pii(event)
    return pseudonymizer.anonymize_events(events)


def write_events_jsonl(events: list[Event], path: str | Path) -> Path:
    """把事件流落盘为 JSONL。

    验收标准要求交付「匿名过程数据」，所以假名化结果必须是一个可检查的产物，
    不能只在内存里过一遍就丢掉：人员 -> PERSON-xxxxxxxx，客户 -> CUST-xxxxxxxx，
    单据 -> REF-xxxxxxxx，事件 ID -> EVT-xxxxxxxx。
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="\n") as fh:
        for event in events:
            fh.write(json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
    return p


def build_retrospective(
    raw_events: list[Event],
    policy: EvidencePolicy,
    ruleset: dict,
    scenario: dict,
) -> Retrospective:
    pseudonymizer = Pseudonymizer()
    events = prepare_events(raw_events, pseudonymizer)

    accepted_refs, rejected_all = collect_evidence(events, policy)
    evidence_map = {ref.evidence_id: ref for ref in accepted_refs}
    accepted_ids = set(evidence_map)

    window = scenario["window"]
    focus = scenario.get("focus") or {}
    scoped = [
        e
        for e in events
        if e.event_id in accepted_ids
        and in_window(e, window["from"], window["to"])
        and match_event(e, focus)
    ]

    rule_ids = set(scenario["rules"])
    rules = [r for r in ruleset["rules"] if r["rule_id"] in rule_ids]
    missing = rule_ids - {r["rule_id"] for r in rules}
    if missing:
        raise ConfigError(f"场景 {scenario['scenario_id']} 引用了不存在的规则：{sorted(missing)}")

    facts, skipped = build_facts(scoped, evidence_map, rules)
    conclusions = build_conclusions(facts, rules)
    improvements = build_improvements(conclusions, rules)

    scoped_ids = {e.event_id for e in scoped}
    evidence_index = [r for r in accepted_refs if r.evidence_id in scoped_ids]
    rejected = [
        r
        for r in rejected_all
        if window["from"] <= r.timestamp < window["to"]
    ]

    return Retrospective(
        scenario_id=scenario["scenario_id"],
        title=scenario["title"],
        window_from=window["from"],
        window_to=window["to"],
        events_total=len(events),
        evidence_index=evidence_index,
        rejected=rejected,
        facts=facts,
        conclusions=conclusions,
        improvements=improvements,
        skipped=skipped,
    )


def _summary_lines(retro: Retrospective) -> list[str]:
    lines = [
        f"场景 {retro.scenario_id}：{retro.title}",
        f"  数据窗口 {retro.window_from} ~ {retro.window_to}",
        f"  采纳证据 {len(retro.evidence_index)} 条；拒绝证据（非白名单来源）{len(retro.rejected)} 条",
        f"  事实 {len(retro.facts)} 条；结论 {len(retro.conclusions)} 条；改进项 {len(retro.improvements)} 条",
    ]
    for c in retro.conclusions:
        lines.append(f"  - {c.conclusion_id}：{c.statement}")
    return lines


def cmd_run(args) -> int:
    policy = EvidencePolicy.load(args.whitelist)
    ruleset = load_ruleset(args.rules)
    raw_events = load_events(args.events)
    scenarios = ruleset["scenarios"]
    scenario = next((s for s in scenarios if s["scenario_id"] == args.scenario), None)
    if scenario is None:
        raise ConfigError(f"未知场景：{args.scenario}（可选：{[s['scenario_id'] for s in scenarios]}）")

    retro = build_retrospective(raw_events, policy, ruleset, scenario)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"retro_{retro.scenario_id}.md"
    out_file.write_text(render(retro, args.template), encoding="utf-8")
    print(f"已生成报告：{out_file}")
    for line in _summary_lines(retro):
        print(line)
    return 0


def cmd_demo(args) -> int:
    policy = EvidencePolicy.load(args.whitelist)
    ruleset = load_ruleset(args.rules)
    raw_events = load_events(args.events)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    log: list[str] = []
    log.append("[复盘 Agent 演示 · 一键复跑]")
    log.append(f"输入事件流：{Path(args.events).name}（原始合成数据，共 {len(raw_events)} 条事件）")
    log.append(f"证据白名单：{'、'.join(policy.allowed_source_types)}")

    # 「匿名过程数据」本身就是交付物之一，落盘成可检查的产物
    anonymized = prepare_events(raw_events, Pseudonymizer())
    anon_file = write_events_jsonl(anonymized, out_dir / "process_events_anonymized.jsonl")
    log.append(f"匿名过程数据：{anon_file.name}（{len(anonymized)} 条，人员/客户/单据/事件 ID 已全部假名化）")
    log.append("")

    reports: list[Retrospective] = []
    for scenario in ruleset["scenarios"]:
        retro = build_retrospective(raw_events, policy, ruleset, scenario)
        reports.append(retro)
        out_file = out_dir / f"retro_{retro.scenario_id}.md"
        out_file.write_text(render(retro, args.template), encoding="utf-8")
        log.append(f"-> 生成报告 {out_file.name}")
        log.extend("   " + line for line in _summary_lines(retro))
        log.append("")

    log.append("预期输出摘要：")
    for retro in reports:
        log.append(
            f"  {retro.scenario_id}: 报告含 事实x{len(retro.facts)} / "
            f"结论x{len(retro.conclusions)} / 改进项x{len(retro.improvements)} / "
            f"被拒证据x{len(retro.rejected)}；每条结论均挂证据 ID + 时间戳。"
        )
    log.append("")
    log.append("说明：本流程确定性，同样输入必得同样输出；不联网、不调用任何模型 API。")

    log_file = out_dir / "demo_run.log"
    log_file.write_text("\n".join(log) + "\n", encoding="utf-8")

    print("\n".join(log))
    print(f"\n运行日志：{log_file}")
    return 0


def cmd_validate_events(args) -> int:
    events = load_events(args.events)
    print(f"事件流校验通过：{args.events} 共 {len(events)} 条事件")
    return 0


def cmd_anonymize(args) -> int:
    """把任意过程事件流假名化成「匿名过程数据」（买家用真实脱敏数据复现同一步骤）。"""
    events = load_events(args.events)
    anonymized = prepare_events(events, Pseudonymizer())
    out_file = write_events_jsonl(anonymized, args.out_file)
    print(f"匿名过程数据已生成：{out_file}（{len(anonymized)} 条事件）")
    print("假名前缀：人员 PERSON- / 客户 CUST- / 单据 REF- / 事件 EVT-")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="retrospective_agent", description="业务复盘 Agent（可溯源）")
    p.add_argument("--rules", default=str(DEFAULT_RULES), help="复盘规则配置")
    p.add_argument("--whitelist", default=str(DEFAULT_WHITELIST), help="证据白名单配置")
    p.add_argument("--template", default=str(DEFAULT_TEMPLATE), help="报告模板")
    p.add_argument("--events", default=str(DEFAULT_EVENTS), help="过程事件流（JSONL）")
    p.add_argument("--out", default=str(DEFAULT_OUT), help="输出目录")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("demo", help="一键复跑：产出两份样例复盘报告 + 运行日志").set_defaults(func=cmd_demo)

    run = sub.add_parser("run", help="运行单个场景")
    run.add_argument("--scenario", required=True)
    run.set_defaults(func=cmd_run)

    val = sub.add_parser("validate-events", help="校验事件流 Schema")
    val.set_defaults(func=cmd_validate_events)

    anon = sub.add_parser("anonymize", help="把过程事件流假名化为匿名过程数据（JSONL）")
    anon.add_argument("--out-file", required=True, help="匿名过程数据输出文件")
    anon.set_defaults(func=cmd_anonymize)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
