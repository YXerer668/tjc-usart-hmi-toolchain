from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable


class WidgetSupport(str, Enum):
    SUPPORTED = "supported"
    PENDING = "pending"
    UNSUPPORTED_CURRENT_TARGET = "unsupported-current-target"


class WidgetWriter(str, Enum):
    BUILT_IN = "built-in"
    FIXTURE = "fixture"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class WidgetTypeInfo:
    type: str
    support: WidgetSupport
    writer: WidgetWriter = WidgetWriter.NONE
    aliases: tuple[str, ...] = ()
    fixture_case: str | None = None
    type_code: str | None = None
    reason: str | None = None
    evidence: str | None = None
    evidence_level: str | None = None
    build_scope: str | None = None
    claim_level: str | None = None
    can_build_tft: bool | None = None
    not_claimed: tuple[str, ...] = ()
    notes: str | None = None

    def to_dict(self, *, include_aliases: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": self.type,
            "support": self.support.value,
            "writer": self.writer.value,
        }
        if include_aliases:
            payload["aliases"] = list(self.aliases)
        if self.fixture_case is not None:
            payload["fixture_case"] = self.fixture_case
        if self.type_code is not None:
            payload["type_code"] = format_type_code(self.type_code)
        if self.reason is not None:
            payload["reason"] = self.reason
        if self.evidence is not None:
            payload["evidence"] = self.evidence
        if self.evidence_level is not None:
            payload["evidence_level"] = self.evidence_level
        if self.not_claimed:
            payload["not_claimed"] = list(self.not_claimed)
        if self.notes is not None:
            payload["notes"] = self.notes
        if self.writer == WidgetWriter.FIXTURE and (
            self.build_scope is not None or self.claim_level is not None or self.can_build_tft is not None
        ):
            can_build_tft = bool(self.can_build_tft) if self.can_build_tft is not None else False
            payload.update(
                {
                    "build_scope": self.build_scope or "hmi-only",
                    "claim_level": self.claim_level or "fixture-structure-clone",
                    "can_validate_scene": True,
                    "can_build_hmi": True,
                    "can_build_tft": can_build_tft,
                    "preview": "approximate",
                }
            )
        return payload


CURRENT_TARGET = "TJC8048X543_011C"


_WIDGETS: tuple[WidgetTypeInfo, ...] = (
    WidgetTypeInfo("button", WidgetSupport.SUPPORTED, WidgetWriter.BUILT_IN, aliases=("btn",)),
    WidgetTypeInfo("image", WidgetSupport.SUPPORTED, WidgetWriter.BUILT_IN, aliases=("pic", "picture")),
    WidgetTypeInfo("number", WidgetSupport.SUPPORTED, WidgetWriter.BUILT_IN),
    WidgetTypeInfo("text", WidgetSupport.SUPPORTED, WidgetWriter.BUILT_IN, aliases=("txt",)),
    WidgetTypeInfo("timer", WidgetSupport.SUPPORTED, WidgetWriter.BUILT_IN),
    WidgetTypeInfo(
        "animation",
        WidgetSupport.SUPPORTED,
        WidgetWriter.FIXTURE,
        aliases=("animated-image", "animated image", "gmov", "moving-picture", "moving picture"),
        fixture_case="case_47_gmov",
        type_code="\x02",
    ),
    WidgetTypeInfo(
        "audio",
        WidgetSupport.SUPPORTED,
        WidgetWriter.FIXTURE,
        aliases=("sound", "wav", "wave-audio"),
        fixture_case="case_49_audio",
        type_code="\x04",
    ),
    WidgetTypeInfo("slider", WidgetSupport.SUPPORTED, WidgetWriter.FIXTURE, fixture_case="case_17_slider", type_code="\x01"),
    WidgetTypeInfo("gauge", WidgetSupport.SUPPORTED, WidgetWriter.FIXTURE, aliases=("gauge1",), fixture_case="case_18_gauge", type_code="z"),
    WidgetTypeInfo("progress", WidgetSupport.SUPPORTED, WidgetWriter.FIXTURE, aliases=("progressbar",), fixture_case="case_20_progress", type_code="j"),
    WidgetTypeInfo("qrcode", WidgetSupport.SUPPORTED, WidgetWriter.FIXTURE, fixture_case="case_21_qrcode", type_code=":"),
    WidgetTypeInfo(
        "scrolling-text",
        WidgetSupport.SUPPORTED,
        WidgetWriter.FIXTURE,
        aliases=("marquee", "scrolling", "scrolling text"),
        fixture_case="case_22_scrolling_text",
        type_code="7",
    ),
    WidgetTypeInfo(
        "dual-button",
        WidgetSupport.SUPPORTED,
        WidgetWriter.FIXTURE,
        aliases=("dualbutton", "dual-state-button", "dual state button", "dual-state", "dualb"),
        fixture_case="case_23_dual_state_button",
        type_code="5",
    ),
    WidgetTypeInfo(
        "dualstate-button",
        WidgetSupport.SUPPORTED,
        WidgetWriter.FIXTURE,
        fixture_case="case_23_dual_state_button",
        type_code="5",
    ),
    WidgetTypeInfo(
        "state-button",
        WidgetSupport.SUPPORTED,
        WidgetWriter.FIXTURE,
        aliases=("statebutton", "state_btn", "state button", "toggle"),
        fixture_case="case_24_state_button",
        type_code="C",
    ),
    WidgetTypeInfo(
        "hotspot",
        WidgetSupport.SUPPORTED,
        WidgetWriter.FIXTURE,
        aliases=("hotspot-area", "hotspot-touch", "hotspot-touch-area"),
        fixture_case="case_25_hotspot_touch_area",
        type_code="m",
    ),
    WidgetTypeInfo("variable", WidgetSupport.SUPPORTED, WidgetWriter.FIXTURE, aliases=("var",), fixture_case="case_26_variable_numeric_string", type_code="4"),
    WidgetTypeInfo("waveform", WidgetSupport.SUPPORTED, WidgetWriter.FIXTURE, aliases=("wave",), fixture_case="case_27_waveform_basic", type_code="\x00"),
    WidgetTypeInfo("checkbox", WidgetSupport.SUPPORTED, WidgetWriter.FIXTURE, aliases=("checkboxes",), fixture_case="case_28_checkbox", type_code="8"),
    WidgetTypeInfo("radio", WidgetSupport.SUPPORTED, WidgetWriter.FIXTURE, aliases=("radio-button",), fixture_case="case_29_radio", type_code="9"),
    WidgetTypeInfo("crop-image", WidgetSupport.SUPPORTED, WidgetWriter.FIXTURE, fixture_case="case_30_crop_image", type_code="q"),
    WidgetTypeInfo("xfloat", WidgetSupport.SUPPORTED, WidgetWriter.FIXTURE, aliases=("float", "virtual-float"), fixture_case="case_36_xfloat", type_code=";"),
    WidgetTypeInfo("combobox", WidgetSupport.SUPPORTED, WidgetWriter.FIXTURE, aliases=("combo", "combo-box"), fixture_case="case_37_combobox", type_code="="),
    WidgetTypeInfo(
        "touch-capture",
        WidgetSupport.SUPPORTED,
        WidgetWriter.FIXTURE,
        aliases=("touchcap", "touch capture", "touch-capture-area"),
        fixture_case="case_45_touchcap_current_gui",
        type_code="\x05",
        notes="No-event object writer is available; event-bearing live probes are quarantined.",
    ),
    WidgetTypeInfo(
        "external-picture",
        WidgetSupport.SUPPORTED,
        WidgetWriter.FIXTURE,
        aliases=("external picture", "external-image", "external image", "expicture", "expic"),
        fixture_case="case_46_expicture_current_gui",
        type_code="<",
    ),
    WidgetTypeInfo("video", WidgetSupport.SUPPORTED, WidgetWriter.FIXTURE, fixture_case="case_48_video", type_code="\x03"),
    WidgetTypeInfo(
        "text-select",
        WidgetSupport.SUPPORTED,
        WidgetWriter.FIXTURE,
        aliases=("select-text", "select text", "text select", "textselect"),
        fixture_case="case_38_text_select",
        type_code="D",
        reason=(
            "case_38_text_select now has an official-GUI-created current-target HMI and "
            "work/output TFT oracle; local HMI authoring uses the fixture template, "
            "and the fixture-backed direct TFT rebuild path is experimental"
        ),
        evidence="examples/advanced_widget_case_outputs_2026-05-17.json",
        evidence_level="official-gui-created-work-output-oracle",
        build_scope="hmi-and-experimental-direct-tft",
        claim_level="fixture-structure-clone-plus-bit-perfect-current-target-tft",
        can_build_tft=True,
        notes=(
            "Direct TFT single-control readback and down-event printh runtime are live-proven; "
            "advanced mixes are limited to the explicitly documented examples."
        ),
        not_claimed=(
            "arbitrary property synthesis",
            "interactive runtime behavior beyond serial field readback and live-proven down-event printh markers",
            "event behavior beyond the live-proven down-event printh and documented ordinary no-event mix paths",
            "cross-model compatibility",
        ),
    ),
    WidgetTypeInfo(
        "sliding-text",
        WidgetSupport.SUPPORTED,
        WidgetWriter.FIXTURE,
        aliases=("sliding text", "sltext"),
        fixture_case="case_41_sltext",
        type_code=">",
        reason=(
            "case_41_sltext now has an official-GUI-created current-target HMI and "
            "work/output TFT oracle; local HMI authoring uses the fixture template, "
            "and the fixture-backed direct TFT rebuild path is experimental"
        ),
        evidence="examples/advanced_widget_case_outputs_2026-05-17.json",
        evidence_level="official-gui-created-work-output-oracle",
        build_scope="hmi-and-experimental-direct-tft",
        claim_level="fixture-structure-clone-plus-bit-perfect-current-target-tft",
        can_build_tft=True,
        notes=(
            "Direct TFT single-control readback and down-event printh runtime are live-proven; "
            "advanced mixes are limited to the explicitly documented examples."
        ),
        not_claimed=(
            "arbitrary property synthesis",
            "interactive runtime behavior beyond serial field readback and live-proven down-event printh markers",
            "event behavior beyond the live-proven down-event printh and documented ordinary no-event mix paths",
            "cross-model compatibility",
        ),
    ),
    WidgetTypeInfo(
        "data-record",
        WidgetSupport.SUPPORTED,
        WidgetWriter.FIXTURE,
        aliases=("datarecord", "data record"),
        fixture_case="case_42_datarecord",
        type_code="B",
        reason=(
            "case_42_datarecord now has an official-GUI-created current-target HMI and "
            "work/output TFT oracle; local HMI authoring uses the fixture template, "
            "and the fixture-shaped direct TFT rebuild path is experimental"
        ),
        evidence="examples/advanced_widget_case_outputs_2026-05-17.json",
        evidence_level="official-gui-created-work-output-oracle",
        build_scope="hmi-and-experimental-direct-tft",
        claim_level="fixture-structure-clone-plus-bit-perfect-current-target-tft",
        can_build_tft=True,
        notes=(
            "Direct TFT single-control readback, the case58-shaped ordinary b1.down printh "
            "event path, and the exact no-event case80 data-record plus text-select shape "
            "are live-proven; data-record-owned events still fail closed."
        ),
        not_claimed=(
            "arbitrary property synthesis",
            "interactive runtime behavior beyond serial field readback, the case58-shaped ordinary button-event marker, and the exact case80 no-event text-select mix",
            "data-record-owned event behavior",
            "same-page data-record mixes beyond the case58-shaped ordinary button-event path and the exact case80 no-event text-select shape",
            "media/file-system side effects",
            "cross-model compatibility",
        ),
    ),
    WidgetTypeInfo(
        "file-browser",
        WidgetSupport.SUPPORTED,
        WidgetWriter.FIXTURE,
        aliases=("filebrowser", "file browser"),
        fixture_case="case_43_filebrowser",
        type_code="A",
        reason=(
            "case_43_filebrowser now has an official-GUI-created current-target HMI and "
            "work/output TFT oracle; local HMI authoring uses the fixture template, "
            "and the fixture-shaped direct TFT rebuild path is experimental"
        ),
        evidence="examples/advanced_widget_case_outputs_2026-05-17.json",
        evidence_level="official-gui-created-work-output-oracle",
        build_scope="hmi-and-experimental-direct-tft",
        claim_level="fixture-structure-clone-plus-bit-perfect-current-target-tft",
        can_build_tft=True,
        notes=(
            "Direct TFT readback, ordinary button-event mixes, file-browser down/up events, "
            "and no-event text-select mix paths are live-proven for the documented examples."
        ),
        not_claimed=(
            "arbitrary property synthesis",
            "interactive runtime behavior beyond serial field readback and the documented event markers",
            "file-browser-owned event behavior beyond live-proven down/up printh callbacks",
            "advanced-control mixes beyond no-event text-select plus optional ordinary native controls/events",
            "file-system side effects",
            "cross-model compatibility",
        ),
    ),
    WidgetTypeInfo(
        "file-stream",
        WidgetSupport.SUPPORTED,
        WidgetWriter.FIXTURE,
        aliases=("filestream", "file stream"),
        fixture_case="case_44_filestream",
        type_code="?",
        reason=(
            "case_44_filestream now has an official-GUI-created current-target HMI and "
            "work/output TFT oracle; local HMI authoring uses the fixture template, "
            "and the fixture-shaped direct TFT rebuild path is experimental"
        ),
        evidence="examples/advanced_widget_case_outputs_2026-05-17.json",
        evidence_level="official-gui-created-work-output-oracle",
        build_scope="hmi-and-experimental-direct-tft",
        claim_level="fixture-structure-clone-plus-bit-perfect-current-target-tft",
        can_build_tft=True,
        notes=(
            "Direct TFT readback, ordinary button-event mixes, and the narrow "
            "button.down -> fs0.open(t1.txt) path are live-proven, including an exact case72 oracle-aligned shape "
            "plus a current-code raw-patch variant; fs0.down printh is live-negative, so file-stream-owned events still fail closed."
        ),
        not_claimed=(
            "arbitrary property synthesis",
            "interactive runtime behavior beyond serial field readback and documented ordinary button markers",
            "file-stream-owned event behavior",
            "mixing file-stream with other advanced controls",
            "file-system side effects beyond the live-proven 16-byte fs0.open probe",
            "cross-model compatibility",
        ),
    ),
)

WIDGET_TYPE_REGISTRY: dict[str, WidgetTypeInfo] = {info.type: info for info in _WIDGETS}
WIDGET_TYPE_ALIASES: dict[str, str] = {
    alias.strip().lower(): info.type
    for info in _WIDGETS
    for alias in info.aliases
}


def normalize_widget_type(widget_type: Any) -> str:
    if not isinstance(widget_type, str):
        raise ValueError("widget.type must be a non-empty string")
    raw = widget_type.strip().lower()
    if not raw:
        raise ValueError("widget.type must be a non-empty string")
    return WIDGET_TYPE_ALIASES.get(raw, raw)


def get_widget_type_info(widget_type: str) -> WidgetTypeInfo | None:
    return WIDGET_TYPE_REGISTRY.get(normalize_widget_type(widget_type))


def iter_widget_type_infos(
    *,
    support: WidgetSupport | Iterable[WidgetSupport] | None = None,
) -> tuple[WidgetTypeInfo, ...]:
    if support is None:
        return tuple(sorted(_WIDGETS, key=lambda item: item.type))
    if isinstance(support, WidgetSupport):
        allowed = {support}
    else:
        allowed = set(support)
    return tuple(sorted((info for info in _WIDGETS if info.support in allowed), key=lambda item: item.type))


def format_type_code(type_code: str) -> str:
    if len(type_code) == 1 and ord(type_code) < 0x20:
        return f"0x{ord(type_code):02X}"
    return type_code


def widget_capability_manifest(*, include_aliases: bool = False) -> dict[str, Any]:
    fixture_types = {
        info.type: {"case": info.fixture_case, "type": format_type_code(info.type_code or "")}
        for info in iter_widget_type_infos(support=WidgetSupport.SUPPORTED)
        if info.writer == WidgetWriter.FIXTURE
    }
    hmi_only_fixture_types = {
        info.type: {
            "case": info.fixture_case,
            "type": format_type_code(info.type_code or ""),
            "build_scope": info.build_scope or "hmi-only",
            "can_build_tft": bool(info.can_build_tft),
        }
        for info in _WIDGETS
        if info.writer == WidgetWriter.FIXTURE and (info.build_scope == "hmi-only" or info.can_build_tft is False)
    }
    experimental_tft_fixture_types = {
        info.type: {
            "case": info.fixture_case,
            "type": format_type_code(info.type_code or ""),
            "build_scope": info.build_scope or "hmi-and-experimental-direct-tft",
            "can_build_tft": True,
        }
        for info in _WIDGETS
        if info.writer == WidgetWriter.FIXTURE and bool(info.can_build_tft) and info.build_scope is not None
    }
    return {
        "target": CURRENT_TARGET,
        "supported_widget_types": sorted(SUPPORTED_WIDGET_TYPES),
        "built_in_writer_types": sorted(BUILT_IN_WRITER_TYPES),
        "fixture_backed_writer_types": fixture_types,
        "fixture_backed_hmi_only_types": hmi_only_fixture_types,
        "fixture_backed_experimental_tft_types": experimental_tft_fixture_types,
        "current_target_unsupported": dict(UNSUPPORTED_CURRENT_TARGET_WIDGET_TYPES),
        "current_target_pending": {
            info.type: info.to_dict(include_aliases=include_aliases)
            for info in iter_widget_type_infos(support=WidgetSupport.PENDING)
        },
        "widgets": [
            info.to_dict(include_aliases=include_aliases)
            for info in iter_widget_type_infos()
        ],
    }


SUPPORTED_WIDGET_TYPES = frozenset(
    info.type for info in _WIDGETS if info.support == WidgetSupport.SUPPORTED
)
BUILT_IN_WRITER_TYPES = frozenset(
    info.type for info in _WIDGETS if info.support == WidgetSupport.SUPPORTED and info.writer == WidgetWriter.BUILT_IN
)
FIXTURE_WIDGET_TEMPLATE_CASES = {
    info.type: (info.fixture_case, info.type_code)
    for info in _WIDGETS
    if info.support == WidgetSupport.SUPPORTED and info.writer == WidgetWriter.FIXTURE
}
AUTHORING_WIDGET_TEMPLATE_CASES = {
    info.type: (info.fixture_case, info.type_code)
    for info in _WIDGETS
    if info.writer == WidgetWriter.FIXTURE and info.fixture_case and info.type_code is not None
}
HMI_ONLY_FIXTURE_WIDGET_TYPES = {
    info.type: info.reason or ""
    for info in _WIDGETS
    if info.writer == WidgetWriter.FIXTURE and (info.build_scope == "hmi-only" or info.can_build_tft is False)
}
EXPERIMENTAL_DIRECT_TFT_FIXTURE_WIDGET_TYPES = frozenset(
    info.type
    for info in _WIDGETS
    if info.writer == WidgetWriter.FIXTURE and bool(info.can_build_tft) and info.build_scope is not None
)
UNSUPPORTED_CURRENT_TARGET_WIDGET_TYPES = {
    info.type: info.reason or ""
    for info in _WIDGETS
    if info.support == WidgetSupport.UNSUPPORTED_CURRENT_TARGET
}
