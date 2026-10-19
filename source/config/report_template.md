# {{title}}

> 生成器：ClawHunt #1501 复盘 Agent（确定性流水线，不联网、不调用任何模型 API）
> 场景：`{{scenario_id}}`｜数据窗口：{{window_from}} ~ {{window_to}}
> 事件总数：{{events_total}}｜采纳证据：{{evidence_accepted}}｜拒绝证据（非白名单来源）：{{evidence_rejected}}

## 1. 事实（Fact）

{{facts}}

## 2. 证据引用（Evidence Index）

每条证据都带证据 ID（事件 ID）与时间戳，可回溯到来源系统与来源单据。

{{evidence_table}}

## 3. 结论（Conclusion）

每条结论强制挂 >= 1 条证据 ID + 时间戳，否则在生成阶段直接报错、不产出该结论。

{{conclusions}}

## 4. 改进项（Improvement）

每条改进项都必须回溯到至少一条结论；结论的证据即改进项的证据。

{{improvements}}

## 5. 被拒绝的证据（非白名单来源）

下列来源不在证据白名单内，已按规则拒绝，且未进入任何事实或结论。

{{rejected}}

## 6. 依据链（可溯源）

事实 → 证据引用 → 结论 → 改进项 的完整回溯链如下。

{{trace}}
