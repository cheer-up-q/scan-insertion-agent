# Task Parser 静态审查记录（2026-10-19）

- 审查对象：`feature/task-parser` @ `6d66ad39af1f8701e765eed4cfa4caad67c93f6f`
- 审查者：A
- 方式：**仅静态阅读**，未执行 Parser，也未运行 `pytest`
- 结论等级：以下均为静态推演，实际行为以运行结果为准

## 1. 公共接口

与 `docs/task_parser.md` 一致：

| 接口 | 状态 |
| --- | --- |
| `TaskParser.parse(task_spec, limitations=None)` | 存在 |
| `TaskParser.parse_file(task_spec_path, limitations_path=None)` | 存在 |
| `parse_task_spec(task_spec, limitations=None)` | 存在 |
| `parse_file(task_spec_path, limitations_path=None)` | 存在 |
| `to_json(requirement, indent=2)` | 存在 |
| `python -m src.task_parser` | `__main__.py` 存在，但无 CLI 测试 |

未修改 `src/contracts/models.py`，使用公共 `TaskRequirement` / `InternalScanRequirement`
/ `WrapperScanRequirement`，没有私改合同。

## 2. 测试计数（静态）

- `tests/test_task_parser.py`：14 个测试函数，其中 1 个参数化 ×3 = **16** 项。
- `tests/test_task_spec_fixtures.py`：**3** 项。
- `tests/test_contracts.py`：**3** 项。
- 合计 **22** 项，与进展文档自报数字一致；**是否实际通过未验证**。

## 3. 静态发现的边界问题

### 3.1 逗号连接多个要求会污染信号列表

- 位置：`src/task_parser/parser.py:38`
- 原因：`_SENTENCE_RE = r"[。；;\n]+"` 不按逗号切分。
- 输入：`测试时钟为 clk_a，复位信号为 rst_n。`
- 静态推演结果：`test_clocks == ["clk_a", "rst_n"]`。
- 期望：`test_clocks == ["clk_a"]`，`resets == ["rst_n"]`。

### 3.2 Wrapper 显式禁用被 scope / control / strategy 覆盖

- 位置：`src/task_parser/parser.py:334`、`:652`
- 原因：`_WRAPPER_DISABLED_RE` 不包含“不使用”；且 `if scope or control_signals or strategy:
  enabled = True` 在禁用判断之后无条件执行。
- 输入 A：`不使用 Wrapper Scan。`
- 静态推演结果：`enabled == True`（命中 `_WRAPPER_ENABLED_RE` 的“使用”）。
- 输入 B：`不启用 Wrapper Scan。Wrapper 控制信号为 wrp_en。`
- 静态推演结果：`enabled == True`，且不产生矛盾记录。
- 期望：显式禁用优先，`enabled == False`；矛盾写入 `unresolved_requirements`。

### 3.3 否定句仍被当作肯定要求

- 位置：`src/task_parser/parser.py:223`、`:505`
- 输入：`不使用 scan_en 作为扫描使能。`
- 静态推演结果：`scan_enable == "scan_en"`。
- 期望：`scan_enable is None`，或写入未决要求。

### 3.4 “至少/最多 N 条”被当成精确链数

- 位置：`src/task_parser/parser.py:246`、`:515`
- 输入：`至少配置 4 条扫描链。`
- 静态推演结果：`chain_count == 4`，无未决记录。
- 期望：下界/上界不得当成精确值；要么写入 `unresolved_requirements`，要么扩展接口。

### 3.5 非法链数导致未捕获的 Pydantic 校验异常

- 位置：`src/task_parser/parser.py:450`，模型约束 `src/contracts/models.py:50`
  （`chain_count` 为 `gt=0`）。
- 输入：`配置 0 条扫描链。`
- 静态推演结果：`InternalScanRequirement(chain_count=0)` 触发 `ValidationError`，
  异常直接从 `parse()` 泄漏。
- 期望：受控处理——保持 `None` 并写入未决要求，或抛出 Parser 自定义异常。

### 3.6 英文输入静默丢失

- 位置：`src/task_parser/parser.py` 的字段正则与 `unresolved` 判定。
- 输入：`For top module chip_top, configure 8 scan chains. Test clock is test_clk. Scan enable is scan_en.`
- 静态推演结果：`top_design`、`chain_count`、`test_clocks` 均未解析，且没有未决记录；
  `scan_enable` 可能被错误解析为 `"is"`。
- 期望：要么正确解析，要么明确写入 `unresolved_requirements`，不得静默返回空值。

## 4. 未覆盖项

- 没有 CLI 测试（`python -m src.task_parser`）。
- 没有覆盖 `limitations` 中的保护模块、排除实例、reset 极性、`test_mode`。
- 链路：本记录不替代 B 的 `pytest` 输出。
