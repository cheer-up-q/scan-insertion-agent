from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    TASK1 = "task1"
    TASK2 = "task2"


class ExitStatus(str, Enum):
    COMPLETED = "completed"
    ERROR = "error"
    ABORTED = "aborted"


# ============================================================
# 1. CaseInput
# C负责生成，表示一个比赛case的完整输入
# ============================================================

class CaseInput(BaseModel):
    case_id: str
    task_type: TaskType

    input_dir: str
    pre_scan_netlist: str
    liberty_file: str
    task_spec: str
    limitations: str

    # 任务二使用
    original_dofile: Optional[str] = None

    # Public case开发阶段可能存在
    # Hidden case正式运行不能依赖
    golden_dofile: Optional[str] = None
    preset_issues: Optional[str] = None


# ============================================================
# 2. TaskRequirement
# B负责从task_spec.md解析得到
# ============================================================

class InternalScanRequirement(BaseModel):
    enabled: bool = True

    chain_count: Optional[int] = Field(default=None, gt=0)
    chain_length: Optional[int] = Field(default=None, gt=0)

    clock_domains: List[str] = Field(default_factory=list)
    edge_strategy: Optional[str] = None

    lockup_required: Optional[bool] = None
    lockup_strategy: Optional[str] = None


class WrapperScanRequirement(BaseModel):
    enabled: bool = False

    scope: List[str] = Field(default_factory=list)
    control_signals: List[str] = Field(default_factory=list)

    wrapper_cell_strategy: Optional[str] = None


class TaskRequirement(BaseModel):
    top_design: Optional[str] = None

    test_clocks: List[str] = Field(default_factory=list)
    resets: List[str] = Field(default_factory=list)

    scan_enable: Optional[str] = None

    internal_scan: InternalScanRequirement = Field(
        default_factory=InternalScanRequirement
    )

    wrapper_scan: WrapperScanRequirement = Field(
        default_factory=WrapperScanRequirement
    )

    output_requirements: List[str] = Field(default_factory=list)

    unresolved_requirements: List[str] = Field(default_factory=list)


# ============================================================
# 3. ToolRunResult
# C每调用一次官方Scan Insertion工具后返回给B
# ============================================================

class ToolError(BaseModel):
    error_type: str
    message: str

    source: Optional[str] = None
    locator: Optional[str] = None


class ToolRunResult(BaseModel):
    tool_call_id: str
    exit_status: ExitStatus
    log_file: str

    reports: Dict[str, str] = Field(default_factory=dict)
    deliverables: Dict[str, str] = Field(default_factory=dict)

    errors: List[ToolError] = Field(default_factory=list)

    wall_time_seconds: Optional[float] = None


# ============================================================
# 4. IssueResolution
# B负责生成诊断/修复决策内容
# C最终写入decision_log.json
# ============================================================

class EvidenceRef(BaseModel):
    run_ref: str
    source: str

    locator: Optional[str] = None
    excerpt: Optional[str] = None


class IssueDiagnosis(BaseModel):
    summary: str
    located_object: str
    root_cause: str

    # DFT配置不符合任务要求时填写
    violated_requirement: Optional[str] = None


class IssueFix(BaseModel):
    action: str
    artifact_ref: List[str] = Field(default_factory=list)


class IssueVerify(BaseModel):
    run_ref: str
    source: str

    resolved: bool

    locator: Optional[str] = None
    excerpt: Optional[str] = None


class RepairAttempt(BaseModel):
    fix: IssueFix
    verify: IssueVerify


class IssueResolution(BaseModel):
    issue_id: str
    phenomenon: str

    found: EvidenceRef
    diagnosis: IssueDiagnosis

    attempts: List[RepairAttempt] = Field(default_factory=list)

    resolved: bool = False