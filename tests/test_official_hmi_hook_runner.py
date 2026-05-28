from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load_tool_module(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


official_hmi_hook_runner = load_tool_module(
    "official_hmi_hook_runner_test",
    "tools/official_hmi_hook_runner.py",
)
official_gui_host_select = load_tool_module(
    "official_gui_host_select_test",
    "tools/official_gui_host_select.py",
)


class OfficialHmiHookRunnerTests(unittest.TestCase):
    def test_dry_run_reports_official_function_boundaries(self) -> None:
        payload = {
            "name": "clickless_patch",
            "hmi_path": r"C:\tmp\lcd_test.HMI",
            "actions": [
                {"kind": "select-page", "page_index": 1, "page_resource": "1.pa"},
                {"kind": "select-object", "object": "b0"},
                {"kind": "patch-field", "field": "txt", "value": "HOOKED"},
                {"kind": "patch-event", "event": "down", "lines": ["printh 11 22"]},
                {"kind": "save"},
                {"kind": "dump-page"},
                {"kind": "compile", "output": r"C:\tmp\out.tft"},
            ],
        }

        report = official_hmi_hook_runner.run_hook_script(payload, dry_run=True)
        functions = [step["official_function"] for step in report["plan"]]

        self.assertEqual(report["status"], "dry_run")
        self.assertIn('HMIFORM.main.filecaozuo("open", hmi_path)', functions)
        self.assertIn("HMIFORM.main.pageadmin1.selectindex(page_index)", functions)
        self.assertIn("hmitype.mpage.changobjattch(object_index, field, value)", functions)
        self.assertIn("hmitype.appbianyi.FileBianyi(myapp, output_tft, log, CompileMode.OutPutTFT)", functions)

    def test_run_hook_script_allows_project_level_save_dump_compile_without_object(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            hmi_path = root / "lcd_test.HMI"
            hmi_path.write_bytes(b"seed")
            payload = {
                "hmi_path": str(hmi_path),
                "out_dir": str(root / "out"),
                "actions": [
                    {"kind": "save"},
                    {"kind": "dump-page"},
                    {"kind": "compile", "output": str(root / "out" / "compiled.tft")},
                ],
            }
            with mock.patch.object(
                official_hmi_hook_runner.official_gui_host_select,
                "run_probe",
                return_value={
                    "returncode": 0,
                    "report_path": str(root / "host.json"),
                    "page_dump_path": str(root / "host.json.page.bin"),
                    "compile_output_path": str(root / "out" / "compiled.tft"),
                    "report_json": {"status": "ok", "saved_project": 1},
                },
            ) as run_probe:
                report = official_hmi_hook_runner.run_hook_script(payload)

        self.assertEqual(report["status"], "ok")
        kwargs = run_probe.call_args.kwargs
        self.assertEqual(kwargs["object_index"], -1)
        self.assertTrue(kwargs["force_save"])
        self.assertTrue(kwargs["force_page_dump"])
        self.assertEqual(Path(kwargs["compile_output_path"]).name, "compiled.tft")

    def test_host_select_command_appends_save_and_dump_flags(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            hmi_path = root / "lcd_test.HMI"
            hmi_path.write_bytes(b"seed")
            (root / "USART HMI.exe").write_bytes(b"exe")
            (root / "ACTR.dll").write_bytes(b"dll")
            report_path = root / "host.json"
            page_dump = report_path.with_suffix(report_path.suffix + ".page.bin")
            report_path.write_text('{"status":"ok","saved_project":1}', encoding="utf-8")
            page_dump.write_bytes(b"page")

            fake_proc = mock.Mock()
            fake_proc.poll.return_value = 0
            fake_proc.communicate.return_value = ("", "")
            fake_proc.returncode = 0

            def fake_popen(*_args, **_kwargs):
                report_path.write_text('{"status":"ok","saved_project":1}', encoding="utf-8")
                page_dump.write_bytes(b"page")
                return fake_proc

            with mock.patch.object(official_gui_host_select, "ensure_binary", return_value=None):
                with mock.patch.object(
                    official_gui_host_select,
                    "_extract_main_hmi_metadata_hint",
                    return_value={"appmedata_string": "", "ram1_open": 0},
                ):
                    with mock.patch.object(
                        official_gui_host_select,
                        "_ensure_runtime_soft_open_markers",
                        return_value=[],
                    ):
                        with mock.patch.object(official_gui_host_select, "_prepare_writable_runtime", return_value=root):
                            with mock.patch.object(official_gui_host_select.shutil, "copy2", return_value=None):
                                with mock.patch.object(official_gui_host_select.subprocess, "Popen", side_effect=fake_popen):
                                    result = official_gui_host_select.run_probe(
                                        hmi_path=hmi_path,
                                        page_index=0,
                                        page_resource="0.pa",
                                        object_index=-1,
                                        report_path=report_path,
                                        force_save=True,
                                        force_page_dump=True,
                                        install_dir=root,
                                    )

        self.assertEqual(result["command"][-4:-2], ["1", "1"])
        self.assertTrue(result["saved_hmi_in_place"])
        self.assertNotIn("patched_hmi_via_page_dump", result)


if __name__ == "__main__":
    unittest.main()
