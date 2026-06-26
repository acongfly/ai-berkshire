#!/usr/bin/env python3
"""Generate Codex-native skill wrappers from the shared skills directory."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


DEFAULT_DESCRIPTION = "AI Berkshire 投资研究工作流。执行前读取原始 skill 文件并遵守项目投研纪律。"
SKILL_BODY_TEMPLATE = """---
name: {name}
description: {description}
---

# {title}

本 Codex skill 是 `skills/{source_name}` 的轻量包装层。`skills/{source_name}` 是 Claude Code 与 Codex 共同使用的单一事实来源。

## 执行要求

1. 在执行本 skill 时，先阅读仓库根目录的 `AGENTS.md`。
2. 完整阅读 `skills/{source_name}`，并按其中的流程、输出格式、数据纪律执行。
3. 用户在 Codex 中可显式输入 `${name}` 触发；在 Claude Code 中继续使用 `/{name}`。
4. 如原始 skill 提到 Claude Code 专用工具名，按 Codex 当前会话可用工具进行等价替换：
   - `Task` / `Agent` / `Team`：优先使用 Codex subagent、并行代理或当前会话中的等价多代理能力；没有可用能力时，在当前会话内分阶段执行并明确说明。
   - `WebSearch`：使用当前会话可用的联网检索工具；涉及最新财务、价格、监管、新闻数据时必须联网核验。
   - 文件写入：遵守 `AGENTS.md` 的报告目录与命名规范。
5. 所有投资研究输出必须保持中文、客观、区分事实与观点，并对关键数据做来源标注与交叉验证。

## 原始 skill

请打开并执行：`skills/{source_name}`
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate .agents/skills wrappers for Codex from skills/*.md."
    )
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="Repository root. Defaults to this script's parent repository.",
    )
    return parser.parse_args()


def first_heading(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def first_description(markdown: str) -> str:
    frontmatter_match = re.match(r"^---\n(.*?)\n---\n", markdown, re.DOTALL)
    if frontmatter_match:
        description_match = re.search(
            r"^description:\s*(.+)$",
            frontmatter_match.group(1),
            re.MULTILINE,
        )
        if description_match:
            return clean_description(description_match.group(1))

    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("---"):
            continue
        if stripped.startswith(">"):
            continue
        return clean_description(stripped)
    return DEFAULT_DESCRIPTION


def clean_description(value: str) -> str:
    value = value.strip().strip("'\"")
    value = re.sub(r"\s+", " ", value)
    if len(value) > 220:
        value = value[:217].rstrip() + "..."
    return value


def render_wrapper(source: Path, repo_root: Path) -> str:
    markdown = source.read_text(encoding="utf-8")
    name = source.stem
    return SKILL_BODY_TEMPLATE.format(
        name=name,
        title=first_heading(markdown, name),
        description=first_description(markdown),
        source_name=source.name,
    )


def sync(repo_root: Path) -> list[Path]:
    skills_dir = repo_root / "skills"
    target_root = repo_root / ".agents" / "skills"

    if not skills_dir.exists():
        raise SystemExit(f"skills directory not found: {skills_dir}")

    written: list[Path] = []
    target_root.mkdir(parents=True, exist_ok=True)
    for source in sorted(skills_dir.glob("*.md")):
        target_dir = target_root / source.stem
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / "SKILL.md"
        target.write_text(render_wrapper(source, repo_root), encoding="utf-8")
        written.append(target)
    return written


def main() -> int:
    args = parse_args()
    written = sync(args.repo_root.resolve())
    for path in written:
        print(path)
    print(f"Generated {len(written)} Codex skill wrappers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
