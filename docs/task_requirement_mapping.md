# Task Requirement Mapping Specification

Version: 0.1.0

Owner: A / DFT Flow

## 1. Purpose

本文件定义 `task_spec.md` 中自然语言 DFT 要求到 `TaskRequirement` 数据结构之间的标准映射关系。

目标：

```text
Natural Language
        ↓
DFT Semantic
        ↓
TaskRequirement
```

要求 Agent 对 `task_spec.md` 中的自然语言描述进行标准化解析，输出与 `src/contracts/models.py` 中 `TaskRequirement` 一致的数据结构。

本规范不负责生成 Dofile。

Dofile 的具体动作映射由 `docs/dofile_mapping.md` 定义。

---

## 2. General Mapping Rules

### 2.1 Explicit Requirement First

任务说明中明确给出的参数，应直接映射到对应字段。

例如：

用户描述：

```text
配置 8 条内部扫描链。
```

映射：

```json
{
  "internal_scan": {
    "chain_count": 8
  }
}
```

### 2.2 No Unsupported Guessing

`task_spec.md` 中没有明确给出的参数，不得由 Agent 或 LLM 自行编造。

例如：

任务未指定 Scan Chain 数量时，应保持对应字段为空。

映射：

```json
{
  "internal_scan": {
    "chain_count": null
  }
}
```

不得自行设置为：

```json
{
  "internal_scan": {
    "chain_count": 8
  }
}
```

规则：

- 如果任务说明中完全没有提到某个参数，对应字段应保持 `null`、空列表或默认值。
- 不得为了让配置“看起来完整”而人为补全参数。
- 不得仅根据常见经验、典型设计规模或字段名称，自行推断任务未明确要求的数值。
- 如果某个参数必须通过后续网表分析、工具手册检索或工具运行才能确定，当前阶段不应直接赋值。

该规则用于避免 LLM 在缺乏依据的情况下生成错误的 DFT 配置，从而影响后续 Dofile 生成和工具执行结果。

### 2.3 Ambiguous Requirements

当 `task_spec.md` 中的自然语言存在歧义时，Agent 不得强制选择某一种解释。

此时应保持对应字段为空，并将无法确定的要求记录到：

```text
unresolved_requirements
```

例如：

用户描述：

```text
适当控制扫描链长度。
```

该描述虽然提到了 Scan Chain Length，但没有给出明确数值，也没有说明这里的“长度”表示固定长度、目标长度还是最大允许长度。

映射：

```json
{
  "internal_scan": {
    "chain_length": null
  },
  "unresolved_requirements": [
    "Scan chain length requirement is ambiguous."
  ]
}
```

规则：

- 如果任务完全没有提及某个字段，对应字段保持 `null`、空列表或默认值。
- 如果任务已经提到某项要求，但语义不明确，对应字段保持 `null`，同时加入 `unresolved_requirements`。
- 如果一句自然语言存在多个合理解释，Agent 不得自行选择其中一个解释作为最终结果。
- 如果当前 `TaskRequirement` 数据结构无法准确表达某项要求，不得私自增加字段，应先记录到 `unresolved_requirements`，后续再决定是否升级公共接口。
- 禁止 Agent 为了补全配置而自行猜测参数。

该规则用于保证存在歧义的需求能够被显式暴露，而不是被 LLM 隐式转换成错误的 DFT 配置。

### 2.4 Evidence Priority

当多个信息来源同时提供同一项 DFT 参数时，Agent 应按照固定的证据规则进行判断。

信息来源包括：

1. `task_spec.md` 中明确给出的任务目标；
2. `limitations.md` 中明确给出的限制条件和禁止事项；
3. Pre-scan Netlist 分析得到的设计事实；
4. 官方 Scan Insertion 工具手册中的规则或约束；
5. Agent 自身的推理结果。

其中：

- `task_spec.md` 用于定义任务目标；
- `limitations.md` 用于定义执行边界和硬约束；
- 两者均属于高优先级输入；
- 当两者发生冲突时，不得让其中一方自动覆盖另一方，应记录到 `unresolved_requirements` 并交给后续诊断流程处理；
- Pre-scan Netlist 用于确认模块、端口、Clock、Reset 等对象是否真实存在；
- 官方工具手册用于确认命令、参数含义、使用条件和工具约束；
- Agent 推理仅用于补充分析和形成候选解释，不得覆盖已有明确证据。

例如：

`task_spec.md` 中明确写明：

```text
Scan Enable 为 scan_en
```

即使 Agent 在网表中发现另一个名为 `test_en` 的信号，并认为它更像测试使能信号，也不得直接将 `scan_enable` 修改为 `test_en`。

正确映射应保持：

```json
{
  "scan_enable": "scan_en"
}
```

如果 `limitations.md` 中进一步规定：

```text
禁止修改 scan_en 信号定义
```

则该限制同样必须被保留，后续 Agent 不得通过修改网表或 Dofile 的方式将其替换为其它信号。

如果 `task_spec.md` 要求：

```text
Scan Enable 为 scan_en
```

但 `limitations.md` 又明确写明：

```text
禁止使用 scan_en 作为测试控制信号
```

则不能直接生成最终配置。

应记录：

```json
{
  "scan_enable": "scan_en",
  "unresolved_requirements": [
    "Conflict detected between task_spec.md and limitations.md for scan_enable."
  ]
}
```

该规则用于保证 Agent 的判断过程可追溯、可解释，并避免 LLM 根据自身经验覆盖比赛输入中已经明确给出的任务要求。

---

## 3. Top Design Mapping

### 3.1 Semantic

Top Design 表示执行 Scan Insertion 的顶层设计模块。

对应字段：

```text
TaskRequirement.top_design
```

### 3.2 Typical Expressions

`task_spec.md` 中可能出现以下表达：

- 顶层模块为 `chip_top`
- 对 `chip_top` 执行 Scan Insertion
- Top Design 为 `chip_top`
- 设计顶层使用 `chip_top`
- 对模块 `soc_top` 完成扫描链插入

以上表达均表示需要确定执行 Scan Insertion 的顶层设计模块。

### 3.3 Example

用户描述：

```text
对顶层模块 chip_top 执行 Scan Insertion。
```

映射：

```json
{
  "top_design": "chip_top"
}
```

### 3.4 Rules

- `top_design` 必须来自明确的任务描述或设计输入。
- 必须保留模块名称原始大小写。
- 不得自行修改模块名称。
- 不得自行增加模块名前缀或后缀。
- 不得由 Agent 构造一个任务中不存在的顶层模块名称。
- 如果 `task_spec.md` 明确指定顶层模块，但该模块在 Pre-scan Netlist 中无法找到，不得自动替换为其它模块，应交由后续诊断流程处理。
- 如果任务要求对当前设计执行 Scan Insertion，但没有明确给出顶层模块名称，并且需要通过网表分析才能确定，则当前解析阶段不得自行猜测。

例如：

用户描述：

```text
对当前设计执行 Scan Insertion。
```

如果当前阶段无法确定顶层模块名称，则映射为：

```json
{
  "top_design": null,
  "unresolved_requirements": [
    "Top design must be determined from design analysis."
  ]
}
```

---

## 4. Test Clock Mapping

### 4.1 Semantic

Test Clock 表示 Scan Insertion 和扫描测试过程中使用的测试时钟信号。

对应字段：

```text
TaskRequirement.test_clocks
```

`test_clocks` 为列表，因此允许存在一个或多个测试时钟。

### 4.2 Typical Expressions

`task_spec.md` 中可能出现以下表达：

- 测试时钟为 `test_clk`
- Scan Clock 使用 `scan_clk`
- 使用 `test_clk` 作为测试时钟
- 测试时钟包括 `clk_a` 和 `clk_b`
- `clk_a`、`clk_b` 均作为 Scan Clock

以上表达均需要映射到：

```text
TaskRequirement.test_clocks
```

### 4.3 Single Clock Example

用户描述：

```text
测试时钟为 test_clk。
```

映射：

```json
{
  "test_clocks": [
    "test_clk"
  ]
}
```

### 4.4 Multiple Clock Example

用户描述：

```text
测试时钟为 clk_a 和 clk_b。
```

映射：

```json
{
  "test_clocks": [
    "clk_a",
    "clk_b"
  ]
}
```

### 4.5 Rules

- Test Clock 名称必须保持输入中的原始名称。
- 不得仅因为某个信号名称包含 `clk` 或 `clock`，就直接将其认定为测试时钟。
- `task_spec.md` 明确指定测试时钟时，应优先保留该要求。
- 如果任务指定多个测试时钟，应全部保存到 `test_clocks`。
- 多个时钟原则上按照任务描述中的出现顺序保存。
- 如果任务没有指定 Test Clock，而必须通过 Pre-scan Netlist 分析才能确定，则不得由 Agent 随意选择一个功能时钟。

例如：

如果任务明确要求必须使用设计中的测试时钟，但没有给出具体信号名称，可以记录：

```json
{
  "test_clocks": [],
  "unresolved_requirements": [
    "Test clock must be determined from design analysis."
  ]
}
```

---

## 5. Reset Mapping

### 5.1 Semantic

Reset 表示 Scan Insertion 流程中涉及的复位控制信号。

对应字段：

```text
TaskRequirement.resets
```

`resets` 为列表，因此允许存在一个或多个复位信号。

### 5.2 Typical Expressions

`task_spec.md` 中可能出现以下表达：

- 复位信号为 `rst_n`
- Reset 使用 `reset_n`
- 使用 `rst` 作为复位控制
- `rst_n` 和 `por_n` 均作为复位信号

以上表达均需要映射到：

```text
TaskRequirement.resets
```

### 5.3 Single Reset Example

用户描述：

```text
复位信号为 rst_n。
```

映射：

```json
{
  "resets": [
    "rst_n"
  ]
}
```

### 5.4 Multiple Reset Example

用户描述：

```text
复位信号包括 rst_n 和 por_n。
```

映射：

```json
{
  "resets": [
    "rst_n",
    "por_n"
  ]
}
```

### 5.5 Rules

- Reset 信号名称必须保持输入中的原始名称。
- 不得仅因为某个信号名称包含 `rst` 或 `reset`，就直接将其认定为 DFT Reset。
- 如果 `task_spec.md` 明确给出 Reset，应直接映射。
- 如果存在多个 Reset，应全部记录。
- 如果任务没有指定 Reset，不得为了补全配置而自行创建 `rst_n`、`reset_n` 等信号。
- 当前 `TaskRequirement` 主要记录 Reset 信号名称。
- 如果后续官方任务要求表达 Reset 极性、同步方式等更多属性，而当前接口无法表示，应提出公共接口升级建议，不得由个人模块私自增加字段。

例如：

任务没有提及 Reset 时，可以保持：

```json
{
  "resets": []
}
```

如果任务明确要求使用设计中的 Reset，但没有说明具体信号，则记录：

```json
{
  "resets": [],
  "unresolved_requirements": [
    "Reset signal must be identified from the design."
  ]
}
```

---

## 6. Scan Enable Mapping

### 6.1 Semantic

Scan Enable 用于控制功能模式与 Scan Shift 模式之间的切换。

对应字段：

```text
TaskRequirement.scan_enable
```

### 6.2 Typical Expressions

`task_spec.md` 中可能出现以下表达：

- Scan Enable 为 `scan_en`
- 扫描使能信号为 `SE`
- 使用 `scan_enable` 控制扫描模式
- `scan_en` 作为扫描使能信号
- 测试模式下使用 `scan_mode` 作为 Scan Enable

### 6.3 Example

用户描述：

```text
Scan Enable 使用 scan_en。
```

映射：

```json
{
  "scan_enable": "scan_en"
}
```

### 6.4 Rules

- Scan Enable 名称必须保持任务输入中的原始名称。
- 不得自行将 `scan_en` 改写为 `SE`、`scan_enable` 或其它名称。
- 任务没有明确指定 Scan Enable 时，不得自行创建 `scan_en`、`SE` 等信号。
- 如果 `task_spec.md` 明确指定 Scan Enable，但该信号在 Pre-scan Netlist 中不存在，应保留原任务要求并交由后续诊断流程处理。
- 不得因为 `test_mode`、`scan_mode` 等信号名称看起来相似，就直接替换用户明确指定的 Scan Enable。

例如：

任务要求：

```text
使用设计中的扫描使能信号。
```

但没有提供具体名称时：

```json
{
  "scan_enable": null,
  "unresolved_requirements": [
    "Scan enable signal must be identified from the design."
  ]
}
```

---

## 7. Scan Chain Count Mapping

### 7.1 Semantic

Scan Chain Count 表示 Internal Scan 中需要建立的扫描链数量。

对应字段：

```text
TaskRequirement.internal_scan.chain_count
```

### 7.2 Typical Expressions

`task_spec.md` 中可能出现以下表达：

- 配置 8 条扫描链
- 建立 8 条 Internal Scan Chain
- 扫描链数量设置为 16
- 使用 4 条内部扫描链
- Internal Scan Chain 数量为 32

### 7.3 Example

用户描述：

```text
配置 8 条内部扫描链。
```

映射：

```json
{
  "internal_scan": {
    "chain_count": 8
  }
}
```

### 7.4 Rules

- `chain_count` 必须为正整数。
- `task_spec.md` 明确指定数量时，应直接保存该值。
- 不得根据设计规模、寄存器数量或常见经验自行改变任务明确给出的 Chain Count。
- 如果任务没有指定扫描链数量，应保持 `null`。
- 如果任务只是使用“尽量少”“合理数量”等模糊描述，则不得自行选择一个具体数值。

例如：

用户描述：

```text
尽量减少 Scan Chain 数量。
```

映射：

```json
{
  "internal_scan": {
    "chain_count": null
  },
  "unresolved_requirements": [
    "Scan chain count is not explicitly specified."
  ]
}
```

---

## 8. Scan Chain Length Mapping

### 8.1 Semantic

Scan Chain Length 表示 Internal Scan 中扫描链长度相关要求。

对应字段：

```text
TaskRequirement.internal_scan.chain_length
```

### 8.2 Typical Expressions

`task_spec.md` 中可能出现以下表达：

- Scan Chain 长度设置为 100
- 每条扫描链长度为 200
- 扫描链最大长度不超过 200
- 尽量保证各条扫描链长度均衡

### 8.3 Exact Length Example

用户描述：

```text
每条 Scan Chain 长度设置为 100。
```

如果该任务语义明确表示固定长度，则可映射为：

```json
{
  "internal_scan": {
    "chain_length": 100
  }
}
```

### 8.4 Semantic Risk

当前公共接口中的：

```text
internal_scan.chain_length
```

只能保存一个整数。

但是实际自然语言中的 Scan Chain Length 可能存在不同语义：

1. 固定长度
2. 目标长度
3. 最大允许长度
4. 推荐长度
5. 链长度均衡要求

因此不能简单地将所有出现的长度数字都直接写入 `chain_length`。

### 8.5 Ambiguous Example

用户描述：

```text
每条 Scan Chain 最大长度不能超过 200。
```

当前 `chain_length` 字段无法明确区分“固定长度”和“最大长度”。

因此当前阶段建议记录：

```json
{
  "internal_scan": {
    "chain_length": null
  },
  "unresolved_requirements": [
    "Maximum scan chain length constraint cannot be represented unambiguously by the current chain_length field."
  ]
}
```

### 8.6 Balance Requirement Example

用户描述：

```text
各条 Scan Chain 长度应尽量均衡。
```

该要求不能直接转换成一个具体整数。

应记录：

```json
{
  "internal_scan": {
    "chain_length": null
  },
  "unresolved_requirements": [
    "Scan chain balancing requirement requires later configuration or tool analysis."
  ]
}
```

### 8.7 Rules

- 只有任务语义明确表示具体链长度时，才允许直接设置 `chain_length`。
- “最大长度”“最小长度”“目标长度”“均衡长度”等不同含义不得强制归一成同一个数值。
- 当当前接口无法准确表达要求时，应写入 `unresolved_requirements`。
- 不得私自在 Agent 模块中新增 `max_chain_length` 等字段。
- 如果 Public Case 或官方任务证明该类约束为必要字段，应按照公共接口修改流程升级 `src/contracts/models.py`。

### 8.8 Contract Extension Candidate

后续如果确认需要更加精确地表达 Scan Chain Length，可以考虑公共接口增加类似：

```text
chain_target_length
chain_max_length
chain_min_length
balance_required
```

但这些字段当前仅作为接口升级候选，不属于 v0.1.0 正式接口。

---

## 9. Clock Domain Mapping

### 9.1 Semantic

Clock Domain 表示 Scan Chain 所涉及的时钟域信息。

对应字段：

```text
TaskRequirement.internal_scan.clock_domains
```

### 9.2 Typical Expressions

`task_spec.md` 中可能出现：

- 设计包含 `clk_a` 和 `clk_b` 两个扫描时钟域
- `clk_a` 与 `clk_b` 分别建立扫描链
- Scan Chain 按 Clock Domain 划分
- 不同时钟域禁止混链

### 9.3 Domain Identification Example

用户描述：

```text
Scan 设计涉及 clk_a 和 clk_b 两个 Clock Domain。
```

映射：

```json
{
  "internal_scan": {
    "clock_domains": [
      "clk_a",
      "clk_b"
    ]
  }
}
```

### 9.4 Rules

- `clock_domains` 保存任务明确涉及的时钟域标识。
- 必须保持时钟名称原始形式。
- 不得仅根据网表中所有 Clock 自动构造 `clock_domains`。
- 如果任务指定多个 Clock Domain，应全部记录。
- 当前 `clock_domains` 字段主要表达“有哪些时钟域”，不能完整表达复杂的混链或分组策略。

例如：

用户描述：

```text
clk_a 和 clk_b 禁止混合在同一条 Scan Chain 中。
```

仅记录：

```json
{
  "internal_scan": {
    "clock_domains": [
      "clk_a",
      "clk_b"
    ]
  },
  "unresolved_requirements": [
    "Clock-domain chain separation policy requires additional configuration semantics."
  ]
}
```

如果后续官方任务要求表达“是否允许混链”“每个 Domain 的 Chain Count”等信息，应考虑公共接口升级。

---

## 10. Edge Strategy Mapping

### 10.1 Semantic

Edge Strategy 表示 Scan Chain 对时钟触发边沿的要求。

对应字段：

```text
TaskRequirement.internal_scan.edge_strategy
```

### 10.2 Standard Values

当前规范建议统一使用：

```text
rising
falling
mixed
```

任务未明确指定时保持：

```text
null
```

### 10.3 Rising Edge Example

用户描述：

```text
所有扫描链使用上升沿触发。
```

映射：

```json
{
  "internal_scan": {
    "edge_strategy": "rising"
  }
}
```

### 10.4 Falling Edge Example

用户描述：

```text
Scan Chain 使用下降沿。
```

映射：

```json
{
  "internal_scan": {
    "edge_strategy": "falling"
  }
}
```

### 10.5 Mixed Edge Example

用户明确要求同时使用不同触发边沿时，可以映射为：

```json
{
  "internal_scan": {
    "edge_strategy": "mixed"
  }
}
```

### 10.6 Rules

- 不得自行将未指定的 Edge Strategy 设置为 `rising`。
- 不得因为功能寄存器采用某一边沿，就直接推断 Scan Chain 必须采用同样边沿。
- 如果任务要求复杂的 Domain-specific Edge Policy，而当前单一字符串字段无法表达，应加入 `unresolved_requirements`。

---

## 11. Lockup Mapping

### 11.1 Semantic

Lockup 表示 Scan Chain 中是否需要 Lockup 结构以及对应策略。

对应字段：

```text
TaskRequirement.internal_scan.lockup_required
TaskRequirement.internal_scan.lockup_strategy
```

### 11.2 Required Example

用户描述：

```text
跨时钟域 Scan Chain 需要插入 Lockup。
```

映射：

```json
{
  "internal_scan": {
    "lockup_required": true
  }
}
```

### 11.3 Disabled Example

用户明确要求：

```text
不允许插入 Lockup Cell。
```

映射：

```json
{
  "internal_scan": {
    "lockup_required": false
  }
}
```

### 11.4 Strategy Example

如果 `task_spec.md` 明确指定 Lockup Strategy，则可记录：

```json
{
  "internal_scan": {
    "lockup_required": true,
    "lockup_strategy": "specified_strategy"
  }
}
```

其中实际策略名称必须保留任务或工具规范中的原始语义。

### 11.5 Rules

- 只有明确要求时，才直接设置 `lockup_required`。
- 如果任务未提及 Lockup，不能默认设置为 `true` 或 `false`。
- 如果是否需要 Lockup 必须通过 Clock Domain、Edge、时序或工具分析才能判断，应保持 `null`。
- 不得仅根据“多时钟域”这一事实就直接认定必须插入 Lockup。
- 如果任务中的 Lockup Strategy 无法由当前字段准确表达，应加入 `unresolved_requirements`。

---

## 12. Wrapper Scan Mapping

### 12.1 Semantic

Wrapper Scan 表示是否启用 Wrapper 结构，以及 Wrapper 的作用范围和控制信号。

对应字段：

```text
TaskRequirement.wrapper_scan.enabled
TaskRequirement.wrapper_scan.scope
TaskRequirement.wrapper_scan.control_signals
TaskRequirement.wrapper_scan.wrapper_cell_strategy
```

### 12.2 Enable Example

用户描述：

```text
启用 Wrapper Scan。
```

映射：

```json
{
  "wrapper_scan": {
    "enabled": true
  }
}
```

### 12.3 Scope Example

用户描述：

```text
对 core0 和 core1 启用 Wrapper Scan。
```

映射：

```json
{
  "wrapper_scan": {
    "enabled": true,
    "scope": [
      "core0",
      "core1"
    ]
  }
}
```

### 12.4 Control Signal Example

用户描述：

```text
Wrapper 控制信号为 wrapper_en。
```

映射：

```json
{
  "wrapper_scan": {
    "enabled": true,
    "control_signals": [
      "wrapper_en"
    ]
  }
}
```

### 12.5 Rules

- `enabled` 表示任务是否明确启用 Wrapper Scan。
- `scope` 用于保存任务明确指定的 Wrapper 作用范围。
- `control_signals` 用于保存任务明确指定的 Wrapper 控制信号。
- `wrapper_cell_strategy` 只有在任务或工具规范明确给出策略时才赋值。
- 不得根据模块名称或 IO 数量自行决定 Wrapper Scope。
- 如果任务要求 Wrapper Scan，但具体范围需要设计分析确定，应将该要求记录到 `unresolved_requirements`。

例如：

```json
{
  "wrapper_scan": {
    "enabled": true,
    "scope": []
  },
  "unresolved_requirements": [
    "Wrapper scope must be determined from design analysis."
  ]
}
```

---

## 13. Output Requirement Mapping

### 13.1 Semantic

Output Requirements 表示任务要求最终生成的交付文件或报告。

对应字段：

```text
TaskRequirement.output_requirements
```

### 13.2 Standard Names

为了避免不同 Agent 产生不同命名，当前规范统一使用以下标准值：

```text
post_scan_netlist
ctl
scandef
scan_report
dft_report
wrapper_report
```

### 13.3 Example

用户描述：

```text
需要生成 Post-scan Netlist、CTL 和 SCANDEF。
```

映射：

```json
{
  "output_requirements": [
    "post_scan_netlist",
    "ctl",
    "scandef"
  ]
}
```

### 13.4 Rules

- 输出名称必须转换为统一的标准值。
- 不得混用 `PostScan`、`post_scan`、`Post Scan Netlist` 等多种内部表示。
- `task_spec.md` 明确要求的输出必须全部保留。
- 如果任务未明确列出某类报告，不得仅为了补全列表而自行添加。
- Runtime 最终真实输出目录仍应遵循比赛规定，`output_requirements` 主要用于表示任务需求。

---

## 14. Unresolved Requirements

### 14.1 Semantic

`unresolved_requirements` 用于保存当前解析阶段无法安全确定的任务要求。

对应字段：

```text
TaskRequirement.unresolved_requirements
```

### 14.2 When to Use

以下情况应写入 `unresolved_requirements`：

1. 自然语言存在明显歧义；
2. `task_spec.md` 与 `limitations.md` 等高优先级输入存在冲突；
3. 当前 `TaskRequirement` 数据结构无法准确表达某项要求；
4. 必须读取 Pre-scan Netlist 后才能确定；
5. 必须检索官方工具手册后才能确定；
6. 必须通过工具运行结果才能进一步判断；
7. 任务给出了定性要求，但没有提供足够的定量信息。

### 14.3 Ambiguous Example

用户描述：

```text
扫描链长度应合理。
```

映射：

```json
{
  "internal_scan": {
    "chain_length": null
  },
  "unresolved_requirements": [
    "Scan chain length is not explicitly specified."
  ]
}
```

### 14.4 Conflict Example

如果：

```text
task_spec.md:
Scan Enable 为 scan_en
```

但：

```text
limitations.md:
禁止使用 scan_en 作为测试控制信号
```

则：

```json
{
  "scan_enable": "scan_en",
  "unresolved_requirements": [
    "Conflict detected between task_spec.md and limitations.md for scan_enable."
  ]
}
```

### 14.5 Rules

- `unresolved_requirements` 不是普通日志字段，而是任务理解阶段的重要输出。
- 不得为了减少 unresolved 数量而强行猜测。
- 后续 Agent 可以通过网表分析、手册检索、工具执行或诊断流程尝试解决这些问题。
- 当问题得到可靠证据确认后，Agent 才可以更新对应 `TaskRequirement` 字段。

---

## 15. Requirement Mapping Summary

下表给出常见自然语言要求到 `TaskRequirement` 字段之间的标准映射关系。

| Natural Language Requirement | DFT Semantic | TaskRequirement Field | Example Value |
|---|---|---|---|
| 顶层模块为 chip_top | Top Design | `top_design` | `"chip_top"` |
| 测试时钟为 test_clk | Test Clock | `test_clocks` | `["test_clk"]` |
| 测试时钟为 clk_a、clk_b | Multiple Test Clocks | `test_clocks` | `["clk_a","clk_b"]` |
| 复位信号为 rst_n | Reset | `resets` | `["rst_n"]` |
| Scan Enable 为 SE | Scan Enable | `scan_enable` | `"SE"` |
| 配置 8 条内部扫描链 | Chain Count | `internal_scan.chain_count` | `8` |
| Scan Chain 长度为 100 | Chain Length | `internal_scan.chain_length` | `100` |
| 涉及 clk_a、clk_b 两个时钟域 | Clock Domain | `internal_scan.clock_domains` | `["clk_a","clk_b"]` |
| 使用上升沿 | Edge Strategy | `internal_scan.edge_strategy` | `"rising"` |
| 使用下降沿 | Edge Strategy | `internal_scan.edge_strategy` | `"falling"` |
| 需要 Lockup | Lockup | `internal_scan.lockup_required` | `true` |
| 不允许 Lockup | Lockup | `internal_scan.lockup_required` | `false` |
| 启用 Wrapper Scan | Wrapper Enable | `wrapper_scan.enabled` | `true` |
| Wrapper 范围为 core0 | Wrapper Scope | `wrapper_scan.scope` | `["core0"]` |
| Wrapper 控制信号为 wrapper_en | Wrapper Control | `wrapper_scan.control_signals` | `["wrapper_en"]` |
| 输出 Post-scan Netlist | Output | `output_requirements` | `"post_scan_netlist"` |
| 输出 CTL | Output | `output_requirements` | `"ctl"` |
| 输出 SCANDEF | Output | `output_requirements` | `"scandef"` |
| 输出 Scan Report | Output | `output_requirements` | `"scan_report"` |
| 输出 Wrapper Report | Output | `output_requirements` | `"wrapper_report"` |

---

## 16. Handoff to Agent Module

本规范由：

```text
A / DFT Flow
```

负责维护。

B / Agent 应基于本规范实现以下转换：

```text
task_spec.md
      ↓
Natural Language Parsing
      ↓
DFT Semantic Identification
      ↓
TaskRequirement
```

Agent 的 Task Parser 必须遵守以下原则：

1. 明确要求优先；
2. 不猜测未提供参数；
3. 歧义要求写入 `unresolved_requirements`；
4. 保持设计对象原始名称；
5. 输出字段必须符合 `src/contracts/models.py`；
6. 不得私自创建新的 `TaskRequirement` 字段；
7. 不得绕过 `TaskRequirement` 直接从自然语言生成最终 Dofile；
8. 对于无法由 Task Parser 确定的问题，应交给后续网表分析、Manual Retrieval、Diagnosis 或 Tool Execution 阶段继续处理。

推荐的数据流如下：

```text
task_spec.md
      ↓
Task Parser
      ↓
TaskRequirement
      ↓
Agent Planner
      ↓
DFT / Dofile Mapping
      ↓
Tool Runner
      ↓
ToolRunResult
```

### 16.1 Acceptance Requirement

B / Agent 后续开发 Task Parser 时，应至少能够验证：

- 明确参数能够正确解析；
- 未提供参数不会被自行补全；
- 多个 Clock / Reset 能够解析为列表；
- DFT 标准字段名称保持统一；
- 歧义要求能够进入 `unresolved_requirements`；
- 输出结果能够被 `TaskRequirement` 模型正常实例化。

---

## 17. Version

Specification Version:

```text
v0.1.0
```

Owner:

```text
A / DFT Flow
```

Status:

```text
Draft for Agent Integration
```

当前版本用于第一阶段 Agent Task Parser 开发和 A/B 模块接口联调。

如果后续发现：

- 官方任务要求现有接口无法表达；
- Public Case 出现新的 DFT Requirement 类型；
- Dofile Mapping 需要更多结构化字段；

则应先提出 Contract Change Proposal，经过团队确认后修改：

```text
src/contracts/models.py
```

并同步升级本规范版本。

禁止个人模块在未更新公共接口的情况下自行扩展字段。
