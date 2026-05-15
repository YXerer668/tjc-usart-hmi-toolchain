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

事件调度差分探针：

```powershell
python tools\page_event_oracle_probe.py `
  --hmi reverse_usarthmi\event_demo_live_probe_20260515\output.hmi `
  --tft reverse_usarthmi\event_demo_live_probe_20260515\output.tft `
  --out reverse_usarthmi\event_demo_live_probe_20260515\page_event_oracle_probe_2026-05-15.json
```

这个探针会列出 HMI 事件表在 TFT object region 中的位置、`slot_0x0c/0x10/0x14` 回调候选、以及 `event_offset_0x34`。当前失败样例的关键形态是：`page0` 的 `event_offset_0x34` 指向 page-load event table，但没有 callback slot；`evtbtn` 的 `slot_0x10` 指向按钮 up 事件 item，所以按钮事件能跑。

2026-05-15 的 oracle 增强：

- 官方 audio wiki 编译产物 `case_49_audio/official_compile/source_raw.run` 被识别为 `post_primary_page_event` 路径：page-load `volume=100` 不在普通 page event table，而是位于 primary records 后面的 `09 1f 04 35 ... 09 30 08` chunk。
- datarecord wiki 样本现在会 fail-soft：遇到未知控件 type `B` 或暂不支持的 `repo primaryKey.val,0` 行时，报告会保留 `compile_context.error` / `event_table_error`，而不是整份 oracle 失败。
- `tools/page_event_oracle_batch.py` 可以批量扫描 `case_for_codex` 并自动配对邻近 `TFT/run`：当前扫到 4 个 page-event HMI，其中只有 `case_49_audio` 是完整 `post_primary_page_event` oracle，datarecord/filebrowser/filestream 都还属于 incomplete oracle。
- 因此当前策略仍然是：普通 page-load callback 猜测不烧录；先用官方 oracle 证明单字段绑定，再生成单变量候选。

批量扫描示例：

```powershell
python tools\page_event_oracle_batch.py C:\Users\SinYu\Desktop\case_for_codex `
  --out reverse_usarthmi\page_lifecycle_oracle_scan_20260515\batch_page_event_oracles.json `
  --compact
```
