# Multi Page Two-Way Jump Probe

最小双页双向跳转样例，用来验证 scene builder 可以同时生成：

- seed `page0` 上已有按钮 `b0` 的事件补丁；
- 新增 `page1` 上普通按钮 `back0` 的事件；
- 两个按钮通过对象事件 callback 执行跨页跳转。

当前恢复出的两页 TFT 布局里运行时页号和 `.pa` 顺序是反直觉的：

- runtime `page 0` 对应新增 `1.pa` / scene `page1`。
- runtime `page 1` 对应 seed `0.pa` / scene `page0`。

因此：

- seed `page0.b0.up = ["page 0"]`：从 seed page0 跳到新增 page1。
- generated `page1.back0.up = ["page 1"]`：从新增 page1 跳回 seed page0。

这个样例需要显式打开：

- `project.experimental_multi_page_events = true`
- `project.patch_seed_page0_widgets = true`

`patch_seed_page0_widgets` 只补丁 seed page0 里已经存在的普通按钮，不新增
page0 对象。第一版要求补丁 widget 仍提供 `x/y/w/h`，这样 preview 和实际补丁
能保持同一份 scene 表达。

2026-05-15 实机结论：已在 `COM36` / `TJC8048X543_011C` 上闭环。

- `output.tft` checksum 有效：`0xFAF23FD8`。
- 串口全量上传成功：`11,411,800` bytes，`2787` chunks，约 `209.578 s`。
- 初始 `sendme` 为 `0`，`get p1title.txt` 返回 `PAGE1 GENERATED`。
- 执行 `page 1` 后 `sendme` 为 `1`。
- 在 runtime page `1` 执行 `click b0,0` 后，`sendme` 变为 `0`。
- 在 runtime page `0` 执行 `click back0,0` 后，`sendme` 变回 `1`。
- 负例 `click missing0,0` 返回 `02 FF FF FF`，页面保持 runtime `1`，排除了“任意 click 都会跳页”的错觉。

注意：runtime page `1` 上 `get b0.txt` 返回 `1A`，但 `click b0,0` 仍能触发
补丁后的事件。后续如果要把 seed 页对象读回也做漂亮，需要继续查多页 hash/name
readback 细节；目前双向跳转事件本身已经活屏证明。

## Build

```powershell
python -m usarthmi --json scene build examples\multi_page_two_way_jump_probe\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft `
  --out reverse_usarthmi\multi_page_two_way_jump_probe\local_build
```
