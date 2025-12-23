"""Tests for Pipedream deployment exceptions."""

import pytest

from src.deploy.exceptions import (
    AuthenticationError,
    CodeUpdateError,
    ConfigurationError,
    NavigationError,
    PipedreamSyncError,
    SaveError,
    StepNotFoundError,
    ValidationError,
)


class TestPipedreamSyncError:
    """Tests for base PipedreamSyncError."""

    def test_basic_exception(self):
        """Test creating base exception with message."""
        error = PipedreamSyncError("Test error message")
        assert str(error) == "Test error message"

    def test_exception_inheritance(self):
        """Test that it inherits from Exception."""
        error = PipedreamSyncError("test")
        assert isinstance(error, Exception)

    def test_exception_without_message(self):
        """Test creating exception without message."""
        error = PipedreamSyncError()
        assert str(error) == ""


class TestAuthenticationError:
    """Tests for AuthenticationError."""

    def test_basic_exception(self):
        """Test creating authentication error."""
        error = AuthenticationError("Login failed")
        assert str(error) == "Login failed"

    def test_inherits_from_base(self):
        """Test inheritance from PipedreamSyncError."""
        error = AuthenticationError("test")
        assert isinstance(error, PipedreamSyncError)


class TestNavigationError:
    """Tests for NavigationError."""

    def test_basic_exception(self):
        """Test creating navigation error."""
        error = NavigationError("Page not found")
        assert str(error) == "Page not found"

    def test_inherits_from_base(self):
        """Test inheritance from PipedreamSyncError."""
        error = NavigationError("test")
        assert isinstance(error, PipedreamSyncError)


class TestStepNotFoundError:
    """Tests for StepNotFoundError with custom attributes."""

    def test_basic_exception(self):
        """Test creating step not found error."""
        error = StepNotFoundError("fetch_gmail_emails", "workflow_123")
        assert "fetch_gmail_emails" in str(error)
        assert "workflow_123" in str(error)

    def test_step_name_attribute(self):
        """Test step_name attribute is set correctly."""
        error = StepNotFoundError("my_step", "wf_456")
        assert error.step_name == "my_step"

    def test_workflow_id_attribute(self):
        """Test workflow_id attribute is set correctly."""
        error = StepNotFoundError("my_step", "wf_456")
        assert error.workflow_id == "wf_456"

    def test_inherits_from_base(self):
        """Test inheritance from PipedreamSyncError."""
        error = StepNotFoundError("step", "workflow")
        assert isinstance(error, PipedreamSyncError)

    def test_error_message_format(self):
        """Test the error message format."""
        error = StepNotFoundError("create_task", "p_abc123")
        assert str(error) == "Step 'create_task' not found in workflow 'p_abc123'"


class TestCodeUpdateError:
    """Tests for CodeUpdateError."""

    def test_basic_exception(self):
        """Test creating code update error."""
        error = CodeUpdateError("Editor not found")
        assert str(error) == "Editor not found"

    def test_inherits_from_base(self):
        """Test inheritance from PipedreamSyncError."""
        error = CodeUpdateError("test")
        assert isinstance(error, PipedreamSyncError)


class TestSaveError:
    """Tests for SaveError."""

    def test_basic_exception(self):
        """Test creating save error."""
        error = SaveError("Autosave failed")
        assert str(error) == "Autosave failed"

    def test_inherits_from_base(self):
        """Test inheritance from PipedreamSyncError."""
        error = SaveError("test")
        assert isinstance(error, PipedreamSyncError)


class TestValidationError:
    """Tests for ValidationError."""

    def test_basic_exception(self):
        """Test creating validation error."""
        error = ValidationError("Invalid config")
        assert str(error) == "Invalid config"

    def test_inherits_from_base(self):
        """Test inheritance from PipedreamSyncError."""
        error = ValidationError("test")
        assert isinstance(error, PipedreamSyncError)


class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_basic_exception(self):
        """Test creating configuration error."""
        error = ConfigurationError("Missing API key")
        assert str(error) == "Missing API key"

    def test_inherits_from_base(self):
        """Test inheritance from PipedreamSyncError."""
        error = ConfigurationError("test")
        assert isinstance(error, PipedreamSyncError)


class TestExceptionHierarchy:
    """Tests for the exception class hierarchy."""

    def test_all_exceptions_inherit_from_base(self):
        """Test all custom exceptions inherit from PipedreamSyncError."""
        exceptions = [
            AuthenticationError("test"),
            NavigationError("test"),
            StepNotFoundError("step", "workflow"),
            CodeUpdateError("test"),
            SaveError("test"),
            ValidationError("test"),
            ConfigurationError("test"),
        ]
        for exc in exceptions:
            assert isinstance(exc, PipedreamSyncError)

    def test_exceptions_can_be_caught_by_base(self):
        """Test that all exceptions can be caught by catching the base class."""
        with pytest.raises(PipedreamSyncError):
            raise AuthenticationError("test")

        with pytest.raises(PipedreamSyncError):
            raise NavigationError("test")

        with pytest.raises(PipedreamSyncError):
            raise StepNotFoundError("step", "workflow")

        with pytest.raises(PipedreamSyncError):
            raise CodeUpdateError("test")

        with pytest.raises(PipedreamSyncError):
            raise SaveError("test")

        with pytest.raises(PipedreamSyncError):
            raise ValidationError("test")

        with pytest.raises(PipedreamSyncError):
            raise ConfigurationError("test")
