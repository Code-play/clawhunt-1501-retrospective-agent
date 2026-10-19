"""业务复盘 Agent（可溯源版，订单 #1501）。

把业务过程数据整理成有依据的结论与改进项，依据链为：
    事实(Fact) -> 证据引用(EvidenceRef) -> 结论(Conclusion) -> 改进项(Improvement)

硬规矩（在代码层强制，而不是文档约定）：
- 结论必须挂 >= 1 条证据 ID + 时间戳，否则无法构造（GroundingError）；
- 改进项必须能回溯到结论，否则无法构造（TraceabilityError）；
- 非白名单来源不得作为证据，拒绝原因可解释。

全流程确定性、只用标准库、不联网、不调用任何模型 API。
"""

from .actions import Improvement, TraceabilityError, build_improvements, trace_improvement
from .anonymize import AnonymizationError, Pseudonymizer, assert_no_pii
from .events import Event, EventSchemaError, load_events, validate_event
from .evidence import EvidencePolicy, EvidenceRef, RejectedEvidence, collect_evidence
from .findings import (
    Conclusion,
    Fact,
    GroundingError,
    build_conclusions,
    build_facts,
)
from .report import Retrospective, render

__all__ = [
    "Event",
    "EventSchemaError",
    "load_events",
    "validate_event",
    "Pseudonymizer",
    "AnonymizationError",
    "assert_no_pii",
    "EvidencePolicy",
    "EvidenceRef",
    "RejectedEvidence",
    "collect_evidence",
    "Fact",
    "Conclusion",
    "GroundingError",
    "build_facts",
    "build_conclusions",
    "Improvement",
    "TraceabilityError",
    "build_improvements",
    "trace_improvement",
    "Retrospective",
    "render",
]

__version__ = "1.0.0"
