# 事件 demo 状态

这个场景是“事件字节码探针”，不是已经完整实机闭环的 UI baseline。

- `page0.events.load` 会生成 `printh 23 02 50 01` 探针。
- `evtbtn.events.up` 会生成 `printh 23 02 54 45` 探针。
- 当前编译器可以把这些事件字节码写进 TFT 对应区域。
- 但屏端运行时调度还没完全啃完，所以这个 demo 主要用于检查字节和继续逆向，不要先当成稳定交互控件用。

构建示例：

```powershell
.\usarthmi.cmd scene build .\examples\event_demo\scene.json --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft --out build\event_demo
```
