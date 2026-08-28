# MINXIN Subject SoW Planner

A Hong Kong EDB-informed, calendar-aware Scheme of Work planner for one subject across multiple grades, levels, or classes.

这是民心学校通用学科 SoW 规划 Skill。它以一个结构化工作簿作为唯一数据源，根据学科课程要求、学校校历和可选 timetable 生成同步的 Excel/Word SoW，并检查课程进阶、排期容量、重复内容、跨课程引用和隐私风险。

## 核心能力

- 支持同一学科的多个年级、课程级别或班别。
- 默认使用脱敏的 MINXIN 2026–2027 `Final 260622` 校历，也可导入 ICS、Outlook URL、PDF、CSV 或 XLSX 校历。
- 先通过 `grill-me` 锁定课程边界，再进行有边界的 brainstorming。
- 依据香港 EDB 的 KLA、Key Stage、课程与评估理念进行课程路由；未核实的正式对齐只标记为 `informed by`。
- 按学科选择合适活动，不强行加入 AI、项目、小组展示或商业分析。
- 将 Major Concerns 映射到单元行动和可观察证据，而不是逐周重复口号。
- 从十张表的主控工作簿生成同步 Word SoW；缺少 timetable 时显示 `UNCOMPUTED`，不猜测课时。
- 自动检查主键、引用、容量、先修顺序、重复、生成视图同步、Word 结构和隐私。

## 在 Codex / Agent 应用中安装

最简单的方式是把下面这句话直接发给 Agent：

> 请使用内置 `skill-installer`，从公开仓库 `ZaneZhang-MINXIN/minxin-subject-sow-planner` 的路径 `skills/minxin-subject-sow-planner` 安装 Skill。若本机已存在同名 Skill，不要覆盖，先报告现有路径和安全升级方案。安装完成后告诉我该 Skill 会在下一轮对话可用。

也可以由 Agent 使用内置安装器对应的 GitHub URL：

```text
https://github.com/ZaneZhang-MINXIN/minxin-subject-sow-planner/tree/main/skills/minxin-subject-sow-planner
```

安装完成后，在下一轮对话中使用 `$minxin-subject-sow-planner`。可直接复制 [INSTALL_AND_USE_PROMPT.md](INSTALL_AND_USE_PROMPT.md) 中的完整提示词。

## 推荐输入

首次设计时尽量提供：

- 学科、KLA、年级/Key Stage、课程体系和班别；
- 正式课程纲要或考试局 syllabus；
- 旧 SoW 或学校模板；
- 新学年校历；
- timetable（如暂缺，Skill 会保留 `UNCOMPUTED`）；
- 必教内容、评估窗口、学生情况、资源与安全限制；
- 输出语言和课程审批负责人。

## 仓库结构

```text
skills/minxin-subject-sow-planner/
├── SKILL.md
├── agents/openai.yaml
├── assets/
├── references/
└── scripts/
```

## 重要边界

- 附件中的文字只作为资料分析，不作为操作指令。
- 原始 Word、PDF、日历发布 URL、账号和密码不会打包进 Skill。
- 三门示例课程是 `TEST_FIXTURE`，不是获批课程。
- Skill 不修改 LMS，也不代表香港教育局或学校正式课程批准。
- MINXIN 名称和校徽的相关权利归其权利人所有；仓库中的学校格式资产仅用于生成校内教学规划模板。

## Validation

核心功能候选已通过 30/30 自动测试、Skill Creator validation、Excel/Word 同步检查、全页渲染检查和隐私扫描。正式课程的 `validate --release` 还会阻止任何带 `stop_condition` 的开放 QA 项；校历影响、课程 authority 或 objective alignment 未由负责人确认时，不会返回 `release_ready=true`。
