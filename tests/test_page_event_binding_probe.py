from __future__ import annotations

from pathlib import Path
import unittest

from tools.page_event_binding_probe import probe_manifest


ROOT = Path(__file__).resolve().parents[1]
PAGE1_LOAD_MANIFEST = (
    ROOT
    / "reverse_usarthmi"
    / "page1_load_printh_event_probe"
    / "local_build"
    / "manifest.json"
)
PAGE1_BUTTON_PRINTH_MANIFEST = (
    ROOT
    / "reverse_usarthmi"
    / "page1_button_printh_event_probe"
    / "local_build"
    / "manifest.json"
)


@unittest.skipUnless(
    PAGE1_LOAD_MANIFEST.exists() and PAGE1_BUTTON_PRINTH_MANIFEST.exists(),
    "local page1 event probe manifests are not available",
)
class PageEventBindingProbeTests(unittest.TestCase):
    def test_page1_load_probe_has_payload_but_no_callback_binding(self) -> None:
        report = probe_manifest(PAGE1_LOAD_MANIFEST)
        diagnosis = report["diagnosis"]

        self.assertTrue(diagnosis["non_empty_page_load_event"])
        self.assertTrue(diagnosis["page_event_table_found"])
        self.assertTrue(diagnosis["page_mirror_event_offset_points_to_table"])
        self.assertFalse(diagnosis["page_load_callback_slot_points_to_table"])

    def test_live_proven_page1_button_event_has_callback_binding(self) -> None:
        report = probe_manifest(PAGE1_BUTTON_PRINTH_MANIFEST)
        callbacks = report["diagnosis"]["object_event_callbacks_found"]

        self.assertEqual(
            callbacks,
            [{"objname": "ping0", "slots": ["maybe_load_or_up_0x10"]}],
        )


if __name__ == "__main__":
    unittest.main()
