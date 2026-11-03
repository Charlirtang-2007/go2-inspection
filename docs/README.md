# 文档入口

> 这是 `docs/` 的导航页。项目概览、快速开始、FAQ 见仓库根目录的 `README.md`。
> 最后更新：2026-11-03
> 负责人：Charlirtang

## 你是哪类读者？

- **不写代码、想快速了解项目现在到哪了** → 进 [`for-non-technical/README.md`](for-non-technical/README.md)
- **要接手开发、排查问题、跑起来** → 先进 [`handover/checklist.md`](handover/checklist.md)，再看 [`architecture/overview.md`](architecture/overview.md)

## 目录导航

### 非技术层（L1）

| 文件 | 内容 |
| :--- | :--- |
| [`for-non-technical/README.md`](for-non-technical/README.md) | 一页看懂项目是什么、现在到哪了 |
| [`for-non-technical/progress-brief.md`](for-non-technical/progress-brief.md) | 阶段进度简报（人话版） |
| [`for-non-technical/demo-plan.md`](for-non-technical/demo-plan.md) | 演示流程与时间节点 |
| [`for-non-technical/what-we-need.md`](for-non-technical/what-we-need.md) | 需要非技术队友配合的事 |
| [`for-non-technical/risks-brief.md`](for-non-technical/risks-brief.md) | 风险与依赖（人话版） |

### 技术层（L2 / L3）

| 文件 | 内容 |
| :--- | :--- |
| [`architecture/overview.md`](architecture/overview.md) | 四级解耦架构、数据流、失败边界 |
| [`architecture/tech-stack.md`](architecture/tech-stack.md) | 版本锁定、选型理由、被否方案 |
| [`architecture/adr/`](architecture/adr/) | 架构决策记录（ADR） |
| [`environment/k2b-setup.md`](environment/k2b-setup.md) | K2B 从烧录到 systemd 的可复现步骤 |
| [`environment/ai-machine-setup.md`](environment/ai-machine-setup.md) | AI机台 `.env` 字段、venv、启动顺序 |
| [`status/progress.md`](status/progress.md) | 当前冲刺项、完成度、阻塞项 |
| [`status/open-questions.md`](status/open-questions.md) | 未决问题与思考方向 |
| [`issues/index.md`](issues/index.md) | 问题索引：现象 → 状态 → 链接 |
| [`references/literature.md`](references/literature.md) | 目标文献，带访问日期 |
| [`references/resources.md`](references/resources.md) | 数据集、模型、比赛资料 |
| [`handover/checklist.md`](handover/checklist.md) | 接手验收清单 |

## 维护规则

1. **事实只在技术层写一次**，非技术层只做翻译和引用，不重复事实。
2. **非技术层禁止出现**协议名、命令、版本号、代码路径。
3. 每份文档头部保留 `最后更新` 和 `对应技术源`，过期时读者能自己判断。
4. 纯技术 commit **不碰** `for-non-technical/`；只有影响进度、演示、需求、风险的变化才同步 L1。
