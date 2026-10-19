# 验证记录 · 业务复盘 Agent（订单 #1501）

生成时间（UTC）：2026-10-19T03:19:30.167324+00:00
复跑命令：`python verify/run_verification.py`

## 0. 输入

- 过程数据：`samples/process_events.jsonl`，共 32 条原始事件
- 证据白名单：chat_ops、deploy_pipeline、incident_log、survey、ticket_system
- 场景：incident_retro、release_retro

## 1. 事件流 Schema 校验

- 加载事件 32 条，必填字段 / 枚举 / 时间戳 / 去重均通过。

## 2. 确定性假名化

- 32 条事件全部通过 PII 扫描；两次假名化结果一致：True
- 示例：原始 `EVT-A01` -> 假名 `EVT-a1de55ec`

## 3. 证据白名单

- 采纳证据 30 条；拒绝证据 2 条
  - 拒绝 `EVT-586e5163`（unverified_hearsay）：来源类型 'unverified_hearsay' 不在证据白名单内（允许：chat_ops, deploy_pipeline, incident_log, survey, ticket_system）
  - 拒绝 `EVT-f5c7073c`（manager_note）：来源类型 'manager_note' 不在证据白名单内（允许：chat_ops, deploy_pipeline, incident_log, survey, ticket_system）

## 4. 场景 `incident_retro` —— 支付服务事故处理复盘

- 窗口 2026-03-02T00:00:00Z ~ 2026-03-09T00:00:00Z
- 采纳证据 14；被拒证据 1
- 事实 2；结论 2；改进项 2

  - F-01（`R-PAY-INC-COUNT`）：窗口内共开启 4 起事故，按严重级别分布：high=2, medium=2。
  - F-02（`R-PAY-DETECT-LAG`）：窗口内事故平均检测时长 37.25 分钟（阈值 30 分钟）。
  - C-01（置信 0.80）：事故数量达到可复盘规模（4 起），且多起事故集中出现，需定位共同根因。
    证据：`EVT-a1de55ec`@2026-03-02T09:12:00Z、`EVT-51341f33`@2026-03-03T14:20:00Z、`EVT-d8c8dcd6`@2026-03-05T11:10:00Z、`EVT-1ce67c94`@2026-03-07T13:00:00Z
  - C-02（置信 0.60）：平均检测时长 37.25 分钟高于阈值 30 分钟，监控告警的发现能力偏弱。
    证据：`EVT-a1de55ec`@2026-03-02T09:12:00Z、`EVT-51341f33`@2026-03-03T14:20:00Z、`EVT-d8c8dcd6`@2026-03-05T11:10:00Z、`EVT-1ce67c94`@2026-03-07T13:00:00Z
  - A-01［high/sre］针对集中出现的事故组织根因复盘，收敛共同失效路径并登记整改项。（回溯 C-01）
  - A-02［medium/oncall_engineer］补齐支付核心链路的告警覆盖与阈值，缩短事故发现时间。（回溯 C-02）

## 4. 场景 `release_retro` —— 结算服务发布复盘

- 窗口 2026-03-09T00:00:00Z ~ 2026-03-16T00:00:00Z
- 采纳证据 16；被拒证据 1
- 事实 2；结论 2；改进项 2

  - F-01（`R-CO-DEPLOY-FAIL`）：窗口内共 5 次部署，其中失败 3 次，失败率 0.6（阈值 0.3）。
  - F-02（`R-CO-REVIEW-LAG`）：窗口内变更评审平均等待 22 小时（阈值 12 小时）。
  - C-01（置信 0.75）：部署失败率 0.6 高于阈值 0.3，发布流水线的稳定性需要治理。
    证据：`EVT-d294d67c`@2026-03-09T10:00:00Z、`EVT-a98a79f5`@2026-03-09T14:00:00Z、`EVT-cc97f54e`@2026-03-10T09:30:00Z、`EVT-b74a4843`@2026-03-11T11:00:00Z、`EVT-e90e8f96`@2026-03-13T10:20:00Z
  - C-02（置信 0.60）：变更评审平均等待 22 小时高于阈值 12 小时，评审环节成为发布瓶颈。
    证据：`EVT-20bb8ab3`@2026-03-12T10:15:00Z、`EVT-0786d6a2`@2026-03-13T15:30:00Z
  - A-01［high/release_manager］为结算服务发布流水线增加发布前校验与灰度门禁，降低失败率。（回溯 C-01）
  - A-02［medium/release_manager］为结算服务变更建立评审人轮值机制并设置等待时长提醒。（回溯 C-02）

## 5. 负向断言（机制在代码层强制）

- 构造无证据结论 -> GroundingError：True
- 构造无结论改进项 -> TraceabilityError：True

## 6. 单元测试

```
Ran 31 tests in 0.013s
```

## 7. 匿名过程数据产物

验收标准要求交付「匿名过程数据」，因此假名化结果必须落盘成可检查的产物，
而不是只在内存里过一遍就丢掉。本节自行生成该产物再断言。

- 产物：`outputs/process_events_anonymized.jsonl`（32 条事件）
- 假名前缀：人员 `PERSON-`、客户 `CUST-`、单据 `REF-`、事件 `EVT-`
- 原始姓名泄漏检查：原始数据含 6 个不同姓名，泄漏 0 个
- 示例：`Chen Wei` -> `PERSON-d48722cc`；`INC-2201` -> `REF-e4146000`
- 买家复现命令：`python -m retrospective_agent anonymize --out-file <输出文件>`

## 结论

- 断言总数：28；通过：28；失败：0
- 结果：**全部通过**

| 断言 | 预期 | 实际 | 结果 |
|---|---|---|---|
| 事件流加载 | 32 | 32 | 通过 |
| 样例无残留 PII | 通过 | 通过 | 通过 |
| 假名化可复现（两次结果一致） | True | True | 通过 |
| 存在非白名单来源且被拒绝 | True | True | 通过 |
| 拒绝原因可解释 | True | True | 通过 |
| 被拒来源未混入采纳集 | 0 | 0 | 通过 |
| incident_retro 产出结论 | True | True | 通过 |
| incident_retro 每条结论挂证据ID+时间戳 | True | True | 通过 |
| incident_retro 结论证据可回溯到采纳集 | True | True | 通过 |
| incident_retro 改进项可回溯到结论/证据 | True | True | 通过 |
| incident_retro 报告渲染确定性 | True | True | 通过 |
| incident_retro 报告无未填充占位符 | True | True | 通过 |
| release_retro 产出结论 | True | True | 通过 |
| release_retro 每条结论挂证据ID+时间戳 | True | True | 通过 |
| release_retro 结论证据可回溯到采纳集 | True | True | 通过 |
| release_retro 改进项可回溯到结论/证据 | True | True | 通过 |
| release_retro 报告渲染确定性 | True | True | 通过 |
| release_retro 报告无未填充占位符 | True | True | 通过 |
| 共产出两份样例复盘 | 2 | 2 | 通过 |
| 无证据的结论无法构造 | GroundingError | True | 通过 |
| 无结论的改进项无法构造 | TraceabilityError | True | 通过 |
| 单元测试全部通过 | returncode 0 | 0 | 通过 |
| 匿名过程数据产物存在 | True | True | 通过 |
| 匿名过程数据条数等于输入 | 32 | 32 | 通过 |
| 匿名产物中无原始人员姓名 | 0 | 0 | 通过 |
| 人员字段全部为 PERSON- 假名 | 0 | 0 | 通过 |
| 单据字段全部为 REF- 假名 | 0 | 0 | 通过 |
| 事件 ID 全部为 EVT- 假名 | 0 | 0 | 通过 |