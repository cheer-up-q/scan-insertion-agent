# DFTEXP Dofile Mapping Specification

版本：0.1.0

负责人：A / DFT Flow

状态：语义映射已完成；厂商命令语法等待官方资料核验

## 1. 文档目的

本文定义从自然语言 DFT 要求到可执行 Dofile 的中间映射，使 Task Parser、Agent 和 Runtime 对“要做什么、需要哪些参数、如何验证”保持一致。

完整转换链路：

```text
task_spec.md
    ↓
TaskRequirement
    ↓
Dofile Action IR（本文定义）
    ↓
DFTEXP 命令适配器
    ↓
run.dofile
    ↓
ToolRunResult + 验收证据
```

重要约束：

- 赛题工具为 DFTEXP，不能把 Tessent、Synopsys 或其他工具的命令当作 DFTEXP 命令。
- 当前仓库没有 DFTEXP 命令手册、示例 dofile 或可执行环境，因此本文不伪造厂商命令。
- `schemas/dofile_actions.yaml` 中 `command_template: null` 表示必须先用官方资料补齐。
- Action IR 是内部协议，不能直接作为 Dofile 交给工具运行。

## 2. 输入与输出

### 2.1 输入

- `CaseInput`：输入目录、pre-scan netlist、liberty、任务说明、限制条件和可选原始 dofile。
- `TaskRequirement`：Agent 解析得到的结构化要求。
- 工具能力信息：DFTEXP 版本、官方命令说明、许可功能和比赛环境限制。

### 2.2 输出

- 有序 `DofileAction` 列表；
- 每个 action 的参数、前置条件和验证方法；
- 经 DFTEXP 适配器渲染后的 `run.dofile`；
- 未能映射的要求和阻塞原因。

## 3. Dofile Action IR

`schema_version: 0.2.0` 的动作目录使用**扁平结构**，与实际 `schemas/dofile_actions.yaml` 一致：

```yaml
- action_id: scan.set_chain_count
  stage: internal_scan
  source_path: TaskRequirement.internal_scan.chain_count
  required_parameters: [chain_count]
  command_template: null
  command_status: needs_official_reference
  depends_on: [scan.enable_internal]
  preconditions:
    - internal_scan.enabled == true
    - chain_count is not null
  validator:
    report_key: scan_chains
    assertion: actual_chain_count == chain_count
  validation: "actual chain count equals chain_count"
```

字段含义：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `parameter_types`（顶层） | 是 | 参数名到类型的注册表；`required_parameters` 中的每个名字必须在此登记 |
| `action_id` | 是 | 工具无关的稳定动作编号 |
| `stage` | 是 | 所属阶段，必须出现在 `generation_order` 中 |
| `source_path` | 是 | 参数来自哪个公共模型字段；`null` 表示当前模型无对应字段，要求必须保留在 `unresolved_requirements` |
| `required_parameters` | 是 | 渲染 Dofile 必需的参数名 |
| `command_template` | 是 | 经官方资料核验的 DFTEXP 命令模板；当前全部为 `null` |
| `command_status` | 是 | `verified` 或 `needs_official_reference` |
| `depends_on` | 否 | 必须先完成的动作（AND） |
| `depends_on_any` | 否 | 多组可选前置序列（OR），例如复合入口与分步入口 |
| `mutually_exclusive_with` | 否 | 同一次运行不得同时出现的动作 |
| `preconditions` | 否 | 执行前必须满足的条件 |
| `validator` | 否 | 结构化验证目标 `{report_key, assertion}` |
| `validation` | 是 | 人类可读的验收说明 |

未声明 `depends_on` / `preconditions` 的动作表示**关系尚未冻结**，不表示没有依赖。`schema_version: 0.2.0` 仍不包含动作实例：具体参数值由 Agent 在生成 Dofile 时填充，`null` 模板永远不得渲染或执行。

## 4. 固定动作顺序

生成 Dofile 时必须保持以下阶段顺序：

1. 初始化工具与运行环境；
2. 读取 standard-cell library；
3. 读取 pre-scan netlist；
4. 选择并链接顶层设计；
5. 应用任务限制；
6. 声明 test clock、reset 和 scan enable；
7. 配置 internal scan；
8. 配置 wrapper scan（如启用）；
9. 执行插链前 DRC；
10. 对允许自动处理的问题实施修复；
11. 执行 scan replacement/insertion/stitching；
12. 执行插链后 DRC 和链结构分析；
13. 写出报告和交付物；
14. 执行功能等价性验证（如要求）。

若 DFTEXP 官方流程要求不同顺序，以对应版本手册为准，并同步更新本文和 schema。

## 5. 核心映射表

### 5.1 设计加载与环境

| ID | 自然语言/来源 | 模型字段 | 参数 | DFT 动作 | 验证 |
| --- | --- | --- | --- | --- | --- |
| `env.initialize` | 使用比赛指定 DFTEXP 环境 | 环境配置 | tool/version | 初始化工具模式 | 日志记录正确工具和版本 |
| `input.load_library` | 使用指定标准单元库 | `CaseInput.liberty_file` | liberty path | 读取 cell library | 日志无 library parse/link error |
| `input.load_netlist` | 使用指定综合网表 | `CaseInput.pre_scan_netlist` | netlist path | 读取 gate-level netlist | 顶层候选和模块统计可用 |
| `design.select_top` | 顶层为 chip_top | `TaskRequirement.top_design` | top name | 选择当前设计 | 日志确认 current/top design |
| `design.link` | 链接设计 | 输入模型 | top/library | 解析引用并链接 | 无 unresolved reference |
| `constraints.apply_limitations` | 不允许修改模块 X | `CaseInput.limitations` | limitation rules | 建立保护/排除集合 | 修改记录不触及保护对象 |

### 5.2 DFT 控制信号

| ID | 自然语言示例 | 模型字段 | 参数 | DFT 动作 | 验证 |
| --- | --- | --- | --- | --- | --- |
| `signal.add_test_clock` | 测试时钟为 test_clk | `test_clocks[]` | clock object | 声明 test clock | clock report 存在该对象 |
| `signal.set_clock_edge` | 使用上升沿/下降沿 | `internal_scan.edge_strategy` | edge | 设置有效边沿 | clock/chain report 边沿一致 |
| `signal.add_reset` | reset_n 为测试复位 | `resets[]` | reset object | 声明 reset/set | DRC 不再报未声明控制信号 |
| `signal.set_reset_polarity` | reset_n 低有效 | 当前无独立字段 | signal/polarity | 设置复位极性 | 报告极性正确；原文进入 unresolved |
| `signal.add_scan_enable` | scan enable 使用 SE | `scan_enable` | signal object | 声明 scan enable | scan signal report 映射正确 |
| `signal.add_test_mode` | test_mode 控制测试模式 | 当前无独立字段 | signal/value | 声明 test mode | 模式报告与任务一致 |

对公共模型尚无独立字段的要求，不得丢弃：原文保留到 `unresolved_requirements`，由 Agent 生成显式待决策项。对应动作 `signal.set_reset_polarity`、`signal.add_test_mode` 已在动作目录中登记，但其 `source_path` 仍为 `null`，在接口扩展前不得由单个模块私自补字段。

### 5.3 Internal Scan

| ID | 自然语言示例 | 模型字段 | 参数 | DFT 动作 | 验证 |
| --- | --- | --- | --- | --- | --- |
| `scan.enable_internal` | 启用内部扫描 | `internal_scan.enabled` | enabled | 开关 internal scan | scan cell population 符合预期 |
| `scan.set_chain_count` | 建立 8 条扫描链 | `internal_scan.chain_count` | positive integer | 设置目标链数 | actual chain count 等于要求 |
| `scan.set_chain_length` | 每条 Scan Chain 长度固定为 500 | `internal_scan.chain_length` | positive integer | 设置固定链长 | 每条链的实际长度等于 `chain_length`；任一条不等即失败 |
| `scan.assign_clock_domains` | 按 clk_a/clk_b 分域 | `internal_scan.clock_domains[]` | domain list | 建立 scan clock domains | chain report 域归属正确 |
| `scan.set_edge_strategy` | 所有扫描链使用上升沿触发 | `internal_scan.edge_strategy` | `rising` / `falling` / `mixed` | 设置时钟有效边沿 | 链报告中的触发边沿与取值一致 |
| `scan.set_lockup_required` | 跨域必须插 lockup | `internal_scan.lockup_required` | boolean | 启用/禁止 lockup | 报告中的 lockup 数量和位置合理 |
| `scan.set_lockup_strategy` | 在跨域边界插入 lockup | `internal_scan.lockup_strategy` | strategy | 设置 lockup 策略 | 跨域边界得到保护 |
| `scan.exclude_instances` | 模块 X 不参与插链 | `CaseInput.limitations` | object patterns | 建立 non-scan/exclude 列表 | 排除对象未被替换或串接 |
| `scan.replace_cells` | 替换为 scan cells | internal scan config | cell population | 执行 scan replacement | scan cell report 无意外遗漏 |
| `scan.stitch_chains` | 连接扫描链 | internal scan config | chain constraints | 执行 chain stitching | 无空链、断链和悬空端口 |

### 5.4 Wrapper Scan

| ID | 自然语言示例 | 模型字段 | 参数 | DFT 动作 | 验证 |
| --- | --- | --- | --- | --- | --- |
| `wrapper.enable` | 启用 wrapper scan | `wrapper_scan.enabled` | enabled | 开关 wrapper scan | wrapper analysis 已执行 |
| `wrapper.set_scope` | 只包装 core_a | `wrapper_scan.scope[]` | object list | 选择 wrapper 范围 | wrapper cell 对象范围正确 |
| `wrapper.set_control_signals` | 使用 wrp_en 控制 | `wrapper_scan.control_signals[]` | signal list | 声明 wrapper 控制 | 信号连接和有效值正确 |
| `wrapper.set_cell_strategy` | 指定 wrapper cell 策略 | `wrapper_scan.wrapper_cell_strategy` | strategy | 配置 cell 选择/类型 | wrapper cell report 符合策略 |

### 5.5 检查、插入和输出

| ID | 自然语言/流程要求 | 模型字段 | 参数 | DFT 动作 | 验证 |
| --- | --- | --- | --- | --- | --- |
| `check.run_pre_drc` | 插链前执行 DRC | 流程固定动作 | phase=pre | 运行 DFT DRC | 无未处理 fatal/error |
| `repair.apply_eco` | 用 ECO 修复 DRC | `IssueResolution` | issue/fix | 应用最小 ECO | 功能不变且原违规消失 |
| `scan.insert` | 执行 Scan Insertion | 已确认配置 | all config | 插入并提交测试逻辑 | post-scan 设计产生 |
| `check.run_post_drc` | 插链后再次检查 | 流程固定动作 | phase=post | 运行 post-insertion DRC | 无新关键违规 |
| `report.write_dft` | 输出 DFT 报告 | `output_requirements[]` | output path | 写 DFT/DRC 报告 | 文件存在、非空、可解析 |
| `report.write_scan_chains` | 输出链报告 | `output_requirements[]` | output path | 写 scan-chain report | 链数、链长、域和 lockup 可提取 |
| `report.write_wrapper` | 输出 Wrapper 报告 | `output_requirements[]` | output path | 写 wrapper report | 文件存在、非空、可解析；范围与控制信号可提取 |
| `output.write_netlist` | 输出 post-scan 网表 | `output_requirements[]` | output path | 写插链后 netlist | 文件非空、顶层可解析 |
| `output.write_ctl` | 输出 CTL | `output_requirements[]` | output path | 写测试控制数据 | 文件存在且下游可读取 |
| `output.write_scandef` | 输出 SCANDEF | `output_requirements[]` | output path | 写物理链数据 | 链/单元记录完整 |
| `verify.run_lec` | 验证功能未改变 | `output_requirements[]` | pre/post netlist | 执行或调用 LEC | 功能模式等价 |

插链入口的互斥规则：

- `scan.insert` 是一次性复合入口，表示由工具完成 cell replacement 与 chain stitching。
- `scan.replace_cells` 与 `scan.stitch_chains` 是分步入口，按此顺序执行。
- 同一次运行只能选择一种入口：要么单独 `scan.insert`，要么
  `scan.replace_cells` 后接 `scan.stitch_chains`；不得同时提交 `scan.insert`
  与任一原子动作。

## 6. 参数冲突与缺省规则

### 6.1 链数与链长

`internal_scan.chain_length` 的语义**唯一**：固定链长，即每条链恰好为该长度。
最大长度、目标长度、推荐长度和均衡长度属于不同语义，当前公共接口无法表达，
必须按 `docs/task_requirement_mapping.md` §8.5 / §8.7 写入
`unresolved_requirements`，不得写入 `chain_length`。

- 只给 `chain_count`：以链数为硬约束，链长由工具平衡。
- 只给 `chain_length`：先依据可扫描单元数推导所需链数，再由报告复核。
- 两者都给：生成前执行**容量预检** `scan_cell_count <= chain_count × chain_length`；
  不满足说明参数组合不可能成立，阻止生成 Dofile。
- 两者都没给：不得凭经验写死，保留为待决策项或使用比赛明确提供的默认值。

容量预检不是长度验收：

- `scan_cell_count <= chain_count × chain_length` 只回答“这些参数有没有可能成立”，
  不能证明任意一条链的长度正确。反例：要求 3 条链、每条固定 3，实际得到
  2/4/3，容量不等式成立，但固定长度要求已被违反。
- 长度验收必须**逐链**进行：从 scan-chain 报告读取每条链的实际长度，逐条与
  `chain_length` 比对，任一条不等即为失败。
- 同时必须按 `docs/dft_output.md` §5.2 检查链长分布、空链和断链，不得只比较总链数。

### 6.2 unknown、null 与 false

- `null`：未知或任务未说明；
- `false`：任务明确禁止；
- 空列表：未提取到对象，不等于工具中可以省略。

Agent 不得把 `lockup_required=null` 转换为“禁用 lockup”。

### 6.3 不支持的要求

如果要求不能映射：

1. 原文写入 `unresolved_requirements`；
2. 不生成猜测命令；
3. 记录缺失的参数或工具能力；
4. 在执行前返回阻塞原因。

## 7. Task 1 生成策略

Task 1 从空模板构建 Dofile：

```text
env.initialize
input.load_library
input.load_netlist
design.select_top
design.link
constraints.apply_limitations
signal.*
scan.*
wrapper.*（可选）
check.run_pre_drc
repair.apply_eco（需要时）
scan.insert
check.run_post_drc
report.*
output.*
verify.run_lec（按要求）
```

生成前必须保证所有硬约束均可映射，且厂商命令模板已验证。

## 8. Task 2 修订策略

Task 2 以 `original_dofile` 为基线：

1. 原样执行并保存 R001 基线；
2. 把原 dofile 解析为 action 序列；
3. 将 action 与 `TaskRequirement` 比较；
4. 只修改导致已证实问题的最小 action；
5. 输出新 dofile，不覆盖原文件；
6. 使用新 run id 执行；
7. 用 `IssueResolution` 记录 found、diagnosis、fix 和 verify。

禁止整份重写 dofile 来掩盖问题，也禁止删除任务硬约束来换取工具成功退出。

## 9. 端到端示例

以下示例只展示 Action IR；`command.template=null` 时不能渲染为真实 DFTEXP Dofile。

### 9.1 单时钟、8 条链

任务原文：

> 顶层为 chip_top，test_clk 为测试时钟，SE 为 scan enable，建立 8 条内部扫描链。

结构化要求：

```json
{
  "top_design": "chip_top",
  "test_clocks": ["test_clk"],
  "scan_enable": "SE",
  "internal_scan": {
    "enabled": true,
    "chain_count": 8
  }
}
```

动作：

```yaml
- design.select_top: {top_design: chip_top}
- signal.add_test_clock: {clock: test_clk}
- signal.add_scan_enable: {signal: SE}
- scan.enable_internal: {enabled: true}
- scan.set_chain_count: {chain_count: 8}
- check.run_pre_drc: {}
- scan.insert: {}
- check.run_post_drc: {}
- report.write_scan_chains: {}
- output.write_netlist: {}
```

验收：实际链数为 8；无空链/断链；SE 和 test_clk 映射正确；post-scan netlist 非空。

### 9.2 多时钟域与 lockup

任务原文：

> clk_a 与 clk_b 分属两个扫描时钟域，跨域边界必须使用 lockup。

```json
{
  "test_clocks": ["clk_a", "clk_b"],
  "internal_scan": {
    "enabled": true,
    "clock_domains": ["clk_a", "clk_b"],
    "lockup_required": true,
    "lockup_strategy": "clock_domain_boundary"
  }
}
```

动作重点：为两个时钟建模、建立 domain、设置 lockup 要求，再执行链分析。验收时检查每个跨域链段的边沿和 lockup 位置，而不是只检查 lockup 总数。

### 9.3 Wrapper Scan

任务原文：

> 对 core_a 启用 wrapper scan，控制信号为 wrp_en。

```json
{
  "wrapper_scan": {
    "enabled": true,
    "scope": ["core_a"],
    "control_signals": ["wrp_en"],
    "wrapper_cell_strategy": null
  }
}
```

动作重点：`wrapper.enable`、`wrapper.set_scope`、`wrapper.set_control_signals`。因为 cell strategy 未指定，不得虚构默认策略；需从任务限制或官方流程获取。

### 9.4 Task 2 最小修复

现象：任务要求 8 条链，基线报告只有 4 条。

修复：只更新 `scan.set_chain_count` 对应命令。

复验：新运行报告显示 8 条链，同时 DRC、LEC 和其他已满足约束没有回归。

最小修改约束：

1. **输入**：`CaseInput.original_dofile` 是基线 dofile，必须原样保存，不得覆盖。
2. **差异**：修复只允许改动与根因对应的动作参数；每个改动必须能由
   `IssueResolution.diagnosis.root_cause` 和 `IssueFix.action` 解释。
3. **产物**：`IssueFix.artifact_ref` 至少包含新的 dofile（类型为 `List[str]`，
   可包含配置或补丁文件）；Runtime 必须逐个校验文件存在。
4. **禁止**：不得整份重写 dofile、不得删除已满足的配置、不得用 golden dofile
   替换基线、不得改动无关动作。
5. **复验**：`IssueVerify.run_ref` 必须指向新的 `ToolRunResult`；验收至少包括
   目标问题消失、DRC 无新增阻断、LEC/结构检查无回归、其余硬约束仍满足。
6. **失败处理**：复验失败时保留本次尝试（追加到 `attempts`），不得覆盖之前的
   证据，也不得把失败的运行标记为 `resolved=true`。

## 10. 厂商命令核验流程

要把本规范升级为可执行映射，必须取得比赛环境中的以下至少一种权威资料：

- `/home/public/README` 或赛题服务器说明；
- DFTEXP SI 对应版本的命令参考；
- 官方 public case 示例 dofile；
- 工具内置 `help`/`man` 命令输出。

每条命令需记录：

| 项目 | 核验要求 |
| --- | --- |
| 工具及版本 | 明确 DFTEXP 子工具和版本 |
| 精确命令 | 命令名、选项名、大小写和参数顺序 |
| 使用模式 | setup/analysis/insertion 等上下文（若存在） |
| 前置命令 | 必须已加载的设计、库或配置 |
| 返回/输出 | 日志标记、报告或文件 |
| 失败特征 | 常见错误消息与原因 |
| 来源 | 手册章节、help 输出或官方示例文件 |

只有完成上述核验后，才把 schema 中的 `command.status` 改为 `verified` 并填入 `command_template`。

## 11. 完成定义

语义映射阶段完成条件：

- 核心动作不少于 20 条；
- 所有现有 `TaskRequirement` 字段均有处理规则；
- 每个动作都有验证证据；
- Task 1 与 Task 2 策略明确；
- 未知参数不会被静默猜测；
- 机器可读 schema 能通过 YAML 解析。

可执行映射完成条件：

- DFTEXP 版本已确认；
- 所有必需命令模板均有官方来源；
- public case 可从干净输入复现；
- 生成 dofile 能运行并产出规定报告；
- 不依赖 golden dofile 或个人绝对路径。

## 12. 参考依据

- EDA² 公开赛题页确认 DFTEXP Scan Insertion 的输入包含综合网表和标准库，参赛者需自行准备运行脚本、调整扫描链长度与数量、修复 DRC，并提交 post-scan netlist 和脚本：
  <https://xiakedao.eda2.com/s/y32/index.html>
- 具体 DFTEXP 命令语法不在当前仓库或上述公开页面中，必须以本届比赛环境提供的官方资料为准。
