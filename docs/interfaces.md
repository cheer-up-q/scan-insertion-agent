\# Scan Insertion Agent Core Interfaces



Version: 0.1.0



\## CaseInput

Owner: C / Runtime



作用：

读取一个比赛case的输入目录，并向其它模块提供统一输入信息。



\## TaskRequirement

Owner: B / Agent



作用：

把task\_spec.md中的自然语言插链要求转换为结构化DFT要求。



\## ToolRunResult

Owner: C / Runtime



作用：

描述一次真实Scan Insertion工具调用的执行结果。



\## IssueResolution

Owner:

B负责决策内容；

C负责持久化和审计记录。



要求形成：



found -> diagnosis -> fix -> verify



闭环。



\## Interface Change Rule



src/contracts/属于全组公共接口。



A、B、C任何人需要修改字段时，

必须先经过队长确认，不允许个人直接修改接口协议。

