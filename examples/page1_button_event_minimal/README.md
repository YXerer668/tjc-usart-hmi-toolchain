# Page1 按钮事件最小样例

这是目前多页面事件 authoring 里最小、最窄的一条可测路径：

- `page0` 故意保持 seed 工程的对象布局不变。
- `page1` 只新增普通文本和普通按钮。
- `back0.events.up = ["page 0"]` 会编译成“松开按钮后跳回 page0”。
- 必须显式打开 `project.experimental_multi_page_events = true`，因为事件调度仍然算实验能力。

编辑器校验和 TFT patcher 现在接受同一组窄范围跳页写法：

- `page 0`
- `page 1`
- `page page0`
- `page page1`

构建示例：

```powershell
.\usarthmi.cmd scene build .\examples\page1_button_event_minimal\scene.json --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft --out build\page1_button_event_minimal
```
