# 场景样例索引

这些样例都走 `usarthmi scene build` / `usarthmi tft build` 这条独立构建链，不需要打开官方 GUI。

## 推荐入口

- `menu_demo`: 最基础的菜单页样例，适合验证文字、图片、按钮、数值区和预览器。
- `external_picture_demo`: 外部图片控件的默认活屏样例，已经在当前 `TJC8048X543_011C` 上验证过 `sendme`、`get exp0.path`、`get guard.txt` 和摄像头显示。
- `media_single_gmov_smoke`: 当前推荐的动画控件最小烧录样例，只验证一个内部 GMOV，边界最稳。
- `media_single_video_sd_smoke`: 单个 SD 视频控件的最小烧录样例，验证 video 对象 tail 和运行时可读字段；不承诺所有视频编码都能播放。
- `media_single_audio_sd_smoke`: 单个 SD 音频控件的最小烧录样例，验证 wav/audio 对象 tail 和运行时可读字段；不承诺扬声器/音量链路。
- `media_widgets_demo`: 动画、视频、音频控件的第一版 authoring 样例，目前主要承诺 HMI/预览；视频和音频还不作为独立 TFT 烧录路径。
- `page1_button_event_minimal`: page1 普通按钮跳回 page0 的最小事件样例，需要显式打开 `experimental_multi_page_events`。
- `page1_button_numeric_event_minimal`: page1 普通按钮执行 `numval.val++` 的最小数字事件样例，已经活屏验证。
- `page1_button_numeric_event_matrix`: page1 多按钮数字事件矩阵，覆盖 `++`、`=7`、`--`，已经活屏验证。
- `page1_button_printh_event_probe`: page1 普通按钮 `printh` 探针事件样例，只放行显式十六进制字节列表。
- `page1_button_click_event_probe`: page1 普通按钮 `click` 级联探针样例，只放行同页按钮到 `printh` 目标的一层级联。
- `page1_load_printh_event_probe`: page1 页面加载 `printh` 探针事件样例，只放行固定 4 字节十六进制 payload；当前已能编译和烧录，但活屏切页未观察到 probe 输出。
- `event_demo`: 单页 `page0.load` 与按钮 `up` 的分离探针；2026-05-15 活屏确认按钮 `up printh` 有效，但 `page0.load` 在 `page 0` 和 `rest` 后均未触发。
- `all_controls_demo`: 已恢复控件的集合展示页，适合做大范围冒烟测试。

## 当前稳定边界

这套 examples 默认服务“独立构建链”，不是官方 GUI 自动化。能烧录的样例应该满足：

- 明确提供 `--baseline-tft`。
- 生成的 `manifest.json` 里有 `output_tft`。
- `tft checksum` 通过。
- 活屏测试至少能跑 `sendme` 和关键 `get obj.attr`。

如果一个样例只生成 `output.hmi` 和 preview，那它就是 authoring/逆向样例，不应该直接当作稳定烧录入口。动画控件目前优先用 `media_single_gmov_smoke`，SD 视频对象最小验证用 `media_single_video_sd_smoke`，SD 音频对象最小验证用 `media_single_audio_sd_smoke`；不要把视频、音频和 GMOV 混在同一个 live TFT 里赌运气。

为了稳定，当前不推荐追官方“相同块跳过下载”的 smart download。全量串口上传慢一点，但行为更可控，也更适合开源用户复现。

## 外部图片样例

`external_picture_demo` 固定引用 SD 卡路径 `sd0/1.jpg`，建议使用当前健康的官方基线：

```powershell
python -m usarthmi --json scene build examples\external_picture_demo\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft `
  --out reverse_usarthmi\external_picture_demo_build
```

更省心的入口是 demo runner，默认只构建和校验，不碰串口：

```powershell
python tools\external_picture_demo_runner.py
```

如果屏幕上已经是这个 TFT，可以加 `--smoke --capture` 做串口和摄像头验收；如果要先烧录，再额外加 `--upload --progress`。

`case_46_expicture_current_gui` 只作为外部图片对象尾部结构 fixture 使用，不作为推荐烧录基线。它的紧凑资源/header 布局会让当前屏幕进入异常的短 `sendme` 返回。

验收时优先看这三件事：

- `sendme` 返回 page `0`。
- `get exp0.path` 返回 `sd0/1.jpg`。
- 摄像头能看到左侧外部图片区域和右侧 `guard.txt ok`。

如果屏幕上已经是这个 TFT，可以直接跑串口冒烟测试，不需要重新烧录：

```powershell
python tools\live_tft_smoke.py `
  --file reverse_usarthmi\external_picture_demo_build\output.tft `
  --out-dir reverse_usarthmi\external_picture_demo_build\smoke `
  --expect-json examples\external_picture_demo\smoke.expect.json
```

要把拍屏也并进同一次 smoke，直接加 `--capture`。默认会走固定的
DirectShow `USB Cam`，不再依赖容易漂移的 OpenCV 默认索引：

```powershell
python tools\live_tft_smoke.py `
  --file reverse_usarthmi\external_picture_demo_build\output.tft `
  --out-dir reverse_usarthmi\external_picture_demo_build\smoke_capture `
  --expect-json examples\external_picture_demo\smoke.expect.json `
  --capture
```
