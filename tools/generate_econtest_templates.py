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


P = {
    "ink": rgb565(20, 24, 31),
    "muted": rgb565(100, 116, 139),
    "white": rgb565(248, 250, 252),
    "card": rgb565(255, 255, 255),
    "paper": rgb565(241, 245, 249),
    "line": rgb565(203, 213, 225),
    "dark": rgb565(15, 23, 42),
    "slate": rgb565(30, 41, 59),
    "soft": rgb565(248, 250, 252),
    "red": rgb565(239, 68, 68),
    "green": rgb565(34, 197, 94),
    "amber": rgb565(245, 158, 11),
}


THEME_BADGES = {
    "power_flow": "PWR",
    "scope": "OSC",
    "source": "DDS",
    "comms": "LINK",
    "pid": "PID",
    "motor": "DRV",
    "daq": "DAQ",
    "robot": "BOT",
    "vision": "AI",
    "debug": "DBG",
}


TEMPLATES: list[dict[str, Any]] = [
    {
        "slug": "power_converter",
        "name": "Power Converter",
        "cn": "电源与功率变换",
        "problem_type": "开关电源 / 恒流源 / 逆变 / MPPT / BMS 前端",
        "home_kind": "power_flow",
        "accent": rgb565(22, 101, 52),
        "accent2": rgb565(132, 204, 22),
        "bg": rgb565(240, 253, 244),
        "code": "31",
        "metrics": [("VIN", "mV", 12000), ("VOUT", "mV", 5000), ("IOUT", "mA", 820), ("EFF", "pct", 91)],
        "params": [("v_set", 5000), ("i_limit", 1000), ("ramp", 50)],
        "log": "BUCK OK | OVP | LOAD",
        "cmd": "LOAD",
        "topic_widgets": ["flow_in", "flow_out", "eff_bar", "prot_ovp"],
    },
    {
        "slug": "measurement_scope",
        "name": "Measurement Scope",
        "cn": "测量仪器",
        "problem_type": "示波 / 频率计 / LCR / 数据记录 / 扫频测量",
        "home_kind": "scope",
        "accent": rgb565(14, 116, 144),
        "accent2": rgb565(45, 212, 191),
        "bg": rgb565(236, 254, 255),
        "code": "32",
        "metrics": [("VPP", "mV", 3300), ("RMS", "mV", 1160), ("FREQ", "Hz", 1000), ("PHASE", "deg", 12)],
        "params": [("range", 5), ("trig", 1200), ("sample", 48)],
        "log": "ADC | TRIG | HOLD",
        "cmd": "HOLD",
        "topic_widgets": ["scope_wave", "range_box", "trig_level", "m0"],
    },
    {
        "slug": "signal_generator",
        "name": "Signal Generator",
        "cn": "信号源与波形",
        "problem_type": "DDS / 函数发生器 / PWM / 脉冲源 / 滤波输出",
        "home_kind": "source",
        "accent": rgb565(79, 70, 229),
        "accent2": rgb565(129, 140, 248),
        "bg": rgb565(238, 242, 255),
        "code": "33",
        "metrics": [("FREQ", "Hz", 1000), ("AMP", "mV", 1800), ("OFFS", "mV", 0), ("DUTY", "pct", 50)],
        "params": [("freq", 1000), ("amp", 1800), ("offset", 0)],
        "log": "DDS | OUT | SYNC",
        "cmd": "SYNC",
        "topic_widgets": ["wave_sine", "freq_set", "amp_set", "out_enable"],
    },
    {
        "slug": "communication_link",
        "name": "Communication Link",
        "cn": "通信链路",
        "problem_type": "无线通信 / 调制解调 / CAN / UART / 误码率测试",
        "home_kind": "comms",
        "accent": rgb565(15, 118, 110),
        "accent2": rgb565(20, 184, 166),
        "bg": rgb565(240, 253, 250),
        "code": "34",
        "metrics": [("RSSI", "dBm", 72), ("SNR", "dB", 28), ("TX", "cnt", 4096), ("ERR", "cnt", 0)],
        "params": [("baud", 1152), ("chan", 8), ("power", 12)],
        "log": "UART | CAN | RF",
        "cmd": "PAIR",
        "topic_widgets": ["link_tx", "link_rx", "rssi_gauge", "ber_bar"],
    },
    {
        "slug": "pid_control",
        "name": "PID Control",
        "cn": "闭环控制",
        "problem_type": "温控 / 液位 / 压力 / 位置伺服 / 稳定平台",
        "home_kind": "pid",
        "accent": rgb565(190, 24, 93),
        "accent2": rgb565(244, 114, 182),
        "bg": rgb565(253, 242, 248),
        "code": "35",
        "metrics": [("SET", "x1", 500), ("PV", "x1", 486), ("ERR", "x1", 14), ("OUT", "pct", 42)],
        "params": [("kp", 120), ("ki", 18), ("kd", 42)],
        "log": "STEP | PID | LOCK",
        "cmd": "STEP",
        "topic_widgets": ["sp_value", "pv_value", "pid_wave", "auto_mode"],
    },
    {
        "slug": "motor_drive",
        "name": "Motor Drive",
        "cn": "电机与运动控制",
        "problem_type": "直流电机 / 步进 / 无刷 / 编码器测速 / 位置闭环",
        "home_kind": "motor",
        "accent": rgb565(29, 78, 216),
        "accent2": rgb565(96, 165, 250),
        "bg": rgb565(239, 246, 255),
        "code": "36",
        "metrics": [("RPM", "rpm", 2450), ("PWM", "pct", 54), ("CURR", "mA", 680), ("TEMP", "C", 38)],
        "params": [("target", 2400), ("accel", 120), ("limit", 800)],
        "log": "ENC | FOC | BRAKE",
        "cmd": "HOME",
        "topic_widgets": ["speed_gauge", "dir_fwd", "dir_rev", "brake_btn"],
    },
    {
        "slug": "sensor_daq",
        "name": "Sensor DAQ",
        "cn": "传感采集",
        "problem_type": "多路 ADC / 环境监测 / IMU / 称重 / 光电 / 超声",
        "home_kind": "daq",
        "accent": rgb565(180, 83, 9),
        "accent2": rgb565(251, 191, 36),
        "bg": rgb565(255, 251, 235),
        "code": "37",
        "metrics": [("TEMP", "C", 28), ("HUM", "pct", 58), ("LIGHT", "lx", 420), ("CO2", "ppm", 615)],
        "params": [("rate", 100), ("avg", 16), ("alarm", 80)],
        "log": "SENS | CAL | REC",
        "cmd": "ZERO",
        "topic_widgets": ["sensor_grid", "sample_bar", "cal_zero", "store_bar"],
    },
    {
        "slug": "robot_task",
        "name": "Robot Task",
        "cn": "机器人与小车",
        "problem_type": "循迹 / 避障 / 机械臂 / 底盘 / 任务调度",
        "home_kind": "robot",
        "accent": rgb565(124, 58, 237),
        "accent2": rgb565(167, 139, 250),
        "bg": rgb565(245, 243, 255),
        "code": "38",
        "metrics": [("X", "cm", 120), ("Y", "cm", 64), ("YAW", "deg", 18), ("DIST", "cm", 126)],
        "params": [("speed", 360), ("turn", 45), ("task", 2)],
        "log": "PATH | IMU | OBS",
        "cmd": "PATH",
        "topic_widgets": ["map_grid_0", "m0", "task_lane", "obs_front"],
    },
    {
        "slug": "vision_audio",
        "name": "Vision Audio",
        "cn": "图像与音频识别",
        "problem_type": "颜色识别 / 目标检测 / 声源定位 / 语音或频谱特征",
        "home_kind": "vision",
        "accent": rgb565(67, 56, 202),
        "accent2": rgb565(129, 140, 248),
        "bg": rgb565(238, 242, 255),
        "code": "39",
        "metrics": [("FPS", "fps", 28), ("OBJ", "cnt", 6), ("CONF", "pct", 92), ("LAT", "ms", 38)],
        "params": [("roi", 1), ("thresh", 65), ("gain", 12)],
        "log": "FRAME | ROI | PUSH",
        "cmd": "SNAP",
        "topic_widgets": ["camera_frame", "target_list", "conf_gauge", "snap_btn"],
    },
    {
        "slug": "field_debug",
        "name": "Field Debug",
        "cn": "综合调试",
        "problem_type": "现场联调 / 状态监控 / 故障诊断 / 日志 / 参数快改",
        "home_kind": "debug",
        "accent": rgb565(71, 85, 105),
        "accent2": rgb565(148, 163, 184),
        "bg": rgb565(248, 250, 252),
        "code": "3A",
        "metrics": [("MODE", "id", 2), ("UP", "s", 360), ("WARN", "cnt", 1), ("BOOT", "cnt", 12)],
        "params": [("mode", 2), ("level", 3), ("mask", 255)],
        "log": "BUS | LOG | SAFE",
        "cmd": "DUMP",
        "topic_widgets": ["console", "fault_count", "bus_uart", "dump_btn"],
    },
]


def style(bg: int, fg: int = P["ink"], border: int | None = None, **extra: Any) -> dict[str, Any]:
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
        "style": style(bg, P["ink"] if fg is None else fg),
    }


def panel(wid: str, x: int, y: int, w: int, h: int, bg: int = P["card"]) -> dict[str, Any]:
    return {
        "id": wid,
        "type": "text",
        "x": x,
        "y": y,
        "w": w,
        "h": h,
        "text": "",
        "style": style(bg, P["ink"], P["line"]),
    }


def num(wid: str, x: int, y: int, w: int, h: int, value: int, fg: int, length: int = 5) -> dict[str, Any]:
    return {
        "id": wid,
        "type": "number",
        "x": x,
        "y": y,
        "w": w,
        "h": h,
        "value": value,
        "style": style(P["white"], fg, P["line"], length=length),
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


def progress(wid: str, x: int, y: int, w: int, h: int, value: int, accent: int) -> dict[str, Any]:
    return {
        "id": wid,
        "type": "progress",
        "x": x,
        "y": y,
        "w": w,
        "h": h,
        "value": value,
        "style": style(P["paper"], accent, P["line"]),
    }


def gauge(wid: str, x: int, y: int, w: int, h: int, value: int, accent: int) -> dict[str, Any]:
    return {
        "id": wid,
        "type": "gauge",
        "x": x,
        "y": y,
        "w": w,
        "h": h,
        "value": value,
        "style": style(P["white"], accent, P["line"]),
    }


def wave(wid: str, x: int, y: int, w: int, h: int, accent: int) -> dict[str, Any]:
    return {"id": wid, "type": "waveform", "x": x, "y": y, "w": w, "h": h, "style": style(P["dark"], accent, P["line"])}


def checkbox(wid: str, x: int, y: int, value: int, accent: int) -> dict[str, Any]:
    return {"id": wid, "type": "checkbox", "x": x, "y": y, "w": 30, "h": 30, "value": value, "style": style(P["white"], accent, P["line"])}


def timer(wid: str, ms: int, event: str) -> dict[str, Any]:
    return {"id": wid, "type": "timer", "x": 0, "y": 0, "w": 1, "h": 1, "style": {"tim": ms, "en": 1}, "events": {"timer": [event]}}


def chip(wid: str, x: int, y: int, w: int, label: str, fg: int, bg: int = P["paper"]) -> dict[str, Any]:
    return text(wid, x, y, w, 18, label, bg, fg)


def header(cfg: dict[str, Any], label: str) -> list[dict[str, Any]]:
    return [
        panel("topbar", 0, 0, 800, 76, P["dark"]),
        text("top_accent", 0, 0, 800, 6, "", cfg["accent2"], P["white"]),
        text("side_accent", 0, 6, 8, 70, "", cfg["accent"], P["white"]),
        text("title", 24, 12, 360, 30, cfg["name"].upper(), P["dark"], P["white"]),
        text("sub", 24, 44, 520, 20, f"{cfg['cn']} | {label}", P["dark"], P["paper"]),
        chip("model_chip", 396, 21, 92, "800x480", cfg["accent2"], P["slate"]),
        chip("bus_chip", 498, 21, 52, "UART", P["paper"], P["slate"]),
        text("domain_badge", 558, 20, 62, 34, THEME_BADGES[cfg["home_kind"]], P["dark"], cfg["accent2"]),
        button("run", 646, 18, 122, 36, "RUN", cfg["accent2"], P["ink"], kind="state-button", value=1),
    ]


def page_chrome(cfg: dict[str, Any], page_code: str, marker: str) -> list[dict[str, Any]]:
    return [
        text("header_shadow", 0, 76, 800, 3, "", P["slate"], P["white"]),
        text("page_rail", 0, 79, 8, 401, "", cfg["accent"], P["white"]),
        chip("page_chip", 24, 84, 76, page_code, cfg["accent"]),
        chip("mark_chip", 112, 84, 86, f"TX {marker}", P["muted"]),
        chip("mode_chip", 210, 84, 72, "READY", cfg["accent2"]),
        chip("lock_chip", 294, 84, 86, "SAFE UI", P["muted"]),
    ]


def nav(active: int, accent: int) -> list[dict[str, Any]]:
    items = [("n_home", "HOME", "page page0"), ("n_param", "PARAM", "page page1"), ("n_log", "LOG", "page page2")]
    widgets: list[dict[str, Any]] = [panel("nav_dock", 498, 416, 284, 52, P["card"])]
    for idx, (wid, label, cmd) in enumerate(items):
        x = 512 + idx * 88
        selected = idx == active
        widgets.append(button(wid, x, 424, 72, 36, label, accent if selected else P["paper"], P["white"] if selected else P["ink"], {"up": [cmd]}))
    return widgets


def metric(widgets: list[dict[str, Any]], idx: int, x: int, y: int, spec: tuple[str, str, int], accent: int) -> None:
    label, unit, value = spec
    widgets.extend(
        [
            panel(f"m{idx}_card", x, y, 128, 78),
            text(f"m{idx}_stripe", x, y, 128, 5, "", accent, P["white"]),
            text(f"m{idx}_lab", x + 10, y + 8, 58, 18, label, P["white"], P["muted"]),
            num(f"m{idx}", x + 10, y + 34, 70, 30, int(value), accent),
            text(f"m{idx}_unit", x + 84, y + 39, 36, 18, unit, P["white"], P["muted"]),
        ]
    )


def action_buttons(cfg: dict[str, Any], y: int = 350) -> list[dict[str, Any]]:
    return [
        button("b_start", 420, y, 92, 44, "START", cfg["accent"], P["white"], {"up": [f"printh 23 {cfg['code']} 10 01", "run.val=1"]}),
        button("b_stop", 530, y, 92, 44, "STOP", P["red"], P["white"], {"up": [f"printh 23 {cfg['code']} 10 00", "run.val=0"]}),
        button("b_cmd", 640, y, 92, 44, cfg["cmd"], cfg["accent2"], P["ink"], {"up": [f"printh 23 {cfg['code']} 20 01"]}),
    ]


def home_power(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    a = cfg["accent"]
    widgets = [panel("flow_panel", 24, 106, 370, 210), text("flow_title", 44, 124, 180, 24, "POWER STAGE", P["white"], a)]
    metric(widgets, 0, 44, 166, cfg["metrics"][0], a)
    metric(widgets, 1, 230, 166, cfg["metrics"][1], a)
    widgets.extend(
        [
            text("flow_in", 72, 272, 72, 24, "INPUT", P["white"], P["muted"]),
            text("flow_arrow", 152, 270, 88, 26, ">>>", P["white"], a),
            text("flow_out", 252, 272, 80, 24, "OUTPUT", P["white"], P["muted"]),
            panel("safe_panel", 420, 106, 348, 210),
            text("safe_title", 444, 124, 170, 24, "PROTECTION", P["white"], a),
            checkbox("prot_ovp", 448, 166, 1, a),
            text("ovp_lab", 490, 172, 100, 22, "OVP", P["white"], P["muted"]),
            checkbox("prot_ocp", 448, 214, 1, a),
            text("ocp_lab", 490, 220, 100, 22, "OCP", P["white"], P["muted"]),
            progress("eff_bar", 610, 170, 118, 28, int(cfg["metrics"][3][2]), cfg["accent2"]),
            text("eff_lab", 610, 210, 110, 22, "efficiency", P["white"], P["muted"]),
            gauge("temp_guard", 610, 244, 92, 70, 38, a),
            text("temp_lab", 708, 266, 42, 20, "temp", P["white"], P["muted"]),
        ]
    )
    return widgets + action_buttons(cfg)


def home_scope(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    a = cfg["accent"]
    widgets = [panel("scope_panel", 24, 104, 500, 222), text("scope_title", 44, 122, 180, 24, "LIVE WAVEFORM", P["white"], a), wave("scope_wave", 44, 158, 460, 132, cfg["accent2"])]
    for idx, pos in enumerate([(552, 104), (672, 104), (552, 202), (672, 202)]):
        metric(widgets, idx, pos[0], pos[1], cfg["metrics"][idx], a)
    widgets.extend(
        [
            panel("range_box", 24, 348, 156, 46),
            text("range_lab", 40, 362, 58, 20, "RANGE", P["white"], P["muted"]),
            num("trig_level", 104, 356, 62, 30, 1200, a),
            button("b_hold", 420, 350, 92, 44, "HOLD", a, P["white"], {"up": [f"printh 23 {cfg['code']} 21 01"]}),
            button("b_auto", 530, 350, 92, 44, "AUTO", cfg["accent2"], P["ink"], {"up": [f"printh 23 {cfg['code']} 21 02"]}),
            button("b_zero", 640, 350, 92, 44, "ZERO", P["paper"], P["ink"], {"up": ["m0.val=0"]}),
        ]
    )
    return widgets


def home_source(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    a = cfg["accent"]
    widgets = [panel("source_panel", 24, 104, 370, 290), text("source_title", 44, 122, 170, 24, "WAVE OUTPUT", P["white"], a)]
    for idx, label in enumerate(["SINE", "SQR", "TRI"]):
        widgets.append(button(f"wave_{label.lower()}", 44 + idx * 104, 166, 86, 42, label, a if idx == 0 else P["paper"], P["white"] if idx == 0 else P["ink"], {"up": [f"printh 23 {cfg['code']} 22 {idx:02X}"]}))
    widgets.extend(
        [
            text("freq_lab", 48, 232, 72, 22, "freq", P["white"], P["muted"]),
            num("freq_set", 126, 226, 100, 34, 1000, a),
            text("amp_lab", 48, 282, 72, 22, "amp", P["white"], P["muted"]),
            num("amp_set", 126, 276, 100, 34, 1800, a),
            progress("duty_bar", 238, 232, 110, 28, 50, cfg["accent2"]),
            text("duty_lab", 238, 270, 92, 22, "duty", P["white"], P["muted"]),
            panel("preview_panel", 420, 104, 348, 222),
            text("preview_lab", 444, 122, 138, 24, "OUTPUT PREVIEW", P["white"], a),
            wave("out_wave", 444, 162, 286, 102, cfg["accent2"]),
            button("out_enable", 444, 280, 112, 38, "OUTPUT", a, P["white"], {"up": ["run.val=1"]}, kind="state-button", value=1),
        ]
    )
    return widgets + action_buttons(cfg, 350)


def home_comms(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    a = cfg["accent"]
    widgets = [panel("link_panel", 24, 104, 370, 222), text("link_title", 44, 122, 180, 24, "LINK STATUS", P["white"], a)]
    widgets.extend(
        [
            text("link_tx", 56, 176, 74, 34, "TX", P["white"], a),
            text("link_pipe", 144, 177, 100, 32, "====>", P["white"], cfg["accent2"]),
            text("link_rx", 260, 176, 74, 34, "RX", P["white"], a),
            progress("ber_bar", 68, 252, 270, 28, 2, cfg["accent2"]),
            text("ber_lab", 68, 288, 160, 22, "bit error monitor", P["white"], P["muted"]),
            panel("radio_panel", 420, 104, 348, 222),
            text("radio_title", 444, 122, 150, 24, "CHANNEL", P["white"], a),
            gauge("rssi_gauge", 456, 164, 112, 112, 72, a),
            progress("snr_bar", 606, 168, 110, 28, 75, cfg["accent2"]),
            text("snr_lab", 606, 204, 90, 22, "SNR", P["white"], P["muted"]),
        ]
    )
    for idx, pos in enumerate([(24, 344), (154, 344), (284, 344)]):
        metric(widgets, idx, pos[0], pos[1], cfg["metrics"][idx], a)
    widgets.extend(action_buttons(cfg, 350)[1:])
    return widgets


def home_pid(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    a = cfg["accent"]
    widgets = [panel("loop_panel", 24, 104, 370, 290), text("loop_title", 44, 122, 170, 24, "CLOSED LOOP", P["white"], a)]
    for idx, (wid, label, value) in enumerate([("sp_value", "SET", 500), ("pv_value", "PV", 486), ("err_value", "ERR", 14)]):
        y = 166 + idx * 52
        widgets.extend([text(f"{wid}_lab", 48, y + 8, 62, 22, label, P["white"], P["muted"]), num(wid, 120, y, 88, 34, value, a)])
    widgets.extend(
        [
            progress("out_bar", 232, 172, 112, 28, 42, cfg["accent2"]),
            text("out_lab", 232, 210, 72, 20, "output", P["white"], P["muted"]),
            button("auto_mode", 232, 262, 104, 40, "AUTO", a, P["white"], {"up": ["run.val=1"]}, kind="state-button", value=1),
            panel("trend_panel", 420, 104, 348, 222),
            text("trend_lab", 444, 122, 160, 24, "STEP RESPONSE", P["white"], a),
            wave("pid_wave", 444, 160, 286, 120, cfg["accent2"]),
        ]
    )
    return widgets + action_buttons(cfg)


def home_motor(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    a = cfg["accent"]
    widgets = [panel("motor_panel", 24, 104, 370, 290), text("motor_title", 44, 122, 160, 24, "DRIVE STATE", P["white"], a), gauge("speed_gauge", 56, 160, 150, 150, 82, a)]
    widgets.extend(
        [
            button("dir_fwd", 238, 166, 92, 38, "FWD", a, P["white"], {"up": [f"printh 23 {cfg['code']} 23 01"]}),
            button("dir_rev", 238, 214, 92, 38, "REV", P["paper"], P["ink"], {"up": [f"printh 23 {cfg['code']} 23 02"]}),
            button("brake_btn", 238, 262, 92, 38, "BRAKE", P["red"], P["white"], {"up": [f"printh 23 {cfg['code']} 23 03"]}),
            panel("telemetry_panel", 420, 104, 348, 222),
            text("telemetry_lab", 444, 122, 150, 24, "MOTOR TELEMETRY", P["white"], a),
        ]
    )
    for idx, pos in enumerate([(444, 164), (606, 164), (444, 244), (606, 244)]):
        metric(widgets, idx, pos[0], pos[1], cfg["metrics"][idx], a)
    return widgets + action_buttons(cfg)


def home_daq(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    a = cfg["accent"]
    widgets = [panel("sensor_grid", 24, 104, 370, 290), text("sensor_title", 44, 122, 180, 24, "SENSOR ARRAY", P["white"], a)]
    for idx, pos in enumerate([(44, 166), (216, 166), (44, 262), (216, 262)]):
        metric(widgets, idx, pos[0], pos[1], cfg["metrics"][idx], a)
    widgets.extend(
        [
            panel("daq_panel", 420, 104, 348, 222),
            text("daq_lab", 444, 122, 160, 24, "ACQUISITION", P["white"], a),
            progress("sample_bar", 444, 170, 260, 30, 64, cfg["accent2"]),
            text("sample_lab", 444, 210, 130, 22, "sample buffer", P["white"], P["muted"]),
            progress("store_bar", 444, 252, 260, 30, 28, a),
            text("store_lab", 444, 292, 110, 22, "storage", P["white"], P["muted"]),
            button("cal_zero", 420, 350, 92, 44, "ZERO", a, P["white"], {"up": [f"printh 23 {cfg['code']} 24 01"]}),
            button("cal_span", 530, 350, 92, 44, "SPAN", cfg["accent2"], P["ink"], {"up": [f"printh 23 {cfg['code']} 24 02"]}),
            button("rec_btn", 640, 350, 92, 44, "REC", P["red"], P["white"], {"up": ["run.val=1"]}, kind="state-button", value=0),
        ]
    )
    return widgets


def home_robot(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    a = cfg["accent"]
    widgets = [panel("map_panel", 24, 104, 370, 290), text("map_title", 44, 122, 180, 24, "TASK MAP", P["white"], a)]
    for idx, (x, y, w, h) in enumerate([(54, 166, 76, 44), (150, 166, 76, 44), (246, 166, 76, 44), (150, 230, 76, 44), (246, 294, 76, 44)]):
        widgets.append(text(f"map_grid_{idx}", x, y, w, h, "NODE", P["paper"] if idx != 1 else cfg["accent2"], P["ink"]))
    widgets.extend(
        [
            text("task_lane", 60, 348, 260, 24, "A1 > A2 > B2 > C3", P["white"], P["muted"]),
            panel("pose_panel", 420, 104, 348, 222),
            text("pose_lab", 444, 122, 150, 24, "POSE / OBSTACLE", P["white"], a),
        ]
    )
    for idx, pos in enumerate([(444, 164), (606, 164), (444, 244), (606, 244)]):
        metric(widgets, idx, pos[0], pos[1], cfg["metrics"][idx], a)
    widgets.extend([progress("obs_front", 444, 330, 120, 28, 38, cfg["accent2"]), *action_buttons(cfg, 350)[1:]])
    return widgets


def home_vision(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    a = cfg["accent"]
    widgets = [panel("camera_frame", 24, 104, 370, 290, P["dark"]), text("frame_title", 44, 122, 160, 24, "CAMERA ROI", P["dark"], cfg["accent2"])]
    widgets.extend(
        [
            text("roi_box", 96, 170, 176, 110, "TARGET", P["paper"], a),
            text("target_list", 44, 322, 250, 24, "id=3  color=red  lock=on", P["dark"], P["white"]),
            panel("ai_panel", 420, 104, 348, 222),
            text("ai_lab", 444, 122, 150, 24, "RECOGNITION", P["white"], a),
            gauge("conf_gauge", 454, 158, 118, 118, 92, a),
            progress("lat_bar", 610, 170, 110, 28, 38, cfg["accent2"]),
            text("lat_lab", 610, 208, 78, 22, "latency", P["white"], P["muted"]),
        ]
    )
    for idx, pos in enumerate([(420, 350), (530, 350), (640, 350)]):
        label = ["SNAP", "MARK", "SEND"][idx]
        widgets.append(button("snap_btn" if idx == 0 else f"vision_btn{idx}", pos[0], pos[1], 92, 44, label, a if idx == 0 else cfg["accent2"], P["white"] if idx == 0 else P["ink"], {"up": [f"printh 23 {cfg['code']} 25 {idx:02X}"]}))
    return widgets


def home_debug(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    a = cfg["accent"]
    widgets = [panel("console", 24, 104, 500, 222, P["dark"]), text("console_title", 44, 122, 150, 24, "LIVE CONSOLE", P["dark"], cfg["accent2"])]
    for idx, line in enumerate(["[00] boot ok", "[01] uart ok", "[02] warn: sensor lag", "[03] ready"]):
        widgets.append(text(f"console_l{idx}", 44, 160 + idx * 32, 310, 22, line, P["dark"], P["white"]))
    widgets.extend(
        [
            panel("fault_panel", 552, 104, 216, 222),
            text("fault_lab", 574, 122, 130, 24, "FAULT BOARD", P["white"], a),
            num("fault_count", 574, 166, 76, 34, 0, a),
            text("fault_unit", 660, 174, 60, 20, "fault", P["white"], P["muted"]),
            checkbox("bus_uart", 574, 224, 1, a),
            text("uart_lab", 616, 230, 80, 22, "UART", P["white"], P["muted"]),
            checkbox("bus_can", 574, 270, 1, a),
            text("can_lab", 616, 276, 80, 22, "CAN", P["white"], P["muted"]),
            button("dump_btn", 420, 350, 92, 44, "DUMP", a, P["white"], {"up": [f"printh 23 {cfg['code']} 26 01"]}),
            button("reset_btn", 530, 350, 92, 44, "RESET", P["red"], P["white"], {"up": [f"printh 23 {cfg['code']} 26 02"]}),
            button("mute_btn", 640, 350, 92, 44, "MUTE", P["paper"], P["ink"], {"up": ["fault_count.val=0"]}),
        ]
    )
    return widgets


HOME_BUILDERS = {
    "power_flow": home_power,
    "scope": home_scope,
    "source": home_source,
    "comms": home_comms,
    "pid": home_pid,
    "motor": home_motor,
    "daq": home_daq,
    "robot": home_robot,
    "vision": home_vision,
    "debug": home_debug,
}


def make_dashboard(cfg: dict[str, Any]) -> dict[str, Any]:
    widgets = header(cfg, "problem dashboard")
    widgets.extend(page_chrome(cfg, "DASH", f"23 {cfg['code']}"))
    widgets.extend(HOME_BUILDERS[cfg["home_kind"]](cfg))
    widgets.extend([timer("tm0", 500, "tick.val++"), num("tick", 786, 78, 1, 1, 0, cfg["accent"], length=1)])
    widgets.extend(nav(0, cfg["accent"]))
    return {"id": "page0", "layout": {"type": "absolute"}, "widgets": widgets}


PAGE1_ROLES = {
    "power_flow": "limits and protection setup",
    "scope": "acquisition and trigger setup",
    "source": "waveform synthesis setup",
    "comms": "protocol and channel setup",
    "pid": "PID gain tuning",
    "motor": "motion profile setup",
    "daq": "sensor channel setup",
    "robot": "task and waypoint setup",
    "vision": "ROI and detection setup",
    "debug": "service command panel",
}

PAGE2_ROLES = {
    "power_flow": "ripple and fault diagnostics",
    "scope": "capture statistics",
    "source": "output quality monitor",
    "comms": "packet and BER diagnostics",
    "pid": "response analysis",
    "motor": "encoder and drive diagnostics",
    "daq": "record and alarm diagnostics",
    "robot": "path replay diagnostics",
    "vision": "recognition result review",
    "debug": "console and fault history",
}

PAGE1_WIDGETS = {
    "power_flow": ["sp0", "i_limit", "load_step", "prot_latch"],
    "scope": ["sp0", "trig_mode", "ch1_en", "sample_depth"],
    "source": ["sp0", "wave_sine_sel", "mod_en", "sweep_bar"],
    "comms": ["sp0", "proto_uart", "chan_num", "tx_power"],
    "pid": ["sp0", "kp_slider", "ki_slider", "manual_out"],
    "motor": ["sp0", "profile_accel", "dir_select", "current_limit"],
    "daq": ["sp0", "ch1_en", "avg_depth", "alarm_level"],
    "robot": ["sp0", "wp_a", "wp_b", "task_mode"],
    "vision": ["sp0", "roi_x", "threshold_bar", "detect_mode"],
    "debug": ["sp0", "svc_mask", "bus_uart_cfg", "safe_boot"],
}

PAGE2_WIDGETS = {
    "power_flow": ["diag_wave", "fault_ovp", "fault_ocp", "eff_hist"],
    "scope": ["capture_wave", "stat_min", "stat_max", "cursor_delta"],
    "source": ["monitor_wave", "thd_bar", "sync_lock", "load_state"],
    "comms": ["packet_log", "rx_good", "rx_bad", "ber_hist"],
    "pid": ["response_wave", "settle_time", "overshoot", "steady_err"],
    "motor": ["encoder_wave", "drv_fault", "thermal_bar", "stall_count"],
    "daq": ["record_wave", "alarm_ch", "sd_fill", "lost_count"],
    "robot": ["path_trace", "checkpoint", "miss_count", "pose_log"],
    "vision": ["result_frame", "class_id", "confidence_bar", "latency_hist"],
    "debug": ["console_log", "fault_code", "reset_count", "trace_qr"],
}


def make_params(cfg: dict[str, Any]) -> dict[str, Any]:
    a = cfg["accent"]
    kind = cfg["home_kind"]
    widgets = header(cfg, PAGE1_ROLES[kind])
    widgets.extend(page_chrome(cfg, "SETUP", f"23 {cfg['code']}"))
    if kind == "power_flow":
        widgets.extend([
            panel("limit_panel", 24, 104, 350, 290), text("limit_title", 44, 122, 220, 24, "OUTPUT LIMITS", P["white"], a),
            text("sp0_lab", 48, 170, 94, 22, "v_set", P["white"], P["muted"]), num("sp0", 150, 164, 100, 34, 5000, a),
            text("i_lab", 48, 224, 94, 22, "i_limit", P["white"], P["muted"]), num("i_limit", 150, 218, 100, 34, 1000, a),
            progress("load_step", 48, 286, 230, 30, 64, cfg["accent2"]), text("load_lab", 48, 324, 120, 22, "load step", P["white"], P["muted"]),
            panel("prot_panel", 420, 104, 348, 290), text("prot_title", 444, 122, 190, 24, "PROTECTION MATRIX", P["white"], a),
            checkbox("prot_latch", 448, 166, 1, a), text("latch_lab", 490, 172, 130, 22, "fault latch", P["white"], P["muted"]),
            checkbox("soft_start", 448, 214, 1, a), text("soft_lab", 490, 220, 130, 22, "soft start", P["white"], P["muted"]),
            button("b_apply", 448, 330, 122, 44, "ARM", a, P["white"], {"up": [f"printh 23 {cfg['code']} 31 01"]}),
            button("b_back", 592, 330, 122, 44, "DISARM", P["paper"], P["ink"], {"up": ["run.val=0"]}),
        ])
    elif kind == "scope":
        widgets.extend([
            panel("acq_panel", 24, 104, 350, 290), text("acq_title", 44, 122, 220, 24, "ACQUISITION", P["white"], a),
            text("range_lab", 48, 168, 80, 22, "range", P["white"], P["muted"]), num("sp0", 140, 162, 86, 34, 5, a),
            text("depth_lab", 48, 222, 90, 22, "depth", P["white"], P["muted"]), num("sample_depth", 140, 216, 86, 34, 48, a),
            checkbox("ch1_en", 48, 280, 1, a), text("ch1_lab", 90, 286, 80, 22, "CH1", P["white"], P["muted"]),
            checkbox("ch2_en", 176, 280, 0, a), text("ch2_lab", 218, 286, 80, 22, "CH2", P["white"], P["muted"]),
            panel("trig_panel", 420, 104, 348, 290), text("trig_title", 444, 122, 180, 24, "TRIGGER", P["white"], a),
            button("trig_mode", 448, 166, 98, 38, "RISING", a, P["white"], {"up": [f"printh 23 {cfg['code']} 32 01"]}),
            button("trig_fall", 560, 166, 98, 38, "FALL", P["paper"], P["ink"], {"up": [f"printh 23 {cfg['code']} 32 02"]}),
            {"id": "trig_slider", "type": "slider", "x": 448, "y": 246, "w": 210, "h": 34, "value": 52, "style": style(P["paper"], cfg["accent2"], P["line"])},
            button("b_apply", 448, 330, 122, 44, "CAPTURE", a, P["white"], {"up": [f"printh 23 {cfg['code']} 32 03"]}),
        ])
    elif kind == "source":
        widgets.extend([
            panel("wave_panel", 24, 104, 350, 290), text("wave_title", 44, 122, 220, 24, "SYNTHESIS", P["white"], a),
            button("wave_sine_sel", 48, 166, 82, 38, "SINE", a, P["white"], {"up": [f"printh 23 {cfg['code']} 33 01"]}),
            button("wave_square_sel", 148, 166, 82, 38, "SQR", P["paper"], P["ink"], {"up": [f"printh 23 {cfg['code']} 33 02"]}),
            button("wave_tri_sel", 248, 166, 82, 38, "TRI", P["paper"], P["ink"], {"up": [f"printh 23 {cfg['code']} 33 03"]}),
            text("sp0_lab", 48, 232, 72, 22, "freq", P["white"], P["muted"]), num("sp0", 126, 226, 100, 34, 1000, a),
            text("amp_lab", 48, 286, 72, 22, "amp", P["white"], P["muted"]), num("amp_cfg", 126, 280, 100, 34, 1800, a),
            panel("mod_panel", 420, 104, 348, 290), text("mod_title", 444, 122, 160, 24, "SWEEP / MOD", P["white"], a),
            checkbox("mod_en", 448, 166, 0, a), text("mod_lab", 490, 172, 120, 22, "mod enable", P["white"], P["muted"]),
            progress("sweep_bar", 448, 230, 230, 30, 25, cfg["accent2"]), text("sweep_lab", 448, 268, 120, 22, "sweep span", P["white"], P["muted"]),
            button("b_apply", 448, 330, 122, 44, "OUTPUT", a, P["white"], {"up": ["run.val=1"]}),
        ])
    elif kind == "comms":
        widgets.extend([
            panel("proto_panel", 24, 104, 350, 290), text("proto_title", 44, 122, 200, 24, "PROTOCOL", P["white"], a),
            button("proto_uart", 48, 166, 88, 38, "UART", a, P["white"], {"up": [f"printh 23 {cfg['code']} 34 01"]}),
            button("proto_can", 156, 166, 88, 38, "CAN", P["paper"], P["ink"], {"up": [f"printh 23 {cfg['code']} 34 02"]}),
            text("sp0_lab", 48, 232, 72, 22, "baud", P["white"], P["muted"]), num("sp0", 126, 226, 100, 34, 1152, a),
            text("chan_lab", 48, 286, 72, 22, "chan", P["white"], P["muted"]), num("chan_num", 126, 280, 100, 34, 8, a),
            panel("rf_panel", 420, 104, 348, 290), text("rf_title", 444, 122, 180, 24, "RF CHANNEL", P["white"], a),
            progress("tx_power", 448, 172, 220, 30, 60, cfg["accent2"]), text("pwr_lab", 448, 210, 90, 22, "tx power", P["white"], P["muted"]),
            checkbox("fec_en", 448, 254, 1, a), text("fec_lab", 490, 260, 90, 22, "FEC", P["white"], P["muted"]),
            button("b_apply", 448, 330, 122, 44, "PAIR", a, P["white"], {"up": [f"printh 23 {cfg['code']} 34 03"]}),
        ])
    elif kind == "pid":
        widgets.extend([
            panel("gain_panel", 24, 104, 370, 290), text("gain_title", 44, 122, 200, 24, "GAIN TUNING", P["white"], a),
            text("sp0_lab", 48, 166, 46, 22, "KP", P["white"], P["muted"]), num("sp0", 104, 160, 70, 34, 120, a), {"id": "kp_slider", "type": "slider", "x": 190, "y": 162, "w": 130, "h": 32, "value": 56, "style": style(P["paper"], cfg["accent2"], P["line"])},
            text("ki_lab", 48, 222, 46, 22, "KI", P["white"], P["muted"]), num("ki_num", 104, 216, 70, 34, 18, a), {"id": "ki_slider", "type": "slider", "x": 190, "y": 218, "w": 130, "h": 32, "value": 18, "style": style(P["paper"], cfg["accent2"], P["line"])},
            text("kd_lab", 48, 278, 46, 22, "KD", P["white"], P["muted"]), num("kd_num", 104, 272, 70, 34, 42, a),
            panel("manual_panel", 420, 104, 348, 290), text("manual_title", 444, 122, 180, 24, "MANUAL OUTPUT", P["white"], a),
            progress("manual_out", 448, 172, 220, 30, 42, cfg["accent2"]),
            checkbox("anti_windup", 448, 236, 1, a), text("windup_lab", 490, 242, 130, 22, "anti windup", P["white"], P["muted"]),
            button("b_apply", 448, 330, 122, 44, "APPLY", a, P["white"], {"up": [f"printh 23 {cfg['code']} 35 01"]}),
        ])
    elif kind == "motor":
        widgets.extend([
            panel("motion_panel", 24, 104, 350, 290), text("motion_title", 44, 122, 190, 24, "MOTION PROFILE", P["white"], a),
            text("sp0_lab", 48, 170, 80, 22, "target", P["white"], P["muted"]), num("sp0", 140, 164, 92, 34, 2400, a),
            text("acc_lab", 48, 224, 80, 22, "accel", P["white"], P["muted"]), num("profile_accel", 140, 218, 92, 34, 120, a),
            progress("current_limit", 48, 286, 230, 30, 80, cfg["accent2"]),
            panel("dir_panel", 420, 104, 348, 290), text("dir_title", 444, 122, 160, 24, "DIRECTION", P["white"], a),
            button("dir_select", 448, 166, 92, 38, "FWD", a, P["white"], {"up": [f"printh 23 {cfg['code']} 36 01"]}),
            button("dir_back", 560, 166, 92, 38, "REV", P["paper"], P["ink"], {"up": [f"printh 23 {cfg['code']} 36 02"]}),
            button("brake_cfg", 448, 250, 92, 38, "BRAKE", P["red"], P["white"], {"up": [f"printh 23 {cfg['code']} 36 03"]}),
            button("b_apply", 448, 330, 122, 44, "RUN", a, P["white"], {"up": ["run.val=1"]}),
        ])
    elif kind == "daq":
        widgets.extend([
            panel("channel_panel", 24, 104, 350, 290), text("channel_title", 44, 122, 190, 24, "CHANNELS", P["white"], a),
            checkbox("ch1_en", 48, 166, 1, a), text("ch1_lab", 90, 172, 80, 22, "CH1", P["white"], P["muted"]),
            checkbox("ch2_en", 176, 166, 1, a), text("ch2_lab", 218, 172, 80, 22, "CH2", P["white"], P["muted"]),
            checkbox("ch3_en", 48, 222, 0, a), text("ch3_lab", 90, 228, 80, 22, "CH3", P["white"], P["muted"]),
            checkbox("ch4_en", 176, 222, 0, a), text("ch4_lab", 218, 228, 80, 22, "CH4", P["white"], P["muted"]),
            text("sp0_lab", 48, 298, 80, 22, "rate", P["white"], P["muted"]), num("sp0", 140, 292, 92, 34, 100, a),
            panel("filter_panel", 420, 104, 348, 290), text("filter_title", 444, 122, 180, 24, "FILTER / ALARM", P["white"], a),
            num("avg_depth", 448, 166, 76, 34, 16, a), text("avg_lab", 534, 174, 80, 20, "avg", P["white"], P["muted"]),
            progress("alarm_level", 448, 230, 220, 30, 80, cfg["accent2"]),
            button("b_apply", 448, 330, 122, 44, "CAL", a, P["white"], {"up": [f"printh 23 {cfg['code']} 37 01"]}),
        ])
    elif kind == "robot":
        widgets.extend([
            panel("wp_panel", 24, 104, 370, 290), text("wp_title", 44, 122, 190, 24, "WAYPOINTS", P["white"], a),
            button("wp_a", 48, 166, 82, 42, "A", a, P["white"], {"up": [f"printh 23 {cfg['code']} 38 01"]}),
            button("wp_b", 150, 166, 82, 42, "B", P["paper"], P["ink"], {"up": [f"printh 23 {cfg['code']} 38 02"]}),
            button("wp_c", 252, 166, 82, 42, "C", P["paper"], P["ink"], {"up": [f"printh 23 {cfg['code']} 38 03"]}),
            text("sp0_lab", 48, 244, 80, 22, "speed", P["white"], P["muted"]), num("sp0", 140, 238, 92, 34, 360, a),
            panel("task_panel", 420, 104, 348, 290), text("task_title", 444, 122, 160, 24, "TASK MODE", P["white"], a),
            button("task_mode", 448, 166, 98, 38, "TRACK", a, P["white"], {"up": [f"printh 23 {cfg['code']} 38 04"]}),
            button("task_pick", 560, 166, 98, 38, "PICK", P["paper"], P["ink"], {"up": [f"printh 23 {cfg['code']} 38 05"]}),
            progress("safe_dist", 448, 246, 210, 30, 42, cfg["accent2"]),
            button("b_apply", 448, 330, 122, 44, "START", a, P["white"], {"up": ["run.val=1"]}),
        ])
    elif kind == "vision":
        widgets.extend([
            panel("roi_panel", 24, 104, 350, 290), text("roi_title", 44, 122, 190, 24, "ROI SETUP", P["white"], a),
            text("sp0_lab", 48, 170, 54, 22, "roi", P["white"], P["muted"]), num("sp0", 112, 164, 76, 34, 1, a),
            text("x_lab", 48, 224, 54, 22, "x", P["white"], P["muted"]), num("roi_x", 112, 218, 76, 34, 96, a),
            text("y_lab", 204, 224, 54, 22, "y", P["white"], P["muted"]), num("roi_y", 268, 218, 76, 34, 64, a),
            panel("detect_panel", 420, 104, 348, 290), text("detect_title", 444, 122, 180, 24, "DETECTION", P["white"], a),
            button("detect_mode", 448, 166, 100, 38, "COLOR", a, P["white"], {"up": [f"printh 23 {cfg['code']} 39 01"]}),
            button("detect_audio", 560, 166, 100, 38, "AUDIO", P["paper"], P["ink"], {"up": [f"printh 23 {cfg['code']} 39 02"]}),
            progress("threshold_bar", 448, 244, 210, 30, 65, cfg["accent2"]),
            button("b_apply", 448, 330, 122, 44, "SNAP", a, P["white"], {"up": [f"printh 23 {cfg['code']} 39 03"]}),
        ])
    else:
        widgets.extend([
            panel("svc_panel", 24, 104, 370, 290), text("svc_title", 44, 122, 190, 24, "SERVICE COMMANDS", P["white"], a),
            text("sp0_lab", 48, 170, 80, 22, "mode", P["white"], P["muted"]), num("sp0", 140, 164, 92, 34, 2, a),
            text("mask_lab", 48, 224, 80, 22, "mask", P["white"], P["muted"]), num("svc_mask", 140, 218, 92, 34, 255, a),
            checkbox("safe_boot", 48, 286, 1, a), text("safe_lab", 90, 292, 100, 22, "safe boot", P["white"], P["muted"]),
            panel("bus_panel", 420, 104, 348, 290), text("bus_title", 444, 122, 160, 24, "BUS CONTROL", P["white"], a),
            checkbox("bus_uart_cfg", 448, 166, 1, a), text("uart_lab", 490, 172, 80, 22, "UART", P["white"], P["muted"]),
            checkbox("bus_can_cfg", 448, 222, 1, a), text("can_lab", 490, 228, 80, 22, "CAN", P["white"], P["muted"]),
            button("b_apply", 448, 330, 122, 44, "DUMP", a, P["white"], {"up": [f"printh 23 {cfg['code']} 3A 01"]}),
            button("b_back", 592, 330, 122, 44, "RESET", P["red"], P["white"], {"up": [f"printh 23 {cfg['code']} 3A 02"]}),
        ])
    widgets.extend(nav(1, a))
    return {"id": "page1", "layout": {"type": "absolute"}, "widgets": widgets}


def make_log(cfg: dict[str, Any]) -> dict[str, Any]:
    a = cfg["accent"]
    kind = cfg["home_kind"]
    widgets = header(cfg, PAGE2_ROLES[kind])
    widgets.extend(page_chrome(cfg, "DIAG", f"23 {cfg['code']}"))
    if kind == "power_flow":
        widgets.extend([
            panel("diag_panel", 24, 104, 500, 222), text("diag_title", 44, 122, 170, 24, "RIPPLE MONITOR", P["white"], a),
            wave("diag_wave", 44, 160, 430, 110, cfg["accent2"]), progress("eff_hist", 44, 298, 260, 28, 91, cfg["accent2"]),
            panel("fault_panel", 552, 104, 216, 222), text("fault_title", 574, 122, 120, 24, "FAULTS", P["white"], a),
            checkbox("fault_ovp", 574, 166, 0, a), text("fovp_lab", 616, 172, 70, 22, "OVP", P["white"], P["muted"]),
            checkbox("fault_ocp", 574, 214, 0, a), text("focp_lab", 616, 220, 70, 22, "OCP", P["white"], P["muted"]),
        ])
    elif kind == "scope":
        widgets.extend([
            panel("capture_panel", 24, 104, 500, 222), text("capture_title", 44, 122, 170, 24, "CAPTURE", P["white"], a),
            wave("capture_wave", 44, 160, 430, 110, cfg["accent2"]),
            panel("stat_panel", 552, 104, 216, 222), text("stat_title", 574, 122, 110, 24, "STATS", P["white"], a),
            num("stat_min", 574, 166, 76, 32, 12, a), text("min_lab", 660, 174, 46, 20, "min", P["white"], P["muted"]),
            num("stat_max", 574, 214, 76, 32, 3300, a), text("max_lab", 660, 222, 46, 20, "max", P["white"], P["muted"]),
            num("cursor_delta", 574, 262, 76, 32, 88, a), text("cur_lab", 660, 270, 46, 20, "dT", P["white"], P["muted"]),
        ])
    elif kind == "source":
        widgets.extend([
            panel("monitor_panel", 24, 104, 500, 222), text("monitor_title", 44, 122, 170, 24, "OUTPUT MONITOR", P["white"], a),
            wave("monitor_wave", 44, 160, 430, 110, cfg["accent2"]),
            panel("quality_panel", 552, 104, 216, 222), text("quality_title", 574, 122, 120, 24, "QUALITY", P["white"], a),
            progress("thd_bar", 574, 170, 132, 28, 6, cfg["accent2"]), text("thd_lab", 574, 208, 70, 20, "THD", P["white"], P["muted"]),
            checkbox("sync_lock", 574, 246, 1, a), text("sync_lab", 616, 252, 70, 22, "SYNC", P["white"], P["muted"]),
            checkbox("load_state", 574, 286, 1, a), text("load_lab", 616, 292, 70, 22, "LOAD", P["white"], P["muted"]),
        ])
    elif kind == "comms":
        widgets.extend([
            panel("packet_log", 24, 104, 500, 222, P["dark"]), text("packet_title", 44, 122, 130, 24, "PACKET LOG", P["dark"], cfg["accent2"]),
            text("pkt_l0", 44, 160, 280, 22, "TX 23 34 10 01", P["dark"], P["white"]), text("pkt_l1", 44, 194, 280, 22, "RX ACK seq=42", P["dark"], P["white"]),
            text("pkt_l2", 44, 228, 280, 22, "BER window clean", P["dark"], P["white"]),
            panel("ber_panel", 552, 104, 216, 222), text("ber_title", 574, 122, 100, 24, "BER", P["white"], a),
            num("rx_good", 574, 166, 76, 32, 4096, a), text("good_lab", 660, 174, 50, 20, "good", P["white"], P["muted"]),
            num("rx_bad", 574, 214, 76, 32, 0, a), text("bad_lab", 660, 222, 50, 20, "bad", P["white"], P["muted"]),
            progress("ber_hist", 574, 270, 132, 28, 2, cfg["accent2"]),
        ])
    elif kind == "pid":
        widgets.extend([
            panel("resp_panel", 24, 104, 500, 222), text("resp_title", 44, 122, 180, 24, "RESPONSE", P["white"], a),
            wave("response_wave", 44, 160, 430, 110, cfg["accent2"]),
            panel("pid_stat_panel", 552, 104, 216, 222), text("pid_stat_title", 574, 122, 120, 24, "ANALYSIS", P["white"], a),
            num("settle_time", 574, 166, 76, 32, 230, a), text("settle_lab", 660, 174, 50, 20, "ms", P["white"], P["muted"]),
            num("overshoot", 574, 214, 76, 32, 5, a), text("over_lab", 660, 222, 50, 20, "pct", P["white"], P["muted"]),
            num("steady_err", 574, 262, 76, 32, 1, a), text("err_lab", 660, 270, 50, 20, "err", P["white"], P["muted"]),
        ])
    elif kind == "motor":
        widgets.extend([
            panel("enc_panel", 24, 104, 500, 222), text("enc_title", 44, 122, 180, 24, "ENCODER TRACE", P["white"], a),
            wave("encoder_wave", 44, 160, 430, 110, cfg["accent2"]),
            panel("drive_panel", 552, 104, 216, 222), text("drive_title", 574, 122, 130, 24, "DRIVE HEALTH", P["white"], a),
            checkbox("drv_fault", 574, 166, 0, a), text("drv_lab", 616, 172, 70, 22, "FAULT", P["white"], P["muted"]),
            progress("thermal_bar", 574, 222, 132, 28, 38, cfg["accent2"]), text("thermal_lab", 574, 260, 80, 20, "thermal", P["white"], P["muted"]),
            num("stall_count", 574, 286, 76, 32, 0, a),
        ])
    elif kind == "daq":
        widgets.extend([
            panel("record_panel", 24, 104, 500, 222), text("record_title", 44, 122, 180, 24, "RECORD STREAM", P["white"], a),
            wave("record_wave", 44, 160, 430, 110, cfg["accent2"]),
            panel("alarm_panel", 552, 104, 216, 222), text("alarm_title", 574, 122, 110, 24, "ALARMS", P["white"], a),
            num("alarm_ch", 574, 166, 76, 32, 2, a), text("alarm_lab", 660, 174, 46, 20, "ch", P["white"], P["muted"]),
            progress("sd_fill", 574, 222, 132, 28, 28, cfg["accent2"]), text("sd_lab", 574, 260, 80, 20, "sd fill", P["white"], P["muted"]),
            num("lost_count", 574, 286, 76, 32, 0, a),
        ])
    elif kind == "robot":
        widgets.extend([
            panel("path_trace", 24, 104, 500, 222), text("path_title", 44, 122, 180, 24, "PATH REPLAY", P["white"], a),
            text("path_nodes", 60, 174, 360, 40, "A1 -> A2 -> B2 -> C3", P["white"], a),
            progress("checkpoint", 60, 250, 360, 30, 66, cfg["accent2"]),
            panel("pose_log", 552, 104, 216, 222), text("pose_title", 574, 122, 120, 24, "MISSION", P["white"], a),
            num("miss_count", 574, 166, 76, 32, 0, a), text("miss_lab", 660, 174, 50, 20, "miss", P["white"], P["muted"]),
            checkbox("dock_ok", 574, 230, 1, a), text("dock_lab", 616, 236, 60, 22, "dock", P["white"], P["muted"]),
        ])
    elif kind == "vision":
        widgets.extend([
            panel("result_frame", 24, 104, 500, 222, P["dark"]), text("result_title", 44, 122, 180, 24, "RESULT REVIEW", P["dark"], cfg["accent2"]),
            text("bbox", 100, 170, 190, 90, "TARGET  id=3", P["paper"], a),
            panel("result_panel", 552, 104, 216, 222), text("result_panel_title", 574, 122, 120, 24, "CLASSIFY", P["white"], a),
            num("class_id", 574, 166, 76, 32, 3, a), text("class_lab", 660, 174, 50, 20, "class", P["white"], P["muted"]),
            progress("confidence_bar", 574, 222, 132, 28, 92, cfg["accent2"]),
            progress("latency_hist", 574, 284, 132, 28, 38, a),
        ])
    else:
        widgets.extend([
            panel("console_log", 24, 104, 500, 222, P["dark"]), text("console_title", 44, 122, 180, 24, "FAULT HISTORY", P["dark"], cfg["accent2"]),
            text("log_l0", 44, 160, 300, 22, "E00 boot ok", P["dark"], P["white"]), text("log_l1", 44, 194, 300, 22, "W12 sensor lag", P["dark"], P["white"]),
            text("log_l2", 44, 228, 300, 22, "I30 recovery armed", P["dark"], P["white"]),
            panel("trace_panel", 552, 104, 216, 222), text("trace_title", 574, 122, 120, 24, "TRACE", P["white"], a),
            num("fault_code", 574, 166, 76, 32, 12, a), text("code_lab", 660, 174, 50, 20, "code", P["white"], P["muted"]),
            num("reset_count", 574, 214, 76, 32, 3, a), text("rst_lab", 660, 222, 50, 20, "rst", P["white"], P["muted"]),
            {"id": "trace_qr", "type": "qrcode", "x": 604, "y": 262, "w": 58, "h": 58, "text": "debug:trace", "style": style(P["white"], a, P["line"])},
        ])
    widgets.extend([
        text("seq_lab", 44, 350, 70, 24, "seq", P["white"], P["muted"]),
        num("seq", 118, 344, 90, 36, 0, a),
        button("b_clear", 232, 344, 94, 40, "CLEAR", P["paper"], P["ink"], {"up": ["seq.val=0"]}),
        button("b_mark", 346, 344, 94, 40, "MARK", a, P["white"], {"up": [f"printh 23 {cfg['code']} 40 01"]}),
        timer("tm1", 1000, "seq.val++"),
    ])
    widgets.extend(nav(2, a))
    return {"id": "page2", "layout": {"type": "absolute"}, "widgets": widgets}


def make_scene(cfg: dict[str, Any]) -> dict[str, Any]:
    return {
        "project": {"name": f"econtest-{cfg['slug']}", "default_page": "page0", "drop_seed_objects": True},
        "canvas": {"width": CANVAS_W, "height": CANVAS_H, "background_color": cfg["bg"]},
        "assets": {},
        "pages": [make_dashboard(cfg), make_params(cfg), make_log(cfg)],
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ordered_unique(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def main() -> None:
    index = {"schema": "usarthmi.econtest_templates.v3", "canvas": {"width": CANVAS_W, "height": CANVAS_H}, "count": len(TEMPLATES), "templates": []}
    for cfg in TEMPLATES:
        scene = make_scene(cfg)
        rel_scene = Path(cfg["slug"]) / "scene.json"
        write_json(OUT_ROOT / rel_scene, scene)
        index["templates"].append(
            {
                "slug": cfg["slug"],
                "name": cfg["name"],
                "cn": cfg["cn"],
                "problem_type": cfg["problem_type"],
                "home_kind": cfg["home_kind"],
                "scene": rel_scene.as_posix(),
                "pages": ["page0", "page1", "page2"],
                "page_roles": {
                    "page0": "problem dashboard",
                    "page1": PAGE1_ROLES[cfg["home_kind"]],
                    "page2": PAGE2_ROLES[cfg["home_kind"]],
                },
                "serial_prefix_hex": f"23 {cfg['code']}",
                "primary_widgets": ordered_unique(
                    ["run", "tick", "sp0", "seq", *cfg["topic_widgets"], *PAGE1_WIDGETS[cfg["home_kind"]], *PAGE2_WIDGETS[cfg["home_kind"]]]
                ),
                "topic_widgets": cfg["topic_widgets"],
                "page1_widgets": PAGE1_WIDGETS[cfg["home_kind"]],
                "page2_widgets": PAGE2_WIDGETS[cfg["home_kind"]],
            }
        )
    write_json(OUT_ROOT / "template_index.json", index)


if __name__ == "__main__":
    main()
