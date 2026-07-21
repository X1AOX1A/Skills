# 项目进展 — long_log_mining

> 按天记录讨论与决策，最新在最上，一天一个 section。仅在用户明确要求时更新。
> 记录阶段结论、关键决策、踩坑、相关目录和下一步；不维护全局路径清单。

---

## 2026-07-21（日志挖掘正式链路）

### 相关目录

- 本阶段代码与说明：`scripts/log_mine_cx_0720/`
- 本阶段正式产物：`outputs/log_mine_cx_0720/`
- 临时分析与人工审阅材料：`.agent/workspace/07.20/`

必须精确定位的外部参考保留完整路径：

- benchmark：`/apdcephfs_qy4/share_302593112/yixiali/CODES/SimpleLong/`
- 最终提交格式示例：`/apdcephfs_jn3/share_302970870/ponybwcao/online_log/toB/badcase/rl_export/complex_sp_bad_case_20260720.jsonl`
- 判卷模板接入说明：`/apdcephfs_qy4/share_302593112/yixiali/CODES/long_log_mining/.agent/workspace/07.20/T1-omini-0说明.md`

### 阶段结果

- 固定了规则粗筛、两轮 AI 任务筛选、checklist 生成、待评模型推理、checklist 判卷和低分导出的完整链路。
- 六类任务统一要求基于已有输入产生长输出，并具有可逐项检查的约束；短输出、普通计算、翻译和开放写作不纳入。
- 第三轮保留池、checklist、模型推理和判卷均使用 journal 断点续跑，并将影响语义的配置写入 immutable config。

### 关键决策与踩坑

- `finish_reason=length` 即使已有文本也属于截断失败，不能进入下游成功池；改变生成上限时使用独立目录补跑并确定性合并。
- 判卷平台的二值 `final_score` 是权威结果；仅在平台返回 judge 原文时额外校验文本格式和分数一致性。
- 项目内部路径按阶段记到目录级即可；外部 benchmark、格式样例和平台说明必须保留可直接定位的完整路径。

### 下一步

1. 完成剩余判卷并核对成功、失败和 0/1 数量。
2. 导出低分数据并做最终格式验证。

---

## 2026-07-20（pilot 复刻与优化探索）

相关目录：`scripts/strict_mine/`、`scripts/strict_mine_judge/`、`outputs/strict_mine/`、`.agent/workspace/07.19/`。

- 将 pilot 严格召回、回答补全和按任务 judge 流水线整理为可复现代码。
- 确认扩展数据源是提高合格数据量的主要杠杆；负向预筛主要用于降低 judge 成本。
- 原始日志默认只读，空输入或失败运行不得覆盖已有正式产物。
