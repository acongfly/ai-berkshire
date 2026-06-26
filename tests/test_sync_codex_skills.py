import subprocess
import unittest
from pathlib import Path


class SyncCodexSkillsTest(unittest.TestCase):
    def make_repo(self, tmp: str) -> Path:
        repo = Path(tmp) / "repo"
        skills = repo / "skills"
        tools = repo / "tools"
        tools.mkdir(parents=True)
        skills.mkdir()

        (skills / "investment-research.md").write_text(
            "# 投资研究：巴菲特-芒格-段永平-李录 四大师综合分析框架\n\n"
            "对 $ARGUMENTS 进行系统化投资研究分析。\n",
            encoding="utf-8",
        )
        return repo

    def test_sync_codex_skills_generates_wrappers(self):
        with self.subTest("temporary repository"):
            import tempfile

            with tempfile.TemporaryDirectory() as tmp:
                repo = self.make_repo(tmp)
                agents = repo / ".agents" / "skills"

                script = (
                    Path(__file__).resolve().parents[1]
                    / "tools"
                    / "sync_codex_skills.py"
                )
                result = subprocess.run(
                    ["python3", str(script), "--repo-root", str(repo)],
                    text=True,
                    capture_output=True,
                    check=False,
                )

                self.assertEqual(result.returncode, 0, result.stderr)
                wrapper = agents / "investment-research" / "SKILL.md"
                self.assertTrue(wrapper.exists())

                content = wrapper.read_text(encoding="utf-8")
                self.assertIn("name: investment-research", content)
                self.assertIn("description:", content)
                self.assertIn("skills/investment-research.md", content)
                self.assertIn(
                    "在执行本 skill 时，先阅读仓库根目录的 `AGENTS.md`",
                    content,
                )

    def test_install_script_installs_claude_and_codex_targets(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            repo = self.make_repo(tmp)
            claude_dir = Path(tmp) / "claude" / "commands"
            script = (
                Path(__file__).resolve().parents[1]
                / "tools"
                / "install_ai_berkshire.py"
            )
            result = subprocess.run(
                [
                    "python3",
                    str(script),
                    "--repo-root",
                    str(repo),
                    "--claude-dir",
                    str(claude_dir),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Codex: refreshed 1 repo skills", result.stdout)
            self.assertIn("Claude Code: installed 1 commands", result.stdout)
            self.assertTrue((claude_dir / "investment-research.md").exists())
            self.assertTrue(
                (
                    repo
                    / ".agents"
                    / "skills"
                    / "investment-research"
                    / "SKILL.md"
                ).exists()
            )


if __name__ == "__main__":
    unittest.main()
