---
name: deep-company-series
description: 为 $ARGUMENTS 撰写一个 8 篇深度长文系列，发布在公众号/视频号等公开渠道。**核心 IP 不是"会写"，而是"会改"——99% 的财经文章在违反本 skill 的事实核查标准**。
---

# 深度公司系列：8 篇长文拆一家公司

本 Codex skill 是 `skills/deep-company-series.md` 的轻量包装层。`skills/deep-company-series.md` 是 Claude Code 与 Codex 共同使用的单一事实来源。

## 执行要求

1. 在执行本 skill 时，先阅读仓库根目录的 `AGENTS.md`。
2. 完整阅读 `skills/deep-company-series.md`，并按其中的流程、输出格式、数据纪律执行。
3. 用户在 Codex 中可显式输入 `$deep-company-series` 触发；在 Claude Code 中继续使用 `/deep-company-series`。
4. 如原始 skill 提到 Claude Code 专用工具名，按 Codex 当前会话可用工具进行等价替换：
   - `Task` / `Agent` / `Team`：优先使用 Codex subagent、并行代理或当前会话中的等价多代理能力；没有可用能力时，在当前会话内分阶段执行并明确说明。
   - `WebSearch`：使用当前会话可用的联网检索工具；涉及最新财务、价格、监管、新闻数据时必须联网核验。
   - 文件写入：遵守 `AGENTS.md` 的报告目录与命名规范。
5. 所有投资研究输出必须保持中文、客观、区分事实与观点，并对关键数据做来源标注与交叉验证。

## 原始 skill

请打开并执行：`skills/deep-company-series.md`
