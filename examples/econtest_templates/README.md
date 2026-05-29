# 电赛通用串口屏模板

这个目录提供 10 个面向电子设计竞赛题型的 `800x480` 串口屏模板。它们不是
简单换色皮肤，而是按题目类型调整三页信息架构、关键控件和串口对象名。每个模板都是 3 页结构：

- `page0`: 运行仪表盘，保留统一的运行态对象，首页控件按题型切换成电源流、波形、链路、路径、ROI 等。
- `page1`: 题型设置页，不同模板分别放限流保护、采样触发、波形合成、协议信道、PID 增益、运动曲线等专属控件。
- `page2`: 题型诊断页，不同模板分别放纹波/故障、捕获统计、BER、响应分析、编码器、记录报警、路径回放、识别结果等专属控件。

模板列表见 [`template_index.json`](template_index.json)。当前 10 个题型：

- `power_converter`: 电源与功率变换，突出输入/输出功率流、效率、保护状态。
- `measurement_scope`: 测量仪器，突出实时波形、量程、触发和测量结果。
- `signal_generator`: 信号源与波形，突出波形选择、频率/幅度/占空比和输出预览。
- `communication_link`: 通信链路，突出 TX/RX、RSSI/SNR、误码和配对。
- `pid_control`: 闭环控制，突出设定值、过程值、误差、输出和阶跃响应。
- `motor_drive`: 电机与运动控制，突出转速、方向、制动和驱动遥测。
- `sensor_daq`: 传感采集，突出多传感器网格、采样缓冲、存储和校准。
- `robot_task`: 机器人与小车，突出任务地图、路径、位姿和障碍距离。
- `vision_audio`: 图像与音频识别，突出 ROI、目标列表、置信度和延迟。
- `field_debug`: 综合调试，突出实时控制台、故障板、总线状态和 dump/reset。

## 使用

先做离线检查：

```powershell
python -m usarthmi --json scene check examples\econtest_templates\power_converter\scene.json --out-dir build\econtest_power_check --simulate-events
```

生成预览图：

```powershell
python -m usarthmi --json scene preview examples\econtest_templates\power_converter\scene.json --page page0 --out build\econtest_power_page0.png
```

生成全部模板的三页总览图：

```powershell
python tools\render_econtest_template_gallery.py --out-dir build\econtest_preview_gallery
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
- 每个模板的 `topic_widgets` 都出现在首页，避免退化成同质化 dashboard。
- 每个模板的 `page1_widgets` / `page2_widgets` 都出现在对应页面，保证第二、第三页不是共用壳。
- 每个模板的 `page_roles` 明确记录三页职责，且 `page1` 和 `page2` 职责不同。
- 每个模板的按钮、状态按钮、滑块、复选框等触控控件没有互相重叠。
- 每页对象数量、文本宽度、控件边界、底部导航位置和导航事件保持在 `800x480` 安全范围内。
