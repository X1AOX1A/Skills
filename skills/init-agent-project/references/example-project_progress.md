# 项目进展 — long_log_mining

> 按天 append 的讨论与决策日志。**最新在最上，旧条目不改写；一天不要拆成多个 section。** 由 AI 助手维护，用户明确要求时再更新。
>
> 本文件同时承担**项目上手与常用路径备忘**：开工前先读顶部路径速查和最新日期记录，避免反复询问或输入长路径。接口、schema 和稳定设计后续归 `docs/`；本文件只记阶段进展、结论、决策、踩坑和文件位置。

## 常用路径速查

### 当前项目

```text
仓库根目录
/apdcephfs_qy4/share_302593112/yixiali/CODES/long_log_mining

协作指南
/apdcephfs_qy4/share_302593112/yixiali/CODES/long_log_mining/AGENT.md

本进展文件
/apdcephfs_qy4/share_302593112/yixiali/CODES/long_log_mining/.agent/memory/project_progress.md

临时工作区
/apdcephfs_qy4/share_302593112/yixiali/CODES/long_log_mining/.agent/workspace/<MM.DD>/

Pilot 现状审阅 HTML
/apdcephfs_qy4/share_302593112/yixiali/CODES/long_log_mining/.agent/workspace/07.19/long_output_online_mining_status_report.html
```

### 历史 pilot（当前事实基线，默认只读）

```text
Pilot 根目录
/apdcephfs_qy4/share_302593112/zenanxu/temp/data/long_output_online_mining_pilot_20260717

交接入口
/apdcephfs_qy4/share_302593112/zenanxu/temp/data/long_output_online_mining_pilot_20260717/HANDOFF.md

试挖结论
/apdcephfs_qy4/share_302593112/zenanxu/temp/data/long_output_online_mining_pilot_20260717/ONLINE_MINING_FINDINGS.md

严格候选全集 / 统计 / 预览
/apdcephfs_qy4/share_302593112/zenanxu/temp/data/long_output_online_mining_pilot_20260717/strict_long_output_candidates.jsonl
/apdcephfs_qy4/share_302593112/zenanxu/temp/data/long_output_online_mining_pilot_20260717/strict_long_output_candidates.summary.json
/apdcephfs_qy4/share_302593112/zenanxu/temp/data/long_output_online_mining_pilot_20260717/strict_long_output_candidates.preview.md

人工 QC 样本 / 统计 / 阅读版
/apdcephfs_qy4/share_302593112/zenanxu/temp/data/long_output_online_mining_pilot_20260717/strict_long_output_qc_sample.labeled.jsonl
/apdcephfs_qy4/share_302593112/zenanxu/temp/data/long_output_online_mining_pilot_20260717/strict_long_output_qc_sample.labeled.summary.json
/apdcephfs_qy4/share_302593112/zenanxu/temp/data/long_output_online_mining_pilot_20260717/strict_long_output_qc_sample.labeled.md

固定数量机械审计
/apdcephfs_qy4/share_302593112/zenanxu/temp/data/long_output_online_mining_pilot_20260717/fixed_count_examples.audit.json
```

### 原始数据源

```text
TOC
/apdcephfs_zwfy4/share_302970870/ponybwcao/online_log/filtered/<date>/kept/part-*.sessions.jsonl

本次 pilot 的 TOC 日期目录
/apdcephfs_zwfy4/share_302970870/ponybwcao/online_log/filtered/20260415/kept

TOB
/apdcephfs_jn3/share_302970870/ponybwcao/online_log/toB/finefilter_student_full/instruct_*/kept.jsonl
/apdcephfs_jn3/share_302970870/ponybwcao/online_log/toB/finefilter_student_full/think_*/kept.jsonl
```

---

## 2026-07-19

### 线上长输出日志挖掘 pilot 接手与现状核验

**任务定位**：从 TOC / TOB 真实线上日志中寻找与 SimpleLong long-output eval 接近的数据。目标不是“长输入”或“长回答”本身，而是模型必须在长输出过程中持续执行可核验规则，例如批量筛选、排序、逐项计算、保真复制、固定数量生成、连续编号、JSON/schema、长度/前后缀、覆盖/漏项/重复/顺序和正确停止。

**三类标签口径**：

- `direct`：输入、规则和目标输出关系封闭，可逐项、逐字符或按明确算法机械复核。
- `adjacent`：内容有开放生成或语义裁量，但数量、格式、编号、结构、边界等客观约束可检查；剩余部分需要 semantic judge。
- `not_target`：普通长文章/报告/代码/小说/方案/改写，或输入很长但最终只需短结论；也包括只设计方法却未实际处理完整数据的任务。

**核心原则**：`direct` 与 `adjacent` 分池建设、分开统计。程序能判定的数量、解析、schema、长度、编号、前后缀、禁用字符、覆盖和停止位置，不交给 LLM 猜。

### Pilot 扫描范围与结果

- TOC：从 `20260415/kept` 的 256 个分片中等距抽 16 个，完整扫描。
- TOB：从 instruct / think 的 295 个可用文件中等距抽 8 个，每文件最多读前 5,000 行。
- 总扫描 **322,074 行**，其中 **287,205 行**记录到可见 assistant 回答。
- 第一版宽召回共命中 21,390 次；每文件限流后保留 6,958 条，再平衡选出 TOC 100 + TOB 100 的 Top 200 用于浏览误召和任务形态。
- 第二版严格启发式召回 **1,379 行**：TOC 562、TOB 817；对应 **1,378 个唯一 ID**。
- 严格候选 tier：`direct_eval_like=497`、`direct_eval_like_with_open_content=810`、`adjacent_format_heavy=72`。这些是正则召回标签，不是真实人工类别。
- 能力族命中：逐项计算 614、条件筛选 508、排序重排 178、保真转换 49、精确重复 44、嵌套 schema 30；一条候选可以命中多个 family。

### 人工 QC

从启发式 `direct_eval_like`、有回答且回答不少于 2,000 字符的候选中，按 6 个能力族和固定随机种子 `20260717` 分层抽样。原计划每族 6 条；实际 verbatim transform 只有 4 条、nested schema 只有 2 条，因此最终为 **30 条**而非 36 条。

人工标签结果：

- `direct`：2 条。
- `adjacent`：6 条。
- `not_target`：22 条。

这 30 条是 family-stratified sample，不是线上自然分布样本，**不能把 8/30 当成严格召回的总体 precision**。QC 样本全部来自 TOC，尚未覆盖 TOB 的误召结构。

### 已确认的代表任务与机械审计

- `a61dd891-e4dd-4da3-bae3-4e0221d586dd`：给定候选数字列表和 10 条封闭条件，要求完整筛选；属于 `direct`，可逐项复算。
- `20b0e9c6-801c-4f0f-96f5-3ad7a4c8831b`：只替换 SQL 中的中文标点，其余内容不得变化；属于 `direct`，可做字符级 diff。
- `872c9ee8-925b-419b-b6f5-c6c3b80497a5`：要求生成 200 条用户指令；实际 200 条，编号 1–200 连续，数量维度通过。
- `302f7600-2fe4-460b-a0c1-eff2e5fff856`：要求 50 个 JSON 问答对象；JSON 可解析，但实际只有 10 个对象。
- `bf3d65fb-30be-4aec-bdbf-f6e81cce7c1f`：要求 50 条、每条 90–100 字并固定结尾；数量和结尾通过，但 50 条长度全部失败，实际 56–83 字。
- `6727e8b0-99fa-4d73-ac03-340a7432baa5`：要求 20 个对象、qid 从 21 开始；实际 qid 为 101–120，且 JSON 存在非法转义。
- `27c0c059-c570-49ad-b823-daf02cd689a6`：要求 20 个对象、qid 从 122 开始；实际为 142–161，且 JSON 缺分隔符。
- `5b81064f-35b7-4300-ad3c-a653b9b94635`：要求 600 条问答；检测到 1,132 个完整表格数据行，最后一行中途截断，属于没有在要求边界正确停止。

### 现有脚本各自做什么

- `mine_long_output_candidates.py`：第一版宽召回。找最后一条 user 任务，用较宽的关键词、显式数量和回答长度打分；每文件最多保留 300 条，再输出平衡 Top 200。用于探索，不是 gold 生成器。
- `mine_strict_long_output_candidates.py`：第二版严格召回。增加最终问题标记截取、更窄的“动作—对象”组合正则、生成数量和格式约束，并输出 tier / family / score。
- `build_stratified_qc_sample.py`：从严格候选按 family 固定种子抽样，并避免同一 ID 被多个 family 重复选中。
- `label_stratified_qc_sample.py`：把首轮 30 条人工标签和理由硬编码到源码，再导出 labeled JSONL / Markdown / summary；是一次性固化脚本，不是通用标注工具。
- `audit_fixed_count_examples.py`：对 6 个固定 ID 编写专用审计分支，检查数量、编号、JSON、qid、长度、固定结尾和截断；已证明 checker 路线有效，但目前不是通用 checker。

脚本完整路径均位于：

```text
/apdcephfs_qy4/share_302593112/zenanxu/temp/data/long_output_online_mining_pilot_20260717/
```

### 关键发现与踩坑（后续分析必须记住）

1. **回答长度不是目标类别的充分条件。** 长报告、长代码、小说和普通改写会占据高分候选的大多数。
2. **输入长度更不是充分条件。** TOB/RAG 常见知识库很长，但最终问题只要求一句答案。
3. **不能在整段 prompt 上匹配关键词。** 检索文档里的“筛选、排序、计算”会产生大量误召，必须先定位最终用户问题。
4. **数字必须绑定输出动作。** “生成 50 条”有效；“96 维向量”“500 章设定”不能据此判为固定数量长输出。
5. **自然日志更偏 adjacent。** 固定数量、编号、长度、结尾和 JSON 格式比大规模封闭计算、UUID 原样复制、稳定排序更常见。
6. **保留通过样本。** 线上既有明确 bad case，也有数量和编号完全满足的回答，适合构建正负对照。
7. **严格候选存在重复业务 ID。** `2c5696cf-e31b-42aa-ac1e-9435e237e67e` 在同一 TOC 源文件第 1117、1120 行各出现一次；稳定键不能只依赖 `cid/req_id`，回查时要同时看 source file 与 row ID。
8. **TOB 当前只有任务、没有可审计回答。** 严格候选中 TOC 562 条全部有回答，TOB 817 条全部未提取到回答；现有 30 条 QC 因此全是 TOC。不能把 TOB 候选直接并入回答质量分析。
9. **严格扫描脚本缺少空输入保护。** 第一版脚本会检查抽到的 TOC/TOB 文件数，严格版不会。2026-07-19 审阅时两个原始数据根目录均不可访问，此时直接运行严格脚本可能把已有候选、summary 和 preview 覆盖成空结果。
10. **当前没有通用 checker。** `fixed_count_examples.audit.json` 是 6 个手工 case 的验证产物；不能把它理解为已经具备自动抽取任意任务约束的能力。

### 当前阶段判断

Pilot 已经完成“方向是否可行”的验证：真实线上日志里确实存在适合长输出规则遵循评测的任务，并且数量、编号、解析、长度和停止边界能够发现不依赖模型裁判的明确错误。

当前仍是**候选分类边界与 checker 原型阶段**，尚未形成可规模化生产的 eval 数据流水线。严格召回中的 `direct_eval_like` 只是启发式命中，不等同于人工 `direct`；TOB 回答提取、来源覆盖、标注规模、通用 checker、运行 provenance 和防覆盖护栏均未形成正式产物。因此现有 1,379 条只能视为候选池，不能视为 gold 或可直接发布的评测集。

