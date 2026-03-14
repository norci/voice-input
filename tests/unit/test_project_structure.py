"""测试 Story 1-1: 项目结构初始化"""

from pathlib import Path

# 项目根目录 (tests/unit/test_project_structure.py → 项目根目录需要向上 3 层)
PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestProjectStructure:
    """测试项目目录结构"""

    def test_src_voice_input_exists(self):
        """验证 src/voice_input/ 源代码目录存在"""
        src_dir = PROJECT_ROOT / "src" / "voice_input"
        assert src_dir.exists(), f"目录 {src_dir} 不存在"
        assert src_dir.is_dir(), f"{src_dir} 不是目录"

    def test_tests_unit_exists(self):
        """验证 tests/unit/ 测试目录存在"""
        unit_dir = PROJECT_ROOT / "tests" / "unit"
        assert unit_dir.exists(), f"目录 {unit_dir} 不存在"
        assert unit_dir.is_dir(), f"{unit_dir} 不是目录"

    def test_tests_integration_exists(self):
        """验证 tests/integration/ 测试目录存在"""
        integration_dir = PROJECT_ROOT / "tests" / "integration"
        assert integration_dir.exists(), f"目录 {integration_dir} 不存在"
        assert integration_dir.is_dir(), f"{integration_dir} 不是目录"

    def test_config_dir_exists(self):
        """验证 config/ 配置目录存在"""
        config_dir = PROJECT_ROOT / "config"
        assert config_dir.exists(), f"目录 {config_dir} 不存在"
        assert config_dir.is_dir(), f"{config_dir} 不是目录"

    def test_docs_dir_exists(self):
        """验证 docs/ 文档目录存在"""
        docs_dir = PROJECT_ROOT / "docs"
        assert docs_dir.exists(), f"目录 {docs_dir} 不存在"
        assert docs_dir.is_dir(), f"{docs_dir} 不是目录"

    def test_src_init_file_exists(self):
        """验证 src/voice_input/__init__.py 存在"""
        init_file = PROJECT_ROOT / "src" / "voice_input" / "__init__.py"
        assert init_file.exists(), f"文件 {init_file} 不存在"

    def test_pyproject_toml_exists(self):
        """验证 pyproject.toml 存在"""
        pyproject = PROJECT_ROOT / "pyproject.toml"
        assert pyproject.exists(), f"文件 {pyproject} 不存在"


class TestPyprojectToml:
    """测试 pyproject.toml 配置"""

    def test_runtime_dependencies(self):
        """验证运行时依赖声明"""
        import tomli

        pyproject = PROJECT_ROOT / "pyproject.toml"
        with open(pyproject, "rb") as f:
            config = tomli.load(f)

        dependencies = config.get("project", {}).get("dependencies", [])

        # 检查必需的运行时依赖
        required_deps = ["funasr", "sounddevice"]
        for dep in required_deps:
            assert any(dep in d for d in dependencies), f"缺少运行时依赖: {dep}"

    def test_dev_dependencies(self):
        """验证开发依赖声明"""
        import tomli

        pyproject = PROJECT_ROOT / "pyproject.toml"
        with open(pyproject, "rb") as f:
            config = tomli.load(f)

        # 支持新版 [dependency-groups] 和旧版 [project.optional-dependencies]
        dev_deps = config.get("dependency-groups", {}).get("dev", [])
        if not dev_deps:
            dev_deps = config.get("project", {}).get("optional-dependencies", {}).get("dev", [])

        # 检查必需的开发依赖
        required_dev_deps = ["pytest", "ruff", "mypy", "pre-commit"]
        for dep in required_dev_deps:
            assert any(dep in d for d in dev_deps), f"缺少开发依赖: {dep}"

    def test_python_version(self):
        """验证 Python 版本要求"""
        import tomli

        pyproject = PROJECT_ROOT / "pyproject.toml"
        with open(pyproject, "rb") as f:
            config = tomli.load(f)

        requires_python = config.get("project", {}).get("requires-python", "")
        assert "3.11" in requires_python, "Python 版本要求应包含 3.11"

    def test_build_system(self):
        """验证构建系统配置"""
        import tomli

        pyproject = PROJECT_ROOT / "pyproject.toml"
        with open(pyproject, "rb") as f:
            config = tomli.load(f)

        build_system = config.get("build-system", {})
        # 支持 PEP 517 格式的 build-backend (新版) 或 requires (旧版)
        assert "hatchling" in build_system.get("requires", []) or "hatchling.build" in str(
            build_system.get("build-backend", "")
        ), "应使用 hatchling 构建系统"
