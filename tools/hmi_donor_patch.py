from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from usarthmi.hmi_donor_patch import *  # noqa: F401,F403
from usarthmi.hmi_donor_patch import main


if __name__ == "__main__":
    raise SystemExit(main())
