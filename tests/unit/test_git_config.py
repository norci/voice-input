"""测试 Story 1-3: Git 仓库配置"""

from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestGitRepository:
    """测试 Git 仓库配置"""

    def test_git_directory_exists(self):
        """验证 .git 目录存在"""
        git_dir = PROJECT_ROOT / ".git"
        assert git_dir.exists(), ".git 目录不存在，Git 仓库未初始化"
        assert git_dir.is_dir(), ".git 不是目录"

    def test_git_config_exists(self):
        """验证 Git 配置文件存在"""
        git_config = PROJECT_ROOT / ".git" / "config"
        assert git_config.exists(), ".git/config 文件不存在"

    def test_initial_commit_exists(self):
        """验证已有初始提交"""
        import subprocess

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, "Git 仓库没有初始提交"

    def test_gitignore_exists(self):
        """验证 .gitignore 文件存在"""
        gitignore = PROJECT_ROOT / ".gitignore"
        assert gitignore.exists(), ".gitignore 文件不存在"

    def test_gitignore_content(self):
        """验证 .gitignore 包含 Python 相关的忽略规则"""
        gitignore = PROJECT_ROOT / ".gitignore"
        content = gitignore.read_text()

        # 检查必需的 Python 忽略规则
        required_patterns = [
            "__pycache__/",
            "*.py[cod]",
            "build/",
            "dist/",
            ".venv",
        ]

        for pattern in required_patterns:
            assert pattern in content, f".gitignore 缺少必要的规则: {pattern}"


class TestGitignoreContent:
    """测试 .gitignore 内容的完整性"""

    def test_pycache_ignored(self):
        """验证 __pycache__ 被忽略"""
        gitignore = PROJECT_ROOT / ".gitignore"
        content = gitignore.read_text()
        assert "__pycache__/" in content

    def test_bytecode_ignored(self):
        """验证 Python 字节码被忽略"""
        gitignore = PROJECT_ROOT / ".gitignore"
        content = gitignore.read_text()
        assert "*.py[cod]" in content

    def test_venv_ignored(self):
        """验证虚拟环境被忽略"""
        gitignore = PROJECT_ROOT / ".gitignore"
        content = gitignore.read_text()
        assert ".venv" in content or "venv/" in content

    def test_pytest_cache_ignored(self):
        """验证 pytest 缓存被忽略"""
        gitignore = PROJECT_ROOT / ".gitignore"
        content = gitignore.read_text()
        assert ".pytest_cache/" in content

    def test_ruff_cache_ignored(self):
        """验证 ruff 缓存被忽略"""
        gitignore = PROJECT_ROOT / ".gitignore"
        content = gitignore.read_text()
        assert ".ruff_cache/" in content

    def test_mypy_cache_ignored(self):
        """验证 mypy 缓存被忽略"""
        gitignore = PROJECT_ROOT / ".gitignore"
        content = gitignore.read_text()
        assert ".mypy_cache/" in content
