# GitHub 远端状态快照（2026-10-19）

- 核查者：A
- 核查时间：2026-10-19 15:50–16:04 (+08:00)
- 核查方式：GitHub 网页 HTML、`raw.githubusercontent.com`、匿名 `git ls-remote`
  （显式禁用 credential helper）、`git clone --mirror`、`pull/4.diff` 与
  `pull/4.patch`。未使用 token，未修改仓库。
- 未执行项：本次核查**没有运行 pytest**。所有“测试通过”均为文档自报，
  未经独立执行验证。

## 1. PR #4 事实

| 字段 | 值 |
| --- | --- |
| 标题 | `test: validate task specification fixtures against TaskRequirement contract` |
| 作者 | `cheer-up-q` |
| 状态 | **Merged** |
| 创建 | 2026-10-18T08:55:28Z = 2026-10-18 16:55:28 +08:00 |
| 合并 | 2026-10-18T08:55:44Z = 2026-10-18 16:55:44 +08:00 |
| base / head | `dev` / `feature/task-parser` |
| 合并时 head SHA | `e6ab0648001654b343194d84c9cbf949b195bdc8` |
| 合并提交 | `de3bb756a88515c07b615611ac47a81970f8c5ba` |
| 草稿 / 冲突 | 否 / 无（已成功合并） |
| 提交数 / 变更文件 | 1 / 1（`tests/test_task_spec_fixtures.py`，+71） |
| 审查 | No reviews |
| CI / checks | 仓库无 `.github/`，未配置 CI，页面无 checks |

结论：

1. PR #4 只包含 A 的 fixture 测试，未包含 B 的 Parser 实现。
2. 该测试只校验 `*.expected.json` 与 `TaskRequirement` 模型一致，不 import
   `TaskParser`，因此不能证明 Parser 行为正确。
3. PR #4 已合入 `dev`；B 的 Parser 提交全部发生在合并之后，未进入该 PR。

## 2. 分支（截至核查时刻）

| 分支 | 最新 SHA | 最新提交时间 (+08) | 标题 |
| --- | --- | --- | --- |
| `main` | `9a874a20b4e730a22ed6baebd6752dcca026a427` | 2026-09-08 14:55:16 | chore: initialize project |
| `dev` | `de3bb756a88515c07b615611ac47a81970f8c5ba` | 2026-10-18 16:55:43 | Merge pull request #4 |
| `feature/task-parser` | `6d66ad39af1f8701e765eed4cfa4caad67c93f6f` | 2026-10-19 11:36:42 | Add unit tests for TaskParser functionality |
| `feature/agent` | `9a874a20b4e730a22ed6baebd6752dcca026a427` | 2026-09-08 14:55:16 | chore: initialize project |
| `feature/runtime` | `9a874a20b4e730a22ed6baebd6752dcca026a427` | 2026-09-08 14:55:16 | chore: initialize project |
| `feature/dft-flow` | `d1f238cb452fd0d31adb4e8b67c88f97e9dc381e` | 2026-09-10 16:05:03 | docs: add DFT workflow knowledge base |
| `feature/dofile-mapping` | `250d8e87286e173f0223f2aa7488db4d105a8679` | 2026-09-11 17:00:21 | docs: add DFTEXP dofile action mappings |
| `feature/requirement-mapping` | `e4d17235388c0112d5bd1765baf71eacf6c92f9e` | 2026-09-20 15:40:40 | test: add task parser acceptance cases |

提交关系：

- `merge-base(dev, feature/task-parser)` = `e6ab064`。
- `dev...feature/task-parser` = **1 ahead / 11 behind**（dev 独有为合并提交）。
- `feature/task-parser` 领先 `main` 20 个提交；`dev` 领先 `main` 10 个。
- `feature/agent` 与 `feature/runtime` 指向初始提交，树中只有 `README.md`，
  **不包含** 2026-10-14 的项目骨架。

## 3. `dev` 是否包含 Parser 交付文件

| 文件 | `dev` 状态 |
| --- | --- |
| `src/task_parser/parser.py` | 不存在 |
| `src/task_parser/__init__.py` | 存在，0 字节 |
| `src/task_parser/__main__.py` | 不存在 |
| `tests/test_task_parser.py` | 不存在 |
| `docs/task_parser.md` | 不存在 |
| `tests/test_task_spec_fixtures.py` | 存在（PR #4） |

## 4. PR 列表

`refs/pull/` 只有 1–4，且全部已由 `dev` 的合并提交证实：

| # | 状态 | 合并提交 |
| --- | --- | --- |
| 1 | Merged | `8cdef58` |
| 2 | Merged | `a631566` |
| 3 | Merged | `9dc5107` |
| 4 | Merged | `de3bb75` |

没有开放的 PR。

## 5. 未核查事项

- B 的测试是否实际通过、运行环境版本、是否存在未推送的本地修改。
- `src/audit/` 之外的 Runtime 设计文档（当前无实现）。
