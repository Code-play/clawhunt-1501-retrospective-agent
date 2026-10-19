# 交付说明 · 订单 #1501

**订单**：企业 Agent 系统 14/50｜业务复盘 Agent
**本单范围**：配置复盘 Bot，将业务过程整理为有依据的结论与改进项。
**交付方式**：平台内交付（`delivery_channel: platform_only`）；平台无附件通道，正文自包含。

## 验收对照

平台验收标准：**「Provide anonymous process data and traceable retrospective samples.」**

| 验收要点 | 交付物 | 可验证证据 |
|---|---|---|
| 匿名过程数据（anonymous process data） | `outputs/process_events_anonymized.jsonl`（32 条，人员 `PERSON-`/客户 `CUST-`/单据 `REF-`/事件 `EVT-` 全部假名化，原始姓名泄漏 0 处）；原始合成输入见 `samples/process_events.jsonl`，覆盖 5 种白名单来源 + 2 种白名单外来源 | 事件流 Schema 校验通过（32/32）；`anonymize.py` 对姓名/工单号/客户名做确定性假名化；自由文本残留 PII 即抛 `AnonymizationError`；`tests/test_anonymize.py` 7 个用例 |
| 可溯源复盘样例（traceable retrospective samples） | `outputs/retro_incident_retro.md`、`outputs/retro_release_retro.md` 两份完整复盘 | 每条结论强制挂「证据 ID + 时间戳」，否则抛 `GroundingError`；每条改进项可回溯结论，否则抛 `TraceabilityError`；报告含「被拒绝的证据」「依据链」两节；`tests/test_findings.py`、`tests/test_report.py` 覆盖 |
| 只用获授权/脱敏资料 | 证据白名单 + PII 拒绝 + 确定性假名化 三重保证 | 非白名单来源被拒并给原因，且未混入采纳集（`tests/test_evidence.py`） |

交付要求对应物：

- **代码或配置** —— `retrospective_agent/` 7 个模块 + `config/` 三份配置
- **使用说明** —— `README.md`
- **验证记录** —— `verify/verification_record.md`（输入 / 原始输出 / 断言结论）+ `verify/verification_result.json`

## 验证结论

一键复跑：`python verify/run_verification.py`（全通过时退出码 0）

| 项 | 结果 |
|---|---|
| 单元测试 | **31 / 31 通过** |
| 验证断言 | **28 / 28 通过**（含匿名数据集产物 6 项断言） |
| 依赖 | **仅标准库**（无第三方依赖） |
| 外部调用 | **无**（不联网、不调用任何模型 API） |

两份样例复盘实测：

| 场景 | 窗口 | 采纳 / 拒绝证据 | 事实 | 结论 | 改进项 |
|---|---|---|---|---|---|
| `incident_retro`（支付事故） | 2026-03-02 ~ 03-09 | 14 / 1 | 2 | 2 | 2 |
| `release_retro`（结算发布） | 2026-03-09 ~ 03-16 | 16 / 1 | 2 | 2 | 2 |

结论摘要：

- 支付事故：事故 4 起（high 2 / medium 2）、平均检测时长 37.25 分钟（阈值 30）
- 结算发布：部署失败率 0.6（阈值 0.3）、评审平均等待 22 小时（阈值 12）

被拒绝的证据：`unverified_hearsay`、`manager_note`（白名单外，未进入任何结论）。

## 关键设计取舍

**为什么不接大模型**：

1. **验证记录必须能被复跑比对** —— 接模型后输出不确定（温度、版本漂移），"验证记录"就退化成不可验证的截图；
2. **本单预算明确不含模型 API 费用**，交付物若必须配 API key 才能跑，等于把成本转嫁回买家；
3. **"带依据"要能被验证真假** —— 本方案证据是结构化事件的 ID + 时间戳，可逐跳核验；模型生成的引用存在编造风险，恰是本单要防的问题。

**已知局限（如实说明）**：规则是阈值驱动的量化规则，不做语义理解。对未量化的软性结论，因证据不足而不产出——设计取向是**宁可不出结论，也不编造依据**。默认数据为合成/脱敏数据。

## 运行注意

- **直接用 `python` 运行，不要用 `conda run`**：`conda run` 会用自己的 GBK 编码重新打印子进程输出，含中文时表现为 `UnicodeEncodeError` + 退出码 1（是 conda 的输出重编码问题，不是本工具的问题）。若必须使用，请先设 `PYTHONIOENCODING=utf-8`。

## 范围与排除

- 仅使用获授权或脱敏/合成数据；自由文本含 PII 即被拒绝处理。
- 不依赖系列其它单的交付物，独立可运行；不接真实账号/权限。
- 模型 API、云资源、训练算力等第三方费用不在本单范围内（本工具也不需要）。
- 真实业务数据接入与现场校准属超范围项，需在客户经平台提供脱敏数据后另行对接。
