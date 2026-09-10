# Scan Insertion Agent：DFT 工作流

版本：0.1.0

适用范围：Task 1（从零生成插链方案）与 Task 2（诊断并修复已有方案）

## 1. 目标与原则

本项目把一次 Scan Insertion 任务拆成可验证的阶段。每个阶段都必须保存输入、输出和判定依据，避免仅凭工具退出码或主观判断宣布成功。

基本原则：

1. 任务要求优先于经验默认值。
2. 未明确的要求进入 `unresolved_requirements`，不得静默猜测。
3. 每次工具调用产生唯一 `tool_call_id`，日志和报告必须可追溯。
4. 修复必须形成 `found -> diagnosis -> fix -> verify` 闭环。
5. 最终交付同时满足任务约束、DFT 检查和输出文件要求。

## 2. 端到端数据流

```text
case 输入目录
    ↓ CaseInput
任务解析与约束归一化
    ↓ TaskRequirement
生成或修订 dofile
    ↓
执行官方 Scan Insertion 工具
    ↓ ToolRunResult
解析日志、报告和交付物
    ↓
诊断问题并生成修复动作
    ↓ IssueResolution
重新执行与验证（必要时循环）
    ↓
审计、验收和最终交付
```

## 3. 阶段说明

### 3.1 读取 Case

Runtime 读取 case 目录并构造 `CaseInput`。至少确认：

- `case_id` 与任务类型正确；
- pre-scan netlist、liberty、任务说明和限制文件存在且可读；
- Task 2 的原始 dofile 已提供；
- 不把 public case 的 golden 文件作为 hidden case 的运行依赖。

门禁：所有必需输入可定位；文件缺失时立即停止并返回明确错误。

### 3.2 解析任务要求

Task Parser 将自然语言转换为 `TaskRequirement`，重点提取：

- 顶层设计名；
- 测试时钟、复位和 scan enable；
- internal scan 是否启用、链数或链长；
- 时钟域、边沿策略和 lockup 要求；
- wrapper scan 范围、控制信号和 cell 策略；
- 输出文件及报告要求。

存在歧义、冲突或无法映射的文字时，保留原文到 `unresolved_requirements`。关键约束未解析完成前不得执行工具。

### 3.3 建立基线

执行修改前保存基线信息：

- 输入文件清单及必要的校验信息；
- 原始 dofile（Task 2）；
- 工具版本和关键环境；
- 第一次运行的日志、DFT 检查和统计报告。

基线用于判断修复是否有效，也用于防止修复引入新的回归。

### 3.4 生成或修订 DFT 配置

Task 1 根据结构化要求生成 dofile；Task 2 在原始 dofile 上做最小必要修改。配置通常按以下顺序组织：

1. 读取库和设计；
2. 解析并链接顶层；
3. 声明测试时钟、复位和 scan enable；
4. 设置 internal scan、clock mixing、lockup 等策略；
5. 配置 wrapper scan（如任务要求）；
6. 执行 DFT 规则检查；
7. 插入 scan 结构；
8. 输出报告、网表及其他交付物。

具体命令必须以比赛提供的官方工具及其版本为准，知识库不硬编码某家工具的私有语法。

### 3.5 执行工具

每次运行创建独立目录，例如 `runs/R001/`，并记录：

- 唯一运行编号；
- 实际执行的 dofile；
- 标准输出、标准错误和完整日志；
- 退出状态和耗时；
- 报告与交付物路径。

工具进程成功退出不等于任务成功；仍需检查日志中的 error/abort、DFT violation、约束符合性和交付物完整性。

### 3.6 解析与诊断

诊断按以下优先级处理：

1. 输入、语法、授权或环境错误；
2. 设计读取、链接、顶层或库错误；
3. 测试时钟、复位、scan enable 等控制信号问题；
4. DFT rule violations；
5. scan chain、时钟域、lockup 或 wrapper 配置不符合任务要求；
6. 输出缺失以及 LEC/结构验证失败。

每个问题形成 `IssueResolution`，必须包含现象、证据、根因、修复动作和复验结果。证据引用应指向具体运行、文件和定位信息。

### 3.7 修复与复验

修复遵循“小步、可回退、一次解决一个根因”的原则：

1. 根据证据提出最小修复；
2. 保存修改后的工件引用；
3. 使用新的 `tool_call_id` 重跑；
4. 验证原问题消失；
5. 检查是否新增其他错误或约束偏差；
6. 未解决时新增 attempt，不覆盖历史记录。

禁止仅删除报错命令、放宽任务硬约束或忽略错误来制造“成功”结果。

### 3.8 最终验收

最终运行必须同时满足：

- 工具未以 error/aborted 结束；
- 必需的 DFT 检查通过，或所有允许豁免都有依据；
- 实际链数、链长、时钟域、边沿和 wrapper 范围符合任务；
- 交付物存在、非空、可解析且来自最终运行；
- 所有关键问题都具备完整修复闭环；
- 不依赖 hidden case 不可用的辅助文件。

详细文件清单见 [`dft_output.md`](dft_output.md)。

## 4. Task 1 与 Task 2 的差异

| 项目 | Task 1 | Task 2 |
| --- | --- | --- |
| 起点 | pre-scan 设计和任务要求 | 既有设计、原始 dofile 和已知问题 |
| 核心动作 | 生成完整插链配置 | 复现、定位并最小化修复 |
| 基线 | 首次配置运行 | 原始 dofile 的原样运行 |
| 重点风险 | 漏配约束、链结构不符合要求 | 未复现即修改、修复造成回归 |
| 交付重点 | 可复现的配置和插链结果 | 变更说明、证据链和复验结果 |

## 5. 失败处理

- 输入缺失：停止运行，报告缺失路径。
- 要求冲突：记录冲突原文，交由上层决策。
- 工具崩溃或超时：保留日志，将状态标记为 `error` 或 `aborted`。
- 报告缺失：即使退出码为零，也视为验收失败。
- 多次修复失败：保留全部 attempt，不覆盖证据，并报告当前最可信根因。

## 6. 推荐审计目录

```text
runs/
└─ R001/
   ├─ run.dofile
   ├─ run.log
   ├─ reports/
   ├─ deliverables/
   └─ decision_log.json
```

实际目录可由 Runtime 调整，但 `ToolRunResult` 和 `IssueResolution` 中的引用必须能够唯一定位这些工件。
