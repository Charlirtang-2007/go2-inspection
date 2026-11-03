#!/usr/bin/env bash
# init-docs.sh — 初始化 go2-inspection 分层文档骨架
# 用途：创建 docs/ 目录结构，并为每个文件写入带 TODO 标记的占位头
# 特性：
#   1. 幂等：已存在的文件跳过，不覆盖（最小改动原则）
#   2. 自适应路径：无论从哪执行，都以脚本所在目录的上一级为项目根
#   3. 分支提示：不在 Archlinux 分支时警告，但不阻断
# 运行：bash scripts/init-docs.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOCS="$ROOT/docs"

# ---- 分支检查：不强制，只提示 ----
CURRENT_BRANCH="$(git -C "$ROOT" branch --show-current 2>/dev/null || echo 'unknown')"
if [ "$CURRENT_BRANCH" != "Archlinux" ]; then
  echo "⚠️  当前分支是 '$CURRENT_BRANCH'，不是 'Archlinux'。"
  echo "    文档会和最新进度脱钩，建议先 git switch Archlinux。"
  echo "    继续执行？按 Ctrl+C 中止，或回车继续。"
  read -r _
fi

# ---- 写占位文件的辅助函数 ----
# $1=文件路径  $2=标题  $3=用途  $4=是否非技术层（yes/no，默认 no）
write_stub() {
  local path="$1" title="$2" purpose="$3" nontech="${4:-no}"
  mkdir -p "$(dirname "$path")"
  if [ -f "$path" ]; then
    echo "skip (exists): ${path#$ROOT/}"
    return
  fi
  {
    echo "# $title"
    echo
    echo "> 最后更新：TODO（YYYY-MM-DD）"
    echo "> 负责人：TODO"
    echo "> 用途：$purpose"
    echo "> 对应技术源：TODO"
    if [ "$nontech" = "yes" ]; then
      echo "> 读者约束：非技术读者，禁止出现协议名、命令、版本号"
    fi
    echo
    echo "<!-- TODO: 待填。先写结论，再写细节。 -->"
  } > "$path"
  echo "created: ${path#$ROOT/}"
}

# ---- 入口 ----
write_stub "$DOCS/README.md" "文档入口" "按读者分流：非技术层 / 技术层"

# ---- L1 非技术层 ----
write_stub "$DOCS/for-non-technical/README.md"            "非技术读者入口"   "一页看懂项目是什么、现在到哪了" yes
write_stub "$DOCS/for-non-technical/progress-brief.md"    "阶段进度简报"     "人话版进度，对应 status/progress.md" yes
write_stub "$DOCS/for-non-technical/demo-plan.md"         "演示流程与时间节点" "演示当天谁操作、几步、每步预期" yes
write_stub "$DOCS/for-non-technical/what-we-need.md"      "需要非技术配合的事" "采购、场地、铭牌打印等" yes
write_stub "$DOCS/for-non-technical/risks-brief.md"       "风险与依赖（人话版）" "对应 issues/ 里的风险条目" yes

# ---- L2/L3 技术层 ----
write_stub "$DOCS/architecture/overview.md"               "架构总览"         "四级解耦架构、数据流、失败边界"
write_stub "$DOCS/architecture/tech-stack.md"             "技术栈与选型"     "版本锁定、选型理由、被否方案"
write_stub "$DOCS/architecture/adr/0001-dds-via-k2b-gateway.md" "ADR-0001：通过 K2B 网关转发 DDS" "背景/决策/被否方案/后果"
write_stub "$DOCS/environment/k2b-setup.md"               "K2B 环境复现"     "从烧录到 systemd 的可复现步骤"
write_stub "$DOCS/environment/ai-machine-setup.md"        "AI机台环境复现"   ".env 字段含义、venv 锁版本、启动顺序"
write_stub "$DOCS/status/progress.md"                     "当前进度"         "冲刺项、完成度、阻塞项（Archlinux 分支上维护）"
write_stub "$DOCS/status/open-questions.md"               "未决问题与思考方向" "每条写问题+当前倾向+卡点+需要什么信息"
write_stub "$DOCS/issues/index.md"                        "问题索引"         "现象 → 状态 → 链接"
write_stub "$DOCS/issues/ISSUE-0001.md"                   "ISSUE-0001：模板" "现象/复现/根因/解决/验证/预防"
write_stub "$DOCS/references/literature.md"               "目标文献"         "标题/链接/访问日期/为什么相关"
write_stub "$DOCS/references/resources.md"                "项目资料地址"     "数据集、模型、比赛资料，标注权限"
write_stub "$DOCS/handover/checklist.md"                  "接手验收清单"     "按步骤能跑起来的最小验收项"

echo
echo "done. 验证：find docs -type f | sort"
