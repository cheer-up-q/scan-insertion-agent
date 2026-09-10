# Scan Insertion Agent

面向 Scan Insertion 竞赛场景的模块化 Agent 项目。系统读取比赛 case，解析 DFT 约束，驱动官方工具执行，并通过“发现—诊断—修复—验证”闭环产出可审计的结果。

## 当前阶段

- 已建立 Python 项目骨架和公共 Pydantic 数据契约。
- 已建立 DFT 流程、核心概念、输出要求和接口说明文档。
- Agent、Runtime、诊断与修复模块仍在后续分支中实现。

## 目录结构

| 路径 | 说明 |
| --- | --- |
| `src/contracts/` | 全组共享的数据模型与接口契约 |
| `src/task_parser/` | 将自然语言任务要求解析为结构化约束 |
| `src/tool_runner/` | 调用 Scan Insertion 工具并收集结果 |
| `src/diagnosis/` | 根据日志、报告和约束定位问题 |
| `src/repair/` | 生成修复动作并组织复验 |
| `src/audit/` | 保存证据链和决策记录 |
| `docs/` | DFT 知识库和接口说明 |
| `tests/` | 自动化测试 |

## 文档索引

- [`docs/dft_flow.md`](docs/dft_flow.md)：端到端 DFT 工作流和阶段门禁。
- [`docs/dft_concepts.md`](docs/dft_concepts.md)：Scan Insertion 核心概念与诊断要点。
- [`docs/dft_output.md`](docs/dft_output.md)：工具输出、交付物和验收标准。
- [`docs/interfaces.md`](docs/interfaces.md)：模块边界和公共数据模型。

## 本地环境

建议使用 Python 3.10 或更高版本：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest
```

## 分支协作

- `main`：稳定版本。
- `dev`：团队集成分支。
- `feature/dft-flow`：DFT 流程和知识库。
- `feature/agent`：任务解析、诊断和决策逻辑。
- `feature/runtime`：case 加载、工具调用、文件持久化和审计。

功能分支应从最新 `dev` 创建，通过 Pull Request 合并回 `dev`。`src/contracts/` 是公共接口；字段变更需要先由模块负责人确认，并同步更新接口文档和测试。
