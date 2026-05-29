from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "examples" / "econtest_templates"
CANVAS_W = 800
CANVAS_H = 480


def rgb565(r: int, g: int, b: int) -> int:
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


PALETTE = {
    "ink": rgb565(20, 24, 31),
    "muted": rgb565(104, 114, 132),
    "white": rgb565(248, 250, 252),
    "paper": rgb565(241, 245, 249),
    "line": rgb565(203, 213, 225),
    "green": rgb565(34, 197, 94),
    "red": rgb565(239, 68, 68),
    "amber": rgb565(245, 158, 11),
}


TEMPLATES: list[dict[str, Any]] = [
    {
        "slug": "instrument_meter",
        "name": "Instrument Meter",
        "cn": "仪器仪表",
        "accent": rgb565(14, 116, 144),
        "accent2": rgb565(45, 212, 191),
        "bg": rgb565(236, 254, 255),
        "metrics": [("VOLT", "mV", 3300), ("CURR", "mA", 125), ("FREQ", "Hz", 1000), ("TEMP", "C", 36)],
        "log": "ADC OK | TRIG | AUTO",
        "cmd": "CAL",
        "code": "31",
    },
    {
        "slug": "power_energy",
        "name": "Power Energy",
        "cn": "电源能源",
        "accent": rgb565(22, 101, 52),
        "accent2": rgb565(132, 204, 22),
        "bg": rgb565(240, 253, 244),
        "metrics": [("VIN", "mV", 12000), ("VOUT", "mV", 5000), ("LOAD", "pct", 68), ("EFF", "pct", 91)],
        "log": "BUCK OK | LOAD | OVP",
        "cmd": "LOAD",
        "code": "32",
    },
    {
        "slug": "motor_motion",
        "name": "Motor Motion",
        "cn": "电机运动",
        "accent": rgb565(29, 78, 216),
        "accent2": rgb565(96, 165, 250),
        "bg": rgb565(239, 246, 255),
        "metrics": [("RPM", "rpm", 2450), ("PWM", "pct", 54), ("POS", "deg", 180), ("ERR", "cnt", 3)],
        "log": "LOOP OK | ENC | BRAKE",
        "cmd": "HOME",
        "code": "33",
    },
    {
        "slug": "robot_chassis",
        "name": "Robot Chassis",
        "cn": "机器人底盘",
        "accent": rgb565(124, 58, 237),
        "accent2": rgb565(167, 139, 250),
        "bg": rgb565(245, 243, 255),
        "metrics": [("VX", "mm/s", 360), ("VY", "mm/s", 42), ("YAW", "deg", 18), ("DIST", "cm", 126)],
        "log": "ROUTE | IMU | CLEAR",
        "cmd": "PATH",
        "code": "34",
    },
    {
        "slug": "communication_link",
        "name": "Communication Link",
        "cn": "通信链路",
        "accent": rgb565(15, 118, 110),
        "accent2": rgb565(20, 184, 166),
        "bg": rgb565(240, 253, 250),
        "metrics": [("RSSI", "dBm", 72), ("PING", "ms", 12), ("PKT", "cnt", 4096), ("ERR", "cnt", 0)],
        "log": "UART | CAN | RF OK",
        "cmd": "PAIR",
        "code": "35",
    },
    {
        "slug": "sensor_fusion",
        "name": "Sensor Fusion",
        "cn": "传感融合",
        "accent": rgb565(180, 83, 9),
        "accent2": rgb565(251, 191, 36),
        "bg": rgb565(255, 251, 235),
        "metrics": [("TEMP", "C", 28), ("HUM", "pct", 58), ("LIGHT", "lx", 420), ("CO2", "ppm", 615)],
        "log": "FUSION | KALMAN | OK",
        "cmd": "ZERO",
        "code": "36",
    },
    {
        "slug": "pid_tuning",
        "name": "PID Tuning",
        "cn": "PID 调参",
        "accent": rgb565(190, 24, 93),
        "accent2": rgb565(244, 114, 182),
        "bg": rgb565(253, 242, 248),
        "metrics": [("KP", "x100", 120), ("KI", "x100", 18), ("KD", "x100", 42), ("OVR", "pct", 5)],
        "log": "STEP | LOCK | SETTLE",
        "cmd": "STEP",
        "code": "37",
    },
    {
        "slug": "battery_bms",
        "name": "Battery BMS",
        "cn": "电池管理",
        "accent": rgb565(5, 150, 105),
        "accent2": rgb565(52, 211, 153),
        "bg": rgb565(236, 253, 245),
        "metrics": [("SOC", "pct", 76), ("CELL", "mV", 3985), ("CURR", "mA", 820), ("CYCLE", "cnt", 128)],
        "log": "BAL | PACK | TEMP OK",
        "cmd": "BAL",
        "code": "38",
    },
    {
        "slug": "vision_aiot",
        "name": "Vision AIoT",
        "cn": "视觉识别",
        "accent": rgb565(67, 56, 202),
        "accent2": rgb565(129, 140, 248),
        "bg": rgb565(238, 242, 255),
        "metrics": [("FPS", "fps", 28), ("OBJ", "cnt", 6), ("CONF", "pct", 92), ("LAT", "ms", 38)],
        "log": "FRAME | ROI | PUSH",
        "cmd": "SNAP",
        "code": "39",
    },
    {
        "slug": "field_debug",
        "name": "Field Debug",
        "cn": "现场调试",
        "accent": rgb565(71, 85, 105),
        "accent2": rgb565(148, 163, 184),
        "bg": rgb565(248, 250, 252),
        "metrics": [("MODE", "id", 2), ("UP", "s", 360), ("WARN", "cnt", 1), ("BOOT", "cnt", 12)],
        "log": "BUS | LOG | SAFE",
        "cmd": "DUMP",
        "code": "3A",
    },
]


def style(bg: int, fg: int = PALETTE["ink"], border: int | None = None, **extra: Any) -> dict[str, Any]:
    data: dict[str, Any] = {"background_color": bg, "foreground_color": fg}
    if border is not None:
        data["border_color"] = border
    data.update(extra)
    return data


def text(wid: str, x: int, y: int, w: int, h: int, value: str, bg: int, fg: int | None = None) -> dict[str, Any]:
    return {
        "id": wid,
        "type": "text",
        "x": x,
        "y": y,
        "w": w,
        "h": h,
        "text": value,
        "style": style(bg, PALETTE["ink"] if fg is None else fg),
    }


def num(
    wid: str,
    x: int,
    y: int,
    w: int,
    h: int,
    value: int,
    bg: int,
    fg: int,
    length: int = 5,
) -> dict[str, Any]:
    return {
        "id": wid,
        "type": "number",
        "x": x,
        "y": y,
        "w": w,
        "h": h,
        "value": value,
        "style": style(bg, fg, PALETTE["line"], length=length),
    }


def button(
    wid: str,
    x: int,
    y: int,
    w: int,
    h: int,
    label: str,
    bg: int,
    fg: int,
    events: dict[str, list[str]] | None = None,
    kind: str = "button",
    value: int | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": wid,
        "type": kind,
        "x": x,
        "y": y,
        "w": w,
        "h": h,
        "text": label,
        "style": style(bg, fg, bg),
    }
    if value is not None:
        item["value"] = value
    if events:
        item["events"] = events
    return item


def panel(wid: str, x: int, y: int, w: int, h: int, bg: int) -> dict[str, Any]:
    return text(wid, x, y, w, h, "", bg, PALETTE["ink"])


def nav_widgets(active: int, accent: int) -> list[dict[str, Any]]:
    labels = [("n_home", "HOME", "page page0"), ("n_param", "PARAM", "page page1"), ("n_log", "LOG", "page page2")]
    widgets: list[dict[str, Any]] = []
    for idx, (wid, label, cmd) in enumerate(labels):
        x = 512 + idx * 88
        bg = accent if idx == active else PALETTE["paper"]
        fg = PALETTE["white"] if idx == active else PALETTE["ink"]
        widgets.append(button(wid, x, 424, 72, 36, label, bg, fg, {"up": [cmd]}))
    return widgets


def metric_cards(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    widgets: list[dict[str, Any]] = []
    accent = cfg["accent"]
    coords = [(24, 104), (214, 104), (24, 226), (214, 226)]
    for idx, ((label, unit, value), (x, y)) in enumerate(zip(cfg["metrics"], coords, strict=True)):
        widgets.append(panel(f"card{idx}", x, y, 166, 96, PALETTE["white"]))
        widgets.append(text(f"m{idx}_lab", x + 14, y + 12, 72, 22, label, PALETTE["white"], PALETTE["muted"]))
        widgets.append(num(f"m{idx}", x + 14, y + 42, 86, 34, value, PALETTE["white"], accent))
        widgets.append(text(f"m{idx}_unit", x + 106, y + 49, 42, 22, unit, PALETTE["white"], PALETTE["muted"]))
    return widgets


def base_header(cfg: dict[str, Any], page_label: str) -> list[dict[str, Any]]:
    accent = cfg["accent"]
    accent2 = cfg["accent2"]
    return [
        panel("topbar", 0, 0, 800, 76, accent),
        text("title", 24, 14, 360, 30, cfg["name"].upper(), accent, PALETTE["white"]),
        text("sub", 24, 45, 430, 20, f"{cfg['cn']} | {page_label}", accent, PALETTE["white"]),
        button("run", 646, 18, 122, 36, "RUN", accent2, PALETTE["ink"], kind="state-button", value=1),
    ]


def make_dashboard(cfg: dict[str, Any]) -> dict[str, Any]:
    accent = cfg["accent"]
    accent2 = cfg["accent2"]
    widgets = base_header(cfg, "runtime dashboard")
    widgets.extend(metric_cards(cfg))
    widgets.extend(
        [
            panel("main_panel", 420, 104, 348, 222, PALETTE["white"]),
            text("main_lab", 444, 122, 180, 24, "SYSTEM LOAD", PALETTE["white"], PALETTE["muted"]),
            {
                "id": "main_gauge",
                "type": "gauge",
                "x": 454,
                "y": 156,
                "w": 126,
                "h": 126,
                "value": int(cfg["metrics"][2][2]) % 100,
                "style": style(PALETTE["white"], accent, PALETTE["line"]),
            },
            {
                "id": "main_bar",
                "type": "progress",
                "x": 610,
                "y": 158,
                "w": 120,
                "h": 30,
                "value": int(cfg["metrics"][2][2]) % 100,
                "style": style(PALETTE["paper"], accent2, PALETTE["line"]),
            },
            text("bar_lab", 610, 198, 118, 22, "live percent", PALETTE["white"], PALETTE["muted"]),
            num("tick", 610, 236, 82, 34, 0, PALETTE["white"], accent, length=4),
            text("tick_lab", 698, 244, 38, 20, "tick", PALETTE["white"], PALETTE["muted"]),
            button("b_start", 420, 350, 92, 44, "START", accent, PALETTE["white"], {"up": [f"printh 23 {cfg['code']} 10 01", "run.val=1"]}),
            button("b_stop", 530, 350, 92, 44, "STOP", PALETTE["red"], PALETTE["white"], {"up": [f"printh 23 {cfg['code']} 10 00", "run.val=0"]}),
            button("b_cmd", 640, 350, 92, 44, cfg["cmd"], accent2, PALETTE["ink"], {"up": [f"printh 23 {cfg['code']} 20 01"]}),
            {
                "id": "tm0",
                "type": "timer",
                "x": 0,
                "y": 0,
                "w": 1,
                "h": 1,
                "style": {"tim": 500, "en": 1},
                "events": {"timer": ["tick.val++"]},
            },
        ]
    )
    widgets.extend(nav_widgets(0, accent))
    return {"id": "page0", "layout": {"type": "absolute"}, "widgets": widgets}


def make_params(cfg: dict[str, Any]) -> dict[str, Any]:
    accent = cfg["accent"]
    accent2 = cfg["accent2"]
    widgets = base_header(cfg, "parameter panel")
    widgets.extend(
        [
            panel("p_left", 24, 104, 350, 290, PALETTE["white"]),
            text("p_title", 44, 122, 210, 26, "CONTROL SETPOINTS", PALETTE["white"], accent),
            text("sp0_lab", 48, 172, 104, 24, "target", PALETTE["white"], PALETTE["muted"]),
            num("sp0", 168, 166, 96, 36, int(cfg["metrics"][0][2]), PALETTE["white"], accent, length=5),
            text("sp1_lab", 48, 222, 104, 24, "limit", PALETTE["white"], PALETTE["muted"]),
            num("sp1", 168, 216, 96, 36, int(cfg["metrics"][1][2]), PALETTE["white"], accent, length=5),
            text("sp2_lab", 48, 272, 104, 24, "gain", PALETTE["white"], PALETTE["muted"]),
            num("sp2", 168, 266, 96, 36, int(cfg["metrics"][3][2]), PALETTE["white"], accent, length=5),
            button("b_dec", 286, 166, 58, 36, "-1", PALETTE["paper"], PALETTE["ink"], {"up": ["sp0.val--"]}),
            button("b_inc", 286, 216, 58, 36, "+1", accent2, PALETTE["ink"], {"up": ["sp0.val++"]}),
            button("b_save", 48, 330, 128, 44, "SAVE", accent, PALETTE["white"], {"up": [f"printh 23 {cfg['code']} 30 01"]}),
            button("b_rst", 198, 330, 128, 44, "RESET", PALETTE["paper"], PALETTE["ink"], {"up": ["sp0.val=0", f"printh 23 {cfg['code']} 30 00"]}),
            panel("p_right", 420, 104, 348, 290, PALETTE["white"]),
            text("mode_lab", 444, 122, 130, 24, "MODE SELECT", PALETTE["white"], accent),
            {"id": "cb_auto", "type": "checkbox", "x": 448, "y": 166, "w": 32, "h": 32, "value": 1, "style": style(PALETTE["white"], accent, PALETTE["line"])},
            text("auto_lab", 492, 172, 148, 24, "auto loop", PALETTE["white"], PALETTE["muted"]),
            {"id": "cb_log", "type": "checkbox", "x": 448, "y": 214, "w": 32, "h": 32, "value": 1, "style": style(PALETTE["white"], accent, PALETTE["line"])},
            text("log_lab", 492, 220, 148, 24, "record log", PALETTE["white"], PALETTE["muted"]),
            {"id": "sl0", "type": "slider", "x": 448, "y": 276, "w": 190, "h": 34, "value": 45, "style": style(PALETTE["paper"], accent2, PALETTE["line"])},
            text("slider_lab", 650, 282, 72, 24, "speed", PALETTE["white"], PALETTE["muted"]),
            button("b_apply", 448, 330, 122, 44, "APPLY", accent, PALETTE["white"], {"up": [f"printh 23 {cfg['code']} 31 01"]}),
            button("b_back", 592, 330, 122, 44, "BACK", PALETTE["paper"], PALETTE["ink"], {"up": ["page page0"]}),
        ]
    )
    widgets.extend(nav_widgets(1, accent))
    return {"id": "page1", "layout": {"type": "absolute"}, "widgets": widgets}


def make_log(cfg: dict[str, Any]) -> dict[str, Any]:
    accent = cfg["accent"]
    accent2 = cfg["accent2"]
    widgets = base_header(cfg, "log and service")
    widgets.extend(
        [
            panel("log_panel", 24, 104, 476, 290, PALETTE["white"]),
            text("log_title", 44, 122, 180, 24, "EVENT STREAM", PALETTE["white"], accent),
            {
                "id": "log0",
                "type": "scrolling-text",
                "x": 44,
                "y": 160,
                "w": 420,
                "h": 48,
                "text": cfg["log"],
                "style": style(PALETTE["paper"], accent, PALETTE["line"]),
            },
            {
                "id": "wave0",
                "type": "waveform",
                "x": 44,
                "y": 232,
                "w": 420,
                "h": 92,
                "style": style(PALETTE["paper"], accent2, PALETTE["line"]),
            },
            text("seq_lab", 44, 342, 70, 24, "seq", PALETTE["white"], PALETTE["muted"]),
            num("seq", 118, 336, 90, 36, 0, PALETTE["white"], accent, length=5),
            button("b_clear", 232, 336, 94, 40, "CLEAR", PALETTE["paper"], PALETTE["ink"], {"up": ["seq.val=0"]}),
            button("b_mark", 346, 336, 94, 40, "MARK", accent, PALETTE["white"], {"up": [f"printh 23 {cfg['code']} 40 01"]}),
            panel("svc_panel", 530, 104, 238, 290, PALETTE["white"]),
            text("svc_title", 552, 122, 140, 24, "SERVICE QR", PALETTE["white"], accent),
            {
                "id": "qr0",
                "type": "qrcode",
                "x": 574,
                "y": 160,
                "w": 128,
                "h": 128,
                "text": f"usarthmi:{cfg['slug']}",
                "style": style(PALETTE["white"], accent, PALETTE["line"]),
            },
            text("qr_lab", 552, 306, 170, 24, cfg["slug"], PALETTE["white"], PALETTE["muted"]),
            {
                "id": "tm1",
                "type": "timer",
                "x": 0,
                "y": 0,
                "w": 1,
                "h": 1,
                "style": {"tim": 1000, "en": 1},
                "events": {"timer": ["seq.val++"]},
            },
        ]
    )
    widgets.extend(nav_widgets(2, accent))
    return {"id": "page2", "layout": {"type": "absolute"}, "widgets": widgets}


def make_scene(cfg: dict[str, Any]) -> dict[str, Any]:
    return {
        "project": {
            "name": f"econtest-{cfg['slug']}",
            "default_page": "page0",
            "drop_seed_objects": True,
        },
        "canvas": {"width": CANVAS_W, "height": CANVAS_H, "background_color": cfg["bg"]},
        "assets": {},
        "pages": [make_dashboard(cfg), make_params(cfg), make_log(cfg)],
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    index = {
        "schema": "usarthmi.econtest_templates.v1",
        "canvas": {"width": CANVAS_W, "height": CANVAS_H},
        "count": len(TEMPLATES),
        "templates": [],
    }
    for cfg in TEMPLATES:
        scene = make_scene(cfg)
        rel_scene = Path(cfg["slug"]) / "scene.json"
        write_json(OUT_ROOT / rel_scene, scene)
        index["templates"].append(
            {
                "slug": cfg["slug"],
                "name": cfg["name"],
                "cn": cfg["cn"],
                "scene": rel_scene.as_posix(),
                "pages": ["page0", "page1", "page2"],
                "serial_prefix_hex": f"23 {cfg['code']}",
                "primary_widgets": ["run", "main_gauge", "main_bar", "tick", "sp0", "seq"],
            }
        )
    write_json(OUT_ROOT / "template_index.json", index)


if __name__ == "__main__":
    main()
