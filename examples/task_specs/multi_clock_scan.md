对顶层模块 multi_clk_top 执行 Scan Insertion。

测试时钟包括 clk_a 和 clk_b。
复位信号为 rst_n。
Scan Enable 为 scan_en。

配置 4 条内部扫描链。

扫描设计包含 clk_a 和 clk_b 两个 Clock Domain。
跨时钟域 Scan Chain 需要插入 Lockup。

需要生成 Post-scan Netlist 和 Scan Report。