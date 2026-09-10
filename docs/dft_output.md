# Scan Insertion 输出与验收规范

版本：0.1.0

本文定义一次工具运行应保存什么，以及最终结果如何判定。实际文件名可由 Runtime 或官方工具调整，但必须通过 `ToolRunResult` 建立稳定映射。

## 1. 输出分层

输出分为三类：

1. 运行证据：命令、配置、日志、状态和耗时；
2. 分析报告：DFT 检查、scan chain、cell、时钟域和 LEC 等报告；
3. 最终交付物：插链网表、最终 dofile、约束及比赛指定文件。

所有最终交付物必须来自同一次通过验收的运行，不得混用不同运行目录中的旧文件。

## 2. 推荐目录结构

```text
runs/
└─ R001/
   ├─ run.dofile
   ├─ run.log
   ├─ metadata.json
   ├─ reports/
   │  ├─ dft_drc.rpt
   │  ├─ scan_chains.rpt
   │  ├─ scan_cells.rpt
   │  ├─ clocks.rpt
   │  └─ lec.rpt
   ├─ deliverables/
   │  ├─ post_scan.v
   │  ├─ final.dofile
   │  └─ constraints.*
   └─ decision_log.json
```

不存在的非必需报告可以省略，但 `reports`/`deliverables` 映射不得指向虚假路径。

## 3. ToolRunResult 映射

```json
{
  "tool_call_id": "R001",
  "exit_status": "completed",
  "log_file": "runs/R001/run.log",
  "reports": {
    "dft_drc": "runs/R001/reports/dft_drc.rpt",
    "scan_chains": "runs/R001/reports/scan_chains.rpt"
  },
  "deliverables": {
    "post_scan_netlist": "runs/R001/deliverables/post_scan.v",
    "final_dofile": "runs/R001/deliverables/final.dofile"
  },
  "errors": [],
  "wall_time_seconds": 42.7
}
```

路径建议相对于项目或 case 工作目录保存。若使用绝对路径，需要保证审计记录迁移后仍能解析或可重映射。

## 4. 运行日志

日志至少应支持定位以下信息：

- 工具名称与版本；
- 开始和结束时间；
- 实际读取的设计、库和配置；
- 关键阶段开始/完成标记；
- error、fatal、abort 和重要 warning；
- 报告及交付物写出位置；
- 退出状态。

日志必须保留原始内容。解析器可以生成摘要，但不得用摘要覆盖原始日志。

## 5. 必需报告及检查点

### 5.1 DFT 规则检查报告

检查：

- 是否存在未解决的 error/violation；
- warning 是否影响任务硬约束；
- 豁免是否有任务依据或明确解释；
- 报告对应插链前还是插链后阶段。

### 5.2 Scan chain 报告

至少提取：

- 实际链数；
- 每条链的长度；
- scan input/output；
- 链所属时钟域与有效边沿；
- lockup cell 的数量与位置；
- 空链、断链或未连接链。

验收不能只比较总链数；还需检查链长分布、跨域策略和任务指定端口。

### 5.3 Scan cell 报告

至少提取：

- 可扫描单元数；
- 已插入/已连接单元数；
- 非扫描单元及排除原因；
- wrapper cells（如启用）的范围和数量。

### 5.4 Clock/constraint 报告

检查任务中的 test clocks、resets 和 scan enable 均已映射到真实对象，极性和边沿与要求一致。

### 5.5 LEC 报告

若任务要求 LEC，则保存完整报告并明确最终结论、未比较点和不等价点。只有工具明确给出等价结论且没有关键未解析项时，才可标记通过。

## 6. 最终交付物

### 6.1 Post-scan netlist

最低检查：

- 文件存在且非空；
- 顶层模块存在；
- 文件可被下游解析；
- scan ports/cells/chains 已实际写入；
- 来源是最终通过运行，而不是先前失败运行。

### 6.2 Final dofile

最低检查：

- 可从干净输入复现最终运行；
- 不包含仅在个人机器有效的硬编码路径；
- 不引用 golden answer 或 hidden case 不可用文件；
- 任务硬约束和输出命令清晰可追踪；
- Task 2 的修复点可以与决策记录对应。

### 6.3 约束及附加文件

只有在任务或工具流程需要时交付。应记录其生成方式、消费者以及是否属于最终验收输入。

## 7. 决策记录

每个问题使用一个 `IssueResolution`。示例：

```json
{
  "issue_id": "ISSUE-001",
  "phenomenon": "实际生成 4 条 scan chain，任务要求 8 条",
  "found": {
    "run_ref": "R001",
    "source": "scan_chains",
    "locator": "summary",
    "excerpt": "Number of chains: 4"
  },
  "diagnosis": {
    "summary": "链数配置未生效",
    "located_object": "internal scan configuration",
    "root_cause": "dofile 未设置任务解析得到的 chain_count",
    "violated_requirement": "internal_scan.chain_count=8"
  },
  "attempts": [
    {
      "fix": {
        "action": "将 internal scan 链数设置为 8",
        "artifact_ref": ["runs/R002/run.dofile"]
      },
      "verify": {
        "run_ref": "R002",
        "source": "scan_chains",
        "resolved": true,
        "locator": "summary",
        "excerpt": "Number of chains: 8"
      }
    }
  ],
  "resolved": true
}
```

`excerpt` 应保持简短，只保留证明结论所需的原文；完整上下文由 `source` 和 `locator` 定位。

## 8. 最终验收清单

| 类别 | 验收项 | 失败条件示例 |
| --- | --- | --- |
| 输入 | 必需输入完整且来自当前 case | 文件缺失、错误顶层、依赖 golden 文件 |
| 执行 | 最终运行正常完成 | `error`、`aborted`、超时 |
| 日志 | 无未解释的 fatal/error | 退出码为零但日志含失败信息 |
| 约束 | 结构化要求全部落实 | 链数、时钟或 wrapper 范围不符 |
| DFT | 必需检查通过 | 未豁免的 violation |
| 结构 | scan chains 完整可用 | 空链、断链、单元遗漏 |
| LEC | 按任务要求通过 | 不等价或关键未比较点 |
| 文件 | 必需交付物存在、非空、可解析 | 文件缺失、陈旧或来自失败运行 |
| 审计 | 关键问题形成完整闭环 | 有修复但无复验证据 |

只有全部强制项通过时，当前运行才能作为最终结果。

## 9. 安全与可复现性

- 不在日志或提交中保存许可证、令牌和其他秘密；
- 不修改比赛提供的受保护工具或输入原件；
- 运行产物默认放在 `.gitignore` 覆盖的目录；
- 最终提交只包含任务要求允许的源码、配置、文档和交付物；
- 任何自动清理动作都不得删除原始输入和最终通过运行的证据。
