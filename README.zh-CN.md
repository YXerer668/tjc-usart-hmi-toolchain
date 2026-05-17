# usarthmi 中文说明

`usarthmi` 是一个面向陶晶驰 / USART HMI 串口屏的实验性 Python 工具链。

这个项目最开始来自一块 `TJC8048X543_011C`、`800x480` 串口屏的实机逆向。目标不是“立刻完整替代官方 USART HMI 编辑器”，而是把常用流程逐步变成可脚本化、可测试、可复现的命令行工具：

1. 用 JSON/YAML 描述页面。
2. 在电脑端生成预览图。
3. 生成可检查的 `.HMI`。
4. 对已经恢复格式的控件，独立生成可烧录的 `.TFT`。
5. 通过串口上传到屏幕，并用 `sendme` / `get obj.attr` 做实机验证。

项目许可证是 MIT。代码和逆向说明可以公开使用；官方编辑器二进制、官方资源包、个人生成的 `.HMI` / `.TFT` / `.zi` 大文件不进入仓库。

## 当前定位

这是一个“证据驱动”的逆向工具链。一个功能如果被标成可用，至少应该有一种证据支撑：

- 官方 fixture 的字节对齐。
- TFT checksum 通过。
- 串口 `get` / `sendme` 读回正常。
- 摄像头或人工确认实机显示正常。
- 对应单元测试或回归测试。

所以文档里会很直接地区分：稳定可用、实验可用、只支持 authoring/预览、仅研究记录、尚未实现。

完整状态表见 [FEATURE_STATUS.md](FEATURE_STATUS.md)。

## 已经比较能用的部分

- 串口运行时命令：`connect`、`sendme`、`get`、`set`、`page`、`ref`、`vis`、`tsw`、`click`、`dim`。
- `.HMI` 检查和拆包：能读出容器项、`Program.s`、`0.pa`、页面对象和部分事件脚本。
- 场景文件：支持 JSON/YAML，能做布局求解和规范化输出。
- 预览器：能渲染 scene、`.HMI`、`.pa`，并且可以使用真实 `.zi` 字库显示中英文。
- 当前 `800x480` 种子工程的 page0 TFT 生成：支持追加/重建一批已经恢复的控件。
- 图片资源：支持 PNG/JPG 导入、TFT 图片资源打包、透明 PNG 展平、图片按钮两态资源。
- 字库：支持生成/替换 `.zi`；`tft build --font-zi` 可以在一次构建里同时替换
  `output.hmi` 和 `output.tft` 的安全字体槽，完整 GB2312 中文/英文小字库路线已经实机验证。
- 外部图片控件：推荐用健康的 `case_00_baseline` 资源布局，SD 卡路径如 `sd0/1.jpg` 已经实机验证。
- 动画控件：单个内部 GMOV 的 smoke 路线已经跑通；混合媒体还在研究。
- 多页实验：支持新增 page1 的普通控件/按钮事件，也支持用 `patch_seed_page0_widgets` 给 seed page0 里已有按钮补窄范围事件，便于做双页双向跳转探针。

## 已恢复或部分恢复的控件

当前工具链里已经有 fixture 或实机证据的控件包括：

- 文本、按钮、数字、图片、图片按钮。
- 进度条、滑块、仪表、二维码。
- 定时器、变量、双态按钮、状态按钮。
- 复选框、单选框、热点触摸区、触摸捕捉。
- 虚拟浮点数 `xfloat`、下拉框 `combobox`。
- 裁剪图、波形、滚动文本。
- 外部图片、单 GMOV 动画。

这些控件并不都等价于“全生态稳定支持”。很多控件目前是“当前 seed + 当前屏幕 + 当前 fixture”条件下可构建，换型号或换资源布局需要重新验证。

## 还没完全解决的部分

- 完整官方编辑器替代：还不能无损反编译/重建所有官方 `.HMI` 工程。
- 通用 TFT 编译器：目前主要服务 `TJC8048X543_011C`、`800x480`、当前种子工程。
- 页面重建：`examples/number_demo/full_page_rebuild_scene.json` 是最小 P1.6 实机闭环。它用 `drop_seed_objects` 删除 seed 对象 `t0/b0/p0`，重建 `page0/title/incbtn/numval`，并在完整 COM36 串口烧录后证明 `incbtn -> numval.val++` 事件仍然可用。最终视觉通过版本使用完整 GB2312 `UiCNEN32GBFull.zi` 和 `numval.lenth=3`；早先 UTF-8 稀疏字库版本串口可过但屏幕会显示错误字形。`examples/number_demo/reorder_broadening_scene.json` 只做离线结构拓宽，覆盖 `page0/status/incbtn/title/footer/numval` 的 text/button/number 重排；`examples/number_demo/event_matrix_scene.json` 只做离线事件保持矩阵，覆盖 clean rebuild 后的 `ref`、`vis`、`tsw` 和数值 `++` 字节码。这个结论还不能外推成“任意页面/任意控件都支持 full-page rebuild”。
- 事件调度：能编译/反解一小部分事件字节码；`ref obj` 已经通过 page0 场景 DSL、TFT 烧录、串口点击和摄像头遮盖重绘做过实机闭环。`examples/number_demo` 的 page0 `incbtn` 按下事件也已实机闭环：两次串口 `click incbtn,1` 把 `numval.val` 从 `123` 验到 `125`，并通过 `printh` 发出 `23 02 4e 31`。`examples/number_demo/tsw_promotion_scene.json` 也已烧录到 COM36，证据在 `examples/number_demo/tsw_promotion_serial_click_hardware_verified_2026-05-16.json`：它证明 clean rebuild 页面和 `disablebtn/enablebtn` 的 T0/T1 事件到达，但 `tsw targetbtn,0` 后串口 `click targetbtn,1` 仍会发出 TG；同一串口会话的 0/10/20/50/100/200 ms 快速时序扫描做了 18 次 critical 试验，全部先看到 T0 再看到 TG，所以这不是指令发太慢导致的串口 click 漏判。这仍只是 serial-click-path 的负结果，不是 physical touch-lockout 证明。page0 定时器 `codestimer-` 已经实机验证过运行时 `tm0.en=1` 后执行 `numval.val++`。page1 普通按钮事件已经实机验证过 `page 1` 跳页、显式十六进制 `printh`、同页一层 `click` 级联、数值字段 `++` / `=` / `--`，以及同页 `vis obj,0/1` 显示/隐藏操作。媒体事件 `wav0.vid=0`、`wav0.en=1`、`play 0,0,0` 已经有官方 fixture 字节对齐证据，但开机自动调度、实机 page-load / 通用调度还没完全闭环。
- 视频和音频资源调度：HMI/预览/记录结构已有，但独立 TFT 的资源 scheduler 还没彻底恢复。
- 官方“相同块跳过下载”：已经做过抓包和分析，但它在测试机上会把 Windows USB/PnP 搞成幽灵 COM，主线不再推荐。
- 文件浏览器、文件流、数据记录、选择文本、滑动文本等高级控件：有研究 case，但当前目标屏/官方编译会丢对象，暂不算完成；详见 [CURRENT_TARGET_LIMITATIONS.md](CURRENT_TARGET_LIMITATIONS.md)。

## 安装

```powershell
python -m pip install -e .
```

依赖写在 `pyproject.toml`，主要是：

- `pyserial`
- `Pillow`
- `PyYAML`

## 常用串口命令

```powershell
python -m usarthmi --json connect --port COM36 --baud 9600
python -m usarthmi --json sendme --port COM36 --baud 9600
python -m usarthmi --json get t0.txt --port COM36 --baud 9600
python -m usarthmi --json set t0.txt '"hello"' --port COM36 --baud 9600
python -m usarthmi --json dim 30 --port COM36 --baud 9600
```

烧录 TFT 建议使用全量串口上传，慢一点，但更稳：

```powershell
python -m usarthmi --json tft upload `
  --file output.tft `
  --port COM36 `
  --baud 9600 `
  --download-baud 921600 `
  --skip-if-current `
  --verify-after-upload `
  --verify-get t0.txt=nihao `
  --verify-get b0.txt=ceshi `
  --verify-step '{"command":"sendme","expected_kind":"page_id","expected_value":0}' `
  --verify-capture `
  --progress
```

成功上传后，CLI 会原子写入 `.usarthmi_last_upload.json`。下次带
`--skip-if-current` 上传时，会用候选 TFT 的 SHA256/大小，加上端口、
波特率和目标型号，对比这份“本工具上次成功上传”记录；匹配时会跳过运行时预检
和实际上传。注意它只代表本工具上次传过什么，不证明屏幕没有被 SD 卡、官方
下载器或另一台机器改过。

需要“烧完就验”时加 `--verify-after-upload`。它会在上传成功或
`--skip-if-current` 命中后重新跑串口健康检查，并按 `--verify-get`
读回对象属性；验证失败时命令返回非零，也不会把这次结果写成新的
known-current manifest。

如果烧完后还需要执行一串运行时动作，用可重复的 `--verify-step`。它可以接
裸命令，也可以接 JSON，例如 `{"command":"sendme","expected_kind":"page_id","expected_value":0}`。
常见读回/点击检查可以用更短的写法：`get numval.val => 124` 或
`click incbtn,1 => hex:23 02 4e 31`。媒体类验证可以先执行
`{"command":"wav0.en=1","expect_response":false}`，再用
`{"command":"get wav0.en","expected_kind":"number","expected_value":1}` 做读回确认。

如果视觉状态也要留证据，再加 `--verify-capture`。默认会用这台机器上更稳的
MSMF 摄像头路径，把照片存到 `reverse_usarthmi/upload_verify_captures/`。

## TSW 真实触摸证明

`examples/number_demo/tsw_promotion_scene.json` 已经有 isolated TSW PROMOTION
页面和串口 click 负结果。真实手指触摸不要再用临时监听脚本，直接跑：

```powershell
python tools\tsw_physical_touch_proof.py `
  --out reverse_usarthmi\number_demo_tsw_promotion_gb2312font_20260516\physical_touch_proof_live.json
```

这个 runner 会先弹出 `tools/wait_user_ack.ps1` 的置顶确认窗口。你点
“继续”后才会打开 COM36，并且会先确认当前页面 `title.txt` 是
`TSW PROMOTION`；错页面会直接退出，不会让你白按。屏幕标题会依次提示：

- `TAP TARGET`：按一次 TARGET，抓到 baseline TG 才继续。
- `TRY TARGET`：runner 已经执行 DISABLE，只在这个窗口里试按 TARGET。
- `TAP AGAIN`：runner 已经执行 ENABLE，再按一次 TARGET 验恢复。

成功条件很窄：baseline 有 TG、disabled 窗口没有 TG、恢复后有 TG，并且
T0/T1 状态 marker 都到达。退出码含义：

- `0`：完成并证明 `physical_touch_lockout_live_observed=true`。
- `1`：跑完但没有形成禁触证明。
- `2`：弹窗取消或超时，没有用户确认。
- `3`：baseline 没抓到 TG，未进入 disable 阶段。
- `4`：页面不是预期的 TSW PROMOTION。

只想检查流程而不碰串口，可以用：

```powershell
python tools\tsw_physical_touch_proof.py --dry-run
```

## 场景构建示例

只做预览：

```powershell
python -m usarthmi --json scene preview examples\menu_demo\scene.json --out preview.png
```

构建外部图片 demo：

```powershell
python -m usarthmi --json scene build examples\external_picture_demo\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft `
  --out reverse_usarthmi\external_picture_demo_build
```

构建媒体 authoring demo：

```powershell
python -m usarthmi --json scene build examples\media_widgets_demo\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --out reverse_usarthmi\media_widgets_demo_build
```

更多示例见 [SCENE_BUILDER.md](SCENE_BUILDER.md) 和 [examples/README.md](examples/README.md)。

## 本地参考仓库说明

开发机里可能会看到 `github_refs/`、`github_tjc_screen_for_codex/`、`external/` 这类目录。它们是逆向时用过的本地参考 clone 或第三方工具，不是主仓库的一部分。

当前 `.gitignore` 已经排除了这些目录，避免把外部仓库、官方资源、生成产物和大文件误提交进来。

## 开发建议

```powershell
python -m pytest -q
```

部分测试依赖本地 fixture，没有对应文件时会自动跳过。给项目加新控件时，最好同时补：

- 最小 scene 示例。
- 对应 fixture 或分析说明。
- 单元测试或字节对齐测试。
- 如果能烧录，补串口读回或摄像头验证记录。

## 风险提示

这是逆向项目，不是官方 SDK。生成的 TFT 在新型号、新分辨率、新资源布局上都应该先做小样例验证。实机烧录前建议先跑 `tft checksum`，并准备一个已知可恢复的 TFT。
