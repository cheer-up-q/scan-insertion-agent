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

每个动作使用以下逻辑结构：

```yaml
action_id: scan.set_chain_count
source:
  model: TaskRequirement
  path: internal_scan.chain_count
parameters:
  chain_count: 8
preconditions:
  - internal_scan.enabled == true
command:
  vendor: DFTEXP
  template: null
  status: needs_official_reference
validation:
  report_key: scan_chains
  assertion: actual_chain_count == 8
```

字段含义：

| 字段 | 说明 |
| --- | --- |
| `action_id` | 工具无关的稳定动作编号 |
| `source` | 参数来自哪个公共模型字段 |
| `parameters` | 渲染 Dofile 所需参数 |
| `preconditions` | 执行前必须满足的条件 |
| `command.template` | 经官方资料核验的 DFTEXP 命令模板 |
| `command.status` | `verified` 或 `needs_official_reference` |
| `validation` | 运行后使用什么证据判断动作生效 |

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

对公共模型尚无独立字段的要求，不得丢弃：原文保留到 `unresolved_requirements`，由 Agent 生成显式待决策项。

### 5.3 Internal Scan

| ID | 自然语言示例 | 模型字段 | 参数 | DFT 动作 | 验证 |
| --- | --- | --- | --- | --- | --- |
| `scan.enable_internal` | 启用内部扫描 | `internal_scan.enabled` | enabled | 开关 internal scan | scan cell population 符合预期 |
| `scan.set_chain_count` | 建立 8 条扫描链 | `internal_scan.chain_count` | positive integer | 设置目标链数 | actual chain count 等于要求 |
| `scan.set_chain_length` | 最大链长 500 | `internal_scan.chain_length` | positive integer | 设置链长目标/上限 | 每条链长度满足定义 |
| `scan.assign_clock_domains` | 按 clk_a/clk_b 分域 | `internal_scan.clock_domains[]` | domain list | 建立 scan clock domains | chain report 域归属正确 |
| `scan.set_edge_strategy` | 同边沿单元成链 | `internal_scan.edge_strategy` | strategy | 设置边沿混合/排序策略 | 相邻单元边沿符合策略 |
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
| `output.write_netlist` | 输出 post-scan 网表 | `output_requirements[]` | output path | 写插链后 netlist | 文件非空、顶层可解析 |
| `output.write_ctl` | 输出 CTL | `output_requirements[]` | output path | 写测试控制数据 | 文件存在且下游可读取 |
| `output.write_scandef` | 输出 SCANDEF | `output_requirements[]` | output path | 写物理链数据 | 链/单元记录完整 |
| `verify.run_lec` | 验证功能未改变 | `output_requirements[]` | pre/post netlist | 执行或调用 LEC | 功能模式等价 |

## 6. 参数冲突与缺省规则

### 6.1 链数与链长

- 只给 `chain_count`：以链数为硬约束，链长由工具平衡。
- 只给 `chain_length`：先依据可扫描单元数推导所需链数，再由报告复核。
- 两者都给：先检查 `scan_cell_count <= chain_count × chain_length`；不满足时阻止生成。
- 两者都没给：不得凭经验写死，保留为待决策项或使用比赛明确提供的默认值。

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
