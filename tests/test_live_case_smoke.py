from __future__ import annotations

import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools.live_case_smoke import run_smoke


class LiveCaseSmokeTests(unittest.TestCase):
    def test_run_smoke_blocks_upload_when_generated_tft_checksum_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            args = _args(Path(temp_dir))

            with (
                _patched_case_build(clean_tft_bytes=b"bad-tft"),
                patch("tools.live_case_smoke.inspect_tft_checksum", side_effect=RuntimeError("bad checksum")),
                patch("tools.live_case_smoke._model_preflight_check") as model_preflight,
                patch("tools.live_case_smoke.upload_tft") as upload_tft,
                patch("tools.live_case_smoke._run_serial_checks") as run_serial_checks,
            ):
                result = run_smoke(args)

        model_preflight.assert_not_called()
        upload_tft.assert_not_called()
        run_serial_checks.assert_not_called()
        self.assertFalse(result["checksum"]["valid"])
        self.assertEqual(result["checksum"]["error"], "bad checksum")
        self.assertEqual(result["upload"]["reason"], "invalid_tft_checksum")
        self.assertTrue(result["summary"]["upload_blocked"])
        self.assertTrue(result["summary"]["serial_checks_skipped"])
        self.assertFalse(result["summary"]["ok"])

    def test_run_smoke_blocks_upload_when_live_model_mismatches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            args = _args(Path(temp_dir))

            with (
                _patched_case_build(clean_tft_bytes=b"valid-tft"),
                patch("tools.live_case_smoke.inspect_tft_checksum", return_value={"valid": True}),
                patch(
                    "tools.live_case_smoke._model_preflight_check",
                    return_value={
                        "required_model": "TJC8048X543_011C",
                        "actual_model": "TJC8048X550_011",
                        "connect": {"ok": True},
                        "ok": False,
                    },
                ) as model_preflight,
                patch("tools.live_case_smoke.upload_tft") as upload_tft,
                patch("tools.live_case_smoke._run_serial_checks") as run_serial_checks,
            ):
                result = run_smoke(args)

        model_preflight.assert_called_once()
        upload_tft.assert_not_called()
        run_serial_checks.assert_not_called()
        self.assertEqual(result["upload"]["reason"], "model_preflight_failed")
        self.assertEqual(result["model_preflight"]["actual_model"], "TJC8048X550_011")
        self.assertFalse(result["summary"]["model_preflight_ok"])
        self.assertTrue(result["summary"]["upload_blocked"])
        self.assertTrue(result["summary"]["serial_checks_skipped"])
        self.assertFalse(result["summary"]["ok"])

    def test_run_smoke_uploads_after_checksum_and_model_preflight_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            args = _args(temp_path)

            with (
                _patched_case_build(clean_tft_bytes=b"valid-tft"),
                patch("tools.live_case_smoke.inspect_tft_checksum", return_value={"valid": True}),
                patch(
                    "tools.live_case_smoke._model_preflight_check",
                    return_value={
                        "required_model": "TJC8048X543_011C",
                        "actual_model": "TJC8048X543_011C",
                        "connect": {"ok": True},
                        "ok": True,
                    },
                ) as model_preflight,
                patch(
                    "tools.live_case_smoke.upload_tft",
                    return_value=SimpleNamespace(to_dict=lambda: {"skipped": False}),
                ) as upload_tft,
                patch("tools.live_case_smoke._run_serial_checks", return_value=[]) as run_serial_checks,
            ):
                result = run_smoke(args)

            self.assertTrue((temp_path / "out" / "case_99_fake" / "known_current.tft").exists())

        model_preflight.assert_called_once()
        upload_tft.assert_called_once()
        run_serial_checks.assert_called_once()
        self.assertTrue(result["summary"]["ok"])
        self.assertFalse(result["summary"]["upload_blocked"])
        self.assertFalse(result["summary"]["serial_checks_skipped"])


def _args(temp_dir: Path) -> Namespace:
    case_root = temp_dir / "cases"
    case_dir = case_root / "case_99_fake"
    case_dir.mkdir(parents=True)
    (case_dir / "lcd_test.HMI").write_bytes(b"hmi")
    baseline_tft = temp_dir / "baseline.tft"
    baseline_tft.write_bytes(b"baseline")
    seed_pa = temp_dir / "seed.pa"
    seed_pa.write_bytes(b"seed")
    return Namespace(
        case_name="case_99_fake",
        case_root=case_root,
        baseline_tft=baseline_tft,
        seed_pa=seed_pa,
        out_root=temp_dir / "out",
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
        progress=False,
    )


def _patched_case_build(*, clean_tft_bytes: bytes):
    patchers = []

    def fake_rebuild(_baseline_tft, *, seed_pa, target_pa, out_tft):  # type: ignore[no-untyped-def]
        out_tft.write_bytes(clean_tft_bytes)
        return SimpleNamespace(to_dict=lambda: {"rebuilt": True, "target_pa": str(target_pa)})

    clean_page = SimpleNamespace(serialize=lambda: b"clean-page")
    patchers.append(patch("tools.live_case_smoke.load_page_file", return_value=SimpleNamespace()))
    patchers.append(patch("tools.live_case_smoke._load_hmi_page0", return_value=SimpleNamespace()))
    patchers.append(
        patch(
            "tools.live_case_smoke._make_clean_page",
            return_value=(clean_page, ["page0"], [], []),
        )
    )
    patchers.append(patch("tools.live_case_smoke.patch_rebuild_page_tft", fake_rebuild))
    return _PatchGroup(patchers)


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
