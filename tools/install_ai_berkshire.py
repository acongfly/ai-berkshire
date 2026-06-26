#!/usr/bin/env python3
"""Install AI Berkshire workflows for Claude Code and Codex."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from sync_codex_skills import sync


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install or refresh AI Berkshire agent workflows."
    )
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="Repository root. Defaults to this script's parent repository.",
    )
    parser.add_argument(
        "--target",
        choices=["all", "claude", "codex"],
        default="all",
        help="Install target. Default: all.",
    )
    parser.add_argument(
        "--claude-dir",
        default=Path.home() / ".claude" / "commands",
        type=Path,
        help="Claude Code commands directory.",
    )
    return parser.parse_args()


def install_claude_commands(repo_root: Path, claude_dir: Path) -> list[Path]:
    skills_dir = repo_root / "skills"
    if not skills_dir.exists():
        raise SystemExit(f"skills directory not found: {skills_dir}")

    claude_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for source in sorted(skills_dir.glob("*.md")):
        target = claude_dir / source.name
        shutil.copy2(source, target)
        written.append(target)
    return written


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()

    if args.target in {"all", "codex"}:
        codex_wrappers = sync(repo_root)
        print(f"Codex: refreshed {len(codex_wrappers)} repo skills under .agents/skills")

    if args.target in {"all", "claude"}:
        claude_commands = install_claude_commands(repo_root, args.claude_dir)
        print(f"Claude Code: installed {len(claude_commands)} commands to {args.claude_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
