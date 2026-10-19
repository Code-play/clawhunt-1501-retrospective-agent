# 业务复盘 Agent（可溯源版）

订单 **#1501**「企业 Agent 系统 14/50｜业务复盘 Agent」交付物。

把业务过程数据整理成有依据的结论与改进项，依据链固定为：

**事实（Fact）→ 证据引用（EvidenceRef）→ 结论（Conclusion）→ 改进项（Improvement）**

同时立四条硬规矩（在代码层强制，而不是文档约定）：

| 规矩 | 落地方式 |
|---|---|
| 事件必须先过 Schema | 必填字段 / 动作 / 结果 / 角色枚举 / 时间戳 / `event_id` 去重，不合规即抛 `EventSchemaError` |
| 只有白名单来源算证据 | 非白名单来源一律拒绝并给出可解释原因，且不进入任何事实或结论 |
| 每条结论必须挂证据 ID + 时间戳 | 构造无证据的结论直接抛 `GroundingError`，不产出该结论 |
| 每条改进项必须能回溯到结论 | 构造无结论的改进项直接抛 `TraceabilityError` |

**不依赖任何模型 API**：全流程确定性，同样输入永远同样输出，买家可一键复跑比对。
**无第三方依赖**：只用 Python 标准库（配置用 JSON，不需要 PyYAML）。

## 目录

```
retrospective_agent/        代码
  events.py                 事件流 Schema：定义 / 加载 / 校验
  anonymize.py              确定性假名化：人名/工单号/客户名 -> 稳定假名；残留 PII 即拒绝
  evidence.py               证据白名单：非白名单来源被拒并给原因
  findings.py               事实 -> 结论：结论强制挂证据
  actions.py                结论 -> 改进项：改进项强制回溯结论
  report.py                 渲染 Markdown 复盘报告
  cli.py                    命令行入口
config/
  evidence_whitelist.json   证据来源白名单
  report_template.md        报告模板（事实->证据引用->结论->改进项）
  retrospective_rules.json  场景与规则（过滤 / 聚合 / 阈值 / 文案模板）
samples/
  process_events.jsonl      脱敏过程数据（32 条事件，覆盖 7 种来源类型）
tests/                      31 个单元测试（标准库 unittest）
verify/
  run_verification.py       一键复跑，生成验证记录
  verification_record.md    验证记录（输入 / 原始输出 / 断言结论）
  verification_result.json  机器可读的断言结果
outputs/                    demo 生成的报告与运行日志（可重建）
```

## 环境

- Python 3.8+（开发验证于 3.13）
- **仅标准库**，无需 `pip install`，无需模型 API 客户端，不联网

## 使用

### 1. 一键复跑（产出两份样例复盘报告 + 运行日志）

```bash
python -m retrospective_agent demo
```

生成 `outputs/retro_incident_retro.md`、`outputs/retro_release_retro.md` 与
`outputs/demo_run.log`，并打印"预期输出"摘要。

### 2. 单独运行某个场景

```bash
python -m retrospective_agent run --scenario incident_retro
python -m retrospective_agent run --scenario release_retro
```

### 3. 校验事件流 Schema

```bash
python -m retrospective_agent validate-events --events samples/process_events.jsonl
```

### 4. 单元测试

```bash
python -m unittest discover -s tests -v
```

### 5. 一键复跑全部验证

```bash
python verify/run_verification.py
```

全部断言通过时退出码为 0，并刷新 `verify/verification_record.md` 与
`verify/verification_result.json`。

## 换场景 / 调规则

- **换场景**：编辑 `config/retrospective_rules.json` 的 `scenarios`，给出新的
  `window`、`focus`（如按 `service`）与选用的 `rules`。
- **加规则**：在 `rules` 里新增一条：`filter`（可匹配 `action`/`outcome`/
  `service`/`attributes.*` 等）+ `aggregate`（`count` / `ratio` / `avg`）+
  `min_value`（阈值）+ `min_evidence`（证据下限）+ 三段文案模板 + `action`。
  改配置不改代码。
- **调白名单**：编辑 `config/evidence_whitelist.json` 的 `allowed_source_types`。
  不在其中的来源会出现在报告的"被拒绝的证据"一节。

## 两份样例复盘（`outputs/`）

| 场景 | 窗口 | 采纳/拒绝证据 | 结论 | 改进项 |
|---|---|---|---|---|
| `incident_retro`（支付事故） | 2026-03-02 ~ 03-09 | 14 / 1 | 事故 4 起、平均检测 37.25 分钟 | 根因复盘、补齐告警 |
| `release_retro`（结算发布） | 2026-03-09 ~ 03-16 | 16 / 1 | 部署失败率 0.6、评审等待 22 小时 | 灰度门禁、评审轮值 |

被拒绝的证据来源：`unverified_hearsay`、`manager_note`（不在白名单内）。

## 运行注意事项

- **直接用 `python` 运行，不要用 `conda run`**：`conda run` 会把子进程输出用自己的
  GBK 编码重新打印，含中文时表现为 `UnicodeEncodeError` + 退出码 1（是 conda 的问题，
  不是本工具的问题）。若必须用 `conda run`，先设 `PYTHONIOENCODING=utf-8`。
- 本工具不联网、不调用任何模型 API、无第三方依赖。

## 范围与排除

- 仅使用获授权或脱敏/合成数据；自由文本残留 PII 即被拒绝处理。
- 不依赖系列其它单的交付物，独立可运行。
- 模型 API、云资源、训练算力等第三方费用不在本单范围内（本工具也不需要）。
- 真实业务数据接入与现场校准属超范围项，需在客户经平台提供脱敏数据后另行对接。
