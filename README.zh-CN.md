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
- 字库：支持生成/替换 `.zi`，完整 GB2312 中文/英文小字库路线已经实机验证。
- 外部图片控件：推荐用健康的 `case_00_baseline` 资源布局，SD 卡路径如 `sd0/1.jpg` 已经实机验证。
- 动画控件：单个内部 GMOV 的 smoke 路线已经跑通；混合媒体还在研究。

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
- 事件调度：能编译/反解一小部分事件字节码；page1 普通按钮事件已经实机验证过 `page 1` 跳页、显式十六进制 `printh`、同页一层 `click` 级联、数值字段 `++` / `=` / `--`，以及同页 `vis obj,0/1` 显示/隐藏操作。媒体事件 `wav0.vid=0`、`wav0.en=1`、`play 0,0,0` 已经有官方 fixture 字节对齐证据，但实机 page-load / 通用调度还没完全闭环。
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
  --progress
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
