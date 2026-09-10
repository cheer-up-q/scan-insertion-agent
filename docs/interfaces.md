# Scan Insertion Agent Core Interfaces

版本：0.1.0

更新时间：2026-09-10

维护者：A（队长）

## 1. 接口概览

```text
Case 输入
    ↓ CaseInput
Task Parser / Agent
    ↓ TaskRequirement
Tool Runner
    ↓ ToolRunResult
Diagnosis / Repair Agent
    ↓ IssueResolution
Audit
```

| 接口 | 生产者 | 主要消费者 | 用途 |
| --- | --- | --- | --- |
| `CaseInput` | C / Runtime | B / Agent | 提供统一 case 输入 |
| `TaskRequirement` | B / Agent | C / Runtime | 描述结构化 DFT 要求 |
| `ToolRunResult` | C / Runtime | B / Agent | 描述一次工具运行及其工件 |
| `IssueResolution` | B / Agent | C / Runtime、Audit | 保存诊断、修复和复验闭环 |

权威模型定义位于 `src/contracts/models.py`。本文用于解释字段语义；若两者不一致，应先停止集成并由接口负责人确认，而不是由单个模块自行解释。

## 2. 公共枚举

### 2.1 TaskType

| 值 | 含义 |
| --- | --- |
| `task1` | 从输入设计和要求建立 Scan Insertion 方案 |
| `task2` | 复现、诊断并修复已有方案 |

### 2.2 ExitStatus

| 值 | 含义 |
| --- | --- |
| `completed` | 工具进程完成；仍需业务验收 |
| `error` | 工具或流程发生错误 |
| `aborted` | 工具被中止、超时或主动终止 |

`completed` 只表示执行结束，不自动代表 DFT 规则、任务约束和交付物全部通过。

## 3. CaseInput

Owner：C / Runtime

表示一个比赛 case 的统一输入。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `case_id` | `str` | 是 | case 唯一标识 |
| `task_type` | `TaskType` | 是 | `task1` 或 `task2` |
| `input_dir` | `str` | 是 | case 输入根目录 |
| `pre_scan_netlist` | `str` | 是 | 插链前网表路径 |
| `liberty_file` | `str` | 是 | 标准单元 liberty 路径 |
| `task_spec` | `str` | 是 | 自然语言任务说明路径 |
| `limitations` | `str` | 是 | 限制条件路径 |
| `original_dofile` | `str \| null` | 否 | Task 2 原始 dofile |
| `golden_dofile` | `str \| null` | 否 | 仅 public case 开发参考，不得成为 hidden case 依赖 |
| `preset_issues` | `str \| null` | 否 | public case 可用的预置问题说明 |

示例：

```json
{
  "case_id": "public_case_1",
  "task_type": "task1",
  "input_dir": "input",
  "pre_scan_netlist": "input/netlist/pre_scan.v",
  "liberty_file": "input/lib/stdcells.lib",
  "task_spec": "input/task_spec.md",
  "limitations": "input/limitations.md",
  "original_dofile": null,
  "golden_dofile": null,
  "preset_issues": null
}
```

## 4. TaskRequirement

Owner：B / Agent

表示从 `task_spec.md` 提取的结构化 DFT 要求。

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `top_design` | `str \| null` | `null` | 顶层设计名 |
| `test_clocks` | `list[str]` | `[]` | 测试时钟对象 |
| `resets` | `list[str]` | `[]` | reset/set 对象 |
| `scan_enable` | `str \| null` | `null` | scan enable 对象 |
| `internal_scan` | `InternalScanRequirement` | 默认启用 | internal scan 要求 |
| `wrapper_scan` | `WrapperScanRequirement` | 默认禁用 | wrapper scan 要求 |
| `output_requirements` | `list[str]` | `[]` | 必需输出与报告 |
| `unresolved_requirements` | `list[str]` | `[]` | 无法可靠解析的原文 |

### 4.1 InternalScanRequirement

| 字段 | 类型 | 默认值 | 约束/说明 |
| --- | --- | --- | --- |
| `enabled` | `bool` | `true` | 是否启用 internal scan |
| `chain_count` | `int \| null` | `null` | 若给出，必须大于 0 |
| `chain_length` | `int \| null` | `null` | 若给出，必须大于 0 |
| `clock_domains` | `list[str]` | `[]` | 目标时钟域 |
| `edge_strategy` | `str \| null` | `null` | 边沿/排序策略 |
| `lockup_required` | `bool \| null` | `null` | 是否要求 lockup |
| `lockup_strategy` | `str \| null` | `null` | lockup 策略 |

### 4.2 WrapperScanRequirement

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `enabled` | `bool` | `false` | 是否启用 wrapper scan |
| `scope` | `list[str]` | `[]` | wrapper 作用范围 |
| `control_signals` | `list[str]` | `[]` | wrapper 控制信号 |
| `wrapper_cell_strategy` | `str \| null` | `null` | wrapper cell 策略 |

示例：

```json
{
  "top_design": "chip_top",
  "test_clocks": ["test_clk"],
  "resets": ["reset_n"],
  "scan_enable": "scan_en",
  "internal_scan": {
    "enabled": true,
    "chain_count": 8,
    "chain_length": null,
    "clock_domains": ["test_clk"],
    "edge_strategy": "same_edge",
    "lockup_required": false,
    "lockup_strategy": null
  },
  "wrapper_scan": {
    "enabled": false,
    "scope": [],
    "control_signals": [],
    "wrapper_cell_strategy": null
  },
  "output_requirements": ["post_scan_netlist", "scan_chain_report"],
  "unresolved_requirements": []
}
```

关键语义：缺失字段不等于任务明确禁止。例如 `lockup_required=null` 表示未确定，而不是 `false`。

## 5. ToolRunResult

Owner：C / Runtime

描述一次真实工具调用的状态、日志、报告、交付物和错误。

| 字段 | 类型 | 必填/默认 | 说明 |
| --- | --- | --- | --- |
| `tool_call_id` | `str` | 必填 | 单次运行唯一编号 |
| `exit_status` | `ExitStatus` | 必填 | completed/error/aborted |
| `log_file` | `str` | 必填 | 原始日志路径 |
| `reports` | `dict[str, str]` | `{}` | 报告类型到路径的映射 |
| `deliverables` | `dict[str, str]` | `{}` | 交付物类型到路径的映射 |
| `errors` | `list[ToolError]` | `[]` | 结构化错误列表 |
| `wall_time_seconds` | `float \| null` | `null` | 运行耗时 |

`ToolError` 字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `error_type` | `str` | 是 | 稳定的错误类别 |
| `message` | `str` | 是 | 错误摘要 |
| `source` | `str \| null` | 否 | 日志或报告来源 |
| `locator` | `str \| null` | 否 | 行号、规则编号或对象定位 |

示例见 [`dft_output.md`](dft_output.md)。

## 6. IssueResolution

Owner：B 负责诊断与决策；C 负责持久化和审计。

每个对象表示一个独立问题的完整闭环。

| 字段 | 类型 | 必填/默认 | 说明 |
| --- | --- | --- | --- |
| `issue_id` | `str` | 必填 | 问题唯一编号 |
| `phenomenon` | `str` | 必填 | 可观察现象 |
| `found` | `EvidenceRef` | 必填 | 首次发现问题的证据 |
| `diagnosis` | `IssueDiagnosis` | 必填 | 定位和根因 |
| `attempts` | `list[RepairAttempt]` | `[]` | 有序修复尝试 |
| `resolved` | `bool` | `false` | 当前是否已解决 |

### 6.1 EvidenceRef

- `run_ref`：发现问题的运行编号；
- `source`：日志或报告标识；
- `locator`：可选的行号、章节或对象；
- `excerpt`：可选的最小必要证据摘录。

### 6.2 IssueDiagnosis

- `summary`：诊断摘要；
- `located_object`：定位到的命令、设计对象或配置；
- `root_cause`：有证据支持的根因；
- `violated_requirement`：可选，违反的任务要求。

### 6.3 RepairAttempt

每次尝试由 `IssueFix` 和 `IssueVerify` 组成：

- `IssueFix.action`：实施的修复动作；
- `IssueFix.artifact_ref`：修改后的 dofile、配置或其他工件；
- `IssueVerify.run_ref`：复验运行编号；
- `IssueVerify.source`、`locator`、`excerpt`：复验证据；
- `IssueVerify.resolved`：该次复验是否解决问题。

`IssueResolution.resolved=true` 时，至少应有一次可定位且 `verify.resolved=true` 的复验证据。当前 Pydantic 模型尚未强制该跨字段规则，业务层必须检查。

## 7. 序列化与路径约定

- 模块间优先传递模型实例；落盘时使用 JSON。
- 字段名保持与 Pydantic 模型一致，不另设别名。
- 路径应统一相对于 case 工作目录或项目根目录；同一对象中不得混用无说明的路径基准。
- `reports` 和 `deliverables` 的 key 应稳定，例如 `dft_drc`、`scan_chains`、`post_scan_netlist`、`final_dofile`。
- 可选字段使用 `null` 表示未知或不适用，不用空字符串代替。

## 8. 错误处理约定

- 输入缺失或模型校验失败：调用方不得继续执行工具。
- 工具失败：仍返回 `ToolRunResult`，并保存可用日志及结构化错误。
- 报告缺失：记录为错误，不能因进程退出码为零而忽略。
- 未解析要求：保留在 `unresolved_requirements`，由决策层显式处理。
- 证据不足：诊断应标记为待确认，不得虚构根因或复验结论。

## 9. 接口变更规则

`src/contracts/` 属于全组公共接口。任何字段的新增、删除、重命名、类型变化或语义变化都必须：

1. 说明变更原因和生产者/消费者影响；
2. 由相关模块负责人确认；
3. 同步更新 `src/contracts/models.py`、本文和测试；
4. 通过 Pull Request 合并到 `dev`；
5. 禁止某个功能分支单方面依赖尚未合并的接口变更。
