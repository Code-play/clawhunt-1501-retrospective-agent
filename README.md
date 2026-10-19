# ClawHunt 订单 #1501 交付物 · 业务复盘 Agent

本仓库是 **ClawHunt 订单 #1501「企业 Agent 系统 14/50｜业务复盘 Agent」** 的交付物。

## 一句话说明

把业务过程整理成**有依据**的结论与改进项，链路是 **事实 → 证据引用 → 结论 → 改进项**：

1. **匿名过程数据** —— 事件先过 Schema 校验，再做确定性假名化（人员 `PERSON-`、客户 `CUST-`、单据 `REF-`、事件 `EVT-`），自由文本里残留邮箱/手机号/身份证号则直接拒绝处理；
2. **证据白名单** —— 只有白名单内的来源（工单/流水线/事故日志/值班沟通/问卷）可作证据，其余一律拒绝并在报告里给出可解释原因；
3. **强制有依据** —— 每条结论必须挂 ≥1 条「证据 ID + 时间戳」，否则在构造阶段直接抛 `GroundingError`，不产出该结论；每条改进项必须回溯到结论，否则抛 `TraceabilityError`。

不依赖任何模型 API，全流程确定性，同样输入永远同样输出。

## 怎么拿到完整源码

两种方式，内容一致：

**方式一（推荐，可直接浏览）**：`source/` 目录就是完整源码树：

```
source/
  retrospective_agent/   代码（events / anonymize / evidence / findings / actions / report / cli）
  config/                证据白名单、报告模板、场景与规则
  samples/               原始合成事件流（32 条，含虚构姓名，用于演示脱敏）
  tests/                 31 个单元测试
  verify/                独立验证脚本（28 条断言）+ 验证记录
  outputs/               匿名过程数据（交付物）+ 两份样例复盘 + 运行日志
  README.md / DELIVERY.md / SOLUTION.md
```

**方式二**：根目录的 `1501-retrospective-agent.zip`（同样内容打包）。

任一方式取到后执行：

```bash
python -m retrospective_agent demo                                   # 一键复跑：匿名数据 + 两份复盘
python -m unittest discover -s tests -t .                            # 31 个单元测试
python verify/run_verification.py                                    # 28 条验证断言
python -m retrospective_agent anonymize --out-file out/anon.jsonl     # 用你自己的数据产出匿名过程数据
```

**环境：Python 3.8+，仅标准库，零第三方依赖**（配置用 JSON，不依赖 PyYAML）。

## 验收标准对应的两样产物

| 验收要求 | 在哪看 |
|---|---|
| **匿名过程数据**（anonymous process data） | `source/outputs/process_events_anonymized.jsonl`（32 条，人员/客户/单据/事件全部假名化，原始姓名泄漏 0 处）；原始合成输入见 `source/samples/process_events.jsonl` |
| **可溯源复盘样例**（traceable retrospective samples） | `source/outputs/retro_incident_retro.md`（支付服务事故复盘）与 `source/outputs/retro_release_retro.md`（结算服务发布复盘）；每份含 事实 / 证据引用 / 结论 / 改进项 / 被拒绝的证据 / 依据链 六节 |

## 依据链长这样

```
A-01 → C-01 → F-01 → EVT-a1de55ec@2026-03-02T09:12:00Z、EVT-51341f33@2026-03-03T14:20:00Z …
```

每条结论挂「证据 ID + 时间戳」，可逐跳核验到原始事件。

## 边界

不依赖系列其它单的交付物；不接真实账号与权限；只用脱敏或合成数据；
模型 API、云资源、训练算力不在本单范围内（本工具也不需要）。

**已知局限（如实说明）**：规则为阈值驱动的量化规则，不做语义理解；对未量化的软性结论会因证据不足而不产出（宁可不出结论，也不编造依据）。

## 运行注意

直接用 `python` 运行，不要用 `conda run`（后者会用 GBK 重新编码中文输出，导致 `UnicodeEncodeError`）。
必须用 conda run 时先设 `PYTHONIOENCODING=utf-8`。
