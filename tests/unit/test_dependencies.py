"""测试 Story 1-2: 核心依赖安装"""

import subprocess
from pathlib import Path

import pytest

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestCoreDependencies:
    """测试核心依赖安装"""

    def test_funasr_installed(self):
        """验证 funasr 依赖已安装"""
        try:
            import funasr
        except ImportError as e:
            pytest.fail(f"funasr 依赖未安装: {e}")
        # 验证可以导入主要模块
        assert hasattr(funasr, "__version__"), "funasr 未正确安装"

    def test_sounddevice_installed(self):
        """验证 sounddevice 依赖已安装"""
        try:
            import sounddevice
        except ImportError as e:
            pytest.fail(f"sounddevice 依赖未安装: {e}")
        # 验证可以访问主要功能
        assert hasattr(sounddevice, "play"), "sounddevice 未正确安装"


class TestDevDependencies:
    """测试开发依赖安装"""

    def test_pytest_installed(self):
        """验证 pytest 已安装"""
        try:
            import pytest
        except ImportError as e:
            pytest.fail(f"pytest 未安装: {e}")
        # 验证可以运行
        assert hasattr(pytest, "__version__"), "pytest 未正确安装"

    def test_ruff_installed(self):
        """验证 ruff 已安装"""
        # ruff 可能不是 Python 模块，使用命令行检查
        result = subprocess.run(["ruff", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            pytest.fail("ruff 未安装")
        assert result.returncode == 0, "ruff 未正确安装"

    def test_mypy_installed(self):
        """验证 mypy 已安装"""
        # mypy 可能不是 Python 模块，使用命令行检查
        result = subprocess.run(["mypy", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            pytest.fail("mypy 未安装")
        assert result.returncode == 0, "mypy 未正确安装"

    def test_pre_commit_installed(self):
        """验证 pre-commit 已安装"""
        # pre-commit 可能不是 Python 模块，使用命令行检查
        result = subprocess.run(["pre-commit", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            pytest.fail("pre-commit 未安装")
        assert result.returncode == 0, "pre-commit 未正确安装"


class TestPyprojectTomlVersions:
    """测试 pyproject.toml 依赖版本"""

    def test_pyproject_has_correct_dependencies(self):
        """验证 pyproject.toml 包含正确的依赖"""
        import tomli

        pyproject = PROJECT_ROOT / "pyproject.toml"
        with open(pyproject, "rb") as f:
            config = tomli.load(f)

        dependencies = config.get("project", {}).get("dependencies", [])

        # 检查必需的运行时依赖声明
        required_deps = ["funasr", "sounddevice"]
        for dep in required_deps:
            assert any(dep in d for d in dependencies), f"pyproject.toml 缺少依赖: {dep}"

    def test_pyproject_has_dev_dependencies(self):
        """验证 pyproject.toml 包含正确的开发依赖"""
        import tomli

        pyproject = PROJECT_ROOT / "pyproject.toml"
        with open(pyproject, "rb") as f:
            config = tomli.load(f)

        # 支持新版 [dependency-groups] 和旧版 [project.optional-dependencies]
        dev_deps = config.get("dependency-groups", {}).get("dev", [])
        if not dev_deps:
            dev_deps = config.get("project", {}).get("optional-dependencies", {}).get("dev", [])

        # 检查必需的开发依赖声明
        required_dev_deps = ["pytest", "ruff", "mypy", "pre-commit"]
        for dep in required_dev_deps:
            assert any(dep in d for d in dev_deps), f"pyproject.toml 缺少开发依赖: {dep}"
