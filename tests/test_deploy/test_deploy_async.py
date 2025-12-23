"""Async tests for deploy_to_pipedream with mocked Playwright."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from src.deploy.config import DeployConfig, DeploySettings, StepConfig, WorkflowConfig
from src.deploy.exceptions import (
    AuthenticationError,
    CodeUpdateError,
    NavigationError,
    StepNotFoundError,
)
from src.deploy.deploy_to_pipedream import (
    PipedreamSyncer,
    PlaywrightTimeout,
    StepResult,
    WorkflowResult,
)


@pytest.fixture
def mock_config():
    """Create a mock DeployConfig for testing."""
    return DeployConfig(
        version="1.0",
        pipedream_base_url="https://pipedream.com",
        workflows={
            "test_workflow": WorkflowConfig(
                id="test-workflow-p_abc123",
                name="Test Workflow",
                steps=[
                    StepConfig(step_name="step1", script_path="src/steps/step1.py"),
                    StepConfig(step_name="step2", script_path="src/steps/step2.py"),
                ],
            )
        },
        settings=DeploySettings(
            step_timeout=60,
            max_retries=3,
            autosave_wait=1.0,
            screenshot_on_failure=True,
            screenshot_path=".tmp/screenshots",
        ),
        pipedream_username="testuser",
        pipedream_project_id="proj_test",
    )


class TestSyncerWithMockedPage:
    """Tests for syncer methods with mocked page object."""

    @pytest.mark.asyncio
    async def test_take_screenshot_with_page(self, mock_config, tmp_path):
        """Test take_screenshot saves file when page is available."""
        syncer = PipedreamSyncer(config=mock_config)
        syncer.config.settings.screenshot_path = str(tmp_path)

        # Mock the page
        mock_page = AsyncMock()
        mock_page.screenshot = AsyncMock()
        syncer.page = mock_page

        result = await syncer.take_screenshot("test_screenshot")

        assert result is not None
        assert "test_screenshot" in result
        mock_page.screenshot.assert_called_once()

    @pytest.mark.asyncio
    async def test_take_screenshot_handles_error(self, mock_config, tmp_path):
        """Test take_screenshot handles errors gracefully."""
        syncer = PipedreamSyncer(config=mock_config)
        syncer.config.settings.screenshot_path = str(tmp_path)

        mock_page = AsyncMock()
        mock_page.screenshot = AsyncMock(side_effect=Exception("Screenshot failed"))
        syncer.page = mock_page

        result = await syncer.take_screenshot("error_test")
        assert result is None

    @pytest.mark.asyncio
    async def test_click_code_tab_clicks_code(self, mock_config):
        """Test click_code_tab clicks CODE section."""
        syncer = PipedreamSyncer(config=mock_config, verbose=True)

        mock_page = AsyncMock()
        mock_page.click = AsyncMock()
        # Mock evaluate to return False (editor not visible), so click proceeds
        mock_page.evaluate = AsyncMock(return_value=False)

        # Mock the locator chain for clicking CODE
        mock_locator = MagicMock()
        mock_locator.first = MagicMock()
        mock_locator.first.count = AsyncMock(return_value=1)
        mock_locator.first.scroll_into_view_if_needed = AsyncMock()
        mock_locator.first.click = AsyncMock()
        mock_page.locator = MagicMock(return_value=mock_locator)

        syncer.page = mock_page

        await syncer.click_code_tab()

        # Should have called locator to find CODE element
        mock_page.locator.assert_called()

    @pytest.mark.asyncio
    async def test_click_code_tab_handles_timeout(self, mock_config):
        """Test click_code_tab handles timeout gracefully."""
        syncer = PipedreamSyncer(config=mock_config, verbose=True)

        mock_page = AsyncMock()
        mock_page.click = AsyncMock(side_effect=PlaywrightTimeout("timeout"))
        syncer.page = mock_page

        # Should not raise, just log and continue
        await syncer.click_code_tab()


class TestUpdateCodeWithMockedPage:
    """Tests for update_code with mocked visible editor detection."""

    @pytest.mark.asyncio
    async def test_update_code_success(self, mock_config):
        """Test update_code successfully updates code via visible editor click, select, paste."""
        syncer = PipedreamSyncer(config=mock_config, verbose=True)

        mock_page = AsyncMock()

        # Mock evaluate to return different values for different calls:
        # 1. First call: editor info debug
        # 2. Second call: find visible editor (returns selector)
        # 3. Third call: cleanup marker
        # 4. Fourth call: clipboard write
        call_count = 0

        async def mock_evaluate(script):
            nonlocal call_count
            call_count += 1
            if "selectors.forEach" in script:
                # Debug info call
                return {".cm-editor": 1, "visible": 1}
            elif "data-sync-target" in script and "setAttribute" in script:
                # Find visible editor call
                return ".cm-editor"
            elif "removeAttribute" in script:
                # Cleanup call
                return None
            elif "clipboard.writeText" in script:
                # Clipboard write call
                return None
            return None

        mock_page.evaluate = mock_evaluate

        # Mock the locator for [data-sync-target="true"]
        mock_locator = AsyncMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.click = AsyncMock()
        mock_page.locator = MagicMock(return_value=mock_locator)

        mock_page.keyboard = AsyncMock()
        mock_page.keyboard.press = AsyncMock()

        syncer.page = mock_page

        await syncer.update_code("def handler(pd): pass")

        # Verify keyboard shortcuts were used
        mock_page.keyboard.press.assert_any_call("ControlOrMeta+KeyA")
        mock_page.keyboard.press.assert_any_call("ControlOrMeta+KeyV")

    @pytest.mark.asyncio
    async def test_update_code_no_editor_found(self, mock_config):
        """Test update_code raises error when no visible editor found."""
        syncer = PipedreamSyncer(config=mock_config)

        mock_page = AsyncMock()

        async def mock_evaluate(script):
            if "selectors.forEach" in script:
                return {".cm-editor": 0, "visible": 0}
            elif "data-sync-target" in script and "setAttribute" in script:
                # No visible editor found
                return None
            return None

        mock_page.evaluate = mock_evaluate
        syncer.page = mock_page

        with pytest.raises(CodeUpdateError, match="No visible editor"):
            await syncer.update_code("test code")

    @pytest.mark.asyncio
    async def test_update_code_clipboard_paste(self, mock_config):
        """Test update_code uses clipboard paste."""
        syncer = PipedreamSyncer(config=mock_config, verbose=True)

        mock_page = AsyncMock()
        clipboard_written = []

        async def mock_evaluate(script):
            if "selectors.forEach" in script:
                return {".cm-editor": 1, "visible": 1}
            elif "data-sync-target" in script and "setAttribute" in script:
                return ".cm-editor"
            elif "removeAttribute" in script:
                return None
            elif "clipboard.writeText" in script:
                clipboard_written.append(script)
                return None
            return None

        mock_page.evaluate = mock_evaluate

        mock_locator = AsyncMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.click = AsyncMock()
        mock_page.locator = MagicMock(return_value=mock_locator)

        mock_page.keyboard = AsyncMock()
        mock_page.keyboard.press = AsyncMock()

        syncer.page = mock_page

        test_code = "print('hello')"
        await syncer.update_code(test_code)

        # Verify clipboard write was called
        assert len(clipboard_written) > 0
        assert "hello" in clipboard_written[0]


class TestNavigateToWorkflow:
    """Tests for navigate_to_workflow with mocked page."""

    @pytest.mark.asyncio
    async def test_navigate_success(self, mock_config):
        """Test successful navigation to workflow."""
        syncer = PipedreamSyncer(config=mock_config, verbose=True)

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        syncer.page = mock_page

        await syncer.navigate_to_workflow("test-workflow-p_abc")

        mock_page.goto.assert_called_once()
        assert "build" in str(mock_page.goto.call_args)

    @pytest.mark.asyncio
    async def test_navigate_timeout(self, mock_config):
        """Test navigation timeout raises error."""
        syncer = PipedreamSyncer(config=mock_config, screenshot_always=False)

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(side_effect=PlaywrightTimeout("timeout"))
        syncer.page = mock_page

        with pytest.raises(NavigationError, match="Timeout"):
            await syncer.navigate_to_workflow("test-p_abc")


class TestDeployWorkflow:
    """Tests for deploy_workflow with mocked page."""

    @pytest.mark.asyncio
    async def test_deploy_success(self, mock_config):
        """Test successful deployment."""
        syncer = PipedreamSyncer(config=mock_config, verbose=True)

        mock_button = AsyncMock()
        mock_button.click = AsyncMock()

        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(return_value=mock_button)
        syncer.page = mock_page

        result = await syncer.deploy_workflow()

        assert result is True
        mock_button.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_deploy_button_not_found(self, mock_config):
        """Test deploy returns False when button not found."""
        syncer = PipedreamSyncer(config=mock_config, verbose=True)

        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(side_effect=PlaywrightTimeout("timeout"))
        syncer.page = mock_page

        result = await syncer.deploy_workflow()

        assert result is False


class TestWaitForSave:
    """Tests for wait_for_save with mocked page."""

    @pytest.mark.asyncio
    async def test_wait_for_save_success(self, mock_config):
        """Test wait_for_save detects save completion."""
        syncer = PipedreamSyncer(config=mock_config, verbose=True)

        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        syncer.page = mock_page

        result = await syncer.wait_for_save()

        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_save_timeout(self, mock_config):
        """Test wait_for_save returns True even on timeout (verification catches issues)."""
        syncer = PipedreamSyncer(config=mock_config, verbose=True)

        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(side_effect=PlaywrightTimeout("timeout"))
        syncer.page = mock_page

        result = await syncer.wait_for_save()

        # Should return True - verification will catch any save failures
        assert result is True


class TestFindAndClickStep:
    """Tests for find_and_click_step with mocked page."""

    @pytest.mark.asyncio
    async def test_find_step_success(self, mock_config):
        """Test successfully finding and clicking a step."""
        syncer = PipedreamSyncer(config=mock_config, verbose=True)

        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()

        # Mock the locator chain for finding the step text
        mock_text_locator = MagicMock()
        mock_text_locator.count = AsyncMock(return_value=1)
        mock_text_locator.first = MagicMock()
        mock_text_locator.first.dblclick = AsyncMock()

        # Mock parent locator that fails (so it falls through to text_el.dblclick)
        mock_parent_locator = MagicMock()
        mock_parent_locator.first = MagicMock()
        mock_parent_locator.first.count = AsyncMock(return_value=0)

        def locator_side_effect(selector):
            if "text=" in selector:
                return mock_text_locator
            return mock_parent_locator

        mock_page.locator = MagicMock(side_effect=locator_side_effect)
        syncer.page = mock_page

        await syncer.find_and_click_step("test_step")

        # Should have double-clicked the text element
        mock_text_locator.first.dblclick.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_step_not_found(self, mock_config):
        """Test StepNotFoundError when step doesn't exist."""
        syncer = PipedreamSyncer(config=mock_config)

        mock_page = AsyncMock()
        mock_page.click = AsyncMock(side_effect=PlaywrightTimeout("timeout"))
        syncer.page = mock_page

        with pytest.raises(StepNotFoundError):
            await syncer.find_and_click_step("nonexistent_step")


class TestSyncStepDryRun:
    """Tests for sync_step in dry run mode."""

    @pytest.mark.asyncio
    async def test_sync_step_dry_run(self, mock_config, tmp_path):
        """Test sync_step in dry run mode."""
        syncer = PipedreamSyncer(config=mock_config, dry_run=True)

        step = StepConfig(step_name="test", script_path="test.py")
        result = await syncer.sync_step("workflow_id", step, tmp_path)

        assert result.status == "skipped"
        assert result.message == "Dry run"


class TestSyncWorkflowDryRun:
    """Tests for sync_workflow in dry run mode."""

    @pytest.mark.asyncio
    async def test_sync_workflow_dry_run(self, mock_config, tmp_path, capsys):
        """Test sync_workflow in dry run mode."""
        syncer = PipedreamSyncer(config=mock_config, dry_run=True)

        result = await syncer.sync_workflow("test_workflow", tmp_path)

        assert result.status == "skipped"
        assert len(result.steps) == 2  # Two steps in mock config

        captured = capsys.readouterr()
        assert "dry-run" in captured.out


class TestWaitForLogin:
    """Tests for wait_for_login with mocked page."""

    @pytest.mark.asyncio
    async def test_already_logged_in(self, mock_config):
        """Test wait_for_login when already logged in."""
        syncer = PipedreamSyncer(config=mock_config, verbose=True)

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()  # Returns immediately (logged in)
        syncer.page = mock_page

        result = await syncer.wait_for_login()

        assert result is True

    @pytest.mark.asyncio
    async def test_login_via_url_check(self, mock_config):
        """Test wait_for_login detects login via URL change."""
        syncer = PipedreamSyncer(config=mock_config, verbose=True)

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        # First call: not logged in, second call: times out but URL check passes
        mock_page.wait_for_selector = AsyncMock(side_effect=PlaywrightTimeout("timeout"))
        # Simulate being on workflows page (logged in)
        type(mock_page).url = PropertyMock(return_value="https://pipedream.com/workflows")
        syncer.page = mock_page

        result = await syncer.wait_for_login()

        assert result is True
