# AI Berkshire 在 Claude Code 与 Codex 中的真实使用流程

本文档说明如何在同一个仓库里同时使用 Claude Code 和 Codex 运行 AI Berkshire。

如果你的目标是用 Codex 选行业或选股票，直接看：[用 Codex 做行业筛选与选股：实战操作手册](codex-stock-selection-guide.md)。

## 一句话结论

- Claude Code 使用 `skills/*.md` 作为 slash commands，调用形式是 `/investment-team 腾讯`。
- Codex 使用 `.agents/skills/*/SKILL.md` 作为 repo skills，调用形式是 `$investment-team 腾讯`。
- `skills/*.md` 是单一事实来源；`.agents/skills` 只是 Codex 包装层，由脚本生成。

## 目录角色

| 路径 | 用途 | 是否手改 |
|------|------|----------|
| `CLAUDE.md` | Claude Code 项目指令 | 可以 |
| `AGENTS.md` | Codex 项目指令 | 可以 |
| `skills/*.md` | 投研 workflow 源文件，Claude 直接使用 | 可以 |
| `.agents/skills/*/SKILL.md` | Codex repo skill 包装层 | 不建议手改 |
| `tools/sync_codex_skills.py` | 从 `skills/*.md` 生成 Codex wrappers | 可以 |
| `tools/install_ai_berkshire.py` | 安装/刷新 Claude 与 Codex 入口 | 可以 |

## 首次安装

### 1. 克隆仓库

```bash
git clone https://github.com/xbtlin/ai-berkshire.git
cd ai-berkshire
```

### 2. 安装 Claude Code commands

```bash
python3 tools/install_ai_berkshire.py --target claude
```

这会把 `skills/*.md` 复制到 `~/.claude/commands/`。

### 3. 刷新 Codex repo skills

```bash
python3 tools/install_ai_berkshire.py --target codex
```

这会生成 `.agents/skills/*/SKILL.md`。Codex 从仓库根目录启动后会自动发现这些 repo skills。

### 4. 一次性全装

```bash
python3 tools/install_ai_berkshire.py
```

等价于同时执行 Claude 安装与 Codex wrapper 刷新。

## 在 Claude Code 中使用

从仓库根目录启动 Claude Code：

```bash
claude
```

常用调用：

```text
/investment-team 腾讯
/investment-research 拼多多
/earnings-review 腾讯 2026Q1
/industry-funnel AI算力
/portfolio-review 腾讯30%, 美团20%, 现金50%
```

Claude Code 会读取 `CLAUDE.md`，并使用 `~/.claude/commands/*.md` 中的命令。

## 在 Codex 中使用

从仓库根目录启动 Codex：

```bash
codex
```

建议先确认状态：

```text
/status
```

常用调用：

```text
$investment-team 腾讯
$investment-research 拼多多
$earnings-review 腾讯 2026Q1
$industry-funnel AI算力
$portfolio-review 腾讯30%, 美团20%, 现金50%
```

Codex 会读取 `AGENTS.md`，并从 `.agents/skills` 发现 repo skills。

## Codex 使用要点

1. 涉及最新股价、财报、监管、新闻时，让 Codex 联网检索并标注来源。
2. 涉及计算时，要求 Codex 使用 `tools/financial_rigor.py` 或 Python 精确计算，不接受心算。
3. 如果原始 skill 写了 Claude Code 的 `Task`、`Agent`、`Team`，Codex wrapper 要求 Codex 使用当前会话可用的等价多代理能力；没有等价能力时分阶段执行并说明限制。
4. 报告仍统一写入 `reports/`，命名规则以 `AGENTS.md` 为准。

## 更新 skill 后的维护流程

修改任何 `skills/*.md` 后，执行：

```bash
python3 tools/sync_codex_skills.py
python3 tools/install_ai_berkshire.py --target claude
python3 -m unittest tests/test_sync_codex_skills.py -v
```

然后重新启动 Claude Code 或 Codex，让新指令进入会话上下文。

## 验证 Codex 是否加载成功

在 Codex 中输入：

```text
/skills
```

应该能看到 `investment-team`、`investment-research`、`earnings-review` 等 repo skills。

也可以直接问：

```text
请列出当前仓库可用的 AI Berkshire skills，并说明 Claude 和 Codex 的调用方式。
```

期望结果：

- Codex 提到 `AGENTS.md`。
- Codex 识别 `$investment-team` 这类调用。
- Codex 说明 Claude Code 仍使用 `/investment-team`。

## 推送前检查

```bash
git status --short
python3 -m unittest tests/test_sync_codex_skills.py -v
python3 tools/sync_codex_skills.py
```

如 `.agents/skills` 有变化，一并提交。推送前仍遵守项目规则：

```bash
git pull --rebase origin main
git push origin main
```
