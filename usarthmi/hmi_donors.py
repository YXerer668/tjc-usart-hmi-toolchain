from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .tft_patch import DEFAULT_CASE_ROOT

REPO_ROOT = Path(__file__).resolve().parents[1]
DONOR_FIXTURE_ROOT = REPO_ROOT / "reverse_usarthmi" / "hmi_donor_lowlevel_probe_20260522"


@dataclass(frozen=True, slots=True)
class HMIDonor:
    donor_id: str
    case_name: str
    block_signature: tuple[tuple[str, str], ...]
    evidence: str
    reopen_preserved_blocks: bool | None = None
    compile_success: bool | None = None
    compile_preserved_complex_page: bool | None = None
    lowlevel_open_accepted: bool | None = None
    lowlevel_compile_accepted: bool | None = None
    hmi_relative_path: str = "lcd_test.HMI"
    hmi_path_override: str | None = None
    notes: str | None = None

    @property
    def hmi_path(self) -> Path:
        if self.hmi_path_override:
            return Path(self.hmi_path_override)
        return Path(DEFAULT_CASE_ROOT) / self.case_name / self.hmi_relative_path

    def matches_signature(self, signature: Iterable[tuple[str | None, str | None]]) -> bool:
        normalized = tuple((str(name or ""), str(type_code or "")) for name, type_code in signature)
        return normalized == self.block_signature

    def is_officially_accepted(
        self,
        *,
        require_compile_preserved_complex_page: bool = True,
    ) -> bool:
        if self.lowlevel_open_accepted is True and self.lowlevel_compile_accepted is True:
            return True
        if self.reopen_preserved_blocks is not True:
            return False
        if require_compile_preserved_complex_page:
            return self.compile_success is True and self.compile_preserved_complex_page is True
        return True


HMI_COMPLEX_DONORS: tuple[HMIDonor, ...] = (
    HMIDonor(
        donor_id="page0-bar1-only-exact-delete-from-case83",
        case_name="",
        block_signature=(
            ("page0", "y"),
            ("t0", "t"),
            ("b0", "b"),
            ("p0", "p"),
            ("bar1", "j"),
        ),
        evidence="examples/advanced_direct_tft_demo/bar1_compile_positive_donor_2026-05-23.json",
        reopen_preserved_blocks=True,
        compile_success=True,
        compile_preserved_complex_page=True,
        lowlevel_open_accepted=True,
        lowlevel_compile_accepted=True,
        hmi_path_override=str(REPO_ROOT / "reverse_usarthmi" / "case83_delete_data0_select0_b1_probe_20260523" / "generated.HMI"),
        notes=(
            "Repo-local compile-positive donor from the exact case83 donor with data0/select0/b1 deleted. "
            "It preserves page0/t0/b0/p0/bar1 and is low-level compile/reopen positive, making it a "
            "compile-positive container for progress-only builder pages that keep the baseline controls."
        ),
    ),
    HMIDonor(
        donor_id="page0-bar1-data0-exact-delete-select0-b1-from-case83",
        case_name="",
        block_signature=(
            ("page0", "y"),
            ("t0", "t"),
            ("b0", "b"),
            ("p0", "p"),
            ("bar1", "j"),
            ("data0", "B"),
        ),
        evidence="examples/advanced_direct_tft_demo/bar1_data0_compile_positive_donor_2026-05-23.json",
        reopen_preserved_blocks=True,
        compile_success=True,
        compile_preserved_complex_page=True,
        lowlevel_open_accepted=True,
        lowlevel_compile_accepted=True,
        hmi_path_override=str(REPO_ROOT / "reverse_usarthmi" / "case83_delete_select0_b1_probe_20260523" / "generated.HMI"),
        notes=(
            "Repo-local compile-positive donor from the exact case83 donor with select0/b1 deleted. "
            "It preserves page0/t0/b0/p0/bar1/data0 and is low-level compile/reopen positive, making it a "
            "compile-positive container for builder pages that stop at the data-record stage."
        ),
    ),
    HMIDonor(
        donor_id="case80-exact",
        case_name="case_80_datarecord_textselect_official_positive_oracle",
        block_signature=(
            ("page0", "y"),
            ("t0", "t"),
            ("b0", "b"),
            ("p0", "p"),
            ("bar1", "j"),
            ("data0", "B"),
            ("select0", "D"),
        ),
        evidence="examples/advanced_direct_tft_demo/official_hmi_roundtrip_supported_datarecord_mixes_2026-05-19.json",
        reopen_preserved_blocks=True,
        compile_success=True,
        compile_preserved_complex_page=True,
        lowlevel_open_accepted=True,
        lowlevel_compile_accepted=True,
        notes=(
            "Exact donor-aligned case80 HMI survives official reopen/save and compiles back "
            "to the positive complex-page size class, and the current 2026-05-22 "
            "fixture-corpus low-level probe accepts it. Keep the historical failed "
            "case80 sample separate from the current donor bytes."
        ),
    ),
    HMIDonor(
        donor_id="case83-exact",
        case_name="case_83_datarecord_textselect_button_official_positive_oracle",
        block_signature=(
            ("page0", "y"),
            ("t0", "t"),
            ("b0", "b"),
            ("p0", "p"),
            ("bar1", "j"),
            ("data0", "B"),
            ("select0", "D"),
            ("b1", "b"),
        ),
        evidence="examples/advanced_direct_tft_demo/official_hmi_roundtrip_supported_datarecord_mixes_2026-05-19.json",
        reopen_preserved_blocks=True,
        compile_success=True,
        compile_preserved_complex_page=True,
        lowlevel_open_accepted=True,
        lowlevel_compile_accepted=True,
        notes=(
            "Exact donor-aligned case83 HMI survives official reopen/save and compiles back "
            "to the positive complex-page size class, and the 2026-05-22 headless "
            "open-lowlevel/compile-lowlevel probe accepted it."
        ),
    ),
    HMIDonor(
        donor_id="case85-exact-unproven-hmi-roundtrip",
        case_name="case_85_datarecord_sltext_official_positive_oracle",
        block_signature=(
            ("page0", "y"),
            ("t0", "t"),
            ("b0", "b"),
            ("p0", "p"),
            ("bar1", "j"),
            ("data0", "B"),
            ("slt0", ">"),
        ),
        evidence="reverse_usarthmi/hmi_donor_lowlevel_probe_20260522/case85_exact/lcd_test.official_lowlevel.json",
        lowlevel_open_accepted=True,
        lowlevel_compile_accepted=True,
        notes=(
            "Exact case85 donor is accepted by the 2026-05-22 headless "
            "open-lowlevel/compile-lowlevel probe even though earlier docs did not yet "
            "record GUI reopen/save roundtrip closure."
        ),
    ),
)


def block_signature_of(blocks) -> tuple[tuple[str, str], ...]:
    return tuple((str(getattr(block, "objname", "") or ""), str(getattr(block, "type_code", "") or "")) for block in blocks)


def iter_proven_complex_donors(
    *,
    require_compile_preserved_complex_page: bool = True,
) -> tuple[HMIDonor, ...]:
    return tuple(
        donor
        for donor in HMI_COMPLEX_DONORS
        if donor.is_officially_accepted(
            require_compile_preserved_complex_page=require_compile_preserved_complex_page,
        )
    )


def find_proven_complex_hmi_donor_entry(
    blocks,
    *,
    require_compile_preserved_complex_page: bool = True,
) -> HMIDonor | None:
    signature = block_signature_of(blocks)
    for donor in iter_proven_complex_donors(
        require_compile_preserved_complex_page=require_compile_preserved_complex_page,
    ):
        if donor.matches_signature(signature) and donor.hmi_path.exists():
            return donor
    return None


def iter_lowlevel_accepted_complex_donors() -> tuple[HMIDonor, ...]:
    return tuple(
        donor
        for donor in HMI_COMPLEX_DONORS
        if donor.lowlevel_open_accepted is True and donor.lowlevel_compile_accepted is True
    )


def find_prefix_proven_complex_hmi_donor_entry(
    blocks,
    *,
    require_compile_preserved_complex_page: bool = True,
) -> HMIDonor | None:
    signature = block_signature_of(blocks)
    matches: list[HMIDonor] = []
    for donor in iter_proven_complex_donors(
        require_compile_preserved_complex_page=require_compile_preserved_complex_page,
    ):
        if not donor.hmi_path.exists():
            continue
        if len(donor.block_signature) >= len(signature):
            continue
        if signature[: len(donor.block_signature)] == donor.block_signature:
            matches.append(donor)
    if not matches:
        return None
    matches.sort(key=lambda donor: len(donor.block_signature), reverse=True)
    return matches[0]


def find_proven_complex_hmi_donor(
    blocks,
    *,
    require_compile_preserved_complex_page: bool = True,
) -> Path | None:
    donor = find_proven_complex_hmi_donor_entry(
        blocks,
        require_compile_preserved_complex_page=require_compile_preserved_complex_page,
    )
    return donor.hmi_path if donor is not None else None


def find_lowlevel_accepted_complex_hmi_donor(blocks) -> Path | None:
    signature = block_signature_of(blocks)
    for donor in iter_lowlevel_accepted_complex_donors():
        if donor.matches_signature(signature) and donor.hmi_path.exists():
            return donor.hmi_path
    return None
