from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path("reverse_usarthmi/hmi_donor_lowlevel_probe_20260522")
CORPUS_ROOT = ROOT / "fixture_corpus"
SUMMARY = ROOT / "donor_patch_capability_summary.json"


class HMIDonorFixtureCorpusTests(unittest.TestCase):
    def test_required_fixture_directories_contain_required_files(self) -> None:
        if not CORPUS_ROOT.exists():
            self.skipTest(f"local donor fixture corpus missing: {CORPUS_ROOT}")
        required_fixtures = {
            "page0_basic_add_text_or_button",
            "page0_basic_delete",
            "page0_basic_move",
            "page0_basic_set_txt",
            "page0_filebrowser_add_or_preserve",
            "page0_textselect_add_or_preserve",
            "page0_datarecord_add_or_preserve",
            "page0_filestream_add_or_preserve",
            "case80_like_from_case83_delete_b1",
        }
        required_files = {
            "input_donor.HMI",
            "patch_spec.json",
            "generated.HMI",
            "open_lowlevel.output.json",
            "compile_lowlevel.output.json",
            "capability_result.json",
            "manifest.json",
        }
        for case_id in required_fixtures:
            fixture_dir = CORPUS_ROOT / "fixtures" / case_id
            with self.subTest(case_id=case_id):
                self.assertTrue(fixture_dir.exists())
                existing = {path.name for path in fixture_dir.iterdir() if path.is_file()}
                self.assertEqual(required_files - existing, set())

    def test_specs_and_corpus_manifest_exist(self) -> None:
        if not CORPUS_ROOT.exists():
            self.skipTest(f"local donor fixture corpus missing: {CORPUS_ROOT}")
        corpus_manifest = json.loads((CORPUS_ROOT / "corpus_manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(Path(corpus_manifest["schema_path"]).exists())
        self.assertTrue(Path(corpus_manifest["summary_json"]).exists())
        self.assertTrue(Path(corpus_manifest["matrix_md"]).exists())
        self.assertTrue(Path(corpus_manifest["specs_dir"]).exists())
        self.assertTrue(Path(corpus_manifest["fixtures_dir"]).exists())
        self.assertTrue(Path(corpus_manifest["donor_probes_dir"]).exists())

    def test_spec_files_exist_for_fixture_records(self) -> None:
        if not SUMMARY.exists():
            self.skipTest(f"local donor patch summary missing: {SUMMARY}")
        payload = json.loads(SUMMARY.read_text(encoding="utf-8"))
        generated_ids = [record["case_id"] for record in payload["records"] if record["kind"] == "generated_fixture"]
        for case_id in generated_ids:
            with self.subTest(case_id=case_id):
                self.assertTrue((CORPUS_ROOT / "specs" / f"{case_id}.json").exists())
