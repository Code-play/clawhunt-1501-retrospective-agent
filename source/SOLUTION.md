【交付物获取方式】
本单 delivery_channel=platform_only，平台无附件上传通道，评审只读提交正文。
因此本正文自包含：交付物的结构、配置、机制、脱敏过程数据节选、两份完整可溯源复盘样例、
一键复跑命令、预期输出与验证记录，均写在正文里，无需下载即可核验。
完整交付物为 30 个文件（清单见下，含 outputs/ 下 4 个 demo 产物），正文已给出复现所需的关键内容；demo 会另产出 outputs/ 下的匿名数据集与两份报告。

【订单与范围】
订单 #1501「企业 Agent 系统 14/50｜业务复盘 Agent」。
本单范围：配置复盘 Bot，将业务过程整理为有依据的结论与改进项。
验收标准：Provide anonymous process data and traceable retrospective samples.

【买家助手三问的正面回答】
1) 代码/配置具体包括什么？——四种都交付，并额外给出完整可运行脚本：
   - 事件流 Schema 定义：retrospective_agent/events.py（字段/枚举/时间戳/去重校验）
   - 证据白名单配置：config/evidence_whitelist.json
   - 依据链生成器：findings.py（事实→结论）+ actions.py（结论→改进项）+ report.py（渲染）
   - 复盘报告模板：config/report_template.md
   - 完整可运行 Agent 脚本：cli.py（`python -m retrospective_agent demo` 一键复跑）
2) 一键复跑依赖什么环境？——只需 Python 3.8+ 标准库；不需要任何框架、
   不需要预装模型 API 客户端、无第三方依赖（配置用 JSON，不依赖 PyYAML）。
3) 预期输出是什么？——两者都给：两份完整 Markdown 复盘报告 + 运行日志（demo_run.log）
   + 机器可读验证结果（verification_result.json）与人可读验证记录。

【交付物清单】共 30 个文件
  retrospective_agent/__init__.py / __main__.py  包初始化与模块入口
  retrospective_agent/events.py      事件流 Schema + 加载 + 校验
  retrospective_agent/anonymize.py   确定性假名化（SHA-256+固定盐，可复现）
  retrospective_agent/evidence.py    证据白名单校验 + 拒绝原因
  retrospective_agent/findings.py    事实→结论（结论强制挂证据）
  retrospective_agent/actions.py     结论→改进项（改进项强制回溯结论）
  retrospective_agent/report.py      渲染 Markdown 复盘报告
  retrospective_agent/cli.py         一键复跑入口
  config/evidence_whitelist.json     证据来源白名单
  config/report_template.md          复盘报告模板
  config/retrospective_rules.json    场景与规则（过滤/聚合/阈值/文案）
  samples/process_events.jsonl       原始合成输入（32 条，含虚构姓名，用于演示脱敏）
  tests/                             31 个单元测试（标准库 unittest）
  verify/run_verification.py         独立验证脚本（28 条断言）
  verify/verification_record.md      人可读验证记录
  verify/verification_result.json    机器可读断言结果
  outputs/process_events_anonymized.jsonl  匿名过程数据（交付物，32 条假名化事件）
  outputs/retro_incident_retro.md          样例复盘一（完整可溯源）
  outputs/retro_release_retro.md           样例复盘二（完整可溯源）
  outputs/demo_run.log                     运行日志
  SOLUTION.md / README.md / DELIVERY.md / .gitignore

【环境要求与一键复跑】
环境：Python 3.8+（开发验证于 3.13）；仅标准库；不联网、不调用任何模型 API。
命令：
  cd 1501-retrospective-agent
  python -m retrospective_agent demo            # 产出两份报告 + 运行日志
  python -m unittest discover -s tests -v       # 31 个单元测试
  python verify/run_verification.py             # 28 条验证断言
  python -m retrospective_agent anonymize --out-file out/anon.jsonl   # 用你自己的数据产出匿名过程数据
预期输出（demo 摘要）：

  -> retro_incident_retro.md
     采纳证据 14 条；拒绝证据 1 条；事实 2；结论 2；改进项 2
     C-01 事故数量达到可复盘规模（4 起）... C-02 平均检测时长 37.25 分钟高于阈值 30 分钟...
  -> retro_release_retro.md
     采纳证据 16 条；拒绝证据 1 条；事实 2；结论 2；改进项 2
     C-01 部署失败率 0.6 高于阈值 0.3...  C-02 变更评审平均等待 22 小时高于阈值 12 小时...

【依据链机制：事实 → 证据引用 → 结论 → 改进项】
1) 事件先过 Schema 校验（必填字段/动作/结果/角色枚举/时间戳/event_id 去重）。
2) 确定性假名化：人员→PERSON-、客户→CUST-、单据→REF-、事件→EVT-，由固定盐+
   SHA-256 前 8 位决定，同输入必得同假名；自由文本残留邮箱/手机号即拒绝处理。
3) 证据白名单：只有 allowed_source_types 中的来源可作证据；其余一律拒绝并给出
   可解释原因（列出被拒来源与白名单），且不进入任何事实或结论。
4) 事实 Fact：对事件流的中性量化观察（计数/比率/均值），自带 >=1 条证据引用。
5) 结论 Conclusion：强制挂 >=1 条「证据 ID + 时间戳」；构造无证据的结论直接抛
   GroundingError，不产出该结论——这是"强制有依据"在数据结构层的落地。
6) 改进项 Improvement：必须回溯到至少一条结论（否则抛 TraceabilityError），
   结论的证据即改进项的证据，形成可逐跳核验的闭环。

【匿名过程数据（交付物之一，完整 32 条见 outputs/process_events_anonymized.jsonl）】
原始输入是 samples/process_events.jsonl（**合成**数据，含虚构姓名与单据号，仅用于演示脱敏流程）；
经 anonymize.py 确定性假名化后落盘为「匿名过程数据」，这才是本单交付的匿名数据集。
字段：event_id/timestamp/actor/actor_role/action/outcome/service/source_type/source_ref/attributes/text。
脱敏后节选（原文照抄，无任何真实姓名）：

  {"action": "incident_opened", "actor": "PERSON-d48722cc", "actor_role": "oncall_engineer", "attributes": {"severity": "high", "time_to_detect_minutes": 34}, "customer": "", "event_id": "EVT-a1de55ec", "outcome": "none", "service": "payment", "source_ref": "REF-e4146000", "source_type": "incident_log", "text": "支付网关超时告警", "timestamp": "2026-03-02T09:12:00Z"}
  {"action": "deploy", "actor": "PERSON-d48722cc", "actor_role": "release_manager", "attributes": {}, "customer": "", "event_id": "EVT-113c7b41", "outcome": "success", "service": "payment", "source_ref": "REF-4b762a9f", "source_type": "deploy_pipeline", "text": "常规发布", "timestamp": "2026-03-04T08:05:00Z"}
  {"action": "incident_opened", "actor": "PERSON-47af7275", "actor_role": "oncall_engineer", "attributes": {"severity": "high", "time_to_detect_minutes": 5}, "customer": "", "event_id": "EVT-586e5163", "outcome": "none", "service": "payment", "source_ref": "REF-c6eb6a4f", "source_type": "unverified_hearsay", "text": "群里有人转述一起未核实的支付事故", "timestamp": "2026-03-03T14:35:00Z"}

原始 -> 假名 的映射示例（固定盐 + SHA-256 前 8 位，同输入必得同假名）：
  Chen Wei -> PERSON-d48722cc；Li Na -> PERSON-3617aea7；INC-2201 -> REF-e4146000；EVT-A01 -> EVT-a1de55ec。
  自由文本中若残留邮箱/手机号/身份证号，直接拒绝处理（AnonymizationError）。
覆盖来源类型：incident_log / deploy_pipeline / ticket_system / chat_ops / survey（白名单内）
与 unverified_hearsay / manager_note（白名单外，必被拒绝）。

【核心配置内嵌】
证据白名单 config/evidence_whitelist.json，allowed_source_types =
  incident_log, deploy_pipeline, ticket_system, chat_ops, survey；
  拒绝示例 denied = unverified_hearsay, manager_note。
报告模板 config/report_template.md 段落：1 事实 / 2 证据引用 / 3 结论 /
  4 改进项 / 5 被拒绝的证据 / 6 依据链。
规则 config/retrospective_rules.json：场景=窗口+服务+选用规则；规则=filter +
  aggregate(count|ratio|avg) + min_value(阈值) + min_evidence(证据下限) + 文案模板 + action。
  四条规则及实测：R-PAY-INC-COUNT（payment 的 incident_opened 计数，阈值 3 → 4 起）；
  R-PAY-DETECT-LAG（同集合 avg time_to_detect_minutes，阈值 30 → 37.25）；
  R-CO-DEPLOY-FAIL（checkout 的 deploy 失败率，阈值 0.3 → 0.6）；
  R-CO-REVIEW-LAG（checkout 的 review_requested avg wait_hours，阈值 12 → 22）。

【样例一：支付服务事故处理复盘】场景 incident_retro
窗口 2026-03-02T00:00:00Z ~ 2026-03-09T00:00:00Z｜采纳证据 14｜拒绝 1
F-01 窗口内共开启 4 起事故，按严重级别分布：high=2, medium=2。
  证据 EVT-a1de55ec@2026-03-02T09:12:00Z、EVT-51341f33@2026-03-03T14:20:00Z、EVT-d8c8dcd6@2026-03-05T11:10:00Z、EVT-1ce67c94@2026-03-07T13:00:00Z
F-02 平均检测时长 37.25 分钟（阈值 30）。证据同上 4 条。
C-01(0.80) 事故数量达到可复盘规模（4 起），多起集中出现，需定位共同根因。
  证据 EVT-a1de55ec@2026-03-02T09:12:00Z、EVT-51341f33@2026-03-03T14:20:00Z、EVT-d8c8dcd6@2026-03-05T11:10:00Z、EVT-1ce67c94@2026-03-07T13:00:00Z
C-02(0.60) 平均检测时长 37.25 分钟高于阈值 30 分钟，监控发现能力偏弱。证据同上 4 条。
A-01[high/sre] 针对集中出现的事故组织根因复盘，收敛共同失效路径并登记整改项。← C-01
A-02[medium/oncall_engineer] 补齐支付核心链路告警覆盖与阈值，缩短发现时间。← C-02
拒绝证据 EVT-586e5163@2026-03-03T14:35:00Z，来源 unverified_hearsay，未进入任何结论。
依据链：A-01→C-01→F-01→EVT-a1de55ec…EVT-1ce67c94；A-02→C-02→F-02→同 4 条。

【样例二：结算服务发布复盘】场景 release_retro
窗口 2026-03-09T00:00:00Z ~ 2026-03-16T00:00:00Z｜采纳证据 16｜拒绝 1
F-01 窗口内共 5 次部署，其中失败 3 次，失败率 0.6（阈值 0.3）。
  证据 EVT-d294d67c@2026-03-09T10:00:00Z、EVT-a98a79f5@2026-03-09T14:00:00Z、EVT-cc97f54e@2026-03-10T09:30:00Z、EVT-b74a4843@2026-03-11T11:00:00Z、EVT-e90e8f96@2026-03-13T10:20:00Z
F-02 变更评审平均等待 22 小时（阈值 12）。
  证据 EVT-20bb8ab3@2026-03-12T10:15:00Z、EVT-0786d6a2@2026-03-13T15:30:00Z
C-01(0.75) 部署失败率 0.6 高于阈值 0.3，发布流水线稳定性需治理。证据同 F-01 的 5 条。
C-02(0.60) 评审平均等待 22 小时高于阈值 12 小时，评审环节成为发布瓶颈。证据同 F-02 的 2 条。
A-01[high/release_manager] 为发布流水线增加发布前校验与灰度门禁，降低失败率。← C-01
A-02[medium/release_manager] 建立变更评审人轮值机制并设置等待时长提醒。← C-02
拒绝证据 EVT-f5c7073c@2026-03-14T13:00:00Z，来源 manager_note，未进入任何结论。
依据链：A-01→C-01→F-01→EVT-d294d67c…EVT-e90e8f96；A-02→C-02→F-02→EVT-20bb8ab3、EVT-0786d6a2。

【验收标准逐条对照】
1) 匿名过程数据（anonymous process data）
   **匿名数据集落盘为 outputs/process_events_anonymized.jsonl**（32 条，人员 PERSON-/
   客户 CUST-/单据 REF-/事件 EVT- 全部假名化，原始姓名泄漏 0 处）；原始合成输入见
   samples/process_events.jsonl。覆盖 5 种白名单来源与 2 种白名单外来源；
   含 PII 的自由文本会被拒绝处理。
2) 可溯源复盘样例（traceable retrospective samples）
   两份完整复盘（样例一/二），每条结论均挂「证据 ID + 时间戳」，每条改进项均回溯
   到结论，报告含「被拒绝的证据」与「依据链」两节，可逐跳核验。
   代码层强制：无证据的结论抛 GroundingError；无结论的改进项抛 TraceabilityError
   （tests/test_findings.py、tests/test_report.py 覆盖）。
3) 只使用获授权或脱敏资料：白名单 + PII 拒绝 + 假名化三重保证。

【验证记录】
`python verify/run_verification.py`：28/28 断言通过（退出码 0），并刷新
verify/verification_record.md 与 verification_result.json。
`python -m unittest discover -s tests -v`：31/31 通过。
关键断言：事件流加载 32/32；样例无残留 PII；假名化两次结果一致；非白名单来源被拒
且原因可解释、未混入采纳集；两场景结论均挂证据 ID+时间戳且可回溯到采纳证据；改进项
可回溯；报告渲染确定性且无未填充占位符；无证据结论/无结论改进项均被拒。

【关键设计取舍】
不使用大模型：验证记录要能被买家复跑比对，接模型后输出不确定；本单预算不含模型 API
费用；「带依据」需可判真假，本方案证据是结构化事件，ID+时间戳即可核验。
已知局限（如实说明）：规则为阈值驱动的量化规则，不做语义理解；对未量化的软性结论会
因证据不足而不产出（宁可不出结论，也不编造依据）。默认数据为合成/脱敏数据。

【范围与排除】
- 不依赖系列其它单（#1494 等）的任何交付物，独立可运行。
- 不接真实账号/权限，不采集任何真实个人数据；只用脱敏或合成数据。
- 模型 API、云资源、训练算力等第三方费用不在本单范围内（本工具也不需要）。
- 真实业务数据接入与现场校准属超范围项，可在客户经平台提供脱敏数据后另行对接。

【运行注意】
直接用 python 运行，不要用 conda run：conda 会用自己的 GBK 编码重新打印子进程输出，
含中文时表现为 UnicodeEncodeError 且退出码 1（是 conda 的输出重编码问题，不是本工具
的问题）。若必须用 conda run，请先设 PYTHONIOENCODING=utf-8。
