from pathlib import Path

from ice_worker.tasks.signal_video import _remotion_command, _remotion_project_dir


def test_source_tree_remotion_project_exists(monkeypatch):
    monkeypatch.setattr(
        "ice_worker.tasks.signal_video.settings.signal_video.remotion_project_dir", ""
    )

    project = Path(_remotion_project_dir())

    assert (project / "src" / "index.ts").is_file()
    assert (project / "package.json").is_file()


def test_render_command_uses_direct_cli(monkeypatch, tmp_path):
    project = tmp_path / "remotion"
    cli = project / "node_modules" / ".bin" / "remotion"
    monkeypatch.setattr(
        "ice_worker.tasks.signal_video.settings.signal_video.remotion_command", ""
    )

    command = _remotion_command(str(project), "out.mp4", "props.json")

    assert command == [
        str(cli),
        "render",
        "src/index.ts",
        "MainComp",
        "out.mp4",
        "--props",
        "props.json",
    ]
