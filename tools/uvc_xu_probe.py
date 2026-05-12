from __future__ import annotations

import argparse
import ctypes
import json
from ctypes import POINTER, byref, c_long, c_ulong, c_void_p, create_string_buffer, sizeof
from typing import Any

from comtypes import COMMETHOD, GUID, HRESULT, IUnknown
from pygrabber.dshow_graph import SystemDeviceEnum
from pygrabber.dshow_ids import DeviceCategories


KSPROPERTY_TYPE_GET = 0x00000001
KSPROPERTY_TYPE_SET = 0x00000002
KSPROPERTY_TYPE_BASICSUPPORT = 0x00000200
KSPROPERTY_TYPE_TOPOLOGY = 0x10000000


class KSPROPERTY(ctypes.Structure):
    _fields_ = [("Set", GUID), ("Id", c_ulong), ("Flags", c_ulong)]


class KSP_NODE(ctypes.Structure):
    _fields_ = [("Property", KSPROPERTY), ("NodeId", c_ulong), ("Reserved", c_ulong)]


class IAMCameraControl(IUnknown):
    _iid_ = GUID("{C6E13370-30AC-11D0-A18C-00A0C9118956}")
    _methods_ = [
        COMMETHOD(
            [],
            HRESULT,
            "GetRange",
            (["in"], c_long, "Property"),
            (["out"], POINTER(c_long), "pMin"),
            (["out"], POINTER(c_long), "pMax"),
            (["out"], POINTER(c_long), "pSteppingDelta"),
            (["out"], POINTER(c_long), "pDefault"),
            (["out"], POINTER(c_long), "pCapsFlags"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "Set",
            (["in"], c_long, "Property"),
            (["in"], c_long, "lValue"),
            (["in"], c_long, "Flags"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "Get",
            (["in"], c_long, "Property"),
            (["out"], POINTER(c_long), "lValue"),
            (["out"], POINTER(c_long), "Flags"),
        ),
    ]


class IKsControl(IUnknown):
    _iid_ = GUID("{28F54685-06FD-11D2-B27A-00A0C9223196}")
    _methods_ = [
        COMMETHOD(
            [],
            HRESULT,
            "KsProperty",
            (["in"], c_void_p, "Property"),
            (["in"], c_ulong, "PropertyLength"),
            (["in"], c_void_p, "PropertyData"),
            (["in"], c_ulong, "DataLength"),
            (["out"], POINTER(c_ulong), "BytesReturned"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "KsMethod",
            (["in"], c_void_p, "Method"),
            (["in"], c_ulong, "MethodLength"),
            (["in"], c_void_p, "MethodData"),
            (["in"], c_ulong, "DataLength"),
            (["out"], POINTER(c_ulong), "BytesReturned"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "KsEvent",
            (["in"], c_void_p, "Event"),
            (["in"], c_ulong, "EventLength"),
            (["in"], c_void_p, "EventData"),
            (["in"], c_ulong, "DataLength"),
            (["out"], POINTER(c_ulong), "BytesReturned"),
        ),
    ]


CAMERA_PROPERTIES = ["Pan", "Tilt", "Roll", "Zoom", "Exposure", "Iris", "Focus"]
FLAG_NAMES = {1: "Auto", 2: "Manual"}


def flag_names(value: int) -> list[str]:
    names = [name for bit, name in FLAG_NAMES.items() if value & bit]
    return names or [str(value)]


def open_video_filter(name: str):
    enum = SystemDeviceEnum()
    devices = enum.get_available_filters(DeviceCategories.VideoInputDevice)
    matches = [index for index, device in enumerate(devices) if device == name]
    if not matches:
        raise SystemExit(f"video device not found: {name}. Available: {devices}")
    return enum.get_filter_by_index(DeviceCategories.VideoInputDevice, matches[0])[0]


def ks_property(ks: IKsControl, guid: GUID, node_id: int, control_id: int, flags: int, payload: bytes) -> tuple[int, bytes]:
    node = KSP_NODE(KSPROPERTY(guid, control_id, flags), node_id, 0)
    data = create_string_buffer(payload, len(payload))
    returned = ks.KsProperty(
        ctypes.cast(byref(node), c_void_p),
        sizeof(node),
        ctypes.cast(data, c_void_p),
        len(data),
    )
    returned_int = int(returned)
    return returned_int, bytes(data.raw[: min(returned_int, len(data))])


def bytes_from_hex(value: str) -> bytes:
    compact = value.replace(" ", "").replace(":", "").replace("-", "")
    if len(compact) % 2:
        raise ValueError("hex payload must contain an even number of hex digits")
    return bytes.fromhex(compact)


def list_camera_controls(device: str) -> dict[str, Any]:
    filt = open_video_filter(device)
    cam = filt.QueryInterface(IAMCameraControl)
    ranges: list[dict[str, Any]] = []
    for prop_id, name in enumerate(CAMERA_PROPERTIES):
        try:
            minimum, maximum, step, default, caps = cam.GetRange(prop_id)
            value, flags = cam.Get(prop_id)
            ranges.append(
                {
                    "property": name,
                    "id": prop_id,
                    "min": minimum,
                    "max": maximum,
                    "step": step,
                    "default": default,
                    "caps": caps,
                    "caps_names": flag_names(caps),
                    "value": value,
                    "flags": flags,
                    "flag_names": flag_names(flags),
                }
            )
        except Exception as exc:
            ranges.append({"property": name, "id": prop_id, "error": repr(exc)})
    return {"device": device, "camera_controls": ranges}


def scan_xu(device: str, guid: str, controls: list[int], nodes: range) -> dict[str, Any]:
    filt = open_video_filter(device)
    ks = filt.QueryInterface(IKsControl)
    xu_guid = GUID(guid)
    hits: list[dict[str, Any]] = []
    for node_id in nodes:
        for control_id in controls:
            for flags_name, flags in [
                ("basic_topology", KSPROPERTY_TYPE_BASICSUPPORT | KSPROPERTY_TYPE_TOPOLOGY),
                ("get_topology", KSPROPERTY_TYPE_GET | KSPROPERTY_TYPE_TOPOLOGY),
                ("basic", KSPROPERTY_TYPE_BASICSUPPORT),
                ("get", KSPROPERTY_TYPE_GET),
            ]:
                try:
                    returned, data = ks_property(ks, xu_guid, node_id, control_id, flags, b"\x00" * 128)
                    hits.append(
                        {
                            "node_id": node_id,
                            "control_id": control_id,
                            "flags": flags_name,
                            "bytes": returned,
                            "hex": data.hex(" "),
                        }
                    )
                except Exception:
                    pass
    return {"device": device, "guid": guid, "hits": hits}


def get_xu(device: str, guid: str, node_id: int, control_id: int, size: int) -> dict[str, Any]:
    filt = open_video_filter(device)
    ks = filt.QueryInterface(IKsControl)
    returned, data = ks_property(
        ks,
        GUID(guid),
        node_id,
        control_id,
        KSPROPERTY_TYPE_GET | KSPROPERTY_TYPE_TOPOLOGY,
        b"\x00" * size,
    )
    return {
        "device": device,
        "guid": guid,
        "node_id": node_id,
        "control_id": control_id,
        "bytes": returned,
        "hex": data.hex(" "),
    }


def set_xu(device: str, guid: str, node_id: int, control_id: int, payload: bytes) -> dict[str, Any]:
    filt = open_video_filter(device)
    ks = filt.QueryInterface(IKsControl)
    returned, data = ks_property(
        ks,
        GUID(guid),
        node_id,
        control_id,
        KSPROPERTY_TYPE_SET | KSPROPERTY_TYPE_TOPOLOGY,
        payload,
    )
    return {
        "device": device,
        "guid": guid,
        "node_id": node_id,
        "control_id": control_id,
        "bytes": returned,
        "payload_hex": payload.hex(" "),
        "echo_hex": data.hex(" "),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe UVC standard and extension-unit controls through DirectShow.")
    parser.add_argument("--device", default="USB Cam")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("camera-controls")

    scan = sub.add_parser("scan-xu")
    scan.add_argument("--guid", default="{1229A78C-47B4-4094-B0CE-DB07386FB938}")
    scan.add_argument("--controls", default="9,10")
    scan.add_argument("--nodes", default="0:16")

    get = sub.add_parser("get-xu")
    get.add_argument("--guid", default="{1229A78C-47B4-4094-B0CE-DB07386FB938}")
    get.add_argument("--node", type=int, default=3)
    get.add_argument("--control", type=int, default=10)
    get.add_argument("--size", type=int, default=8)

    set_cmd = sub.add_parser("set-xu")
    set_cmd.add_argument("--guid", default="{1229A78C-47B4-4094-B0CE-DB07386FB938}")
    set_cmd.add_argument("--node", type=int, default=3)
    set_cmd.add_argument("--control", type=int, default=10)
    set_cmd.add_argument("--payload-hex", required=True)

    args = parser.parse_args()
    if args.command == "camera-controls":
        result = list_camera_controls(args.device)
    elif args.command == "scan-xu":
        start, end = [int(part) for part in args.nodes.split(":", 1)]
        controls = [int(part) for part in args.controls.split(",") if part.strip()]
        result = scan_xu(args.device, args.guid, controls, range(start, end))
    elif args.command == "get-xu":
        result = get_xu(args.device, args.guid, args.node, args.control, args.size)
    else:
        result = set_xu(args.device, args.guid, args.node, args.control, bytes_from_hex(args.payload_hex))

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
