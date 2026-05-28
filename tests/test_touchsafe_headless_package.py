from __future__ import annotations

import tempfile
from pathlib import Path

from tools import package_touchsafe_headless_toolchain as package_tool


def test_package_manifest_file_set_has_portable_entrypoints() -> None:
    files = set(package_tool.REQUIRED_FILES)

    assert "tools/touchsafe_headless_bootstrap.ps1" in files
    assert "tools/run_touchsafe_pipeline.ps1" in files
    assert "tools/official_gui_host_select.py" in files
    assert "tools/OfficialGuiHostSelect.cs" in files
    assert "skills" in package_tool.REQUIRED_DIRS


def test_package_excludes_generated_hmi_and_tft_payloads() -> None:
    assert package_tool.should_exclude("build/demo/lcd_test.HMI")
    assert package_tool.should_exclude("build/demo/lcd_test.tft")
    assert package_tool.should_exclude("capture.png")
    assert not package_tool.should_exclude("tools/OfficialGuiHostSelect.cs")
    assert not package_tool.should_exclude("tools/UsartHmiHostAutomation.exe")


def test_official_runtime_discovery_accepts_fake_install(monkeypatch) -> None:
    from tools import official_gui_host_select

    with tempfile.TemporaryDirectory() as temp_dir:
        install = Path(temp_dir) / "USART HMI"
        install.mkdir()
        (install / "USART HMI.exe").write_bytes(b"exe")
        (install / "ACTR.dll").write_bytes(b"dll")
        monkeypatch.setenv(official_gui_host_select.OFFICIAL_DIR_ENV, str(install))

        resolved = official_gui_host_select._resolve_official_install_dir(None)

        assert resolved == install.resolve()


def test_prepare_runtime_uses_localappdata_cache(monkeypatch) -> None:
    from tools import official_gui_host_select

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        install = temp_root / "official"
        install.mkdir()
        (install / "USART HMI.exe").write_bytes(b"exe")
        (install / "ACTR.dll").write_bytes(b"dll")
        (install / "keep.txt").write_text("ok", encoding="utf-8")
        (install / "skip.log").write_text("skip", encoding="utf-8")
        runtime_root = temp_root / "runtime-root"
        monkeypatch.setenv(official_gui_host_select.RUNTIME_ROOT_ENV, str(runtime_root))

        runtime = official_gui_host_select._prepare_writable_runtime(install)

        assert runtime.is_dir()
        assert (runtime / "USART HMI.exe").is_file()
        assert (runtime / "ACTR.dll").is_file()
        assert (runtime / "keep.txt").read_text(encoding="utf-8") == "ok"
        assert not (runtime / "skip.log").exists()
        assert Path(runtime).is_relative_to(runtime_root)
