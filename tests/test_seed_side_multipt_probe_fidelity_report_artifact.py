from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT = Path("examples/lifecycle_runtime_smoke/seed_side_multipt_probe_fidelity_2026-05-21.json")


class SeedSideMultiPageProbeFidelityReportArtifactTests(unittest.TestCase):
    def test_artifact_prioritizes_textselect_and_filebrowser_over_filestream(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        cases = payload["cases"]
        conclusions = payload["conclusions"]

        self.assertEqual(payload["status"], "seed-side-fidelity-compared")
        self.assertTrue(cases["filebrowser"]["compiled_fidelity_ok"])
        self.assertTrue(cases["textselect"]["compiled_fidelity_ok"])
        self.assertTrue(cases["filestream"]["compiled_fidelity_ok"])
        self.assertTrue(cases["filestream"]["user_records_match_after_runtime_index_normalization"])
        self.assertFalse(cases["filestream"]["page_event_table_identical"])
        self.assertTrue(conclusions["filebrowser_seed_side_probe_is_compiled_faithful_modulo_runtime_index_and_event_shift"])
        self.assertTrue(conclusions["textselect_seed_side_probe_is_compiled_faithful_modulo_runtime_index_and_event_shift"])
        self.assertTrue(conclusions["filestream_seed_side_probe_has_a_small_page_event_delta"])
        self.assertTrue(conclusions["seed_side_runtime_limiter_runner_should_treat_textselect_as_the_strongest_control"])


if __name__ == "__main__":
    unittest.main()
