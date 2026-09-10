# Scan Insertion 核心概念

版本：0.1.0

本文提供 Agent 解析要求、诊断日志和判断输出时需要的最小 DFT 语义。具体命令和规则名称以比赛指定工具版本为准。

## 1. Scan Insertion

Scan Insertion 将设计中的部分或全部普通触发器替换或连接为可串行移位的 scan cells。测试模式下，测试数据经 scan input 移入，在功能时钟作用下捕获，再从 scan output 移出，从而提高内部状态的可控性与可观测性。

典型链路：

```text
scan_in → scan cell 0 → scan cell 1 → ... → scan cell N → scan_out
```

功能模式下，scan cell 应保持普通时序单元的功能行为；测试模式由 scan enable 控制进入移位路径。

## 2. Scan Chain

Scan chain 是串联的 scan cells 集合。常见约束包括：

- `chain_count`：期望链数；
- `chain_length`：目标或最大链长；
- 链的输入/输出端口；
- 是否允许跨时钟域或跨边沿混合；
- 链长平衡策略。

链数增加通常能缩短移位时间，但会增加 scan I/O、布线和控制成本。若任务同时给出链数与链长，应检查两者能否覆盖可扫描单元总数，不能把其中一个静默忽略。

## 3. Test Clock 与 Clock Domain

Test clock 是测试模式下驱动 scan shift/capture 的时钟。Clock domain 通常由时钟源、频率关系、边沿和控制条件共同决定。

诊断时需要确认：

- 任务声明的时钟都能映射到设计对象；
- 时钟极性和有效边沿正确；
- 工具是否允许不同时钟域进入同一条链；
- 跨域连接是否需要 lockup cell；
- generated/gated clock 是否已正确建模。

“端口名称存在”不等于“测试时钟约束正确”。

## 4. Scan Enable

Scan enable 在功能路径和移位路径之间切换。常见问题包括：

- 信号不存在或层级路径错误；
- 有效电平配置相反；
- 信号在部分层级不可控；
- 测试模式下被其他逻辑遮蔽；
- 配置中重复或冲突声明。

验收时要结合插链网表或报告确认 scan enable 实际控制了预期 scan cells。

## 5. Reset 与 Set

异步 reset/set 可能在测试模式下阻止移位或捕获。工具需要知道这些信号的类型、极性以及测试时的约束方式。

不得为了消除违规而无依据地关闭 reset 检查。应先判断是约束缺失、极性错误、不可控，还是设计本身需要 test override。

## 6. DFT Rule Check

DFT rule check 用于在插链前后识别影响可测试性的结构。常见类别包括：

- 不可控时钟、复位或 set；
- 非扫描时序单元；
- 组合环路；
- clock-as-data 或 data-as-clock；
- 多时钟/多边沿链的潜在竞态；
- 黑盒、未解析引用或缺失库模型；
- scan chain 连接不完整。

报告中的 warning 不应一律视为失败，也不能一律忽略。必须结合任务限制、工具说明和最终结构判断其影响，并为豁免保存证据。

## 7. Lockup Cell

Lockup cell 常用于缓解 scan shift 时跨时钟域、跨边沿或大时钟偏斜引起的保持时间风险。它通常放在潜在危险的链段之间。

判断是否需要 lockup 时，应结合：

- 是否允许 clock mixing；
- 相邻 scan cells 的有效边沿；
- 时钟域关系及偏斜；
- 任务是否明确要求或禁止；
- 工具报告的插入位置与数量。

不能仅以“插入了 lockup”判断正确，还要验证位置和链连接。

## 8. Edge Strategy

Edge strategy 描述 scan cells 的排序是否考虑上升沿/下降沿。例如把同边沿单元分组，或在边沿切换处使用 lockup。

需要区分：

- 功能捕获边沿；
- scan shift 使用的有效边沿；
- 工具对 falling-edge scan cell 的排序规则。

边沿理解错误可能导致 shift hold violation 或链结构与要求不符。

## 9. Wrapper Scan

Wrapper scan 在模块或 core 边界增加 wrapper cells，用于控制输入、观测输出以及隔离 core。它与 internal scan 的作用范围不同：

- internal scan 面向 core 内部时序状态；
- wrapper scan 面向 core 边界和层级测试访问。

解析 wrapper 要求时至少明确：目标 scope、控制信号、输入/输出端口范围和 wrapper cell 策略。任务未要求 wrapper scan 时，不应自动启用。

## 10. Pre-scan 与 Post-scan Netlist

- pre-scan netlist：插链前的设计，是主要输入。
- post-scan netlist：插链后的实现，是关键交付物。

两者的功能模式应保持等价。新增 scan cells、scan ports、test mux 和 lockup cells 属于预期测试结构变化，但不应破坏正常功能逻辑。

## 11. LEC

LEC（Logic Equivalence Check）用于检查转换前后设计在规定模式下是否逻辑等价。Scan Insertion 场景通常关注功能模式等价，需要正确约束测试端口和 scan enable。

LEC 失败时优先检查：

- 比较点和顶层是否正确；
- 库与宏模型是否一致；
- 测试模式信号是否固定到功能值；
- 未映射点是否来自预期的 scan 结构；
- dofile 修改是否改变了功能逻辑。

## 12. ATPG 与覆盖率

ATPG（Automatic Test Pattern Generation）利用 scan 结构生成测试向量，并给出 fault coverage。若比赛阶段只要求 Scan Insertion，ATPG 结果可能不是强制交付物，但 scan chain 可用性会直接影响后续 ATPG。

覆盖率不能替代结构验收：高覆盖率不代表链数、wrapper 范围或指定输出均符合任务要求。

## 13. 常见诊断映射

| 现象 | 优先检查 |
| --- | --- |
| 找不到设计或顶层 | 读取顺序、顶层名、库和未解析引用 |
| test clock 不可控 | 时钟声明、层级路径、gating 和测试覆盖信号 |
| reset/set violation | 极性、异步控制、测试模式约束 |
| scan cells 数量为零 | 可扫描单元识别、排除规则、插链命令是否执行 |
| 实际链数不符 | 链数/链长约束、domain 分组、工具自动调整 |
| 跨域 shift 风险 | clock mixing、edge strategy、lockup 配置 |
| wrapper 未覆盖目标 | scope、端口筛选、wrapper cell 策略 |
| 工具成功但无网表 | 写出命令、输出路径、前序阶段是否真正完成 |
| LEC 不等价 | 测试信号约束、库模型、功能逻辑意外变化 |

这些映射只用于确定排查顺序，最终根因必须由当前运行的日志、报告和设计对象共同证明。
