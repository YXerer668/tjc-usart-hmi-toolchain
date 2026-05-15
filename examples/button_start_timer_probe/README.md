# Button Start Timer Probe

验证普通按钮事件中的 assignment 能不能启动 timer scheduler。

- `tm0` 初始 `enabled=false`，`codestimer-` 执行 `numval.val++`。
- `start0.up` 执行三行：`tm0.en=0`、`numval.val=0`、`tm0.en=1`。
- `stop0.up` 执行：`tm0.en=0`。

如果 `click start0,1` 后 `numval.val` 增长，说明按钮事件里的
`tm0.en=1` 和串口运行时 `set tm0.en 1` 一样能启动 scheduler；之后再研究
page load/unload 才更有底气。

2026-05-15 实机结论：已在 `COM36` / `TJC8048X543_011C` 上闭环。

- `output.tft` checksum 有效：`0xE6349E42`。
- 串口全量上传成功：`11,413,824` bytes，`2787` chunks，约 `210.36 s`。
- 初始 `get tm0.en` 为 `0`，`get numval.val` 为 `0`。
- `click start0,0` 后等待 1.8 s，`get numval.val` 返回 `4`。
- `click stop0,0` 后等待 1.2 s，`get numval.val` 仍返回 `4`。

因此按钮事件里的 `tm0.en=1` assignment 已经确认能启动 timer scheduler。
page-load/page-unload 失败不应再归因于 assignment 编译路径本身，而应继续查
lifecycle scheduler 入口、callback slot 或特殊 flag。

## Build

```powershell
python -m usarthmi --json scene build examples\button_start_timer_probe\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft `
  --out reverse_usarthmi\button_start_timer_probe\local_build
```
