# 事件 demo 状态

这个场景是“事件字节码探针”，用于拆分 page 事件和 object 事件的调度问题。

- `page0.events.load` 会生成 `printh 23 02 50 01` 探针。
- `evtbtn.events.up` 会生成 `printh 23 02 54 45` 探针。
- 2026-05-15 在 `COM36 / TJC8048X543_011C` 活屏验证：
  - `click evtbtn,0` 两次均返回 `23 02 54 45`，按钮 up 事件调度有效。
  - `page 0` 和 `rest` 重启后均未返回 `23 02 50 01`，page load 事件调度仍未恢复。
- 当前结论：object/button 事件链是可用的；page-load 缺口不是 page1 特有问题，单页 page0 也未触发。

构建示例：

```powershell
.\usarthmi.cmd scene build .\examples\event_demo\scene.json --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft --out build\event_demo
```
