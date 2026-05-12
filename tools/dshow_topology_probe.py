from __future__ import annotations

import argparse
import json
from ctypes import POINTER, byref, c_ulong, c_wchar, c_wchar_p, c_void_p, sizeof
from typing import Any

from comtypes import COMMETHOD, GUID, HRESULT, IUnknown
from pygrabber.dshow_graph import SystemDeviceEnum
from pygrabber.dshow_ids import DeviceCategories


class KSTOPOLOGY_CONNECTION(__import__("ctypes").Structure):
    _fields_ = [
        ("FromNode", c_ulong),
        ("FromNodePin", c_ulong),
        ("ToNode", c_ulong),
        ("ToNodePin", c_ulong),
    ]


class IKsTopologyInfo(IUnknown):
    _iid_ = GUID("{720D4AC0-7533-11D0-A5D6-28DB04C10000}")
    _methods_ = [
        COMMETHOD([], HRESULT, "get_NumCategories", (["out"], POINTER(c_ulong), "pdwNumCategories")),
        COMMETHOD([], HRESULT, "get_Category", (["in"], c_ulong, "dwIndex"), (["out"], POINTER(GUID), "pCategory")),
        COMMETHOD([], HRESULT, "get_NumConnections", (["out"], POINTER(c_ulong), "pdwNumConnections")),
        COMMETHOD(
            [],
            HRESULT,
            "get_ConnectionInfo",
            (["in"], c_ulong, "dwIndex"),
            (["out"], POINTER(KSTOPOLOGY_CONNECTION), "pConnectionInfo"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "get_NodeName",
            (["in"], c_ulong, "dwNodeId"),
            (["in"], c_wchar_p, "pwchNodeName"),
            (["in"], c_ulong, "dwBufSize"),
            (["out"], POINTER(c_ulong), "pdwNameLen"),
        ),
        COMMETHOD([], HRESULT, "get_NumNodes", (["out"], POINTER(c_ulong), "pdwNumNodes")),
        COMMETHOD([], HRESULT, "get_NodeType", (["in"], c_ulong, "dwNodeId"), (["out"], POINTER(GUID), "pNodeType")),
        COMMETHOD(
            [],
            HRESULT,
            "CreateNodeInstance",
            (["in"], c_ulong, "dwNodeId"),
            (["in"], POINTER(GUID), "iid"),
            (["out"], POINTER(c_void_p), "ppvObject"),
        ),
    ]


KNOWN_NODE_TYPES = {
    "{DFF229E1-F70F-11D0-B917-00A0C9223196}": "KSNODETYPE_DEV_SPECIFIC",
    "{DFF229E2-F70F-11D0-B917-00A0C9223196}": "KSNODETYPE_VIDEO_CAMERA_TERMINAL",
    "{DFF229E3-F70F-11D0-B917-00A0C9223196}": "KSNODETYPE_VIDEO_INPUT_TERMINAL",
    "{DFF229E4-F70F-11D0-B917-00A0C9223196}": "KSNODETYPE_VIDEO_OUTPUT_TERMINAL",
    "{DFF229E5-F70F-11D0-B917-00A0C9223196}": "KSNODETYPE_VIDEO_SELECTOR",
    "{DFF229E6-F70F-11D0-B917-00A0C9223196}": "KSNODETYPE_VIDEO_PROCESSING",
}


def open_video_filter(name: str):
    enum = SystemDeviceEnum()
    devices = enum.get_available_filters(DeviceCategories.VideoInputDevice)
    matches = [index for index, device in enumerate(devices) if device == name]
    if not matches:
        raise SystemExit(f"video device not found: {name}. Available: {devices}")
    return enum.get_filter_by_index(DeviceCategories.VideoInputDevice, matches[0])[0]


def get_node_name(topology: IKsTopologyInfo, node_id: int) -> str:
    name_len = c_ulong(0)
    try:
        topology.get_NodeName(node_id, None, 0, byref(name_len))
    except Exception:
        pass
    if name_len.value == 0:
        return ""
    buf = (c_wchar * max(1, name_len.value))()
    try:
        topology.get_NodeName(node_id, buf, len(buf), byref(name_len))
        return "".join(buf).rstrip("\x00")
    except Exception:
        return ""


def probe(device: str) -> dict[str, Any]:
    filt = open_video_filter(device)
    topology = filt.QueryInterface(IKsTopologyInfo)

    categories: list[dict[str, Any]] = []
    try:
        num_categories = topology.get_NumCategories()
        for idx in range(int(num_categories)):
            guid = topology.get_Category(idx)
            categories.append({"index": idx, "guid": str(guid).upper()})
    except Exception as exc:
        categories.append({"error": repr(exc)})

    nodes: list[dict[str, Any]] = []
    try:
        num_nodes = int(topology.get_NumNodes())
        for node_id in range(num_nodes):
            guid = topology.get_NodeType(node_id)
            guid_text = str(guid).upper()
            nodes.append(
                {
                    "node_id": node_id,
                    "type_guid": guid_text,
                    "type_name": KNOWN_NODE_TYPES.get(guid_text, ""),
                    "name": get_node_name(topology, node_id),
                }
            )
    except Exception as exc:
        nodes.append({"error": repr(exc)})

    connections: list[dict[str, Any]] = []
    try:
        num_connections = int(topology.get_NumConnections())
        for idx in range(num_connections):
            conn = topology.get_ConnectionInfo(idx)
            connections.append(
                {
                    "index": idx,
                    "from_node": int(conn.FromNode),
                    "from_node_pin": int(conn.FromNodePin),
                    "to_node": int(conn.ToNode),
                    "to_node_pin": int(conn.ToNodePin),
                }
            )
    except Exception as exc:
        connections.append({"error": repr(exc)})

    return {"device": device, "categories": categories, "nodes": nodes, "connections": connections}


def main() -> int:
    parser = argparse.ArgumentParser(description="Dump DirectShow IKsTopologyInfo for a video device.")
    parser.add_argument("--device", default="USB Cam")
    args = parser.parse_args()
    print(json.dumps(probe(args.device), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
