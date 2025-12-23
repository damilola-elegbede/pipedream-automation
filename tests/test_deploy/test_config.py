"""Tests for deployment configuration loading and validation."""

import pytest
from pathlib import Path

from src.deploy.config import (
    DeployConfig,
    DeploySettings,
    StepConfig,
    WorkflowConfig,
    load_config,
    validate_config,
)
from src.deploy.exceptions import ConfigurationError, ValidationError


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_valid_config(self, tmp_path):
        """Test loading a valid configuration file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
version: "1.0"
pipedream_base_url: "https://pipedream.com"
workflows:
  test_workflow:
    id: "p_test123"
    name: "Test Workflow"
    steps:
      - step_name: "test_step"
        script_path: "src/steps/test.py"
settings:
  headless: true
""")

        config = load_config(str(config_file))
        assert config.version == "1.0"
        assert len(config.workflows) == 1
        assert "test_workflow" in config.workflows

    def test_load_missing_file(self):
        """Test loading a non-existent file raises error."""
        with pytest.raises(ConfigurationError, match="not found"):
            load_config("/nonexistent/path.yaml")

    def test_load_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML raises error."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [")

        with pytest.raises(ConfigurationError, match="Invalid YAML"):
            load_config(str(config_file))


class TestStepConfig:
    """Tests for StepConfig validation."""

    def test_valid_step(self, tmp_path):
        """Test validation of a valid step configuration."""
        # Create a valid script file
        script_dir = tmp_path / "src" / "steps"
        script_dir.mkdir(parents=True)
        script_file = script_dir / "test.py"
        script_file.write_text('def handler(pd): pass')

        step = StepConfig(
            step_name="test_step",
            script_path="src/steps/test.py",
        )
        step.validate(tmp_path)  # Should not raise

    def test_missing_script(self, tmp_path):
        """Test validation fails for missing script."""
        step = StepConfig(
            step_name="test_step",
            script_path="src/steps/missing.py",
        )
        with pytest.raises(ValidationError, match="not found"):
            step.validate(tmp_path)

    def test_invalid_python_syntax(self, tmp_path):
        """Test validation fails for invalid Python syntax."""
        script_dir = tmp_path / "src" / "steps"
        script_dir.mkdir(parents=True)
        script_file = script_dir / "bad.py"
        script_file.write_text('def handler( invalid syntax')

        step = StepConfig(
            step_name="test_step",
            script_path="src/steps/bad.py",
        )
        with pytest.raises(ValidationError, match="Syntax error"):
            step.validate(tmp_path)

    def test_missing_handler_function(self, tmp_path):
        """Test validation fails when handler function is missing."""
        script_dir = tmp_path / "src" / "steps"
        script_dir.mkdir(parents=True)
        script_file = script_dir / "no_handler.py"
        script_file.write_text('def main(): pass')

        step = StepConfig(
            step_name="test_step",
            script_path="src/steps/no_handler.py",
        )
        with pytest.raises(ValidationError, match="handler"):
            step.validate(tmp_path)


class TestWorkflowConfig:
    """Tests for WorkflowConfig validation."""

    def test_valid_workflow(self, tmp_path):
        """Test validation of a valid workflow configuration."""
        script_dir = tmp_path / "src" / "steps"
        script_dir.mkdir(parents=True)
        (script_dir / "test.py").write_text('def handler(pd): pass')

        workflow = WorkflowConfig(
            id="p_test123",
            name="Test Workflow",
            steps=[
                StepConfig(step_name="test", script_path="src/steps/test.py")
            ],
        )
        workflow.validate(tmp_path)  # Should not raise

    def test_missing_workflow_id(self, tmp_path):
        """Test validation fails for missing workflow ID."""
        workflow = WorkflowConfig(
            id="",
            name="Test Workflow",
            steps=[],
        )
        with pytest.raises(ValidationError, match="missing an ID"):
            workflow.validate(tmp_path)

    def test_invalid_workflow_id_format(self, tmp_path):
        """Test validation fails for invalid workflow ID format."""
        workflow = WorkflowConfig(
            id="invalid_id",
            name="Test Workflow",
            steps=[StepConfig(step_name="test", script_path="test.py")],
        )
        with pytest.raises(ValidationError, match="should contain 'p_'"):
            workflow.validate(tmp_path)


class TestDeployConfig:
    """Tests for DeployConfig."""

    def test_get_workflow(self):
        """Test getting a workflow by key."""
        config = DeployConfig(
            version="1.0",
            pipedream_base_url="https://pipedream.com",
            workflows={
                "test": WorkflowConfig(
                    id="p_test",
                    name="Test",
                    steps=[],
                )
            },
        )
        workflow = config.get_workflow("test")
        assert workflow.id == "p_test"

    def test_get_missing_workflow(self):
        """Test getting a non-existent workflow raises error."""
        config = DeployConfig(
            version="1.0",
            pipedream_base_url="https://pipedream.com",
            workflows={},
        )
        with pytest.raises(ConfigurationError, match="not found"):
            config.get_workflow("missing")
