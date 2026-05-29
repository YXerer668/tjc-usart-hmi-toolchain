from __future__ import annotations

import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LIB_ROOT = REPO_ROOT / "firmware" / "usarthmi_serial"


class UsartHmiSerialLibraryTests(unittest.TestCase):
    def test_header_declares_small_public_api(self) -> None:
        header = (LIB_ROOT / "usarthmi_serial.h").read_text(encoding="utf-8")
        for symbol in (
            "usarthmi_init",
            "usarthmi_send_cmd",
            "usarthmi_set_value",
            "usarthmi_set_txt",
            "usarthmi_printh",
            "usarthmi_rx_feed",
            "usarthmi_parse_frame",
        ):
            self.assertIn(symbol, header)

    @unittest.skipIf(shutil.which("gcc") is None, "gcc is not available")
    def test_c99_library_compiles_and_handles_basic_commands(self) -> None:
        test_c = r"""
        #include <stdint.h>
        #include <stddef.h>
        #include <string.h>
        #include "usarthmi_serial.h"

        static uint8_t sink[512];
        static size_t sink_len;

        static int write_cb(const uint8_t *data, size_t len, void *user) {
            (void)user;
            if (sink_len + len > sizeof(sink)) {
                return -1;
            }
            memcpy(&sink[sink_len], data, len);
            sink_len += len;
            return 0;
        }

        static void reset_sink(void) {
            memset(sink, 0, sizeof(sink));
            sink_len = 0;
        }

        static int expect_cmd(const char *cmd) {
            const size_t n = strlen(cmd);
            return sink_len == n + 3u &&
                   memcmp(sink, cmd, n) == 0 &&
                   sink[n] == 0xFFu &&
                   sink[n + 1u] == 0xFFu &&
                   sink[n + 2u] == 0xFFu;
        }

        int main(void) {
            usarthmi_t hmi;
            usarthmi_frame_t frame;
            usarthmi_rx_t rx;
            const uint8_t marker[] = {0x23u, 0x31u};
            const uint8_t number_frame[] = {0x71u, 0x2Au, 0x00u, 0x00u, 0x00u, 0xFFu, 0xFFu, 0xFFu};
            const uint8_t touch_frame[] = {0x65u, 0x01u, 0x02u, 0x01u, 0xFFu, 0xFFu, 0xFFu};
            int rc = 0;
            size_t i;

            usarthmi_init(&hmi, write_cb, 0);

            reset_sink();
            if (usarthmi_bkcmd(&hmi, 2) != USARTHMI_OK || !expect_cmd("bkcmd=2")) {
                return 1;
            }

            reset_sink();
            if (usarthmi_set_value(&hmi, "m0", 123) != USARTHMI_OK || !expect_cmd("m0.val=123")) {
                return 2;
            }

            reset_sink();
            if (usarthmi_printh(&hmi, marker, sizeof(marker)) != USARTHMI_OK || !expect_cmd("printh 23 31")) {
                return 3;
            }

            if (usarthmi_set_txt(&hmi, "t0", "bad\"value") != USARTHMI_ERR_ARGUMENT) {
                return 4;
            }

            if (usarthmi_parse_frame(number_frame, sizeof(number_frame), &frame) != USARTHMI_OK ||
                frame.type != USARTHMI_FRAME_NUMBER ||
                frame.number != 42) {
                return 5;
            }

            usarthmi_rx_init(&rx);
            for (i = 0; i < sizeof(touch_frame); ++i) {
                rc = usarthmi_rx_feed(&rx, touch_frame[i], &frame);
            }
            if (rc != USARTHMI_RX_FRAME ||
                frame.type != USARTHMI_FRAME_TOUCH ||
                frame.page != 1u ||
                frame.component != 2u ||
                frame.event != 1u) {
                return 6;
            }

            return 0;
        }
        """

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "test_usarthmi_serial.c"
            exe = Path(temp_dir) / "test_usarthmi_serial.exe"
            source.write_text(textwrap.dedent(test_c), encoding="utf-8")
            subprocess.run(
                [
                    "gcc",
                    "-std=c99",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-I",
                    str(LIB_ROOT),
                    str(source),
                    str(LIB_ROOT / "usarthmi_serial.c"),
                    "-o",
                    str(exe),
                ],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run([str(exe)], check=True, capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
