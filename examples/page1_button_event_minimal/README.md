# Page1 按钮事件最小样例

这是目前多页面事件 authoring 里最小、最窄的一条可测路径：

- `page0` 故意保持 seed 工程的对象布局不变。
- `page1` 只新增普通文本和普通按钮。
- `back0.events.up = ["page 1"]` 会编译成“松开按钮后跳回 seed page0”。
- 必须显式打开 `project.experimental_multi_page_events = true`，因为事件调度仍然算实验能力。

注意：当前恢复出的 case31 多页布局里，运行时页号和 `.pa` 文件顺序是反直觉的：

- `page 0` / `sendme = 0` 对应新增的 `1.pa` / `page1`。
- `page 1` / `sendme = 1` 对应 seed 的 `0.pa` / `page0`。

所以这个 BACK 按钮要写 `page 1`，而不是直觉上的 `page 0`。

编辑器校验和 TFT patcher 现在接受同一组窄范围跳页写法：

- `page 0`
- `page 1`
- `page page0`
- `page page1`

构建示例：

```powershell
.\usarthmi.cmd scene build .\examples\page1_button_event_minimal\scene.json --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft --out build\page1_button_event_minimal
```
