# v7：80 MHz DELAY 0 与 v6 AREA 0 对比

**结论：本轮 DELAY 0 的 setup 时序和面积均退化，不推荐替代 v6 的 AREA 0。**

实验已完成，GDS 和 TinyTapeout precheck 通过；RTL 回归通过；门级功能回归失败。九角评估显示 TT/FF setup 通过、三个 SS setup 失败，九角 hold 均通过。

## 实验来源与可比性

- v6 来源提交：`dae89331466486dab23fe0605b45c979ee50ef03`；导入后的完整目录树 SHA 为 `bed996911aaa2ec462782405bcb8f5468eb54add`，与 v6 相同。
- v7 实验提交：`411552acfb124ca4a9dec3f6768957c3cc51fceb`。
- RTL SHA256：`E070E8658952FF7314BFD6CE7E69E035233953CCCED5E57FA44714AE7D9F2FE2`；提交、RTL 仿真快照和 GDS 提交产物中的源文件字节完全一致。
- 芯片实现配置只改 `SYNTH_STRATEGY: AREA 0 → DELAY 0`；80 MHz、12.5 ns、2.5 ns IO、4×2、密度和 hold 修复参数保持一致。
- 固定 LibreLane 3.0.14、GDS action 395eedb、支持工具 01d5d28、GF180MCU D PDK 54435919；完整版本与约束见 `build_lock.json`。
- 30 项最终解析配置、源文件哈希、工具与 PDK 版本检查通过；提交产物 metrics 与评估产物 metrics 完全一致，归档 SHA256 与 GitHub 返回值一致。
- precheck 使用所固定 action 自带的检查 PDK e8daeda，与原 v6 precheck 的设置一致；实现及门级模型使用 54435919。

## 主要指标

| 指标 | v6 AREA 0 | v7 DELAY 0 | 变化 |
|---|---:|---:|---:|
| 最差 setup slack | −7.933554 ns | −9.887542 ns | 恶化 1.953987 ns |
| 最小 hold slack | +0.038824 ns | +0.506420 ns | 改善 0.467596 ns |
| 标准单元面积 | 314418 µm² | 323709 µm² | +9291 µm²（+2.955%） |
| 标准单元数 | 10407 | 10806 | +399 |
| setup 违规计数（九角累计） | 3880 | 6694 | +2814 |
| hold 违规计数（九角累计） | 0 | 0 | 0 |
| 最多 slew 违规 | 68 | 236 | +168 |
| 最多 capacitance 违规 | 1 | 2 | +1 |
| 每角 fanout 违规 | 103 | 105 | +2 |

九角累计的违规计数不是去重后的寄存器或唯一物理路径数。同一端点可在不同角重复计数。

## 九角 setup / hold

| Corner | AREA setup ns | DELAY setup ns | setup 变化 ns | AREA hold ns | DELAY hold ns | DELAY setup 违规 |
|---|---:|---:|---:|---:|---:|---:|
| nom_tt_025C_3v30 | 2.442409 | 1.413715 | -1.028694 | 1.108759 | 1.096075 | 0 |
| nom_ss_125C_3v00 | -7.547740 | -9.028725 | -1.480984 | 0.109247 | 1.522937 | 2232 |
| nom_ff_n40C_3v60 | 6.142608 | 5.579961 | -0.562648 | 0.506290 | 0.508075 | 0 |
| min_tt_025C_3v30 | 2.607089 | 1.797474 | -0.809615 | 1.103794 | 1.092067 | 0 |
| min_ss_125C_3v00 | -7.257013 | -8.317113 | -1.060100 | 0.168146 | 1.607401 | 2229 |
| min_ff_n40C_3v60 | 6.202996 | 5.636527 | -0.566469 | 0.505164 | 0.506420 | 0 |
| max_tt_025C_3v30 | 2.165281 | 0.956841 | -1.208440 | 1.096322 | 1.100884 | 0 |
| max_ss_125C_3v00 | -7.933554 | -9.887542 | -1.953987 | 0.038824 | 1.420161 | 2233 |
| max_ff_n40C_3v60 | 6.069330 | 5.508842 | -0.560488 | 0.507669 | 0.509340 | 0 |

九个角的 setup slack 全部下降。最差 TT 余量从 +2.165281 ns 降至 +0.956841 ns；三个 SS 角的最差值为 −9.887542 ns。

## 最差峰值路径

- AREA 0：`sample_magnitude[2] → peak_second_position[5]`；数据段延迟 18.876020 ns。
- DELAY 0：`sample_valid → peak_first[4]`；数据段延迟 21.150382 ns。
- 数据段延迟按 launch CLK 引脚到数据到达时刻计算，包含 CLK-to-Q、组合单元及连线；两轮的最差起终点不同，应结合完整路径阅读。

## 功能与物理验证

- RTL：PASS，460637 个周期，真实 level 0/1/5；level 23：PASS，25166114 个周期、三个真实采样、无强制内部状态。
- GDS：PASS；4×2 尺寸内完成路由。Magic DRC、LVS、路由 DRC、天线违规计数均为 0。
- TinyTapeout precheck：PASS。
- 门级功能：FAIL，未使用 SDF。第一复位边沿通过，在第32周期（400 ns）首次面积输出阶段，`uo_out` 含 X，cocotb 无法转为整数。正式失败结果未放宽或屏蔽。
- X 的具体来源尚未完全定位。本机 Icarus 在编译完整网表时崩溃，未取得可支持根因结论的本地复现；门级 X 对实际硬件行为的影响仍需单独验证。
- 九角评估：FAIL，三个 SS setup 角失败且仍有电气违规；全部 hold 通过。

## 建议

保留 v7 作为此次 DELAY 0 实验记录。下一轮 RTL 优化建议继续用 AREA 0，以 v6 的稳定功能基线先做分频位宽精简，再优化峰值比较与选择结构。本轮结果不支持把默认综合策略直接换成 DELAY 0。

## 可核验的原始证据

- [v7 GDS、precheck、门级与九角检查](https://github.com/BarryLee911/tt-gf-ucl-project-v7/actions/runs/37654327507)
- [v7 RTL 和 level23](https://github.com/BarryLee911/tt-gf-ucl-project-v7/actions/runs/37654327470)
- [v6 原基线构建](https://github.com/BarryLee911/tt-gf-ucl-project-v6/actions/runs/35853433128)
- [v6 固定基线复跑](https://github.com/BarryLee911/tt-gf-ucl-project-v6/actions/runs/37642992390)
- `v7-delay0-results.json` 保存机器可读指标、九角数据、工作流结论及产物 SHA256。
- 本地归档包括 GDS_logs、九角评估、tt_submission、RTL 测试和正式门级失败产物；GDS_logs 内保留完整实现步骤日志和原始报告。

源码和指标的来源记录保留原实验提交 411552a；结果文档及寄存器名显示修正另行提交，不改变该实验的 RTL、配置或物理产物。
