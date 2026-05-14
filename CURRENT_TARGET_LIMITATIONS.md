# 当前目标屏限制记录

本仓库当前主线目标是 `TJC8048X543_011C` / `800x480` / 现有 seed 工程。

有些官方控件在其他型号或官方 wiki 示例里存在，但放进当前目标屏工程后，官方 `USART HMI` 编译器会静默丢弃对象。因此这些控件暂时不进入独立 TFT writer 的实现队列，除非后续拿到“当前型号也会生成对象”的官方对照。

## 已确认会被当前目标丢弃的控件

| 控件 | 场景别名 | HMI type | 证据 case | 当前处理 |
| --- | --- | --- | --- | --- |
| 选择文本 / TextSelect | `text-select` | `D` | `case_38_text_select` | scene 直接报 unsupported |
| 滑动文本 / SLText | `sliding-text`, `sltext` | `>` | `case_41_sltext` | scene 直接报 unsupported |
| 数据记录 / DataRecord | `data-record` | `B` | `case_42_datarecord` | scene 直接报 unsupported |
| 文件浏览器 / FileBrowser | `file-browser` | `A` | `case_43_filebrowser` | scene 直接报 unsupported |
| 文件流 / FileStream | `file-stream` | `?` | `case_44_filestream` | scene 直接报 unsupported |

这些 case 的共同现象是：

- `.HMI` 里能看到被 graft 的对象。
- 官方 GUI 打开后底部状态栏确认是 `Model:TJC8048X543_011  inch:4.3(800X480)`，不是未改型号的 `TJC8048X550_011`。
- 官方编译能完成，通常没有错误，输出仍显示 `页面:page0 占用内存:16+340=356`。
- 生成 `.TFT` 的对象数仍等于原始 seed 对象数。
- 在 `.TFT` object tail 中找不到对应对象名、type/id header 或关键 payload。

2026-05-14 复查证据保存在本机 `C:\Users\SinYu\Desktop\case_for_codex\case_*/official_gui_model_recheck\`：

- `01_opened_model_status.png`：官方 GUI 打开工程时的全窗口截图。
- `01_opened_model_status_bottom_status.png`：底部型号状态栏裁剪图。
- `02_after_compile.png`：官方编译后的全窗口截图。
- `lcd_test.official_recheck.json`：编译输出、run.run 路径和大小记录。

这次复查的意义是排除了“只是官方例程没改板子型号”的主要误判路径。

## 容易混淆的名字

- `scrolling-text` 是已经有 fixture 的滚动文本，对应 `case_22`。
- `sltext` / `sliding-text` 是另一类滑动文本，对应 `case_41`，当前目标屏不生成 TFT 对象。

所以工具链不会把 `sltext` 自动当成 `scrolling-text`，而是明确报错，避免生成看似成功但语义错误的页面。
