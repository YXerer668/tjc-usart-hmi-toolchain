from __future__ import annotations

import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools.live_page_smoke import _load_hmi_pages, run_smoke


class LivePageSmokeTests(unittest.TestCase):
    def test_load_hmi_pages_uses_container_order_for_runtime_page_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            hmi_path = Path(temp_dir) / "lcd_test.HMI"
            hmi_path.write_bytes(b"zero one two shadow")
            entries = [
                SimpleNamespace(name="1.pa", in_file=True, data_offset=5, length=3),
                SimpleNamespace(name="\x000.pa", in_file=True, data_offset=14, length=6),
                SimpleNamespace(name="0.pa", in_file=True, data_offset=0, length=4),
                SimpleNamespace(name="2.pa", in_file=True, data_offset=9, length=3),
            ]
            parsed_pages = {
                b"zero": SimpleNamespace(page_name="page0", blocks=[]),
                b"one": SimpleNamespace(page_name="page1", blocks=[]),
                b"two": SimpleNamespace(page_name="page2", blocks=[]),
            }

            def fake_parse(data: bytes):  # type: ignore[no-untyped-def]
                return parsed_pages[data]

            with (
                patch("tools.live_page_smoke.inspect_hmi", return_value=SimpleNamespace(entries=entries)),
                patch("tools.live_page_smoke.parse_page_data", fake_parse),
            ):
                pages = _load_hmi_pages(hmi_path)

        self.assertEqual([page.page_id for page in pages], [0, 1, 2])
        self.assertEqual([page.entry_name for page in pages], ["1.pa", "0.pa", "2.pa"])
        self.assertEqual([page.page_name for page in pages], ["page1", "page0", "page2"])

    def test_run_smoke_blocks_upload_when_tft_checksum_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            args, _hmi_path, _tft_path, _out_dir = _args(Path(temp_dir))

            with (
                _patched_page_inputs(_hmi_path, _tft_path, _out_dir),
                patch("tools.live_page_smoke._inspect_tft_checksum_safe", return_value={"valid": False, "error": "bad"}),
                patch("tools.live_page_smoke._model_preflight_check") as model_preflight,
                patch("tools.live_page_smoke.upload_tft") as upload_tft,
                patch("tools.live_page_smoke._run_page_checks") as run_page_checks,
            ):
                result = run_smoke(args)

        model_preflight.assert_not_called()
        upload_tft.assert_not_called()
        run_page_checks.assert_not_called()
        self.assertEqual(result["upload"]["reason"], "invalid_tft_checksum")
        self.assertFalse(result["summary"]["checksum_valid"])
        self.assertTrue(result["summary"]["upload_blocked"])
        self.assertTrue(result["summary"]["serial_checks_skipped"])
        self.assertFalse(result["summary"]["ok"])

    def test_run_smoke_blocks_upload_when_model_mismatches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            args, _hmi_path, _tft_path, _out_dir = _args(Path(temp_dir))

            with (
                _patched_page_inputs(_hmi_path, _tft_path, _out_dir),
                patch("tools.live_page_smoke._inspect_tft_checksum_safe", return_value={"valid": True}),
                patch(
                    "tools.live_page_smoke._model_preflight_check",
                    return_value={
                        "required_model": "TJC8048X543_011C",
                        "actual_model": "TJC8048X550_011",
                        "connect": {"ok": True},
                        "ok": False,
                    },
                ) as model_preflight,
                patch("tools.live_page_smoke.upload_tft") as upload_tft,
                patch("tools.live_page_smoke._run_page_checks") as run_page_checks,
            ):
                result = run_smoke(args)

        model_preflight.assert_called_once()
        upload_tft.assert_not_called()
        run_page_checks.assert_not_called()
        self.assertEqual(result["upload"]["reason"], "model_preflight_failed")
        self.assertEqual(result["model_preflight"]["actual_model"], "TJC8048X550_011")
        self.assertFalse(result["summary"]["model_preflight_ok"])
        self.assertTrue(result["summary"]["upload_blocked"])
        self.assertTrue(result["summary"]["serial_checks_skipped"])
        self.assertFalse(result["summary"]["ok"])

    def test_run_smoke_uploads_after_checksum_and_model_preflight_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            args, _hmi_path, _tft_path, out_dir = _args(Path(temp_dir))

            with (
                _patched_page_inputs(_hmi_path, _tft_path, out_dir),
                patch("tools.live_page_smoke._inspect_tft_checksum_safe", return_value={"valid": True}),
                patch(
                    "tools.live_page_smoke._model_preflight_check",
                    return_value={
                        "required_model": "TJC8048X543_011C",
                        "actual_model": "TJC8048X543_011C",
                        "connect": {"ok": True},
                        "ok": True,
                    },
                ) as model_preflight,
                patch(
                    "tools.live_page_smoke.upload_tft",
                    return_value=SimpleNamespace(to_dict=lambda: {"skipped": False}),
                ) as upload_tft,
                patch("tools.live_page_smoke._run_page_checks", return_value=[]) as run_page_checks,
            ):
                result = run_smoke(args)

            self.assertTrue((out_dir / "known_current.tft").exists())

        model_preflight.assert_called_once()
        upload_tft.assert_called_once()
        run_page_checks.assert_called_once()
        self.assertTrue(result["summary"]["ok"])
        self.assertFalse(result["summary"]["upload_blocked"])
        self.assertFalse(result["summary"]["serial_checks_skipped"])


def _args(temp_dir: Path) -> tuple[Namespace, Path, Path, Path]:
    hmi_path = temp_dir / "lcd_test.HMI"
    hmi_path.write_bytes(b"hmi")
    tft_path = temp_dir / "lcd_test.tft"
    tft_path.write_bytes(b"tft")
    out_dir = temp_dir / "out"
    args = Namespace(
        case_name="case_31_fake_page",
        case_root=temp_dir / "cases",
        hmi=None,
        tft=None,
        out_root=temp_dir / "live_page_smoke",
        port="COM36",
        baud=9600,
        download_baud=921600,
        timeout_ms=3000,
        post_upload_wait_s=0,
        upload=True,
        skip_upload_if_identical=False,
        require_model="TJC8048X543_011C",
        capture=False,
        camera_index=0,
        camera_backend="dshow",
        camera_warmup_s=0,
    )
    return args, hmi_path, tft_path, out_dir


def _patched_page_inputs(hmi_path: Path, tft_path: Path, out_dir: Path):
    page = SimpleNamespace(to_dict=lambda: {"page_id": 0, "page_name": "page0", "objects": []})
    return _PatchGroup(
        [
            patch("tools.live_page_smoke._resolve_paths", return_value=(hmi_path, tft_path, out_dir)),
            patch("tools.live_page_smoke._load_hmi_pages", return_value=[page]),
        ]
    )


class _PatchGroup:
    def __init__(self, patchers):
        self._patchers = patchers

    def __enter__(self):
        for patcher in self._patchers:
            patcher.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        for patcher in reversed(self._patchers):
            patcher.__exit__(exc_type, exc, tb)
        return False


if __name__ == "__main__":
    unittest.main()
