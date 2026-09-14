import pytest
from textual.app import App

from magic_prompt.workspaces import WorkspaceModal, Workspace


@pytest.mark.asyncio
async def test_add_workspace_modal_blank_selects_no_crash(tmp_path):
    """Mount WorkspaceModal with blank selects and save without crashing."""

    class TestApp(App):
        pass

    results: list[Workspace | None] = []

    app = TestApp()
    async with app.run_test() as pilot:
        # Push the modal and capture the result via callback
        pilot.app.push_screen(WorkspaceModal(), callback=lambda res: results.append(res))
        # Allow the screen to mount
        await pilot.pause()

        # Fill in required fields; leave optional selects blank
        await pilot.click("#ws-name-input")
        await pilot.press(*list("TestWS"))
        await pilot.click("#ws-path-input")
        await pilot.press(*list(str(tmp_path)))

        # Save and ensure no exception occurs
        await pilot.click("#modal-save-btn")
        await pilot.pause()

    assert results, "Modal did not dismiss with a result"
    ws = results[0]
    assert isinstance(ws, Workspace)
    assert ws.name == "TestWS"
    assert ws.path == str(tmp_path.resolve())
    # Optional fields should be None when left blank
    assert ws.model is None
    assert ws.mode is None

