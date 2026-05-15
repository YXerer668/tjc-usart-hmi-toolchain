# Timer Numeric Probe

最小 timer 事件样例：`tm0` 每 500 ms 执行一次 `numval.val++`，用于验证
`codestimer-` 事件表、数字对象字段引用和运行时 timer 调度。

## Build

```powershell
python -m usarthmi --json scene build examples\timer_numeric_probe\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft `
  --out reverse_usarthmi\timer_numeric_probe\local_build
```

## Live Validation

2026-05-15 在 `COM36` / `TJC8048X543_011C` 上完成实机验证：

- `output.tft` checksum 有效：`0x36FCD131`。
- 串口全量上传成功：`11,412,496` bytes，`2787` chunks，约 `210.016 s`。
- 停止 timer 后清零，等待 1.4 s，`get numval.val` 返回 `0`。
- `set tm0.en 1` 后等待 1.8 s，`get numval.val` 返回 `4`。
- 再次 `set tm0.en 0` 后等待 1.2 s，`get numval.val` 仍返回 `4`。
- 额外 `page 0` 重载实验：页面重载后 `get tm0.en` 返回 `1`，但等待
  1.8 s 后 `get numval.val` 仍为 `0`。

当前结论：timer 的 `codestimer-` 事件和运行时调度已经实机闭环；但页面初始
`style.enabled: true` 只会恢复属性值，不等价于启动 scheduler。本样例验收时
应显式通过串口执行 `tm0.en=0 -> numval.val=0 -> tm0.en=1` 触发。
