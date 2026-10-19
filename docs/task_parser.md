# Task Parser (B / Agent)

Version: 0.1.0

Owner: B / Agent

## 1. Purpose

`src/task_parser` 将 `task_spec.md` 中的自然语言 DFT 要求转换为
`src/contracts/models.py` 中的 `TaskRequirement`。

实现遵循 `docs/task_requirement_mapping.md`：

- 明确给出的参数直接映射；
- 未给出的参数保持 `null`、空列表或模型默认值，不做猜测；
- 歧义、冲突或当前接口无法表达的要求写入
  `unresolved_requirements`；
- 设计对象名称保持输入中的原始大小写。

解析器是确定性的规则实现，不调用 LLM，因此同一输入总是得到同一输出，
每个字段都可以追溯到任务描述中的明确表达。

## 2. Public Interface

模块：`src.task_parser`

### 2.1 Class

```python
from src.task_parser import TaskParser

parser = TaskParser()
requirement = parser.parse(task_spec_text)
```

输入：

- `task_spec: str`：`task_spec.md` 的文本内容；
- `limitations: str | None`：可选的 `limitations.md` 文本内容。

输出：

- `TaskRequirement`：已经通过 Pydantic 校验的模型实例。

### 2.2 Convenience Functions

```python
from src.task_parser import parse_file, parse_task_spec

requirement = parse_task_spec(task_spec_text)
requirement = parse_file("examples/task_specs/basic_internal_scan.md")
```

### 2.3 File Parsing with Limitations

```python
requirement = TaskParser().parse_file(
    "input/task_spec.md",
    limitations_path="input/limitations.md",
)
```

当 `limitations.md` 明确禁止使用 `task_spec.md` 指定的信号时，解析器保留
`task_spec.md` 的值，并在 `unresolved_requirements` 中记录冲突，例如：

```text
Conflict detected between task_spec.md and limitations.md for scan_enable.
```

仅限制“修改信号定义”的描述（例如 `禁止修改 scan_en 信号定义`）不会被判定为
使用冲突。

## 3. Command Line

```bash
python -m src.task_parser examples/task_specs/basic_internal_scan.md
```

带限制条件：

```bash
python -m src.task_parser input/task_spec.md --limitations input/limitations.md
```

命令输出为 UTF-8 JSON，可直接与 `*.expected.json` 比较。

## 4. Supported Requirements

| Task requirement | TaskRequirement field |
| --- | --- |
| 顶层模块 | `top_design` |
| 单个/多个测试时钟 | `test_clocks` |
| 单个/多个复位信号 | `resets` |
| Scan Enable | `scan_enable` |
| 内部扫描链数量 | `internal_scan.chain_count` |
| 明确的扫描链长度 | `internal_scan.chain_length` |
| 时钟域 | `internal_scan.clock_domains` |
| 上升沿/下降沿/混合边沿 | `internal_scan.edge_strategy` |
| Lockup 要求与策略 | `internal_scan.lockup_required` / `lockup_strategy` |
| Wrapper 启用、范围、控制信号、策略 | `wrapper_scan.*` |
| 输出产物 | `output_requirements` |
| 歧义或冲突要求 | `unresolved_requirements` |

输出产物统一使用以下标准值：

```text
post_scan_netlist
ctl
scandef
scan_report
dft_report
wrapper_report
```

## 5. Ambiguity Handling

以下情况不会写入具体数值，而是记录到
`unresolved_requirements`：

- 只给出“尽量少”“合理数量”等定性描述；
- 只给出“最大长度”“目标长度”“均衡长度”等无法由单一
  `chain_length` 字段表达的约束；
- 任务提到某项要求但没有给出具体对象名称；
- `task_spec.md` 与 `limitations.md` 存在明确冲突；
- 需要读取网表或工具手册后才能确定的参数。

例如：

```python
requirement = TaskParser().parse("每条 Scan Chain 最大长度不能超过 200。")
assert requirement.internal_scan.chain_length is None
```

## 6. Tests

```bash
pytest tests/test_task_parser.py
```

测试覆盖：

- 三组标准样例的逐字段比对；
- 未提供参数不被补全；
- 多时钟、多复位列表及顺序；
- 歧义链数量和链长度；
- Wrapper 控制信号与范围；
- 输出产物标准化与顺序；
- `limitations.md` 冲突检测；
- 文本解析与文件解析结果一致。
