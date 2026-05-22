from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .tft_patch import DEFAULT_CASE_ROOT


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
    notes: str | None = None

    @property
    def hmi_path(self) -> Path:
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


def iter_lowlevel_accepted_complex_donors() -> tuple[HMIDonor, ...]:
    return tuple(
        donor
        for donor in HMI_COMPLEX_DONORS
        if donor.lowlevel_open_accepted is True and donor.lowlevel_compile_accepted is True
    )


def find_proven_complex_hmi_donor(
    blocks,
    *,
    require_compile_preserved_complex_page: bool = True,
) -> Path | None:
    signature = block_signature_of(blocks)
    for donor in iter_proven_complex_donors(
        require_compile_preserved_complex_page=require_compile_preserved_complex_page,
    ):
        if donor.matches_signature(signature) and donor.hmi_path.exists():
            return donor.hmi_path
    return None


def find_lowlevel_accepted_complex_hmi_donor(blocks) -> Path | None:
    signature = block_signature_of(blocks)
    for donor in iter_lowlevel_accepted_complex_donors():
        if donor.matches_signature(signature) and donor.hmi_path.exists():
            return donor.hmi_path
    return None
