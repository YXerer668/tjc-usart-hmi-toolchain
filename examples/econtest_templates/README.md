# 电赛通用串口屏模板

这个目录提供 10 个面向电子设计竞赛的 `800x480` 串口屏模板。每个模板都是
3 页结构：

- `page0`: 运行仪表盘，带关键指标、进度条、仪表盘、启动/停止/动作按钮。
- `page1`: 参数页，带数值设定、复选项、滑块、保存/复位/应用按钮。
- `page2`: 日志/维护页，带滚动日志、波形区域、序号计数、二维码服务入口。

模板列表见 [`template_index.json`](template_index.json)。当前 10 个主题：

- `instrument_meter`: 仪器仪表
- `power_energy`: 电源能源
- `motor_motion`: 电机运动
- `robot_chassis`: 机器人底盘
- `communication_link`: 通信链路
- `sensor_fusion`: 传感融合
- `pid_tuning`: PID 调参
- `battery_bms`: 电池管理
- `vision_aiot`: 视觉识别
- `field_debug`: 现场调试

## 使用

先做离线检查：

```powershell
python -m usarthmi --json scene check examples\econtest_templates\power_energy\scene.json --out-dir build\econtest_power_check --simulate-events
```

生成预览图：

```powershell
python -m usarthmi --json scene preview examples\econtest_templates\power_energy\scene.json --page page0 --out build\econtest_power_page0.png
```

需要重新生成全部模板时：

```powershell
python tools\generate_econtest_templates.py
```

## MCU 通信约定

所有模板保留一组一致的对象名，便于单片机代码复用：

- `run`: 运行状态开关。
- `m0`..`m3`: 四个主指标数值。
- `main_gauge`: 主仪表盘。
- `main_bar`: 主进度条。
- `tick`: page0 timer 计数。
- `sp0`..`sp2`: 参数页设定值。
- `seq`: 日志页序号。
- `b_start` / `b_stop` / `b_cmd`: page0 主动作按钮。
- `b_save` / `b_rst` / `b_apply`: 参数页操作按钮。

按钮事件会发出 `printh 23 XX ...` 形式的 marker。`template_index.json` 里的
`serial_prefix_hex` 给出每个模板的 `23 XX` 前缀，便于 MCU 或上位机区分主题。

MCU 侧通用 C 封装在 [`../../firmware/usarthmi_serial`](../../firmware/usarthmi_serial)。

## 质量门禁

`tests/test_econtest_templates.py` 会验证：

- 索引中正好有 10 个模板。
- 每个模板都是 `page0/page1/page2` 三页。
- 每个模板能通过 `scene check --simulate-events`。
- 每个模板的按钮、状态按钮、滑块、复选框等触控控件没有互相重叠。
